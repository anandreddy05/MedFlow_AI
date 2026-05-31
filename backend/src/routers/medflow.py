from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    BackgroundTasks,
)
from passlib.context import CryptContext
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
import uuid
from pathlib import Path
import shutil
from datetime import datetime, timezone
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import tempfile
import os
from fastapi import UploadFile, File
from openai import OpenAI
import base64

from src.models import (
    User,
    Patient,
    AuditLog,
    MedicalDocument,
    Base,
    DoctorPatientAssignment,
)
from src.database import SessionLocal
from src.ingestion.schemas import (
    ApproveReportRequest,
    DirectPrescriptionPayload,
    ChatMessage,
    ChatRequest,
)
from src.ingestion.extractor import BaseExtractor
from starlette import status
from .auth import get_current_user
from src.rag.vectorstore import QdrantVectorStore
from src.rag.retriever import MedicalRetriever
from qdrant_client import QdrantClient
from src.rag.embedder import MedicalEmbedder

from src.guardrails.input_router import InputGuard
from src.guardrails.output_auditor import OutputGuard

load_dotenv(override=True)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# backend/src/routers/medflow.py

extractor = BaseExtractor()

print("Booting up Shared AI Resources...")
shared_qdrant_client = QdrantClient(path="storage/qdrant_db")
shared_embedder = MedicalEmbedder()

vector_store = QdrantVectorStore(client=shared_qdrant_client, embedder=shared_embedder)
retriever = MedicalRetriever(client=shared_qdrant_client, embedder=shared_embedder)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/registration/create-patient")
async def register_new_patient(
    user: user_dependency,
    db: db_dependency,
    full_name: str,
    date_of_birth: str,
    gender: str,
    phone: str,
    email: str,
    assigned_doctor_id: int,  # ← NEW: Assign doctor immediately
    department: str = "General OPD",
    password: str = None,
):
    """
    Hospital registration desk creates new patient account.
    Assigns to a specific doctor at registration time.
    """
    if user.get("role") not in ["registration", "admin"]:
        raise HTTPException(403, "Registration desk only")

    # Verify the doctor exists
    doctor = (
        db.query(User)
        .filter(User.id == assigned_doctor_id, User.role == "doctor")
        .first()
    )

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    import random
    import string

    year = datetime.now().year
    random_digits = "".join(random.choices(string.digits, k=8))
    mrn = f"MRN{year}{random_digits}"

    # Generate temporary password
    temp_password = password or "".join(
        random.choices(string.ascii_letters + string.digits, k=10)
    )

    # Create User account
    new_user = User(
        email=email,
        full_name=full_name,
        hashed_password=bcrypt_context.hash(temp_password),
        role="patient",
        is_active=True,
        must_change_password=True,
    )
    db.add(new_user)
    db.flush()

    # Create Patient profile
    patient = Patient(
        patient_id=mrn, user_id=new_user.id, date_of_birth=date_of_birth, gender=gender
    )
    db.add(patient)
    db.flush()

    # Assign doctor to patient
    assignment = DoctorPatientAssignment(
        doctor_id=assigned_doctor_id, patient_id=mrn, is_primary=True, status="active"
    )
    db.add(assignment)
    db.commit()

    # Generate OP ticket with doctor info
    op_ticket = {
        "op_number": f"OP-{datetime.now().strftime('%Y%m%d')}-{random_digits[:4]}",
        "patient_name": full_name,
        "mrn": mrn,
        "assigned_doctor": doctor.full_name,
        "department": department,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
    }

    return {
        "message": "Patient registered and assigned to doctor",
        "mrn": mrn,
        "email": email,
        "temporary_password": temp_password,
        "assigned_doctor": doctor.full_name,
        "op_ticket": op_ticket,
    }


@router.get("/doctor/my-patients")
async def get_my_patients(
    user: user_dependency, db: db_dependency, skip: int = 0, limit: int = 50
):
    """Doctor sees ONLY patients assigned to them"""
    if user.get("role") != "doctor":
        raise HTTPException(403, "Doctors only")

    # Get all patients assigned to this doctor
    assignments = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.doctor_id == user.get("id"),
            DoctorPatientAssignment.status == "active",
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    patients = []
    for assignment in assignments:
        patient = (
            db.query(Patient)
            .filter(Patient.patient_id == assignment.patient_id)
            .first()
        )

        if patient:
            # Get recent documents
            recent_docs = (
                db.query(MedicalDocument)
                .filter(
                    MedicalDocument.patient_id == patient.patient_id,
                    MedicalDocument.approval_status == "approved",
                )
                .order_by(MedicalDocument.created_at.desc())
                .limit(5)
                .all()
            )

            patients.append(
                {
                    "patient_id": patient.patient_id,
                    "full_name": patient.user.full_name,
                    "date_of_birth": patient.date_of_birth,
                    "gender": patient.gender,
                    "assigned_at": assignment.assigned_at,
                    "recent_documents": len(recent_docs),
                    "last_visit": recent_docs[0].created_at if recent_docs else None,
                }
            )

    return {
        "doctor_name": user.get("username"),
        "total_patients": len(patients),
        "patients": patients,
    }


@router.get("/doctor/patient/{patient_id}/full-history")
async def get_patient_full_history(
    user: user_dependency, db: db_dependency, patient_id: str
):
    """Doctor views complete history of THEIR patient only"""
    if user.get("role") != "doctor":
        raise HTTPException(403, "Doctors only")

    # Verify this patient is assigned to this doctor
    assignment = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.doctor_id == user.get("id"),
            DoctorPatientAssignment.patient_id == patient_id,
            DoctorPatientAssignment.status == "active",
        )
        .first()
    )

    if not assignment:
        raise HTTPException(403, "This patient is not assigned to you")

    # Get all approved documents for this patient
    documents = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.patient_id == patient_id,
            MedicalDocument.approval_status == "approved",
        )
        .order_by(MedicalDocument.created_at.desc())
        .all()
    )

    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()

    return {
        "patient": {
            "patient_id": patient_id,
            "full_name": patient.user.full_name,
            "date_of_birth": patient.date_of_birth,
            "gender": patient.gender,
        },
        "documents": [
            {
                "document_id": doc.document_id,
                "report_type": doc.report_type,
                "data": doc.extracted_data,
                "created_at": doc.created_at,
            }
            for doc in documents
        ],
        "total_documents": len(documents),
    }


@router.post("/doctor/transfer-patient")
async def transfer_patient(
    user: user_dependency,
    db: db_dependency,
    patient_id: str,
    new_doctor_id: int,
    reason: str = "Transfer",
):
    """Transfer patient to another doctor"""
    if user.get("role") not in ["doctor", "admin"]:
        raise HTTPException(403, "Not authorized")

    # Find current active assignment
    current_assignment = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.patient_id == patient_id,
            DoctorPatientAssignment.status == "active",
        )
        .first()
    )

    if not current_assignment:
        raise HTTPException(404, "No active assignment found")

    # Mark current as inactive
    current_assignment.status = "transferred"
    current_assignment.assigned_at = datetime.now(timezone.utc)

    # Create new assignment
    new_assignment = DoctorPatientAssignment(
        doctor_id=new_doctor_id, patient_id=patient_id, is_primary=True, status="active"
    )
    db.add(new_assignment)

    # Log the transfer
    audit_log = AuditLog(
        user_id=user.get("id"),
        action="TRANSFER_PATIENT",
        document_id=f"patient_{patient_id}_to_doctor_{new_doctor_id}",
    )
    db.add(audit_log)
    db.commit()

    return {
        "message": f"Patient transferred successfully",
        "patient_id": patient_id,
        "from_doctor": current_assignment.doctor_id,
        "to_doctor": new_doctor_id,
    }

@router.post("/doctor/transcribe")
async def transcribe_medical_dictation(
    user: user_dependency, audio: UploadFile = File(...)
):
    """ Voice to text dictation for doctors (Digital Prescription)"""
    if user.get("role") != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can use medical dictation."
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(await audio.read())
        temp_audio_path = temp_audio.name
    
    try:
        client = OpenAI(base_url="https://us.api.openai.com/v1")
        with open(temp_audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model='whisper-1',
                file=audio_file,
                prompt = "Medical dictation. Patient notes, clinical instructions, dosages like mg, ml, and frequencies like BID, TID, OD.",
            )
            return {"transcription": transcription.text}
        
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

@router.post("/upload")
async def upload_medical_report(
    user: user_dependency,
    db: db_dependency,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    report_type: str = Form(...),
):
    role = user.get("role")
    allowed_upload = ["nurse", "admin", "doctor", "finance"]
    if role not in allowed_upload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to upload reports.",
        )
    if role == "finance" and report_type != "medical_invoice":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Finance can only upload medical invoices.",
        )
    if role in ["doctor", "nurse"] and report_type == "medical_invoice":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinical staff cannot upload financial documents.",
        )
    try:
        # Save file
        document_id = f"{patient_id}_{report_type}_{uuid.uuid4().hex[:8]}"
        save_path = UPLOAD_DIR / f"{document_id}{Path(file.filename).suffix}"

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract to markdown ONLY
        extractor = BaseExtractor().get_extractor(report_type)
        result = extractor.process_document(file_path=str(save_path))

        structured_data = result.get("structured_report", {})
        markdown_content = result.get("markdown", "")

        # Save to database
        new_document = MedicalDocument(
            document_id=document_id,
            patient_id=patient_id,
            uploaded_by=user.get("id"),
            report_type=report_type,
            original_file_path=str(save_path),
            content_markdown=markdown_content,
            extracted_data=structured_data,
            approval_status="pending",
        )

        db.add(new_document)
        db.commit()

        return {
            "message": "Document uploaded successfully",
            "document_id": document_id,
            "approval_status": "pending",
        }
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)}
        )


@router.get("/documents/{document_id}/file")
async def get_document_file(document_id: str, user: user_dependency, db: db_dependency):
    """Serve original uploaded file for nurse/clinical review."""
    role = user.get("role")
    if role not in ["nurse", "doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view document files.",
        )

    document = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.document_id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = document.original_file_path
    if file_path and Path(file_path).is_file():
        return FileResponse(path=file_path, filename=Path(file_path).name)

    matches = list(UPLOAD_DIR.glob(f"{document_id}*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Original file not found on disk.")

    target = matches[0]
    return FileResponse(path=str(target), filename=target.name)


@router.get("/reports/pending")
async def get_pending_reports(user: user_dependency, db: db_dependency):
    """
    Fetch all pending reports..
    """
    role = user.get("role")
    if role != "nurse":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to review reports.",
        )
    try:
        pending_reports = (
            db.query(MedicalDocument)
            .filter(MedicalDocument.approval_status == "pending")
            .all()
        )
        if not pending_reports:
            return {"message": "No pending reports found.", "pending_reports": []}
        serialized_reports = []
        for report in pending_reports:
            serialized_reports.append(
                {
                    "document_id": report.document_id,
                    "patient_id": report.patient_id,
                    "uploaded_by": report.uploaded_by,
                    "report_type": report.report_type,
                    "extracted_data": report.extracted_data,
                    "content_markdown": report.content_markdown,
                    "has_original_file": bool(report.original_file_path),
                    "created_at": report.created_at.isoformat()
                    if report.created_at
                    else None,
                }
            )

        return {
            "pending_reports": serialized_reports,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/approve")
async def approve_report(
    user: user_dependency,
    db: db_dependency,
    request: ApproveReportRequest,
    background_tasks: BackgroundTasks,
):
    """
    Nurse reviews all pending files and corrects them before feeding them to the db
    """
    role = user.get("role")
    if role != "nurse":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to approve reports.",
        )
    try:
        document = (
            db.query(MedicalDocument)
            .filter(MedicalDocument.document_id == request.document_id)
            .first()
        )

        if not document:
            raise HTTPException(status_code=404, detail="Pending report not found.")

        if document.approval_status == "approved":  # type: ignore
            raise HTTPException(status_code=400, detail="Report is already approved.")

        document.extracted_data = request.corrected_report  # type: ignore
        document.approval_status = "approved"  # type: ignore
        document.reviewed_by = user.get("id")  # type: ignore
        document.reviewed_at = datetime.now(timezone.utc)  # type: ignore

        validated_text_parts = [f"## Validated Report: {document.report_type.upper()}"]
        if isinstance(request.corrected_report, dict):
            for key, value in request.corrected_report.items():
                # Format lists (like medications or line items) properly
                if isinstance(value, list):
                    validated_text_parts.append(f"### {key.replace('_', ' ').title()}")
                    for item in value:
                        validated_text_parts.append(f"- {item}")
                else:
                    validated_text_parts.append(
                        f"**{key.replace('_', ' ').title()}**: {value}"
                    )

        # Overwrite the flawed original markdown with the perfect, validated text
        document.content_markdown = "\n\n".join(validated_text_parts)
        audit_log = AuditLog(
            user_id=user.get("id"),
            action=f"APPROVED_REPORT_{document.report_type.upper()}",
            document_id=document.document_id,
        )
        db.add(audit_log)
        db.commit()

        if str(document.content_markdown):
            background_tasks.add_task(
                vector_store.ingest_docs,
                document_id=str(document.document_id),
                patient_id=str(document.patient_id),
                report_type=str(document.report_type),
                markdown_text=str(document.content_markdown),
                role=str(user.get("role")),
                created_at=document.created_at,
            )

        return {
            "message": "Report approved and successfully logged.",
            "document_id": document.document_id,
            "approval_status": "approved",
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()  # Protect the DB from partial, corrupted writes
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prescriptions/direct")
async def create_direct_prescription(
    user: user_dependency,
    db: db_dependency,
    payload: DirectPrescriptionPayload,
    background_tasks: BackgroundTasks,
):
    """Doctor writes prescription - ONLY for their assigned patients"""

    # FIRST: Check role
    if user.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only doctors can write prescriptions.",
        )

    # SECOND: Verify doctor ID matches token
    if str(payload.doctor_id) != str(user.get("id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Payload doctor_id does not match the authenticated user.",
        )

    # THIRD: Verify this patient is assigned to this doctor
    assignment = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.doctor_id == user.get("id"),
            DoctorPatientAssignment.patient_id == payload.patient_id,
            DoctorPatientAssignment.status == "active",
        )
        .first()
    )

    if not assignment:
        raise HTTPException(403, "This patient is not assigned to you")

    role = user.get("role")
    if role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to upload reports.",
        )
    if str(payload.doctor_id) != str(user.get("id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Payload doctor_id does not match the authenticated user.",
        )
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{payload.patient_id}_digital_prescription_{timestamp}_{uuid.uuid4().hex[:8]}"
        markdown_text = f"## Clinical Instructions\n{payload.instructions}\n\n## Prescribed Medications\n"
        for med in payload.medications:
            markdown_text += f"- **{med.medicine_name}**: {med.dosage} ({med.timing}, {med.food_instruction}, {med.frequency})\n"
        clinical_data = {
            "clinical_notes": payload.instructions,
            "medications": [med.model_dump() for med in payload.medications],
        }

        # Save to Database using the validated ID
        new_document = MedicalDocument(
            document_id=document_id,
            patient_id=payload.patient_id,
            uploaded_by=user.get("id"),  # Always trust the token over the payload
            report_type="digital_prescription",
            original_file_path="direct_entry",
            extracted_data=clinical_data,
            content_markdown=markdown_text,
            approval_status="approved",
            reviewed_by=user.get("id"),
            reviewed_at=datetime.now(timezone.utc),
        )
        db.add(new_document)
        audit_log = AuditLog(
            user_id=user.get("id"),
            action="DIRECT_ENTRY_PRESCRIPTION",
            document_id=document_id,
        )
        db.add(audit_log)
        db.commit()

        if clinical_data.get("clinical_notes"):
            background_tasks.add_task(
                vector_store.ingest_docs,
                document_id=str(new_document.document_id),
                patient_id=str(new_document.patient_id),
                report_type=str(new_document.report_type),
                markdown_text=str(new_document.content_markdown),
                role=str(user.get("role")),
            )

        return {
            "message": "Prescription successfully saved to Approved Memory.",
            "document_id": document_id,
            "approval_status": "approved",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registration/available-doctors")
async def get_available_doctors(
    user: user_dependency, db: db_dependency, department: str = None
):
    """Registration desk sees which doctors they can assign patients to"""
    if user.get("role") not in ["registration", "admin"]:
        raise HTTPException(403, "Not authorized")

    query = db.query(User).filter(User.role == "doctor", User.is_active == True)

    if department:
        # You'd need a department field on User model
        pass

    doctors = query.all()

    return [
        {
            "doctor_id": d.id,
            "full_name": d.full_name,
            "email": d.email,
            "current_patient_count": db.query(DoctorPatientAssignment)
            .filter(
                DoctorPatientAssignment.doctor_id == d.id,
                DoctorPatientAssignment.status == "active",
            )
            .count(),
        }
        for d in doctors
    ]


@router.get("/patient/history")
async def get_patient_history(user: user_dependency, db: db_dependency):
    """
    Fetches the approved medical history for the currently logged-in patient.
    """
    if user.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to patients.",
        )
    try:
        patient_profile = (
            db.query(Patient).filter(Patient.user_id == user.get("id")).first()
        )
        if not patient_profile:
            return {"message": "Patient profile incomplete", "history": []}

        documents = (
            db.query(MedicalDocument)
            .filter(
                MedicalDocument.patient_id == patient_profile.patient_id,
                MedicalDocument.approval_status == "approved",
            )
            .order_by(MedicalDocument.created_at.desc())
            .all()
        )

        history = [
            {
                "document_id": doc.document_id,
                "report_type": doc.report_type,
                "data": doc.extracted_data,
                "date": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ]
        return {"patient_id": patient_profile.patient_id, "history": history}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/finance/invoices")
async def get_approved_invoices(user: user_dependency, db: db_dependency):
    """
    Fetches all approved medical invoices for the Finance department.
    """
    if user.get("role") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to finance.",
        )

    try:
        invoices = (
            db.query(MedicalDocument)
            .filter(
                MedicalDocument.report_type == "medical_invoice",
                MedicalDocument.approval_status == "approved",
            )
            .order_by(MedicalDocument.reviewed_at.desc())
            .all()
        )

        serialized = [
            {
                "document_id": inv.document_id,
                "patient_id": inv.patient_id,
                "financial_data": inv.extracted_data,  # This holds the UniversalInvoiceSchema JSON
                "approved_at": inv.reviewed_at.isoformat() if inv.reviewed_at else None,
            }
            for inv in invoices
        ]

        return {"invoices": serialized}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users")
async def get_all_users(
    user: user_dependency, db: db_dependency, skip: int = 0, limit: int = 100
):
    """Admin endpoint to get all users"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")

    users = db.query(User).offset(skip).limit(limit).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": db.query(User).count(),
    }


@router.get("/admin/logs")
async def get_audit_logs(user: user_dependency, db: db_dependency, limit: int = 100):
    """
    Fetches the system compliance and audit logs for Administrators.
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to admins."
        )

    try:
        # Join the User table so the admin can see the email/name instead of just an ID
        logs = (
            db.query(AuditLog, User.email)
            .join(User, AuditLog.user_id == User.id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        serialized = [
            {
                "log_id": log.AuditLog.id,
                "user_email": log.email,
                "action": log.AuditLog.action,
                "document_id": log.AuditLog.document_id,
                "timestamp": log.AuditLog.timestamp.isoformat()
                if log.AuditLog.timestamp
                else None,
            }
            for log in logs
        ]

        return {"logs": serialized}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def question(user: user_dependency, db: db_dependency, request: ChatRequest):
    role = user.get("role")
    target_patient_id = None

    # --- 1. Role-Based Identity Resolution ---
    if role == "patient":
        patient_profile = (
            db.query(Patient).filter(Patient.user_id == user.get("id")).first()
        )
        if not patient_profile:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        target_patient_id = str(patient_profile.patient_id)

    elif role == "doctor":
        if not request.patient_id:
            raise HTTPException(
                status_code=400,
                detail="Doctors must provide a patient_id in the request.",
            )

        # Security: Is this doctor actively assigned to this patient?
        assignment = (
            db.query(DoctorPatientAssignment)
            .filter(
                DoctorPatientAssignment.doctor_id == user.get("id"),
                DoctorPatientAssignment.patient_id == request.patient_id,
                DoctorPatientAssignment.status == "active",
            )
            .first()
        )

        if not assignment:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this patient's records.",
            )
        target_patient_id = request.patient_id

    else:
        raise HTTPException(
            status_code=403, detail="Role not authorized for conversational AI."
        )

    input_check = InputGuard.verify(request.query)
    if not input_check.is_safe:
        return {
            "user_query": request.query,
            "final_answer": input_check.fallback_message,
            "sources": [],
        }

    target_collection = "medical_documents"  # Default to private records

    if input_check.route == "general_health":
        target_patient_id = "PUBLIC_DOMAIN"
        target_collection = "general_health"

    retrieved_docs = retriever.retrieve(
        query=request.query,
        patient_id=target_patient_id,
        collection_name=target_collection,
    )

    context_parts = []
    for idx, doc in enumerate(retrieved_docs, start=1):
        context_parts.append(f"[SOURCE {idx}]\n{doc['content']}")
    context = "\n\n".join(context_parts)

    history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    # --- 3. LLM Generation ---
    model = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
    )

    system_prompt = """
        You are a highly capable and empathetic clinical intelligence assistant.
        
        1. GREETINGS: If the user says "hello" or "hi", respond politely and ask how you can help.
        2. STRICT GROUNDING: For medical questions, you MUST rely STRICTLY on the provided Medical Record Context.
        3. MANDATORY IGNORANCE: If the provided Context is empty, or if the answer is not explicitly written in the Context, you are FORBIDDEN from guessing. You MUST reply exactly with: "I do not have specific knowledge regarding this in the provided documents."
        4. NO DIAGNOSES: Never hallucinate diagnoses, medications, or treatments.
        """

    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Medical Record Context:\n{context}"},
        *history,
        {"role": "user", "content": request.query},
    ]

    final_answer = model.invoke(messages_for_llm)

    print("\n=== RAW LLM OUTPUT BEFORE AUDITOR ===")
    print(final_answer.content)
    print("=====================================\n")

    output_check = OutputGuard.verify(
        context=context, proposed_answer=final_answer.content
    )
    # --- 4. Source Mapping ---
    sources = []
    seen_documents = set()
    for idx, doc in enumerate(retrieved_docs, start=1):
        # Only include the source if it is actually a relevant match!
        metadata = doc["metadata"]
        doc_id = (
            metadata.get("document_id")
            or metadata.get("source_file")
            or f"Unknown_Doc_{idx}"
        )

        if doc_id not in seen_documents:
            seen_documents.add(doc_id)

        sources.append(
            {
                "source_id": idx,
                "document_id": metadata.get("document_id"),
                "report_type": metadata.get("report_type"),
                "date": metadata.get("created_at"),
            }
        )
    display_text = (
        final_answer.content if output_check.is_safe else output_check.safe_content
    )
    static_fallback = "I apologize, but I am unable to process that request right now. Please consult your healthcare provider."

    return {
        "user_query": request.query,
        "final_answer": display_text or static_fallback,
        "sources": sources if output_check.is_safe else [],
    }


@router.post("/chat/voice")
async def voice_question(
    user: user_dependency, db: db_dependency, audio: UploadFile = File(...)
):
    if user.get("role") != "patient":
        raise HTTPException(
            status_code=403, detail="Only patients can use this voice chat."
        )

    patient_profile = (
        db.query(Patient).filter(Patient.user_id == user.get("id")).first()
    )
    if not patient_profile:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    # 1. Save the incoming audio blob to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(await audio.read())
        temp_audio_path = temp_audio.name

    try:
        # 2. Transcribe the audio using Whisper
        client = OpenAI(base_url="https://us.api.openai.com/v1")
        with open(temp_audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                prompt="The user might speak English.",  # Context hint for the model
            )
        user_query = transcription.text

    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

    target_patient_id = str(patient_profile.patient_id)
    target_collection = "medical_documents"

    # 2. Actually RUN the InputGuard on the transcribed text
    input_check = InputGuard.verify(user_query)
    if not input_check.is_safe:
        return {
            "user_transcript": user_query,
            "final_answer": input_check.fallback_message,
            "sources": [],
        }

    # 3. Add our routing switch
    if input_check.route == "general_health":
        target_patient_id = "PUBLIC_DOMAIN"
        target_collection = "general_health"

    # 4. Pass BOTH variables and the TRANSCRIBED text (user_query) to the retriever
    retrieved_docs = retriever.retrieve(
        query=user_query,
        patient_id=target_patient_id,
        collection_name=target_collection,
    )

    context_parts = []
    for idx, doc in enumerate(retrieved_docs, start=1):
        context_parts.append(f"[SOURCE {idx}]\n{doc['content']}")
    context = "\n\n".join(context_parts)

    model = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
    )

    system_prompt = """
        You are a helpful, multilingual AI Health Assistant for patients.
        1. You may summarize lab reports and explain medication schedules strictly based on the provided clinical context.
        2. You MUST NOT diagnose conditions.
        3. If the user asks for a diagnosis, gently explain that you are an AI and they must consult their doctor.
        4. If the provided Context is empty, you MUST reply exactly with: "I do not have specific knowledge regarding this in your provided records."
        """

    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Medical Record Context:\n{context}"},
        {"role": "user", "content": user_query},
    ]

    final_answer = model.invoke(messages_for_llm)

    # Run the voice output through the auditor too!
    output_check = OutputGuard.verify(
        context=context, proposed_answer=final_answer.content
    )

    # Source Mapping & Deduplication
    sources = []
    seen_documents = set()
    for doc in retrieved_docs:
        metadata = doc["metadata"]
        doc_id = (
            metadata.get("document_id") or metadata.get("source_file") or "Unknown_Doc"
        )

        if doc_id not in seen_documents:
            seen_documents.add(doc_id)
            sources.append(
                {
                    "source_id": len(sources)
                    + 1,  # This ensures UI numbering is 1, 2, 3 (no skipped numbers!)
                    "document_id": metadata.get("document_id"),
                    "report_type": metadata.get("report_type"),
                    "date": metadata.get("created_at"),
                }
            )

    display_text = (
        final_answer.content if output_check.is_safe else output_check.safe_content
    )
    static_fallback = "I apologize, but I am unable to process that request right now."
    final_text = display_text or static_fallback

    audio_base64 = None

    try:
        tts_client = OpenAI(base_url="https://us.api.openai.com/v1")

        tts_response = tts_client.audio.speech.create(
            model = 'tts-1',
            voice = 'nova',
            input = final_text
        )
        audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
    except Exception as e:
        print(f"TTS Generation failed: {e}")
        # If voice fails, we just fail gracefully and still return the text!
        pass
    # Return BOTH the transcription and the answer so the frontend can display them
    return {
        "user_transcript": user_query,
        "final_answer": display_text or static_fallback,
        "audio_base64": audio_base64,
        "sources": sources if output_check.is_safe else [],
    }

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
import uuid
from pathlib import Path
import shutil
from datetime import datetime, timezone
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from src.models import User, Patient, AuditLog, MedicalDocument, Base
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


@router.post("/upload")
async def upload_medical_report(
    user: user_dependency,
    db: db_dependency,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    report_type: str = Form(...),
):
    role = user.get("role")
    if role not in ["nurse", "admin", "doctor"]:
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
                    # Convert datetime to a clean ISO string so the frontend can parse it
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
    """
    CPOE Fast Track for Doctors.
    Bypasses AI extraction and nurse quarantine.
    Saves directly to Approved Medical Memory.
    """
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
    if user.get("role") != "patient":
        raise HTTPException(status_code=403, detail="Only patients can use this chat.")
    patient_profile = (
        db.query(Patient).filter(Patient.user_id == user.get("id")).first()
    )
    if not patient_profile:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    retrieved_docs = retriever.retrieve(
        query=request.query,
        patient_id=str(patient_profile.patient_id),
    )
    context_parts = []

    for idx, doc in enumerate(retrieved_docs, start=1):
        context_parts.append(
            f"[SOURCE {idx}]\n{doc['content']}"
        )

    context = "\n\n".join(context_parts)
        
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    model = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
    )

    system_prompt = """
        You are a helpful medical AI assistant.

        Use ONLY the provided medical context.
        If the answer is not present in the records, say you do not know.
        Do not hallucinate diagnoses, medications, or treatments.
        """

    messages_for_llm = [
        {"role": "system", "content": system_prompt},
        {
            "role": "system",
            "content": f"Medical Record Context:\n{context}"
        },
        *history,
        {"role": "user", "content": request.query},
    ]

    final_answer = model.invoke(messages_for_llm)

    sources = []

    for idx, doc in enumerate(retrieved_docs, start=1):
        metadata = doc["metadata"]

        sources.append({
            "source_id": idx,
            "document_id": metadata.get("document_id"),
            "report_type": metadata.get("report_type"),
            "page": metadata.get("page"),
            "score": round(doc["score"], 3),
        })

    return {
        "user_query": request.query,
        "final_answer": final_answer.content,
        "sources": sources
    }
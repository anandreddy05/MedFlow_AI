import os
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
)

from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
from pathlib import Path
from datetime import timezone
from dotenv import load_dotenv
import tempfile
from openai import OpenAI

from src.models import (
    Patient,
    AuditLog,
    MedicalDocument,
    DoctorPatientAssignment,
)
from .auth import get_current_user, get_db
from src.utils.logger import get_logger, log_ctx, timed_log

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@timed_log(logger, "openai_transcription")
def _transcribe_dictation(temp_audio_path: str) -> str:
    client = OpenAI(base_url="https://us.api.openai.com/v1")
    with open(temp_audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            prompt="Medical dictation. Patient notes, clinical instructions, dosages like mg, ml, and frequencies like BID, TID, OD.",
        )
    return transcription.text


@router.post("/doctor/transcribe")
async def transcribe_medical_dictation(
    user: user_dependency, audio: UploadFile = File(...)
):
    """Voice to text dictation for doctors (Digital Prescription)"""
    logger.info(
        "Transcription request",
        extra=log_ctx(user_id=user.get("id"), filename=audio.filename),
    )
    if user.get("role") != "doctor":
        logger.warning(
            "Authorization failure: medical dictation",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(
            status_code=403, detail="Only doctors can use medical dictation."
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(await audio.read())
        temp_audio_path = temp_audio.name

    try:
        return {"transcription": _transcribe_dictation(temp_audio_path)}

    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)



@router.get("/doctor/my-patients")
async def get_my_patients(
    user: user_dependency, db: db_dependency, skip: int = 0, limit: int = 50
):
    """Doctor sees ONLY patients assigned to them"""
    logger.info(
        "Fetching assigned patients",
        extra=log_ctx(doctor_id=user.get("id"), skip=skip, limit=limit),
    )
    if user.get("role") != "doctor":
        logger.warning(
            "Authorization failure: doctor patients list",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
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
    logger.info(
        "Fetching patient full history",
        extra=log_ctx(doctor_id=user.get("id"), patient_id=patient_id),
    )
    if user.get("role") != "doctor":
        logger.warning(
            "Authorization failure: patient full history",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
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
        logger.warning(
            "Authorization failure: patient not assigned to doctor",
            extra=log_ctx(doctor_id=user.get("id"), patient_id=patient_id),
        )
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
    logger.info(
        "Patient transfer request",
        extra=log_ctx(
            user_id=user.get("id"),
            patient_id=patient_id,
            new_doctor_id=new_doctor_id,
        ),
    )
    if user.get("role") not in ["doctor", "admin"]:
        logger.warning(
            "Authorization failure: patient transfer",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
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

    logger.info(
        "Patient transferred successfully",
        extra=log_ctx(
            patient_id=patient_id,
            from_doctor=current_assignment.doctor_id,
            to_doctor=new_doctor_id,
        ),
    )

    return {
        "message": "Patient transferred successfully",
        "patient_id": patient_id,
        "from_doctor": current_assignment.doctor_id,
        "to_doctor": new_doctor_id,
    }

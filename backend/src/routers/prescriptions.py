from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
import uuid
from pathlib import Path
from datetime import timezone
from dotenv import load_dotenv

from src.models import (
    AuditLog,
    MedicalDocument,
    DoctorPatientAssignment,
)
from src.ingestion.schemas import (
    DirectPrescriptionPayload,
)
from starlette import status
from .auth import get_current_user, get_db
from src.rag.shared_resources import get_vector_store
from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/prescriptions/direct")
async def create_direct_prescription(
    user: user_dependency,
    db: db_dependency,
    payload: DirectPrescriptionPayload,
    background_tasks: BackgroundTasks,
):
    """Doctor writes prescription - ONLY for their assigned patients"""
    logger.info(
        "Direct prescription request",
        extra=log_ctx(
            doctor_id=user.get("id"),
            patient_id=payload.patient_id,
        ),
    )

    # FIRST: Check role
    if user.get("role") != "doctor":
        logger.warning(
            "Authorization failure: direct prescription",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only doctors can write prescriptions.",
        )

    # SECOND: Verify doctor ID matches token
    if payload.doctor_id != user.get("id"):
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
        logger.warning(
            "Authorization failure: unassigned patient prescription",
            extra=log_ctx(
                doctor_id=user.get("id"),
                patient_id=payload.patient_id,
            ),
        )
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
        human_readable_date = datetime.now().strftime("%B %d, %Y")
        iso_timestamp = datetime.now().isoformat()
        document_id = f"{payload.patient_id}_digital_prescription_{timestamp}_{uuid.uuid4().hex[:8]}"

        markdown_text = f"# Prescription Date: {human_readable_date}\n\n## Clinical Instructions\n{payload.instructions}\n\n## Prescribed Medications\n"
        for med in payload.medications:
            timings_str = ", ".join(med.timings).title()
            food_str = med.foodTiming.replace("_", " ").title()

            markdown_text += f"- **{med.name} {med.strength}**: Take {med.quantityPerDose} for {med.duration} {med.durationUnit}.\n"
            markdown_text += f"  - Timing: {timings_str} ({food_str})\n"
            if med.notes:
                markdown_text += f"  - Notes: {med.notes}\n"

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

        logger.info(
            "Prescription saved successfully",
            extra=log_ctx(document_id=document_id, patient_id=payload.patient_id),
        )

        if clinical_data.get("clinical_notes"):
            background_tasks.add_task(
                get_vector_store().ingest_docs,
                document_id=str(new_document.document_id),
                patient_id=str(new_document.patient_id),
                report_type=str(new_document.report_type),
                markdown_text=str(new_document.content_markdown),
                role=str(user.get("role")),
                created_at=iso_timestamp,
            )

        return {
            "message": "Prescription successfully saved to Approved Memory.",
            "document_id": document_id,
            "approval_status": "approved",
        }

    except Exception as e:
        db.rollback()
        logger.exception(
            "Database failure while saving prescription",
            extra=log_ctx(
                doctor_id=user.get("id"),
                patient_id=payload.patient_id,
            ),
        )
        raise HTTPException(status_code=500, detail=str(e))

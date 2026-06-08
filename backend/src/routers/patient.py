from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from sqlalchemy.orm import Session
from typing import Annotated
from dotenv import load_dotenv
from starlette import status

from src.models import (
    Patient,
    MedicalDocument,
)
from .auth import get_current_user, get_db
from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]



@router.get("/patient/history")
async def get_patient_history(user: user_dependency, db: db_dependency):
    """
    Fetches the approved medical history for the currently logged-in patient.
    """
    if user.get("role") != "patient":
        logger.warning(
            "Authorization failure: patient history",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to patients.",
        )
    logger.info("Fetching patient history", extra=log_ctx(user_id=user.get("id")))
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
        logger.exception(
            "Database failure while fetching patient history",
            extra=log_ctx(user_id=user.get("id")),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

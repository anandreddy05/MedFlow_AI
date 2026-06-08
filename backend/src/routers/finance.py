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
    MedicalDocument,
)
from .auth import get_current_user, get_db
from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]




@router.get("/finance/invoices")
async def get_approved_invoices(user: user_dependency, db: db_dependency):
    """
    Fetches all approved medical invoices for the Finance department.
    """
    if user.get("role") != "finance":
        logger.warning(
            "Authorization failure: finance invoices",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to finance.",
        )

    logger.info("Fetching approved invoices", extra=log_ctx(user_id=user.get("id")))
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
        logger.exception(
            "Database failure while fetching invoices",
            extra=log_ctx(user_id=user.get("id")),
        )
        raise HTTPException(status_code=500, detail=str(e))


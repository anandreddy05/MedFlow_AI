from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
import uuid
from pathlib import Path
import shutil
from datetime import timezone
from dotenv import load_dotenv

from src.models import (
    AuditLog,
    MedicalDocument,
)
from src.ingestion.extractor import BaseExtractor
from starlette import status
from .auth import get_current_user, get_db
from src.rag.shared_resources import get_vector_store
from src.ingestion.schemas import (
    ApproveReportRequest,
)
from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post("/upload", tags=["Documents"])
async def upload_medical_report(
    user: user_dependency,
    db: db_dependency,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    report_type: str = Form(...),
):
    role = user.get("role")
    logger.info(
        "Document upload request",
        extra=log_ctx(
            user_id=user.get("id"),
            role=role,
            patient_id=patient_id,
            report_type=report_type,
            filename=file.filename,
        ),
    )
    allowed_upload = ["nurse", "admin", "doctor", "finance"]
    if role not in allowed_upload:
        logger.warning(
            "Authorization failure: document upload",
            extra=log_ctx(user_id=user.get("id"), role=role),
        )
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
        from src.ingestion.extractor import BaseExtractor

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

        logger.info(
            "Document uploaded successfully",
            extra=log_ctx(
                document_id=document_id,
                patient_id=patient_id,
                report_type=report_type,
                uploaded_by=user.get("id"),
            ),
        )

        return {
            "message": "Document uploaded successfully",
            "document_id": document_id,
            "approval_status": "pending",
        }
    except Exception as e:
        db.rollback()
        logger.exception(
            "Document upload failed",
            extra=log_ctx(
                patient_id=patient_id,
                report_type=report_type,
                user_id=user.get("id"),
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)}
        )


@router.get("/documents/{document_id}/file", tags=["Documents"])
async def get_document_file(document_id: str, user: user_dependency, db: db_dependency):
    """Serve original uploaded file for nurse/clinical review."""
    logger.info(
        "Document file request",
        extra=log_ctx(document_id=document_id, user_id=user.get("id")),
    )
    role = user.get("role")
    if role not in ["nurse", "doctor", "admin"]:
        logger.warning(
            "Authorization failure: document file access",
            extra=log_ctx(user_id=user.get("id"), role=role, document_id=document_id),
        )
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


@router.get("/reports/pending", tags=["Reports"])
async def get_pending_reports(user: user_dependency, db: db_dependency):
    """
    Fetch all pending reports..
    """
    role = user.get("role")
    if role != "nurse":
        logger.warning(
            "Authorization failure: pending reports",
            extra=log_ctx(user_id=user.get("id"), role=role),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to review reports.",
        )
    logger.info("Fetching pending reports", extra=log_ctx(user_id=user.get("id")))
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
        logger.exception(
            "Database failure while fetching pending reports",
            extra=log_ctx(user_id=user.get("id")),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/approve", tags=["Reports"])
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
        logger.warning(
            "Authorization failure: approve report",
            extra=log_ctx(user_id=user.get("id"), role=role),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to approve reports.",
        )
    logger.info(
        "Approve report request",
        extra=log_ctx(
            user_id=user.get("id"),
            document_id=request.document_id,
        ),
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
            logger.info(
                "Scheduling document ingestion after approval",
                extra=log_ctx(
                    document_id=document.document_id,
                    patient_id=document.patient_id,
                    report_type=document.report_type,
                ),
            )
            background_tasks.add_task(
                get_vector_store().ingest_docs,
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
        db.rollback()
        logger.exception(
            "Database failure while approving report",
            extra=log_ctx(
                user_id=user.get("id"),
                document_id=request.document_id,
            ),
        )
        raise HTTPException(status_code=500, detail=str(e))

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
    User,
    AuditLog,
)
from .auth import get_current_user, get_db
from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]




@router.get("/admin/users")
async def get_all_users(
    user: user_dependency, db: db_dependency, skip: int = 0, limit: int = 100
):
    """Admin endpoint to get all users"""
    if user.get("role") != "admin":
        logger.warning(
            "Authorization failure: admin users list",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(403, "Admin access required")

    logger.info(
        "Fetching all users",
        extra=log_ctx(admin_id=user.get("id"), skip=skip, limit=limit),
    )

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
        logger.warning(
            "Authorization failure: admin audit logs",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to admins."
        )

    logger.info(
        "Fetching audit logs",
        extra=log_ctx(admin_id=user.get("id"), limit=limit),
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
        logger.exception(
            "Database failure while fetching audit logs",
            extra=log_ctx(admin_id=user.get("id")),
        )
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
from dotenv import load_dotenv

from src.models import (
    User,
    Patient,
    DoctorPatientAssignment,
)
from .auth import get_current_user, get_db
from src.utils.logger import get_logger, log_ctx

load_dotenv(override=True)

logger = get_logger(__name__)

router = APIRouter()

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
    assigned_doctor_id: int,  
    department: str = "General OPD",
    password: str = None,
):
    """
    Hospital registration desk creates new patient account.
    Assigns to a specific doctor at registration time.
    """
    if user.get("role") not in ["registration", "admin"]:
        logger.warning(
            "Authorization failure: registration endpoint",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(403, "Registration desk only")

    logger.info(
        "Create patient request",
        extra=log_ctx(
            email=email,
            assigned_doctor_id=assigned_doctor_id,
            user_id=user.get("id"),
        ),
    )

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

    logger.info(
        "Patient registered successfully",
        extra=log_ctx(mrn=mrn, email=email, assigned_doctor_id=assigned_doctor_id),
    )

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


@router.get("/registration/available-doctors")
async def get_available_doctors(
    user: user_dependency, db: db_dependency, department: str = None
):
    """Registration desk sees which doctors they can assign patients to"""
    if user.get("role") not in ["registration", "admin"]:
        logger.warning(
            "Authorization failure: available doctors endpoint",
            extra=log_ctx(user_id=user.get("id"), role=user.get("role")),
        )
        raise HTTPException(403, "Not authorized")

    logger.info(
        "Fetching available doctors",
        extra=log_ctx(user_id=user.get("id"), department=department),
    )

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

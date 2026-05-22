from src.database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, JSON, Text
from datetime import timezone, datetime
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(
        Enum("doctor", "nurse", "patient", "finance", "admin", name="user_roles"),
        nullable=False,
    )  # doctor, nnurse, patient, finance, admin,
    full_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    audit_logs = relationship("AuditLog", back_populates="user")
    patient_profile = relationship("Patient", back_populates="user", uselist=False)


class Patient(Base):
    """
    Patient Demographics Table.
    Separated from the User table because doctors/nurses don't need these fields,
    but patients still need a link to the User table to log in.
    """

    __tablename__ = "patients"

    # The medical record number (MRN) used across your JSON files
    patient_id = Column(String, primary_key=True, index=True)

    # Links the patient demographic data to their login credentials
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)

    date_of_birth = Column(String)  # Format: YYYY-MM-DD
    gender = Column(String)
    blood_type = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="patient_profile")


class AuditLog(Base):
    """
    The Compliance Engine.
    Tracks every major action taken in the system for legal/hospital accountability.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # e.g., "UPLOADED_CBC", "APPROVED_PRESCRIPTION", "DIRECT_ENTRY_CPOE"
    action = Column(String, nullable=False)

    # The exact filename or ID stored in Qdrant / Approved folder
    document_id = Column(String, nullable=False)

    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    document_id = Column(String, primary_key=True, index=True)

    patient_id = Column(String, ForeignKey("patients.patient_id"))

    uploaded_by = Column(Integer, ForeignKey("users.id"))

    report_type = Column(
        Enum(
            "cbc",
            "digital_prescription",
            "discharge_summary",
            "medical_invoice",
            name="report_types",
        ),
        nullable=False,
    )

    extraction_type = Column(String)

    original_file_path = Column(String)

    # For RAG (semantic search)
    content_markdown = Column(Text)
    extracted_data = Column(JSON)

    approval_status = Column(String)

    reviewed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

import uuid
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from src.database import Base
from src.main import app
from src.routers.auth import get_current_user
from src.routers.auth import get_db
from src.models import User, Patient, DoctorPatientAssignment, MedicalDocument
from fastapi.testclient import TestClient
import pytest


SQLALCHEMY_DATABASE_URL = "sqlite:///./testdb.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="session", autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ============================================================
# Shared session fixture
# ============================================================


@pytest.fixture
def db_session():
    """Single session for both seeding AND routes"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================
# Override_get_db uses the SAME session
# ============================================================


@pytest.fixture
def client(db_session):
    """Test client with the shared session wired into get_db"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ============================================================
# SEED HELPERS - They MUST use the shared db_session
# ============================================================


def seed_user(
    db: Session, *, email: str, role: str, full_name: str = "Test User"
) -> User:
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=bcrypt_context.hash("testpass123"),
        role=role,
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_patient(db: Session, *, user_id: int, patient_id: str) -> Patient:
    patient = Patient(
        patient_id=patient_id,
        user_id=user_id,
        date_of_birth="1990-05-20",
        gender="male",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def seed_assignment(
    db: Session, *, doctor_id: int, patient_id: str
) -> DoctorPatientAssignment:
    assignment = DoctorPatientAssignment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        is_primary=True,
        status="active",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def seed_document(
    db: Session,
    *,
    document_id: str,
    patient_id: str,
    uploaded_by: int,
    report_type: str = "cbc",
    approval_status: str = "pending",
) -> MedicalDocument:
    doc = MedicalDocument(
        document_id=document_id,
        patient_id=patient_id,
        uploaded_by=uploaded_by,
        report_type=report_type,
        original_file_path="storage/uploads/test.pdf",
        content_markdown="## CBC Report\n**WBC**: 7.0",
        extracted_data={"test_key": "test_value"},
        approval_status=approval_status,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"


def make_identity(role: str, user_id: int, username: str = "test@test.com") -> dict:
    return {"id": user_id, "role": role, "username": username}


# ============================================================
# ROLE FIXTURES
# ============================================================


@pytest.fixture
def as_registration(client):
    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "registration", user_id=9001
    )
    return client


@pytest.fixture
def as_admin(client):
    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "admin", user_id=9002
    )
    return client


@pytest.fixture
def as_nurse(client):
    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "nurse", user_id=9003
    )
    return client


@pytest.fixture
def as_patient(client):
    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "patient", user_id=9004
    )
    return client


@pytest.fixture
def as_finance(client):
    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "finance", user_id=9005
    )
    return client


# ============================================================
# SEEDED FIXTURES - Use the SHARED db_session
# ============================================================


@pytest.fixture
def seeded_doctor(client, db_session):
    """Creates a REAL doctor in the shared session"""
    doctor = seed_user(
        db_session, email=unique_email("doctor"), role="doctor", full_name="Dr. Sharma"
    )
    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "doctor", user_id=doctor.id, username=doctor.email
    )
    return client, doctor


@pytest.fixture
def seeded_doctor_with_patient(client, db_session):
    """Creates doctor + patient + assignment in the shared session"""
    doctor = seed_user(
        db_session, email=unique_email("dr"), role="doctor", full_name="Dr. Test"
    )
    patient_user = seed_user(
        db_session, email=unique_email("pat"), role="patient", full_name="Jane Doe"
    )
    patient_id = f"MRN_{uuid.uuid4().hex[:8]}"
    patient = seed_patient(db_session, user_id=patient_user.id, patient_id=patient_id)
    seed_assignment(db_session, doctor_id=doctor.id, patient_id=patient.patient_id)

    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "doctor", user_id=doctor.id, username=doctor.email
    )
    return client, doctor, patient_user, patient


@pytest.fixture
def seeded_patient_with_doc(client, db_session):
    """Creates patient + approved document in the shared session"""
    patient_user = seed_user(
        db_session,
        email=unique_email("patwdoc"),
        role="patient",
        full_name="Bob Patient",
    )
    patient_id = f"MRN_{uuid.uuid4().hex[:8]}"
    patient = seed_patient(db_session, user_id=patient_user.id, patient_id=patient_id)
    doc = seed_document(
        db_session,
        document_id=f"DOC_{uuid.uuid4().hex[:8]}",
        patient_id=patient.patient_id,
        uploaded_by=patient_user.id,
        approval_status="approved",
    )

    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "patient", user_id=patient_user.id, username=patient_user.email
    )
    return client, patient_user, patient, doc


@pytest.fixture
def seeded_pending_doc(client, db_session):
    """Creates nurse + pending document in the shared session"""
    nurse = seed_user(
        db_session, email=unique_email("nurse"), role="nurse", full_name="Nurse Joy"
    )
    patient_user = seed_user(
        db_session,
        email=unique_email("pendpat"),
        role="patient",
        full_name="Pending Pat",
    )
    patient_id = f"MRN_{uuid.uuid4().hex[:8]}"
    patient = seed_patient(db_session, user_id=patient_user.id, patient_id=patient_id)
    doc = seed_document(
        db_session,
        document_id=f"DOC_PEND_{uuid.uuid4().hex[:8]}",
        patient_id=patient.patient_id,
        uploaded_by=nurse.id,
        approval_status="pending",
    )

    app.dependency_overrides[get_current_user] = lambda: make_identity(
        "nurse", user_id=nurse.id, username=nurse.email
    )
    return client, nurse, doc


# ============================================================
# TESTS START HERE
# ============================================================


class TestCreatePatient:
    ENDPOINT = "/registration/create-patient"

    def test_successful_registration(self, as_registration, db_session):
        doctor = seed_user(
            db_session, email=unique_email("regdoc"), role="doctor", full_name="Dr. Reg"
        )

        response = as_registration.post(
            self.ENDPOINT,
            params={
                "full_name": "New Patient",
                "date_of_birth": "1995-03-10",
                "gender": "female",
                "phone": "9876543210",
                "email": unique_email("newpat"),
                "assigned_doctor_id": doctor.id,
                "department": "Cardiology",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "mrn" in body
        assert body["mrn"].startswith("MRN")


class TestDoctorEndpoints:
    def test_my_patients_returns_assigned_patient(self, seeded_doctor_with_patient):
        client, doctor, patient_user, patient = seeded_doctor_with_patient
        response = client.get("/doctor/my-patients")
        assert response.status_code == 200
        body = response.json()
        assert body["total_patients"] == 1
        assert body["patients"][0]["patient_id"] == patient.patient_id

    def test_full_history_returns_correct_shape(self, seeded_doctor_with_patient):
        client, doctor, _, patient = seeded_doctor_with_patient
        response = client.get(f"/doctor/patient/{patient.patient_id}/full-history")
        assert response.status_code == 200
        body = response.json()
        assert body["patient"]["patient_id"] == patient.patient_id
        assert "documents" in body


class TestPendingReports:
    ENDPOINT = "/reports/pending"

    def test_nurse_sees_seeded_pending_doc(self, seeded_pending_doc):
        client, nurse, doc = seeded_pending_doc
        response = client.get(self.ENDPOINT)
        assert response.status_code == 200
        doc_ids = [r["document_id"] for r in response.json()["pending_reports"]]
        assert doc.document_id in doc_ids


class TestApproveReport:
    ENDPOINT = "/reports/approve"

    def test_nurse_can_approve_pending_doc(self, seeded_pending_doc):
        client, nurse, doc = seeded_pending_doc
        response = client.post(
            self.ENDPOINT,
            json={
                "document_id": doc.document_id,
                "corrected_report": {"wbc": "7.0", "hemoglobin": "14.5"},
            },
        )
        assert response.status_code == 200
        assert response.json()["approval_status"] == "approved"


class TestDirectPrescription:
    ENDPOINT = "/prescriptions/direct"

    def _valid_payload(self, doctor_id: int, patient_id: str) -> dict:
        return {
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "instructions": "Rest",
            "medications": [
                {
                    "name": "Paracetamol",
                    "strength": "500mg",
                    "quantityPerDose": "1",
                    "duration": "5",
                    "durationUnit": "days",
                    "timings": ["morning"],
                    "foodTiming": "after_food",
                    "notes": "",
                }
            ],
        }

    def test_nurse_cannot_prescribe(self, as_nurse):
        response = as_nurse.post(
            self.ENDPOINT, json=self._valid_payload(doctor_id=1, patient_id="MRN_ANY")
        )
        assert response.status_code == 401

    def test_patient_cannot_prescribe(self, as_patient):
        response = as_patient.post(
            self.ENDPOINT, json=self._valid_payload(doctor_id=1, patient_id="MRN_ANY")
        )
        assert response.status_code == 401

    def test_doctor_id_mismatch_is_403(self, seeded_doctor):
        client, doctor = seeded_doctor
        payload = self._valid_payload(doctor_id=9999, patient_id="MRN_ANY")
        response = client.post(self.ENDPOINT, json=payload)
        assert response.status_code == 403

    def test_unassigned_patient_is_403(self, seeded_doctor):
        client, doctor = seeded_doctor
        payload = self._valid_payload(doctor_id=doctor.id, patient_id="MRN_NOT_MINE")
        response = client.post(self.ENDPOINT, json=payload)
        assert response.status_code == 403

    def test_prescription_saved_for_assigned_patient(self, seeded_doctor_with_patient):
        client, doctor, _, patient = seeded_doctor_with_patient
        payload = self._valid_payload(
            doctor_id=doctor.id, patient_id=patient.patient_id
        )
        response = client.post(self.ENDPOINT, json=payload)
        assert response.status_code == 200
        assert response.json()["approval_status"] == "approved"


class TestPatientHistory:
    ENDPOINT = "/patient/history"

    def test_patient_sees_their_approved_docs(self, seeded_patient_with_doc):
        client, patient_user, patient, doc = seeded_patient_with_doc
        response = client.get(self.ENDPOINT)
        assert response.status_code == 200
        body = response.json()
        assert body["patient_id"] == patient.patient_id
        assert len(body["history"]) >= 1
        assert body["history"][0]["document_id"] == doc.document_id


class TestChat:
    ENDPOINT = "/chat"

    def test_patient_with_no_profile_returns_404(self, as_patient):
        response = as_patient.post(
            self.ENDPOINT, json={"query": "Hello", "history": []}
        )
        assert response.status_code == 404

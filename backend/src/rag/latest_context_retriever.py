from sqlalchemy.orm import Session
from src.models import MedicalDocument


class LatestContextRetriever:
    """
    Builds the patient's current clinical context.

        Strategy:
        1. Fetch approved documents ordered by newest first.
        2. Keep only the FIRST occurrence of each report_type.
        3. This guarantees:
        - Latest prescription
        - Latest CBC
        - Latest HbA1c
        - Latest consultation
        - Latest future report types
    """

    def retrieve(self, db: Session, patient_id: str, max_scan_documents: int = 100):
        documents = (
            db.query(MedicalDocument)
            .filter(
                MedicalDocument.patient_id == patient_id,
                MedicalDocument.approval_status == "approved",
            )
            .order_by(MedicalDocument.created_at.desc())
            .limit(max_scan_documents)
            .all()
        )

        latest_by_type = {}
        seen_types = set()

        for doc in documents:
            report_type = doc.report_type
            if report_type in seen_types:
                continue
            latest_by_type[report_type] = doc
            seen_types.add(report_type)
        return latest_by_type

    def build_context(self, documents: dict[str, MedicalDocument]) -> str:
        """
        Converts latest documents into LLM ready context.
        """

        if not documents:
            return "No current records available."

        context_parts = []

        for doc in documents.values():
            context_parts.append(
                f"""
### Document Type: {doc.report_type}
Document ID: {doc.document_id}
Date: {doc.created_at}

Content:
{doc.content_markdown}
"""
            )
        return (
            "The following are the latest approved records "
            "for each report category.\n\n" + "\n\n-----\n\n".join(context_parts)
        )

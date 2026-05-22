# backend/src/ingestion/extractor.py

from .extractors.cbc_extractor import CBCExtractor
from .extractors.digital_prescription_extractor import DigitalPrescriptionExtractor
from .extractors.discharge_summary_extractor import DischargeSummaryExtractor
from .extractors.medical_invoice_extractor import MedicalInvoiceExtractor

class BaseExtractor:
    def get_extractor(self, report_type: str):
        if report_type == "cbc":
            return CBCExtractor()
        elif report_type == "digital_prescription":
            return DigitalPrescriptionExtractor()
        elif report_type == "discharge_summary":
            return DischargeSummaryExtractor()
        elif report_type == "medical_invoice":
            return MedicalInvoiceExtractor()
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
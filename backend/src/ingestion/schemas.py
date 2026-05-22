from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class BloodTestResult(BaseModel):
    test_name: str = Field(
        description="The name of the parameter tested, e.g., Haemoglobin, Platelet Count"
    )
    value: float = Field(description="The numerical result of the test")
    unit: str = Field(description="The unit of measurement, e.g., g/dL, %")
    reference_range_min: Optional[float] = Field(
        None, description="The minimum normal value"
    )
    reference_range_max: Optional[float] = Field(
        None, description="The maximum normal value"
    )
    flag: str = Field(
        default="Normal", description="High, Low, or Normal based on reference range"
    )


class UniversalBloodReport(BaseModel):
    patient_name: str
    collection_date: str
    results: List[BloodTestResult]


class ApproveReportRequest(BaseModel):
    document_id: str  # Replaced file_name
    corrected_report: Dict[str, Any]


class InvoiceLineItem(BaseModel):
    """Schema for individual billed services or items."""

    cpt_code: Optional[str] = Field(
        None,
        description="The CPT, ICD-10, or internal billing code for the procedure/item.",
    )
    description: str = Field(
        description="Description of the medical service, medication, or equipment."
    )
    quantity: float = Field(description="Number of units billed.")
    unit_price: float = Field(description="Cost per unit.")
    total_price: float = Field(description="Total cost for this specific line item.")


class UniversalInvoiceSchema(BaseModel):
    """Strict financial schema for Medical Invoices."""

    hospital_name: str = Field(
        description="Name of the hospital, clinic, or vendor issuing the invoice."
    )
    invoice_number: str = Field(description="Unique identifier for the invoice.")
    invoice_date: str = Field(
        description="Date the invoice was issued (Format: YYYY-MM-DD)."
    )
    patient_id: Optional[str] = Field(
        None, description="Patient MRN or ID, if available on the document."
    )
    patient_name: str = Field(
        description="Name of the patient or the responsible billing party."
    )
    line_items: List[InvoiceLineItem] = Field(
        description="List of all individual billed services or items."
    )
    subtotal: float = Field(
        description="Total amount before taxes, insurance adjustments, or discounts."
    )
    tax_amount: float = Field(description="Total tax applied.")
    total_amount_due: float = Field(
        description="Final total amount due after all calculations."
    )


class StructuredMedication(BaseModel):
    medicine_name: str
    dosage: str
    # These literals perfectly match your frontend UI dropdowns!
    timing: Literal["morning", "afternoon", "evening", "night"]
    food_instruction: Literal["before_food", "after_food", "with_food", "independent"]
    frequency: Literal["daily", "weekly", "as_needed"]


class DirectPrescriptionPayload(BaseModel):
    patient_id: str
    doctor_id: str
    instructions: Optional[str] = "Follow structured medication plan."
    medications: List[StructuredMedication]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    history: List[ChatMessage] = []

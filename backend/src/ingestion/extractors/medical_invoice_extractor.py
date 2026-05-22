from docling.document_converter import DocumentConverter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Ensure you define these in your respective files
from ..schemas import UniversalInvoiceSchema
from ..prompts import INVOICE_EXTRACTION_PROMPT

load_dotenv(override=True)


class MedicalInvoiceExtractor:
    """
    Medical Invoice Extraction Service

    Responsibilities:
    - Extract tabular billing data using Docling
    - Enforce financial schema (ICD-10/CPT codes, totals) using LLM
    """

    def __init__(self):
        self.converter = DocumentConverter()
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
        )
        self.structured_extractor = self.llm.with_structured_output(
            UniversalInvoiceSchema
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", INVOICE_EXTRACTION_PROMPT),
                (
                    "human",
                    "Extract the following billing document:\n\n{docling_markdown}",
                ),
            ]
        )
        self.extraction_chain = self.prompt | self.structured_extractor

    def process_document(self, file_path: str):
        result = self.converter.convert(file_path)
        markdown = result.document.export_to_markdown()

        structured_report = self.extraction_chain.invoke({"docling_markdown": markdown})

        return {
            "structured_report": structured_report.model_dump(),
        }

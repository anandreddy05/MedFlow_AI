from dotenv import load_dotenv

from docling.document_converter import DocumentConverter


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..schemas import UniversalBloodReport
from ..prompts import CBC_EXTRACTION_PROMPT


# =========================================================
# Load Environment Variables
# =========================================================

load_dotenv(override=True)


class CBCExtractor:
    """
    CBC Document Extraction Service

    Responsibilities:
    - Convert medical image/PDF using Docling
    - Export markdown
    - Extract structured medical schema using LLM
    - Save outputs
    """

    def __init__(self):

        self.converter = DocumentConverter()

        self.llm = ChatOpenAI(
            model="gpt-4o-mini", temperature=0, base_url="https://us.api.openai.com/v1"
        )

        self.structured_extractor = self.llm.with_structured_output(
            UniversalBloodReport
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    CBC_EXTRACTION_PROMPT,
                ),
                (
                    "human",
                    "Extract the following medical document:\n\n{docling_markdown}",
                ),
            ]
        )

        self.extraction_chain = self.prompt | self.structured_extractor

    def extract_markdown(self, file_path: str):

        result = self.converter.convert(file_path)

        document = result.document

        markdown = document.export_to_markdown()

        raw_docling_json = document.export_to_dict()

        return markdown, raw_docling_json

    def extract_structured_report(
        self,
        markdown: str,
    ):

        extracted_report = self.extraction_chain.invoke({"docling_markdown": markdown})

        return extracted_report

    def process_document(
        self,
        file_path: str,
    ):

        print("\n================================================")
        print("Starting Medical Document Extraction Pipeline")
        print("================================================\n")

        print("Step 1 → Extracting markdown using Docling...")

        markdown, raw_docling_json = self.extract_markdown(file_path)

        print("Docling extraction completed.\n")

        print("Step 2 → Extracting structured medical schema...")

        structured_report = self.extract_structured_report(markdown)

        print("Structured extraction completed.\n")

        print("Outputs saved successfully.\n")

        print("================================================")
        print("Pipeline Completed Successfully")
        print("================================================\n")

        return {
            "markdown": markdown,
            "structured_report": structured_report.model_dump(),
            "raw_docling_json": raw_docling_json,
        }


# if __name__ == "__main__":
#     extractor = CBCExtractor()

#     eso = extractor.process_document(file_path="storage/uploads/1_cbc_20260514_165041_41768e5337d04098bb656f6b50bd9ef7.png")
#     print(eso)

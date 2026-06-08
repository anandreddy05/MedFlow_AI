from dotenv import load_dotenv

from docling.document_converter import DocumentConverter

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..schemas import UniversalBloodReport
from ..prompts import CBC_EXTRACTION_PROMPT
from src.utils.logger import get_logger, log_ctx, timed_log

load_dotenv(override=True)

logger = get_logger(__name__)


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

    @timed_log(logger, "openai_generation")
    def extract_structured_report(self, markdown: str):
        return self.extraction_chain.invoke({"docling_markdown": markdown})

    def process_document(self, file_path: str):
        logger.info(
            "Starting medical document extraction pipeline",
            extra=log_ctx(file_path=file_path, report_type="cbc"),
        )

        logger.info("Extracting markdown using Docling", extra=log_ctx(file_path=file_path))
        markdown, raw_docling_json = self.extract_markdown(file_path)
        logger.info(
            "Docling extraction completed",
            extra=log_ctx(file_path=file_path, markdown_length=len(markdown)),
        )

        logger.info("Extracting structured medical schema", extra=log_ctx(file_path=file_path))
        structured_report = self.extract_structured_report(markdown)
        logger.info("Structured extraction completed", extra=log_ctx(file_path=file_path))

        logger.info(
            "Medical document extraction pipeline completed",
            extra=log_ctx(file_path=file_path, report_type="cbc"),
        )

        return {
            "markdown": markdown,
            "structured_report": structured_report.model_dump(),
            "raw_docling_json": raw_docling_json,
        }

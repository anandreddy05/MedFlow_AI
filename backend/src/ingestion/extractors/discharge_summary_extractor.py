from docling.document_converter import DocumentConverter


class DischargeSummaryExtractor:
    """
    Discharge Summary Extraction Service

    Responsibilities:
    - Extract long-form clinical summaries
    - Convert to markdown using Docling for semantic chunking
    """

    def __init__(self):
        self.converter = DocumentConverter()

    def process_document(self, file_path: str):
        result = self.converter.convert(file_path)
        document = result.document
        markdown = document.export_to_markdown()

        return {"structured_report": {"markdown_text": markdown}}

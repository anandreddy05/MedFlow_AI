

class DigitalPrescriptionExtractor:
    """
    Digital Prescription Extraction Service

    Responsibilities:
    - Extract printed/digital prescriptions
    - Convert to markdown using Docling OCR
    """

    def __init__(self):
        from docling.document_converter import DocumentConverter
        self.converter = DocumentConverter()

    def process_document(
        self,
        file_path: str,
    ):

        result = self.converter.convert(file_path)

        document = result.document

        markdown = document.export_to_markdown()

        return {"structured_report": {"markdown_text": markdown}}

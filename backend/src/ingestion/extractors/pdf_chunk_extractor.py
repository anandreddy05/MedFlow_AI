import os
import time
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from docling.document_converter import DocumentConverter


doc_converter = DocumentConverter()


def process_pdf_to_markdown(file_path: str, converter=doc_converter) -> str:
    """Converts a PDF directly into a structured Markdown string."""
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


def extract_pdf_in_chunks(
    file_path: str,
    chunk_size: int = 5,
    output_dir: str = "extraction_logs",
):
    """
    Memory-safe PDF extraction using Docling.

    Processes PDFs in page chunks instead of loading the
    entire document into Docling at once.

    Returns:
        List[dict]
    """

    file_path = str(file_path)

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)

    os.makedirs(output_dir, exist_ok=True)

    extracted_chunks = []

    print(
        f"\nPROCESSING: {Path(file_path).name}"
        f"\nTOTAL PAGES: {total_pages}"
        f"\nCHUNK SIZE: {chunk_size}\n"
    )

    for start_page in range(1, total_pages + 1, chunk_size):
        end_page = min(start_page + chunk_size - 1, total_pages)

        temp_pdf = os.path.join(output_dir, f"temp_{start_page}_{end_page}.pdf")

        try:
            writer = PdfWriter()

            for page_num in range(start_page - 1, end_page):
                writer.add_page(reader.pages[page_num])

            with open(temp_pdf, "wb") as f:
                writer.write(f)

            markdown_text = process_pdf_to_markdown(temp_pdf)

            md_file = os.path.join(
                output_dir, f"{Path(file_path).stem}_pages_{start_page}_{end_page}.md"
            )

            with open(md_file, "w", encoding="utf-8") as f:
                f.write(markdown_text)

            extracted_chunks.append(
                {
                    "content": markdown_text,
                    "metadata": {
                        "source_file": Path(file_path).name,
                        "page_start": start_page,
                        "page_end": end_page,
                    },
                }
            )

            print(f"✓ Pages {start_page}-{end_page} extracted")

        except Exception as e:
            print(f"✗ Failed pages {start_page}-{end_page}: {e}")

        finally:
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)

            time.sleep(0.25)

    return extracted_chunks

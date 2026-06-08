import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from src.rag.embedder import MedicalEmbedder
from src.rag.vectorstore import QdrantVectorStore
from src.ingestion.extractors.pdf_chunk_extractor import extract_pdf_in_chunks

load_dotenv()


def process_documents(
    source_folder: str,
    target_collection: str,
    patient_id: str,
    report_type: str,
    role: str = "system",
):
    """Unified document processing function"""

    print(f"Initializing Vector DB...")
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embedder = MedicalEmbedder()
    vector_store = QdrantVectorStore(client, embedder)

    target_folder = Path(source_folder)
    logs_dir = Path("./extraction_logs")
    merged_dir = logs_dir / "merged_docs"
    merged_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(target_folder.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs in {source_folder}")

    total = len(pdf_files)
    skipped = 0
    ingested = 0

    for pdf_file in pdf_files:
        print(f"\n{'=' * 60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'=' * 60}")

        document_id = pdf_file.stem
        merged_file_path = merged_dir / f"{document_id}_complete.md"

        # Check if already in Qdrant
        print(f"Checking existence for {document_id}")
        if vector_store.document_exists(
            document_id=document_id,
            target_collection=target_collection,
        ):
            print(f"⏭️ Skipping {document_id} - already exists")
            skipped += 1
            continue

        # Check if merged markdown already exists
        if merged_file_path.exists():
            print(f"📄 Using existing merged markdown: {merged_file_path.name}")
            markdown_text = merged_file_path.read_text(encoding="utf-8")

        else:
            print(f"📄 Extracting from PDF...")

            try:
                # Extract PDF in chunks (same for both)
                chunks = extract_pdf_in_chunks(
                    file_path=str(pdf_file), chunk_size=5, output_dir="extraction_logs"
                )

                valid_chunks = [
                    chunk for chunk in chunks if chunk and chunk.get("content")
                ]

                if not valid_chunks:
                    print(f"❌ No valid content extracted")
                    continue

                print(f"✓ Extracted {len(valid_chunks)} chunks")

                # Merge chunks (same for both - no external script!)
                merged_text = ""
                for chunk in valid_chunks:
                    merged_text += chunk["content"]
                    merged_text += "\n\n"

                merged_file_path.write_text(merged_text, encoding="utf-8")
                markdown_text = merged_text
                print(f"✓ Merged file created: {merged_file_path.name}")

            except Exception as e:
                print(f"❌ Extraction failed: {e}")
                continue

        # Ingest document
        print(f"💾 Ingesting into Qdrant...")

        vector_store.ingest_docs(
            document_id=document_id,
            patient_id=patient_id,
            report_type=report_type,
            markdown_text=markdown_text,
            role=role,
            target_collection=target_collection,
        )

        print(f"✅ Successfully ingested {pdf_file.name}")
        ingested += 1

    print(f"\n{'=' * 60}")
    print(f"📊 Summary: {ingested} ingested, {skipped} skipped, {total} total")
    print(f"{'=' * 60}")


# Usage for different document types
if __name__ == "__main__":
    # For finance documents
    # process_documents(
    #     source_folder="./storage/finance_docs",
    #     target_collection="knowledge_base",
    #     patient_id="COMPLIANCE_DOMAIN",
    #     report_type="finance_compliance"
    # )

    # For general health documents
    process_documents(
        source_folder="./storage/general_docs",
        target_collection="knowledge_base",
        patient_id="PUBLIC_DOMAIN",
        report_type="general_health",
    )

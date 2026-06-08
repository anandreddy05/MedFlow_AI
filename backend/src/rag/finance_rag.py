from pathlib import Path

from qdrant_client import QdrantClient
from src.rag.embedder import MedicalEmbedder
from src.rag.vectorstore import QdrantVectorStore
from src.ingestion.extractors.pdf_chunk_extractor import extract_pdf_in_chunks


def main():

    print("Initializing Vector DB and Models...")

    client = QdrantClient(path="./storage/qdrant_db")

    embedder = MedicalEmbedder()

    vector_store = QdrantVectorStore(client, embedder)

    target_folder = Path("./storage/finance_docs")
    logs_dir = Path("./extraction_logs")
    merged_dir = logs_dir / "merged_docs"
    merged_dir.mkdir(parents=True, exist_ok=True)

    target_collection = "knowledge_base"

    pdf_files = list(target_folder.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDFs")

    # Track statistics
    total = len(pdf_files)
    skipped = 0
    ingested = 0

    for pdf_file in pdf_files:
        print(f"\n{'=' * 60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'=' * 60}")

        # Generate document_id the same way you use in ingestion
        document_id = pdf_file.stem
        merged_file_path = merged_dir / f"{document_id}_complete.md"

        # Check if document already exists in vector store
        if vector_store.document_exists(
            document_id=document_id,
            target_collection=target_collection,
        ):
            print(f"⏭️ Skipping {pdf_file.name} - already exists in {target_collection}")
            skipped += 1
            continue

        # Check if merged markdown already exists
        if merged_file_path.exists():
            print(f"📄 Found existing merged markdown: {merged_file_path.name}")
            print(f"   Using existing file (skipping Docling)")
            markdown_text = merged_file_path.read_text(encoding="utf-8")

        else:
            print(f"📄 No merged markdown found. Extracting from PDF...")

            try:
                # Use chunked Docling extraction
                chunks = extract_pdf_in_chunks(
                    file_path=str(pdf_file), chunk_size=5, output_dir="extraction_logs"
                )

                # Filter out failed chunks
                valid_chunks = [
                    chunk for chunk in chunks if chunk and chunk.get("content")
                ]

                if not valid_chunks:
                    print(f"❌ No valid content extracted from {pdf_file.name}")
                    continue

                print(f"✓ Extracted {len(valid_chunks)} chunks from PDF")

                # Merge chunks into a single markdown file
                print(f"📝 Merging chunks into {merged_file_path.name}...")

                merged_text = ""
                for chunk in valid_chunks:
                    merged_text += chunk["content"]
                    merged_text += "\n\n"

                # Save merged file
                merged_file_path.write_text(merged_text, encoding="utf-8")
                markdown_text = merged_text

                print(f"✓ Created merged file: {merged_file_path}")

            except Exception as e:
                print(f"❌ Extraction failed for {pdf_file.name}: {e}")
                continue

        # Ingest the document
        print(f"💾 Ingesting {document_id} into Qdrant...")
        print(f"   Markdown size: {len(markdown_text):,} chars")

        # Remove source_file parameter if your ingest_docs doesn't have it
        vector_store.ingest_docs(
            document_id=document_id,
            patient_id="COMPLIANCE_DOMAIN",
            report_type="finance_compliance",
            markdown_text=markdown_text,
            role="system",
            # source_file=str(pdf_file),  # Comment this out if not needed
            target_collection=target_collection,
        )

        print(f"✅ Successfully ingested {pdf_file.name}")
        ingested += 1

    print(f"\n{'=' * 60}")
    print(f"📊 Summary: {ingested} ingested, {skipped} skipped, {total} total")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

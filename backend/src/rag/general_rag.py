import os
from pathlib import Path

from qdrant_client import QdrantClient
from langchain_community.document_loaders import PyMuPDFLoader

from src.rag.vectorstore import QdrantVectorStore
from src.rag.embedder import MedicalEmbedder


def main():

    print("Initializing Vector DB and Models...")

    client = QdrantClient(path="./storage/qdrant_db")

    embedder = MedicalEmbedder()

    vector_store = QdrantVectorStore(client, embedder)

    target_folder = Path("./storage/general_docs")

    pdf_files = list(target_folder.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDFs")

    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")

        try:
            loader = PyMuPDFLoader(str(pdf_file))

            docs = loader.load()

            text = "\n".join(doc.page_content for doc in docs)

            print(f"Extracted {len(text):,} chars")

            vector_store.ingest_docs(
                document_id=pdf_file.stem,
                patient_id="PUBLIC_DOMAIN",
                report_type="general_health",
                markdown_text=text,
                role="system",
                target_collection="general_health",
            )

            print(f"Successfully ingested {pdf_file.name}")

        except Exception as e:
            print(f"Failed: {pdf_file.name}")

            print(e)


if __name__ == "__main__":
    main()

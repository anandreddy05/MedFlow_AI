"""
QdrantVectorStore - Handles document ingestion, chunking, and vector storage.

This module is responsible for:
1. Cleaning raw markdown documents (removing images, TOC, references)
2. Splitting documents into chunks with header preservation
3. Generating dense and sparse embeddings
4. Storing vectors in Qdrant for hybrid search

The chunking strategy differs by document type:
- Finance/Compliance: Larger chunks (1200 chars) - dense policy text
- General Health: Medium chunks (1000 chars) - mixed content (burns, CPR, nutrition)
- Medical Documents: Small chunks (500 chars) - patient records (prescriptions, labs)
"""

import re
import uuid
import os
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langfuse import observe

from src.utils.logger import get_logger, log_ctx, timed_log
from .embedder import MedicalEmbedder

logger = get_logger(__name__)


class QdrantVectorStore:
    """
    Vector store for medical documents using Qdrant with hybrid search.

    Two collections:
    - medical_documents: Patient-specific records (prescriptions, lab results)
    - knowledge_base: General health and finance compliance documents
    """

    def __init__(self, client: QdrantClient, embedder: MedicalEmbedder):
        """
        Initialize the vector store and create collections if they don't exist.

        Args:
            client: Qdrant client connection
            embedder: Local embedding model for dense and sparse vectors
        """
        logger.info("Initializing Qdrant Vector DB")

        self.client = client
        self.embedder = embedder
        self.collection_name = "medical_documents"
        self.knowledge_collection = "knowledge_base"

        self._setup_collection()

    # ============================================================
    # COLLECTION SETUP
    # ============================================================

    def _setup_collection(self):
        """
        Create Qdrant collections with hybrid search support.

        Each collection has:
        - Dense vectors: Semantic search (384-dim BGE embeddings)
        - Sparse vectors: BM25-style keyword search
        - Payload indexes: Fast filtering by patient_id, role, created_at
        """
        # Create medical_documents collection for patient records
        if not self.client.collection_exists(self.collection_name):
            # Configure dense vector (semantic search)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=384,  # BGE-small embedding dimension
                        distance=models.Distance.COSINE,
                    )
                },
                # Configure sparse vector (keyword/BM25 search)
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )

            # Add indexes for fast filtering (like database indexes)
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="patient_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="role",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="created_at",
                field_schema=models.PayloadSchemaType.INTEGER,
            )

            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            logger.info(
                "Qdrant collection created",
                extra=log_ctx(collection=self.collection_name),
            )

        # Create knowledge_base collection for general health and finance docs
        if not self.client.collection_exists(self.knowledge_collection):
            self.client.create_collection(
                collection_name=self.knowledge_collection,
                vectors_config={
                    "dense": models.VectorParams(
                        size=384, distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
            # Index by report_type to isolate finance from general health
            self.client.create_payload_index(
                self.knowledge_collection,
                "report_type",
                models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                self.knowledge_collection, "role", models.PayloadSchemaType.KEYWORD
            )
            self.client.create_payload_index(
                self.knowledge_collection,
                "created_at",
                models.PayloadSchemaType.INTEGER,
            )
            self.client.create_payload_index(
                self.knowledge_collection,
                "document_id",
                models.PayloadSchemaType.KEYWORD,
            )
            logger.info(
                "Qdrant collection created",
                extra=log_ctx(collection=self.knowledge_collection),
            )

        self._ensure_payload_index(
            self.knowledge_collection, "document_id", models.PayloadSchemaType.KEYWORD
        )
        self._ensure_payload_index(
            self.collection_name, "document_id", models.PayloadSchemaType.KEYWORD
        )

    def _ensure_payload_index(
        self, collection_name: str, field_name: str, field_schema: models.PayloadSchemaType
    ) -> None:
        """Create a payload index if missing (required by Qdrant Cloud for filters)."""
        if not self.client.collection_exists(collection_name):
            return
        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )
            logger.info(
                "Payload index ensured",
                extra=log_ctx(collection=collection_name, field=field_name),
            )
        except Exception as e:
            logger.warning(
                "Payload index creation skipped",
                extra=log_ctx(
                    collection=collection_name,
                    field=field_name,
                    error=str(e),
                ),
            )

    # ============================================================
    # DOCUMENT UTILITIES
    # ============================================================

    def document_exists(self, document_id: str, target_collection: str) -> bool:
        """
        Check if a document already exists in the collection.

        Used to avoid duplicate ingestion during re-indexing.

        Args:
            document_id: Unique identifier for the document
            target_collection: Which collection to check

        Returns:
            True if document exists, False otherwise
        """
        try:
            points, _ = self.client.scroll(
                collection_name=target_collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            exists = len(points) > 0
            logger.debug(
                "Document existence check",
                extra=log_ctx(document_id=document_id, collection=target_collection, exists=exists),
            )
            return exists
        except Exception:
            logger.exception(
                "Error checking document existence",
                extra=log_ctx(document_id=document_id, collection=target_collection),
            )
            return False

    # ============================================================
    # MEDICAL DOCUMENT CHUNKING (Patient Records)
    # ============================================================

    def _medical_chunking(self, text: str):
        """
        Chunk patient medical records (prescriptions, lab reports).

        These documents are already structured as JSON/Key-Value pairs,
        so we use small, simple chunks with minimal overlap.

        Args:
            text: Markdown text from extracted medical document

        Returns:
            List of text chunks
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Small chunks for structured data
            chunk_overlap=50,  # Minimal overlap
        )
        return splitter.split_text(text)

    # ============================================================
    # DOCUMENT CLEANING (Remove Noise)
    # ============================================================

    def pre_process_document(self, text: str) -> str:
        """
        Clean raw markdown before chunking.

        Removes:
        - Image placeholders: <!-- image -->
        - Table of Contents sections
        - "In This Issue" sections
        - References sections
        - Image credits and source URLs
        - Watermarks (e.g., "PEPID")

        Preserves:
        - Medical URLs (MEDLINEPLUS, etc.) - useful for citations
        - All content that aids retrieval

        Args:
            text: Raw markdown text

        Returns:
            Cleaned text ready for chunking
        """
        if not text:
            return text

        # ---------------------------------------------------------
        # 1. Remove image placeholders
        #    Docling adds <!-- image --> tags for embedded images
        # ---------------------------------------------------------
        text = re.sub(
            r"<!--\s*image\s*-->",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # ---------------------------------------------------------
        # 2. Remove Table of Contents sections
        #    These are long lists of page numbers that add no value
        # ---------------------------------------------------------
        text = re.sub(
            r"(?ims)^#+\s*table\s+of\s+contents.*?(?=^#+|\Z)",
            "",
            text,
        )

        # ---------------------------------------------------------
        # 3. Remove "In This Issue" sections (common in magazines/guides)
        # ---------------------------------------------------------
        text = re.sub(
            r"(?ims)^#+\s*in\s+this\s+issue.*?(?=^#+|\Z)",
            "",
            text,
        )

        # ---------------------------------------------------------
        # 4. Remove references section
        #    Only removes exact "References" heading, not "References for X"
        # ---------------------------------------------------------
        text = re.sub(
            r"(?ims)^#+\s*references\s*$.*?(?=^#+|\Z)",
            "",
            text,
        )

        # ---------------------------------------------------------
        # 5. Remove image credits and attribution lines
        # ---------------------------------------------------------
        text = re.sub(
            r"Image.*?Available at .*?$",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        # ---------------------------------------------------------
        # 6. Remove PEPID watermark
        # ---------------------------------------------------------
        text = re.sub(
            r"(?i)^PEPID\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )

        # ---------------------------------------------------------
        # 7. Normalize whitespace
        #    Replace 3+ newlines with 2 (single blank line)
        # ---------------------------------------------------------
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    # ============================================================
    # KNOWLEDGE CHUNKING (Main Logic)
    # ============================================================

    def _knowledge_chunking(self, text: str, report_type: str = None):
        """
        Main chunking function for knowledge_base documents.

        Processing pipeline:
        1. Clean document (remove images, TOC, references)
        2. Split by markdown headers (h1, h2, h3)
        3. Recursively chunk with size based on document type
        4. Preserve header hierarchy in each chunk

        Chunk sizes:
        - Finance compliance: 1200 chars (dense policy text, tables)
        - General health: 1000 chars (mixed content)

        Args:
            text: Raw markdown text
            report_type: Type of document (finance_compliance or general_health)

        Returns:
            List of text chunks ready for embedding
        """
        if not text:
            return []

        # ---------------------------------------------------------
        # STEP 1: Clean the document
        # Remove noise that doesn't help retrieval
        # ---------------------------------------------------------
        text = self.pre_process_document(text)

        # ---------------------------------------------------------
        # STEP 2: Split by markdown headers
        # This creates sections based on h1, h2, h3
        # ---------------------------------------------------------
        headers_to_split_on = [
            ("#", "h1"),  # Main title
            ("##", "h2"),  # Section
            ("###", "h3"),  # Subsection
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )

        sections = markdown_splitter.split_text(text)

        # Filter out tiny/empty sections that add no value
        # Example: "## References" with no content
        filtered_sections = []
        for section in sections:
            if len(section.page_content.strip()) >= 50:  # Minimum 50 characters
                filtered_sections.append(section)
            else:
                logger.debug("Skipping tiny document section during chunking")

        # ---------------------------------------------------------
        # STEP 3: Set chunk size based on document type
        # Different documents need different strategies
        # ---------------------------------------------------------
        if report_type == "finance_compliance":
            # Finance documents: dense policy text, multiple table rows
            chunk_size = 1200
            chunk_overlap = 250
        else:
            # General health: mixed content (burns, CPR, first aid)
            chunk_size = 1000
            chunk_overlap = 200

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunks = []

        # ---------------------------------------------------------
        # STEP 4: Preserve header hierarchy in each chunk
        # Each chunk contains its parent headers for context
        # ---------------------------------------------------------
        for section in filtered_sections:
            # Build header path (e.g., "# Burns\n## Treatment")
            header_parts = []

            if section.metadata.get("h1"):
                header_parts.append(f"# {section.metadata['h1']}")

            if section.metadata.get("h2"):
                header_parts.append(f"## {section.metadata['h2']}")

            if section.metadata.get("h3"):
                header_parts.append(f"### {section.metadata['h3']}")

            header_context = "\n".join(header_parts)

            # Split the section content into smaller chunks if needed
            sub_chunks = splitter.split_text(section.page_content)

            # Attach headers to each sub-chunk
            for sub_chunk in sub_chunks:
                if header_context:
                    full_chunk = f"{header_context}\n{sub_chunk}"
                else:
                    full_chunk = sub_chunk
                chunks.append(full_chunk)

        return chunks

    # ============================================================
    # DOCUMENT INGESTION (Main Entry Point)
    # ============================================================

    @observe(as_type="span", name="Vector_Ingestion_Pipeline")
    @timed_log(logger, "vector_ingestion")
    def ingest_docs(
        self,
        document_id: str,
        patient_id: str,
        report_type: str,
        markdown_text: str,
        role: str,
        created_at: datetime = None,
        target_collection: str = "medical_documents",
    ):
        """
        Main entry point for ingesting documents into the vector store.

        This method:
        1. Saves original document for debugging
        2. Generates chunks (different strategies for different collections)
        3. Saves chunks for debugging
        4. Creates dense and sparse embeddings
        5. Stores vectors in Qdrant

        Args:
            document_id: Unique identifier for this document
            patient_id: Associated patient ID (or "PUBLIC_DOMAIN" for knowledge_base)
            report_type: Type of report (finance_compliance, general_health, etc.)
            markdown_text: Extracted markdown content
            role: User role (system, nurse, doctor, etc.)
            created_at: Timestamp (defaults to now)
            target_collection: Which collection to store in
        """
        if not markdown_text or markdown_text.strip() == "":
            logger.warning(
                "Document ingestion skipped: empty markdown",
                extra=log_ctx(document_id=document_id),
            )
            return

        logger.info(
            "Document ingestion started",
            extra=log_ctx(
                document_id=document_id,
                patient_id=patient_id,
                report_type=report_type,
                target_collection=target_collection,
            ),
        )

        # ---------------------------------------------------------
        # Create debug directory and save original document
        # This helps verify pre-processing worked correctly
        # ---------------------------------------------------------
        pre_processed_dir = "extraction_logs/pre_processed"
        os.makedirs(pre_processed_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save original text before any processing
        original_path = f"{pre_processed_dir}/{document_id}_{timestamp}_original.md"
        with open(original_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        logger.debug(
            "Saved original markdown for ingestion debug",
            extra=log_ctx(path=original_path),
        )

        # ---------------------------------------------------------
        # Generate chunks based on collection type
        # ---------------------------------------------------------
        if target_collection == self.collection_name:
            # Medical documents: simple chunking
            chunks = self._medical_chunking(markdown_text)
            pre_processed_path = (
                f"{pre_processed_dir}/{document_id}_{timestamp}_chunks.txt"
            )
        else:
            # Knowledge base: full pre-processing + header preservation
            chunks = self._knowledge_chunking(markdown_text, report_type=report_type)
            pre_processed_path = (
                f"{pre_processed_dir}/{document_id}_{timestamp}_chunks.txt"
            )

            # Also save the cleaned text for debugging
            cleaned_text = self.pre_process_document(markdown_text)
            cleaned_path = f"{pre_processed_dir}/{document_id}_{timestamp}_cleaned.md"
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)
            logger.debug(
                "Saved cleaned document for ingestion debug",
                extra=log_ctx(path=cleaned_path),
            )

        # ---------------------------------------------------------
        # Save chunks for debugging
        # This helps verify chunk sizes and content
        # ---------------------------------------------------------
        with open(pre_processed_path, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks):
                f.write(f"{'=' * 60}\nCHUNK {i + 1} ({len(chunk)} chars)\n{'=' * 60}\n")
                f.write(chunk)
                f.write("\n\n")
        logger.debug(
            "Saved ingestion chunks for debug",
            extra=log_ctx(path=pre_processed_path, chunk_count=len(chunks)),
        )

        # ---------------------------------------------------------
        # Create embeddings and store in Qdrant
        # ---------------------------------------------------------
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        timestamp_int = int(created_at.timestamp())

        # Generate dense (semantic) and sparse (keyword) embeddings
        dense_vectors = self.embedder.embed_batch(chunks)
        sparse_vectors = self.embedder.embed_sparse_batch(chunks)

        # Create Qdrant points (vectors + metadata)
        points = []
        for i, (chunk, dense_vector, sparse_vector) in enumerate(
            zip(chunks, dense_vectors, sparse_vectors)
        ):
            point_id = str(uuid.uuid4())
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vector,
                        "sparse": models.SparseVector(
                            indices=sparse_vector["indices"],
                            values=sparse_vector["values"],
                        ),
                    },
                    payload={
                        "document_id": document_id,
                        "patient_id": patient_id,
                        "report_type": report_type,
                        "role": role,
                        "content_markdown": chunk,
                        "chunk_index": i,
                        "created_at": timestamp_int,
                    },
                )
            )

        # Upload to Qdrant
        batch_size = 50

        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]

            self.client.upsert(
                collection_name=target_collection,
                points=batch,
            )

            logger.info(
                f"Uploaded batch {(i // batch_size) + 1}",
                extra=log_ctx(
                    uploaded=len(batch),
                    total=len(points),
                ),
            )

from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
from datetime import datetime, timezone

from .embedder import MedicalEmbedder


class QdrantVectorStore:
    def __init__(self, client: QdrantClient, embedder: MedicalEmbedder):
        print("Initializing Qdrant Vector DB.")

        self.client = client
        self.embedder = embedder
        self.collection_name = "medical_documents"
        self.general_collection = "general_health"
        self.embedder = MedicalEmbedder()

        self._setup_collection()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )

    def _setup_collection(self):
        if not self.client.collection_exists(self.collection_name):
            # 1. Setup the Dense Vector (Semantic) configuration
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=384,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )

            # 3. Security/RBAC Indexes (For fast pre-filtering)
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

            print(
                f"Collection '{self.collection_name}' "
                f"created successfully with hybrid retrieval."
            )
        if not self.client.collection_exists(self.general_collection):
            self.client.create_collection(
                collection_name=self.general_collection,
                vectors_config={
                    "dense": models.VectorParams(
                        size=384, distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        modifier=models.Modifier.IDF
                    )
                },
            )
        self.client.create_payload_index(
            self.general_collection, "report_type", models.PayloadSchemaType.KEYWORD
        )
        print(f"Collection '{self.general_collection}' created.")

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
        if not markdown_text or markdown_text.strip() == "":
            return

        chunks = self.text_splitter.split_text(markdown_text)
        if not chunks:
            return

        if created_at is None:
            created_at = datetime.now(timezone.utc)

        timestamp_int = int(created_at.timestamp())

        dense_vectors = self.embedder.embed_batch(chunks)
        sparse_vectors = self.embedder.embed_sparse_batch(chunks)
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
        self.client.upsert(collection_name=target_collection, points=points)
        print(f"Successfully ingested {len(points)} chunks into {target_collection}")

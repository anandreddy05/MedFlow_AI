from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed.rerank.cross_encoder import TextCrossEncoder

from .embedder import MedicalEmbedder
from .optimizer import QueryOptimizer


class MedicalRetriever:
    def __init__(self, client: QdrantClient, embedder: MedicalEmbedder):
        print("Initializing Hybrid Medical Retriever...")

        self.client = client  
        self.embedder = embedder
        self.collection_name = "medical_documents"
        self.embedder = MedicalEmbedder()
        self.optimizer = QueryOptimizer()

        print("Loading FastEmbed Cross-Encoder Reranker...")
        self.reranker = TextCrossEncoder(model_name="BAAI/bge-reranker-base")

    def retrieve(self, query: str, patient_id: str, limit: int = 20):
        """
        Executes a secure Hybrid Search (Dense + BM25) for a specific patient.
        """

        expansion_terms = self.optimizer.expand_query(query)
        search_query = f"{query} {expansion_terms}".strip()

        print("\n--- RAG PIPELINE ---")
        print(f"Original Query (For Reranker + Retriver): {query}")
        print(f"Combined Query (For Qdrant):   {search_query}\n")

        # 1. Generate both vectors using your custom local embedder
        dense_vector = self.embedder.embed_text(query)
        sparse_vector_dict = self.embedder.embed_sparse_text(search_query)

        sparse_vector = models.SparseVector(
            indices=sparse_vector_dict["indices"],
            values=sparse_vector_dict["values"],
        )

        # 2. Build the strict RBAC / Data Isolation Filter
        # This guarantees the AI can never retrieve another patient's data
        security_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="patient_id",
                    match=models.MatchValue(value=patient_id),
                )
            ]
        )

        # 3. Execute the Hybrid Prefetch Query with RRF Fusion
        initial_results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                # Search 1: Semantic Meaning (Dense)
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=limit,
                    filter=security_filter,
                ),
                # Search 2: Exact Medical Keywords (Sparse/BM25)
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    limit=limit,
                    filter=security_filter,
                ),
            ],
            # Fuse the two lists together using Reciprocal Rank Fusion
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        )
        if not initial_results.points:
            return "No medical records found for this query."

        documents = []
        chunk_texts = []

        for point in initial_results.points:
            text = point.payload.get("content_markdown", "")
            documents.append(point)
            chunk_texts.append(text)
        new_scores = list(self.reranker.rerank(query, chunk_texts))

        scored_documents = list(zip(documents, new_scores))
        scored_documents.sort(key=lambda x: x[1], reverse=True)

        retrieved_docs = []

        for best_point, score in scored_documents[:limit]:
            payload = best_point.payload

            retrieved_docs.append(
                {
                    "content": payload.get("content_markdown", ""),
                    "score": float(score),
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "patient_id": payload.get("patient_id"),
                        "report_type": payload.get("report_type"),
                        "source_file": payload.get("source_file"),
                        "chunk_id": payload.get("chunk_id"),
                        "page": payload.get("page"),
                    },
                }
            )

        return retrieved_docs

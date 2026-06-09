from qdrant_client import QdrantClient
from qdrant_client.http import models
# from fastembed.rerank.cross_encoder import TextCrossEncoder
from langfuse import observe
import os

from src.utils.logger import get_logger, log_ctx, timed_log
from .embedder import MedicalEmbedder
from .optimizer import QueryOptimizer
import cohere
from dotenv import load_dotenv

load_dotenv(override=True)
cohere_api_key = os.getenv("COHERE_API_KEY")

logger = get_logger(__name__)


class MedicalRetriever:
    def __init__(self, client: QdrantClient, embedder: MedicalEmbedder):
        logger.info("Initializing Hybrid Medical Retriever")

        self.client = client
        self.embedder = embedder
        self.collection_name = "medical_documents"
        self.optimizer = QueryOptimizer()

        logger.info("Loading FastEmbed Cross-Encoder Reranker")
        # self.reranker = TextCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.cohere = cohere.ClientV2(api_key=cohere_api_key)

    @observe(as_type="span", name="Qdrant_Hybrid_Search")
    @timed_log(logger, "qdrant_retrieval")
    def retrieve(
        self,
        query: str,
        patient_id: str,
        collection_name: str = "medical_documents",
        retrieval_k: int = 20,
        report_type: str = None,
        final_k: int = 5,
    ):
        """
        Executes a secure Hybrid Search (Dense + BM25) for a specific patient.
        """

        expansion_terms = self.optimizer.expand_query(query)
        search_query = f"{query} \n{expansion_terms}".strip()

        logger.info(
            "Qdrant retrieval query",
            extra=log_ctx(
                query=query,
                patient_id=patient_id,
                collection_name=collection_name,
                report_type=report_type,
                search_query=search_query,
            ),
        )

        # 1. Generate both vectors using your custom local embedder
        dense_vector = self.embedder.embed_text(query)
        sparse_vector_dict = self.embedder.embed_sparse_text(search_query)

        sparse_vector = models.SparseVector(
            indices=sparse_vector_dict["indices"],
            values=sparse_vector_dict["values"],
        )

        # 2. Build the strict RBAC / Data Isolation Filter
        filter_conditions = []

        # Always filter by patient_id for medical_documents (RBAC)
        if collection_name == "medical_documents":
            filter_conditions.append(
                models.FieldCondition(
                    key="patient_id",
                    match=models.MatchValue(value=patient_id),
                )
            )

        # For knowledge_base, scope by report_type to avoid cross-contamination
        if collection_name == "knowledge_base" and report_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="report_type",
                    match=models.MatchValue(value=report_type),
                )
            )

        security_filter = models.Filter(must=filter_conditions)

        # 3. Execute the Hybrid Prefetch Query with RRF Fusion
        initial_results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=retrieval_k,
                    filter=security_filter,
                ),
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    limit=retrieval_k,
                    filter=security_filter,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=retrieval_k,
        )

        if not initial_results.points:
            logger.warning(
                "Qdrant retrieval returned no results",
                extra=log_ctx(
                    query=query,
                    patient_id=patient_id,
                    collection_name=collection_name,
                ),
            )
            return []

        # 4. Extract for Reranker
        documents = []
        chunk_texts = []

        for point in initial_results.points:
            text = point.payload.get("content_markdown", "")
            documents.append(point)
            chunk_texts.append(text)

        # 5. Get true semantic scores from Cross-Encoder
        # new_scores = list(self.reranker.rerank(query, chunk_texts))
        # scored_documents = list(zip(documents, new_scores))

        # final_scored_documents = [
        #     (doc, float(score)) for doc, score in scored_documents
        # ]

        # final_scored_documents.sort(key=lambda x: x[1], reverse=True)

        # retrieved_docs = []
        # for best_point, score in final_scored_documents[:final_k]:
        #     payload = best_point.payload
        #     retrieved_docs.append(
        #         {
        #             "content": payload.get("content_markdown", ""),
        #             "score": float(score),
        #             "metadata": {
        #                 "document_id": payload.get("document_id"),
        #                 "patient_id": payload.get("patient_id"),
        #                 "report_type": payload.get("report_type"),
        #                 "source_file": payload.get("source_file"),
        #                 "chunk_id": payload.get("chunk_id"),
        #                 "page": payload.get("page"),
        #                 "created_at": payload.get("created_at"),
        #             },
        #         }
        #     )

        # logger.info(
        #     "Qdrant retrieval completed",
        #     extra=log_ctx(
        #         query=query,
        #         patient_id=patient_id,
        #         collection_name=collection_name,
        #         result_count=len(retrieved_docs),
        #     ),
        # )
        rerank_response = self.cohere.rerank(
            model="rerank-v3.5",
            query=query,
            documents=chunk_texts,
            top_n=final_k
        )

        retrieved_docs = []

        for result in rerank_response.results:
            point = documents[result.index]
            score = result.relevance_score

            payload = point.payload

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
                        "created_at": payload.get("created_at"),
                    },
                }
            )
        return retrieved_docs

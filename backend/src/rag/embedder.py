from typing import List
from fastembed import TextEmbedding, SparseTextEmbedding


class MedicalEmbedder:
    def __init__(self):
        """
        Local Hybrid Embedder
        - Dense embeddings for semantic retrieval
        - Sparse embeddings for BM25-style keyword retrieval
        """

        print("Loading Dense Embedding Model...")
        self.dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

        print("Loading Sparse Embedding Model...")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    # =========================================================
    # Dense Embeddings
    # =========================================================

    def embed_text(self, text: str) -> List[float]:
        vector = list(self.dense_model.embed([text]))[0]
        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        vectors = list(self.dense_model.embed(texts))
        return [v.tolist() for v in vectors]

    # =========================================================
    # Sparse Embeddings
    # =========================================================

    def embed_sparse_text(self, text: str):
        sparse_vector = list(self.sparse_model.embed([text]))[0]

        return {
            "indices": sparse_vector.indices.tolist(),
            "values": sparse_vector.values.tolist(),
        }

    def embed_sparse_batch(self, texts: List[str]):
        sparse_vectors = list(self.sparse_model.embed(texts))

        formatted_sparse_vectors = []

        for vec in sparse_vectors:
            formatted_sparse_vectors.append(
                {
                    "indices": vec.indices.tolist(),
                    "values": vec.values.tolist(),
                }
            )

        return formatted_sparse_vectors

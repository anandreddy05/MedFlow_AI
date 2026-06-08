import os

from qdrant_client import QdrantClient
from langfuse import get_client
from langfuse.langchain import CallbackHandler

from src.ingestion.extractor import BaseExtractor
from src.rag.vectorstore import QdrantVectorStore
from src.rag.retriever import MedicalRetriever
from src.rag.embedder import MedicalEmbedder
from src.rag.utils.intent_classifier import IntentRouter
from src.rag.latest_context_retriever import LatestContextRetriever
from src.utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv(override=True)

logger = get_logger(__name__)

logger.info("Booting up Shared AI Resources")
shared_qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
shared_embedder = MedicalEmbedder()

vector_store = QdrantVectorStore(client=shared_qdrant_client, embedder=shared_embedder)
retriever = MedicalRetriever(client=shared_qdrant_client, embedder=shared_embedder)
latest_retriever = LatestContextRetriever()

intent_router = IntentRouter()
extractor = BaseExtractor()

langfuse = get_client()
handler = CallbackHandler()

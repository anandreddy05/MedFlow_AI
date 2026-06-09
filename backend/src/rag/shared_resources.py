import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langfuse import get_client
from langfuse.langchain import CallbackHandler

# from src.ingestion.extractor import BaseExtractor
from src.rag.vectorstore import QdrantVectorStore
from src.rag.retriever import MedicalRetriever
from src.rag.embedder import MedicalEmbedder
from src.rag.utils.intent_classifier import IntentRouter
from src.rag.latest_context_retriever import LatestContextRetriever
from src.utils.logger import get_logger

load_dotenv(override=True)

logger = get_logger(__name__)

# Singleton instances
_shared_qdrant_client = None
_shared_embedder = None
_vector_store = None
_retriever = None
_latest_retriever = None
_intent_router = None
_extractor = None
_langfuse = None
_handler = None


def get_qdrant_client():
    global _shared_qdrant_client

    if _shared_qdrant_client is None:
        logger.info("Initializing Qdrant Client")
        _shared_qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )

    return _shared_qdrant_client


def get_embedder():
    global _shared_embedder

    if _shared_embedder is None:
        logger.info("Initializing Medical Embedder")
        _shared_embedder = MedicalEmbedder()

    return _shared_embedder


def get_vector_store():
    global _vector_store

    if _vector_store is None:
        logger.info("Initializing Qdrant Vector Store")
        _vector_store = QdrantVectorStore(
            client=get_qdrant_client(),
            embedder=get_embedder(),
        )

    return _vector_store


def get_retriever():
    global _retriever

    if _retriever is None:
        logger.info("Initializing Medical Retriever")
        _retriever = MedicalRetriever(
            client=get_qdrant_client(),
            embedder=get_embedder(),
        )

    return _retriever


def get_latest_retriever():
    global _latest_retriever

    if _latest_retriever is None:
        logger.info("Initializing Latest Context Retriever")
        _latest_retriever = LatestContextRetriever()

    return _latest_retriever


def get_intent_router():
    global _intent_router

    if _intent_router is None:
        logger.info("Initializing Intent Router")
        _intent_router = IntentRouter()

    return _intent_router


# def get_extractor():
#     global _extractor

#     if _extractor is None:
#         logger.info("Initializing Base Extractor")
#         _extractor = BaseExtractor()

#     return _extractor


def get_langfuse():
    global _langfuse

    if _langfuse is None:
        logger.info("Initializing Langfuse Client")
        _langfuse = get_client()

    return _langfuse


def get_handler():
    global _handler

    if _handler is None:
        logger.info("Initializing Langfuse Callback Handler")
        _handler = CallbackHandler()

    return _handler

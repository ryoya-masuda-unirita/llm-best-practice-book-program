"""ChromaDB client configuration for knowledge base storage."""

import os

import chromadb
from chromadb.config import Settings

from src.logger import make_logger

logger = make_logger(__name__)

CHROMA_HOST = os.getenv("CHROMA_HOST", None)
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")

if CHROMA_HOST:
    logger.info(f"Connecting to remote ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
    chroma_client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=int(CHROMA_PORT),
        settings=Settings(anonymized_telemetry=False),
    )
else:
    logger.info("Using local ChromaDB with persistent storage at ./data/chromadb")
    chroma_client = chromadb.Client(
        Settings(
            persist_directory="./data/chromadb",
            anonymized_telemetry=False,
        )
    )

KNOWLEDGE_COLLECTION_NAME = "character_knowledge"


def get_knowledge_collection():
    """Get or create the knowledge collection for character data."""
    try:
        collection = chroma_client.get_or_create_collection(
            name=KNOWLEDGE_COLLECTION_NAME,
            metadata={
                "description": "Storage for character generation requests and responses",
                "hnsw:space": "cosine",
            },
            embedding_function=None,
        )
        logger.info(f"Knowledge collection '{KNOWLEDGE_COLLECTION_NAME}' initialized with custom embeddings")
        return collection
    except Exception as e:
        logger.error(f"Error initializing knowledge collection: {e}")
        raise

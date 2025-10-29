"""ChromaDB client configuration for knowledge base storage."""

import os

import chromadb
from chromadb.config import Settings

from src.logger import make_logger

logger = make_logger(__name__)

# Get ChromaDB configuration from environment
CHROMA_HOST = os.getenv("CHROMA_HOST", None)
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")

# Initialize ChromaDB client
# If CHROMA_HOST is set, use HTTP client (for Docker)
# Otherwise, use persistent client (for local development)
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

# Collection names for different data types
KNOWLEDGE_COLLECTION_NAME = "character_knowledge"


def get_knowledge_collection():
    """
    Get or create the knowledge collection for character data.

    Note: This collection uses custom embeddings from OpenAI/Gemini APIs,
    not ChromaDB's default embedding function. The embedding_function is
    set to None to indicate we provide our own embeddings.
    """
    try:
        collection = chroma_client.get_or_create_collection(
            name=KNOWLEDGE_COLLECTION_NAME,
            metadata={
                "description": "Storage for character generation requests and responses",
                "hnsw:space": "cosine",  # Use cosine similarity for semantic search
            },
            embedding_function=None,  # We provide custom embeddings from OpenAI/Gemini
        )
        logger.info(f"Knowledge collection '{KNOWLEDGE_COLLECTION_NAME}' initialized with custom embeddings")
        return collection
    except Exception as e:
        logger.error(f"Error initializing knowledge collection: {e}")
        raise

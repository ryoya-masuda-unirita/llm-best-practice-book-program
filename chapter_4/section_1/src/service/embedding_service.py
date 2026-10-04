"""Embedding service using Amazon Titan Text Embeddings on Bedrock."""

import asyncio
import json

from src.client.llm_client import bedrock_runtime_client
from src.logger import make_logger

logger = make_logger(__name__)

BEDROCK_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
BEDROCK_EMBEDDING_DIMENSION = 1024


def _get_bedrock_embedding_sync(text: str) -> list[float]:
    logger.debug(f"Generating Bedrock embedding for text: {text[:50]}...")

    response = bedrock_runtime_client.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL,
        body=json.dumps({"inputText": text, "dimensions": BEDROCK_EMBEDDING_DIMENSION}),
    )
    embedding = json.loads(response["body"].read())["embedding"]

    logger.debug(f"Generated Bedrock embedding with dimension: {len(embedding)}")
    return embedding


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector using Bedrock."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_bedrock_embedding_sync, text)


def get_embedding_dimension() -> int:
    """Get the embedding dimension for the Bedrock embedding model."""
    return BEDROCK_EMBEDDING_DIMENSION

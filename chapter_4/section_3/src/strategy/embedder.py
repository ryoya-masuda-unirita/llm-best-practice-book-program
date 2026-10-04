"""Embedder component for creating embeddings."""

import asyncio
import json

from src.client.llm_client import BedrockEmbeddingModel, bedrock_runtime_client
from src.logger import make_logger
from src.model.rag_model import Chunk, ChunkWithEmbedding
from src.strategy.base import Component

logger = make_logger(__name__)


class Embedder(Component[list[Chunk], list[ChunkWithEmbedding]]):
    """Component for creating embeddings from text chunks."""

    def __init__(self, model: BedrockEmbeddingModel = BedrockEmbeddingModel.TITAN_EMBED_TEXT_V2):
        self.model = model

    async def process(self, input_data: list[Chunk]) -> list[ChunkWithEmbedding]:
        chunks_with_embeddings = []

        for chunk in input_data:
            try:
                embedding = await self._create_embedding(chunk.text)
                chunk_with_embedding = ChunkWithEmbedding(chunk=chunk, embedding=embedding)
                chunks_with_embeddings.append(chunk_with_embedding)

            except Exception as e:
                logger.error(f"Failed to create embedding for chunk from {chunk.source_file}: {e}")
                continue

        logger.info(f"Created embeddings for {len(chunks_with_embeddings)} chunks")
        return chunks_with_embeddings

    async def _create_embedding(self, text: str) -> list[float]:
        response = await asyncio.to_thread(
            bedrock_runtime_client.invoke_model,
            modelId=self.model,
            body=json.dumps({"inputText": text}),
        )
        return json.loads(response["body"].read())["embedding"]

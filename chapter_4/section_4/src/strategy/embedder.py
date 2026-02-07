"""Embedder component for creating embeddings."""

from src.client.llm_client import GeminiEmbeddingModel, google_genai_client
from src.logger import make_logger
from src.model.rag_model import Chunk, ChunkWithEmbedding
from src.strategy.base import Component

logger = make_logger(__name__)


class Embedder(Component[list[Chunk], list[ChunkWithEmbedding]]):
    """Component for creating embeddings from text chunks."""

    def __init__(self, model: GeminiEmbeddingModel = GeminiEmbeddingModel.GEMINI_EMBEDDING_001):
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
        result = await google_genai_client.aio.models.embed_content(model=self.model, contents=text)
        return result.embeddings[0].values

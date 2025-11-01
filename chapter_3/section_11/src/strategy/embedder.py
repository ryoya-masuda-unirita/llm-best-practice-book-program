"""Embedder component for creating embeddings."""

from openai import AsyncOpenAI

from src.client.llm_client import GeminiEmbeddingModel, OpenAIEmbeddingModel, google_genai_client
from src.config import config
from src.logger import make_logger
from src.model.rag_model import Chunk, ChunkWithEmbedding
from src.strategy.base import Component

logger = make_logger(__name__)


class Embedder(Component[list[Chunk], list[ChunkWithEmbedding]]):
    """Component for creating embeddings from text chunks."""

    def __init__(
        self, model: OpenAIEmbeddingModel | GeminiEmbeddingModel = OpenAIEmbeddingModel.TEXT_EMBEDDING_3_SMALL
    ):
        """
        Initialize the embedder.

        Args:
            model: The embedding model to use
        """
        self.model = model
        self.openai_client = AsyncOpenAI(api_key=config.openai_api_key)

    async def process(self, input_data: list[Chunk]) -> list[ChunkWithEmbedding]:
        """
        Create embeddings for all chunks.

        Args:
            input_data: List of text chunks

        Returns:
            List of chunks with their embeddings
        """
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
        """
        Create embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            Embedding vector
        """
        # Determine if using OpenAI or Gemini based on model name
        if self.model in OpenAIEmbeddingModel.list_str():
            response = await self.openai_client.embeddings.create(input=text, model=self.model)
            return response.data[0].embedding
        else:
            # Gemini embedding
            result = await google_genai_client.aio.models.embed_content(model=self.model, content=text)
            return result.embeddings[0].values

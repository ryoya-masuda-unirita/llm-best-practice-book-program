"""Vector store and retriever component."""

import numpy as np

from src.client.llm_client import GeminiEmbeddingModel, google_genai_client
from src.logger import make_logger
from src.model.rag_model import Chunk, ChunkWithEmbedding
from src.strategy.base import Component

logger = make_logger(__name__)


class VectorStore:
    """In-memory vector store for storing and searching embeddings."""

    def __init__(self):
        self.chunks_with_embeddings: list[ChunkWithEmbedding] = []

    def store(self, chunks_with_embeddings: list[ChunkWithEmbedding]) -> None:
        self.chunks_with_embeddings.extend(chunks_with_embeddings)
        logger.info(f"Stored {len(chunks_with_embeddings)} chunks. Total: {len(self.chunks_with_embeddings)}")

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Chunk]:
        if not self.chunks_with_embeddings:
            logger.warning("Vector store is empty")
            return []

        query_array = np.array(query_embedding)
        similarities = []

        for chunk_with_embedding in self.chunks_with_embeddings:
            chunk_array = np.array(chunk_with_embedding.embedding)
            similarity = self._cosine_similarity(query_array, chunk_array)
            similarities.append((similarity, chunk_with_embedding.chunk))

        similarities.sort(reverse=True, key=lambda x: x[0])

        top_chunks = [chunk for _, chunk in similarities[:top_k]]
        logger.info(f"Retrieved {len(top_chunks)} chunks for query")

        return top_chunks

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class Retriever(Component[str, list[Chunk]]):
    """Component for retrieving relevant chunks based on a query."""

    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 5,
        embedding_model: GeminiEmbeddingModel = GeminiEmbeddingModel.GEMINI_EMBEDDING_001,
    ):
        self.vector_store = vector_store
        self.top_k = top_k
        self.embedding_model = embedding_model

    async def process(self, input_data: str) -> list[Chunk]:
        query_embedding = await self._create_query_embedding(input_data)
        chunks = self.vector_store.search(query_embedding, self.top_k)

        return chunks

    async def _create_query_embedding(self, query: str) -> list[float]:
        result = await google_genai_client.aio.models.embed_content(model=self.embedding_model, content=query)
        return result.embeddings[0].values

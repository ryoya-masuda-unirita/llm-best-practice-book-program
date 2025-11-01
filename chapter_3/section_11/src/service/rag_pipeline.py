"""RAG pipeline orchestrator that chains all components."""

from src.client.llm_client import GeminiEmbeddingModel, GeminiModel, OpenAIEmbeddingModel, OpenAIModel
from src.logger import make_logger
from src.model.rag_model import RAGAnswer
from src.strategy.chunker import SemanticChunker
from src.strategy.embedder import Embedder
from src.strategy.generator import AnswerGenerator, AnswerGeneratorInput
from src.strategy.loader import DocumentLoader
from src.strategy.retriever import Retriever, VectorStore

logger = make_logger(__name__)


class RAGPipeline:
    """Pipeline that orchestrates the RAG workflow."""

    def __init__(
        self,
        data_directory: str,
        chunker_model: OpenAIModel | GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        embedding_model: OpenAIEmbeddingModel | GeminiEmbeddingModel = OpenAIEmbeddingModel.TEXT_EMBEDDING_3_SMALL,
        generator_model: OpenAIModel | GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        top_k: int = 5,
    ):
        """
        Initialize the RAG pipeline.

        Args:
            data_directory: Directory containing documents to index
            chunker_model: Model for semantic chunking
            embedding_model: Model for creating embeddings
            generator_model: Model for answer generation
            top_k: Number of top chunks to retrieve
        """
        self.data_directory = data_directory
        self.vector_store = VectorStore()

        self.loader = DocumentLoader()
        self.chunker = SemanticChunker(model=chunker_model)
        self.embedder = Embedder(model=embedding_model)
        self.retriever = Retriever(vector_store=self.vector_store, top_k=top_k, embedding_model=embedding_model)
        self.generator = AnswerGenerator(model=generator_model)

        self._is_indexed = False

    async def index_documents(self) -> None:
        """
        Index all documents in the data directory.

        This method loads documents, chunks them, creates embeddings,
        and stores them in the vector store.
        """
        logger.info(f"Starting document indexing from {self.data_directory}")

        documents = await self.loader.process(self.data_directory)

        if not documents:
            logger.warning(f"No documents found in {self.data_directory}")
            return

        chunks = await self.chunker.process(documents)

        if not chunks:
            logger.warning("No chunks created from documents")
            return

        chunks_with_embeddings = await self.embedder.process(chunks)

        self.vector_store.store(chunks_with_embeddings)

        self._is_indexed = True
        logger.info("Document indexing completed")

    async def query(self, question: str) -> RAGAnswer:
        """
        Query the RAG system with a question.

        Args:
            question: The user's question

        Returns:
            Generated answer with source information

        Raises:
            RuntimeError: If documents are not indexed yet
        """
        if not self._is_indexed:
            raise RuntimeError("Documents must be indexed before querying. Call index_documents() first.")

        logger.info(f"Processing query: {question}")

        relevant_chunks = await self.retriever.process(question)

        generator_input = AnswerGeneratorInput(question=question, chunks=relevant_chunks)
        answer = await self.generator.process(generator_input)

        logger.info("Query processing completed")
        return answer

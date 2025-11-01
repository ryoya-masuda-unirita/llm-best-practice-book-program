"""Document loader component for reading files."""

from pathlib import Path

from src.logger import make_logger
from src.model.rag_model import Document
from src.strategy.base import Component

logger = make_logger(__name__)


class DocumentLoader(Component[str, list[Document]]):
    """Component for loading documents from a directory."""

    def __init__(self, file_extensions: list[str] | None = None):
        """
        Initialize the document loader.

        Args:
            file_extensions: List of file extensions to load (e.g., ['.md', '.txt']).
                           If None, defaults to ['.md']
        """
        self.file_extensions = file_extensions or [".md"]

    async def process(self, input_data: str) -> list[Document]:
        """
        Load all documents from the specified directory.

        Args:
            input_data: Path to the directory containing documents

        Returns:
            List of loaded documents
        """
        directory = Path(input_data)

        if not directory.exists() or not directory.is_dir():
            logger.error(f"Directory does not exist: {directory}")
            raise ValueError(f"Invalid directory path: {directory}")

        documents = []

        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix in self.file_extensions:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    document = Document(file_path=str(file_path), content=content)
                    documents.append(document)
                    logger.info(f"Loaded document: {file_path}")

                except Exception as e:
                    logger.error(f"Failed to load document {file_path}: {e}")
                    continue

        logger.info(f"Loaded {len(documents)} documents from {directory}")
        return documents

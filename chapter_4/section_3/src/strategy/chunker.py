"""Semantic chunker component using LLM."""

from google.genai.types import GenerateContentConfig
from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger
from src.model.rag_model import Chunk, ChunkingResponse, Document
from src.strategy.base import Component

logger = make_logger(__name__)


class SemanticChunker(Component[list[Document], list[Chunk]]):
    """Component for splitting documents into semantic chunks using LLM."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH):
        self.model = model

    async def process(self, input_data: list[Document]) -> list[Chunk]:
        all_chunks = []

        for document in input_data:
            try:
                chunks = await self._chunk_document(document)
                all_chunks.extend(chunks)
                logger.info(f"Created {len(chunks)} chunks from {document.file_path}")
            except Exception as e:
                logger.error(f"Failed to chunk document {document.file_path}: {e}")
                continue

        logger.info(f"Created total {len(all_chunks)} chunks from {len(input_data)} documents")
        return all_chunks

    async def _chunk_document(self, document: Document) -> list[Chunk]:
        lines = document.content.split("\n")
        numbered_content = "\n".join([f"{i + 1}: {line}" for i, line in enumerate(lines)])

        system_instruction = """あなたは文書を意味のあるセグメントに分割する専門家です。
与えられた文書を、トピックや意味的なまとまりに基づいて適切なセグメントに分割してください。

各セグメントは以下の条件を満たす必要があります：
1. 一つの明確なトピックや概念を扱っている
2. 文脈として独立して理解できる
3. 適切な長さ（最小3行、最大100行程度）

行番号付きのテキストが与えられるので、セグメントの開始行と終了行、そのトピックと分割理由を指定してください。"""

        user_prompt = f"""以下の文書を意味のあるセグメントに分割してください：

{numbered_content}

各セグメントについて、開始行番号、終了行番号、トピック、分割理由を提供してください。"""

        result = await google_genai_client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ChunkingResponse,
            ),
        )
        chunking_response: ChunkingResponse = result.parsed

        chunks = []
        for idx, segment in enumerate(chunking_response.segments):
            start_idx = segment.start_line - 1
            end_idx = segment.end_line

            if start_idx < 0:
                start_idx = 0
            if end_idx > len(lines):
                end_idx = len(lines)

            chunk_text = "\n".join(lines[start_idx:end_idx])

            chunk = Chunk(text=chunk_text, source_file=document.file_path, chunk_index=idx)
            chunks.append(chunk)

        return chunks

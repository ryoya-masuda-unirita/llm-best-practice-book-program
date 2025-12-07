"""Answer generator component using LLM."""

from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger
from src.model.rag_model import Chunk, RAGAnswer
from src.strategy.base import Component

logger = make_logger(__name__)


class AnswerGeneratorInput:
    """Input data for answer generator."""

    def __init__(self, question: str, chunks: list[Chunk]):
        self.question = question
        self.chunks = chunks


class AnswerGenerator(Component[AnswerGeneratorInput, RAGAnswer]):
    """Component for generating answers based on retrieved chunks."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH):
        self.model = model

    async def process(self, input_data: AnswerGeneratorInput) -> RAGAnswer:
        """Generate an answer based on the question and retrieved chunks."""
        question = input_data.question
        chunks = input_data.chunks

        if not chunks:
            logger.warning("No chunks provided for answer generation")
            return RAGAnswer(
                question=question,
                answer="申し訳ありませんが、質問に関連する情報が見つかりませんでした。",
                source_chunks=[],
            )

        context = self._build_context(chunks)
        answer = await self._generate_answer(question, context)
        source_files = list(set([chunk.source_file for chunk in chunks]))

        rag_answer = RAGAnswer(question=question, answer=answer, source_chunks=source_files)

        logger.info(f"Generated answer for question: {question}")
        return rag_answer

    def _build_context(self, chunks: list[Chunk]) -> str:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[文書{i}] (出典: {chunk.source_file})\n{chunk.text}\n")

        return "\n".join(context_parts)

    async def _generate_answer(self, question: str, context: str) -> str:
        system_instruction = """あなたは与えられた文書に基づいて質問に答える専門家です。

以下のルールに従ってください：
1. 与えられた文書の情報のみを使用して回答してください
2. 文書に記載されていない情報については推測せず、「文書には記載されていません」と答えてください
3. 回答は明確で簡潔にしてください
4. 必要に応じて、どの文書から情報を得たか参照してください
5. 日本語で回答してください"""

        user_prompt = f"""以下の文書に基づいて質問に答えてください。

【文書】
{context}

【質問】
{question}

【回答】"""

        result = await google_genai_client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        return result.text

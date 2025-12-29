"""LLM generation tools for article pipeline."""

from typing import Any, Literal
from uuid import uuid4

from google.genai.types import GenerateContentConfig
from src.agent.core.base import Tool, ToolParams, ToolResult
from src.client.llm_client import LLMProvider, google_genai_client
from src.logger import make_logger
from src.model.model import (
    ArticleHalf,
    ArticleOutline,
    ArticleReview,
    BestArticleSelection,
)
from src.prompt.prompt import (
    make_article_review_system_instruction,
    make_choose_best_first_half_system_instruction,
    make_first_half_generation_system_instruction,
    make_outline_generation_system_instruction,
    make_second_half_generation_system_instruction,
    make_second_half_regeneration_system_instruction,
)

logger = make_logger(__name__)


async def _generate_with_gemini(
    system_instruction: str,
    user_content: str,
    response_schema: type,
    model: str,
) -> Any:
    """Generic Gemini generation helper."""
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    return result.parsed


class OutlineGeneratorTool(Tool):
    def __init__(self):
        super().__init__(
            name="outline_generator",
            description="Generate an article outline based on theme and language",
        )

    def execute(self, params: ToolParams) -> ToolResult:
        return ToolResult(
            success=False,
            data=None,
            error="Use execute_async for this tool",
        )

    async def execute_async(
        self,
        theme: str,
        language: Literal["en", "ja"],
        model: str,
        provider: LLMProvider,
    ) -> ArticleOutline | None:
        system_instruction, user_content = make_outline_generation_system_instruction(theme, language)
        try:
            return await _generate_with_gemini(system_instruction, user_content, ArticleOutline, model)
        except Exception as e:
            logger.error(f"Failed to generate outline with {provider.value}: {e}")
            return None


class FirstHalfGeneratorTool(Tool):
    def __init__(self):
        super().__init__(
            name="first_half_generator",
            description="Generate the first half of an article based on outline",
        )

    def execute(self, params: ToolParams) -> ToolResult:
        return ToolResult(
            success=False,
            data=None,
            error="Use execute_async for this tool",
        )

    async def execute_async(
        self,
        outline: ArticleOutline,
        language: Literal["en", "ja"],
        model: str,
        provider: LLMProvider,
    ) -> ArticleHalf | None:
        system_instruction, user_content = make_first_half_generation_system_instruction(outline, language)
        try:
            return await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
        except Exception as e:
            logger.error(f"Failed to generate first half with {provider.value}: {e}")
            return None


class BestFirstHalfSelectorTool(Tool):
    def __init__(self):
        super().__init__(
            name="best_first_half_selector",
            description="Select the best first half from multiple candidates using LLM",
        )

    def execute(self, params: ToolParams) -> ToolResult:
        return ToolResult(
            success=False,
            data=None,
            error="Use execute_async for this tool",
        )

    async def execute_async(
        self,
        outline: ArticleOutline,
        first_half_candidates: list[ArticleHalf],
        language: Literal["en", "ja"],
        model: str,
        provider: LLMProvider,
    ) -> ArticleHalf | None:
        first_halves = {uuid4().hex: candidate for candidate in first_half_candidates}
        system_instruction, user_content = make_choose_best_first_half_system_instruction(
            outline, first_halves, language
        )
        try:
            result = await _generate_with_gemini(system_instruction, user_content, BestArticleSelection, model)

            if result.selected_id not in first_halves:
                valid_ids = list(first_halves.keys())
                logger.error(f"LLM returned invalid selected_id: '{result.selected_id}'. Valid IDs were: {valid_ids}")
                logger.warning("Falling back to first candidate due to invalid selection")
                return first_half_candidates[0] if first_half_candidates else None

            return first_halves[result.selected_id]
        except Exception as e:
            logger.error(f"Failed to choose best first half with {provider.value}: {e}")
            return None


class SecondHalfGeneratorTool(Tool):
    def __init__(self):
        super().__init__(
            name="second_half_generator",
            description="Generate the second half of an article based on outline and first half",
        )

    def execute(self, params: ToolParams) -> ToolResult:
        return ToolResult(
            success=False,
            data=None,
            error="Use execute_async for this tool",
        )

    async def execute_async(
        self,
        outline: ArticleOutline,
        first_half: str,
        language: Literal["en", "ja"],
        model: str,
        provider: LLMProvider,
    ) -> str | None:
        system_instruction, user_content = make_second_half_generation_system_instruction(outline, first_half, language)
        try:
            result = await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
            return result.content
        except Exception as e:
            logger.error(f"Failed to generate second half with {provider.value}: {e}")
            return None


class ArticleReviewerTool(Tool):
    def __init__(self):
        super().__init__(
            name="article_reviewer",
            description="Review an article using LLM-as-a-Judge and provide grade and feedback",
        )

    def execute(self, params: ToolParams) -> ToolResult:
        return ToolResult(
            success=False,
            data=None,
            error="Use execute_async for this tool",
        )

    async def execute_async(
        self,
        theme: str,
        outline: ArticleOutline,
        full_article: str,
        model: str,
        provider: LLMProvider,
    ) -> ArticleReview | None:
        system_instruction, user_content = make_article_review_system_instruction(theme, outline, full_article)
        try:
            return await _generate_with_gemini(system_instruction, user_content, ArticleReview, model)
        except Exception as e:
            logger.error(f"Failed to review article with {provider.value}: {e}")
            return None


class SecondHalfRegeneratorTool(Tool):
    def __init__(self):
        super().__init__(
            name="second_half_regenerator",
            description="Regenerate second half with feedback from previous rejected attempts",
        )

    def execute(self, params: ToolParams) -> ToolResult:
        return ToolResult(
            success=False,
            data=None,
            error="Use execute_async for this tool",
        )

    async def execute_async(
        self,
        outline: ArticleOutline,
        first_half: str,
        language: Literal["en", "ja"],
        model: str,
        provider: LLMProvider,
        previous_attempts: list[tuple[str, ArticleReview]],
    ) -> str | None:
        system_instruction, user_content = make_second_half_regeneration_system_instruction(
            outline, first_half, language, previous_attempts
        )
        try:
            result = await _generate_with_gemini(system_instruction, user_content, ArticleHalf, model)
            return result.content
        except Exception as e:
            logger.error(f"Failed to regenerate second half with {provider.value}: {e}")
            return None


class GenerationToolBox:
    def __init__(self):
        self.outline_generator = OutlineGeneratorTool()
        self.first_half_generator = FirstHalfGeneratorTool()
        self.best_first_half_selector = BestFirstHalfSelectorTool()
        self.second_half_generator = SecondHalfGeneratorTool()
        self.article_reviewer = ArticleReviewerTool()
        self.second_half_regenerator = SecondHalfRegeneratorTool()

    def get_all_tools(self) -> list[Tool]:
        return [
            self.outline_generator,
            self.first_half_generator,
            self.best_first_half_selector,
            self.second_half_generator,
            self.article_reviewer,
            self.second_half_regenerator,
        ]

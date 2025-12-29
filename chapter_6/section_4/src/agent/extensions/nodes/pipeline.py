"""Pipeline nodes for article generation workflow."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from src.agent.core.mediator import Node, NodeResult, NodeType
from src.agent.extensions.tools.generation import GenerationToolBox
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import (
    ArticleOutline,
    ArticleReview,
)

logger = make_logger(__name__)


@dataclass
class PipelineState:
    """State passed through pipeline nodes.

    This is a simplified single-session state for the "forget the past" pattern.
    Each phase stores a single value, and rollback clears phases after the target.
    """

    theme: str
    language: Literal["en", "ja"]
    llm_provider: LLMProvider
    model: str

    # Phase 1: Outline generation
    outline: ArticleOutline | None = None

    # Phase 2: First half generation
    first_half: str | None = None

    # Phase 3: Second half generation
    second_half: str | None = None

    # Phase 4: Review
    review: ArticleReview | None = None

    # Phase 5: Human approval
    human_approved: bool | None = None

    # Regeneration tracking
    review_loop_iteration: int = 0
    previous_feedback: list[tuple[str, ArticleReview]] | None = None

    # Error tracking
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "language": self.language,
            "llm_provider": self.llm_provider.value,
            "model": self.model,
            "outline": self.outline.model_dump() if self.outline else None,
            "first_half": self.first_half,
            "second_half": self.second_half,
            "review": self.review.model_dump() if self.review else None,
            "human_approved": self.human_approved,
            "review_loop_iteration": self.review_loop_iteration,
            "error": self.error,
        }


class OutlineGenerationNode(Node):
    def __init__(self, node_id: str, toolbox: GenerationToolBox):
        super().__init__(node_id, NodeType.AGENT)
        self.toolbox = toolbox

    def execute(self, input_data: str | dict | list) -> NodeResult:
        return NodeResult(
            node_id=self.node_id,
            success=False,
            output=None,
            error="Use execute_async for this node",
        )

    async def execute_async(self, state: PipelineState) -> NodeResult:
        logger.info(f"Generating outline for theme: {state.theme}")

        outline = await self.toolbox.outline_generator.execute_async(
            state.theme,
            state.language,
            state.model,
            state.llm_provider,
        )

        if not outline:
            state.error = "Failed to generate outline"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.outline = outline
        logger.info(f"Successfully generated outline: {outline.title}")

        return NodeResult(
            node_id=self.node_id,
            success=True,
            output=state,
        )


class FirstHalfGenerationNode(Node):
    def __init__(self, node_id: str, toolbox: GenerationToolBox):
        super().__init__(node_id, NodeType.AGENT)
        self.toolbox = toolbox

    def execute(self, input_data: str | dict | list) -> NodeResult:
        return NodeResult(
            node_id=self.node_id,
            success=False,
            output=None,
            error="Use execute_async for this node",
        )

    async def execute_async(self, state: PipelineState) -> NodeResult:
        logger.info("Generating first half of article...")

        if not state.outline:
            state.error = "No outline available for first half generation"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        first_half_result = await self.toolbox.first_half_generator.execute_async(
            state.outline,
            state.language,
            state.model,
            state.llm_provider,
        )

        if not first_half_result:
            state.error = "Failed to generate first half"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.first_half = first_half_result.content
        logger.info(f"Successfully generated first half ({len(state.first_half)} characters)")

        return NodeResult(
            node_id=self.node_id,
            success=True,
            output=state,
        )


class SecondHalfGenerationNode(Node):
    def __init__(self, node_id: str, toolbox: GenerationToolBox):
        super().__init__(node_id, NodeType.AGENT)
        self.toolbox = toolbox

    def execute(self, input_data: str | dict | list) -> NodeResult:
        return NodeResult(
            node_id=self.node_id,
            success=False,
            output=None,
            error="Use execute_async for this node",
        )

    async def execute_async(self, state: PipelineState) -> NodeResult:
        logger.info("Generating second half of article...")

        if not state.outline or not state.first_half:
            state.error = "No outline or first half available for second half generation"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        second_half = await self.toolbox.second_half_generator.execute_async(
            state.outline,
            state.first_half,
            state.language,
            state.model,
            state.llm_provider,
        )

        if not second_half:
            state.error = "Failed to generate second half"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.second_half = second_half
        logger.info(f"Successfully generated second half ({len(second_half)} characters)")

        return NodeResult(
            node_id=self.node_id,
            success=True,
            output=state,
        )


class ArticleReviewNode(Node):
    def __init__(self, node_id: str, toolbox: GenerationToolBox):
        super().__init__(node_id, NodeType.AGENT)
        self.toolbox = toolbox

    def execute(self, input_data: str | dict | list) -> NodeResult:
        return NodeResult(
            node_id=self.node_id,
            success=False,
            output=None,
            error="Use execute_async for this node",
        )

    async def execute_async(self, state: PipelineState) -> NodeResult:
        logger.info("Reviewing article...")

        if not state.outline or not state.first_half or not state.second_half:
            state.error = "Article is incomplete for review"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        full_article = f"{state.first_half}\n\n{state.second_half}"
        review = await self.toolbox.article_reviewer.execute_async(
            state.theme,
            state.outline,
            full_article,
            state.model,
            state.llm_provider,
        )

        if not review:
            state.error = "Failed to review article"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.review = review
        logger.info(f"Successfully reviewed article: Grade {review.grade}/5")

        return NodeResult(
            node_id=self.node_id,
            success=True,
            output=state,
        )


class SecondHalfRegenerationNode(Node):
    def __init__(self, node_id: str, toolbox: GenerationToolBox):
        super().__init__(node_id, NodeType.AGENT)
        self.toolbox = toolbox

    def execute(self, input_data: str | dict | list) -> NodeResult:
        return NodeResult(
            node_id=self.node_id,
            success=False,
            output=None,
            error="Use execute_async for this node",
        )

    async def execute_async(self, state: PipelineState) -> NodeResult:
        logger.info("Regenerating second half based on previous feedback...")

        if not state.outline or not state.first_half:
            state.error = "No outline or first half available for regeneration"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        # Use previous feedback if available
        previous_attempts = state.previous_feedback or []
        logger.info(f"Using feedback from {len(previous_attempts)} previous attempt(s)")

        second_half = await self.toolbox.second_half_regenerator.execute_async(
            state.outline,
            state.first_half,
            state.language,
            state.model,
            state.llm_provider,
            previous_attempts,
        )

        if not second_half:
            state.error = "Failed to regenerate second half"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.second_half = second_half
        logger.info(f"Successfully regenerated second half ({len(second_half)} characters)")

        return NodeResult(
            node_id=self.node_id,
            success=True,
            output=state,
        )


class HumanDecisionNode(Node):
    def __init__(
        self,
        node_id: str,
        decision_fn: Callable[[PipelineState], tuple[str, Any]],
    ):
        super().__init__(node_id, NodeType.DECISION)
        self.decision_fn = decision_fn

    def execute(self, input_data: str | dict | list) -> NodeResult:
        if isinstance(input_data, dict) and "state" in input_data:
            state = input_data["state"]
        else:
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=None,
                error="Invalid input: expected dict with 'state' key",
            )

        try:
            next_node_id, updated_state = self.decision_fn(state)
            return NodeResult(
                node_id=self.node_id,
                success=True,
                output={"state": updated_state, "next_node": next_node_id},
                metadata={"decision": "route_to", "next_node": next_node_id},
            )
        except Exception as e:
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=None,
                error=str(e),
            )

"""Pipeline nodes for article generation workflow."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from src.agent.core.mediator import Node, NodeResult, NodeType
from src.agent.extensions.tools.generation import GenerationToolBox
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import (
    ArticleReview,
    ParallelSession,
)

logger = make_logger(__name__)


@dataclass
class PipelineState:
    """State passed through pipeline nodes."""

    theme: str
    language: Literal["en", "ja"]
    llm_provider: LLMProvider
    model: str
    num_outline_variants: int = 3
    num_second_half_variants: int = 3
    outline_sessions: list[ParallelSession] = field(default_factory=list)
    selected_outline_session_id: str | None = None
    first_half_session: ParallelSession | None = None
    second_half_sessions: list[ParallelSession] = field(default_factory=list)
    reviewed_sessions: list[ParallelSession] = field(default_factory=list)
    final_selected_session_id: str | None = None
    human_approved: bool | None = None
    rejected_session_ids: list[str] = field(default_factory=list)
    review_loop_iteration: int = 0
    error: str | None = None

    def get_selected_outline_session(self) -> ParallelSession | None:
        if not self.selected_outline_session_id:
            return None
        return next(
            (s for s in self.outline_sessions if s.session_id == self.selected_outline_session_id),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "language": self.language,
            "llm_provider": self.llm_provider.value,
            "model": self.model,
            "num_outline_variants": self.num_outline_variants,
            "num_second_half_variants": self.num_second_half_variants,
            "outline_sessions": self.outline_sessions,
            "selected_outline_session_id": self.selected_outline_session_id,
            "first_half_session": self.first_half_session,
            "second_half_sessions": self.second_half_sessions,
            "reviewed_sessions": self.reviewed_sessions,
            "final_selected_session_id": self.final_selected_session_id,
            "human_approved": self.human_approved,
            "rejected_session_ids": self.rejected_session_ids,
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
        logger.info(f"Generating {state.num_outline_variants} parallel outline variants for theme: {state.theme}")

        tasks = [
            self.toolbox.outline_generator.execute_async(
                state.theme,
                state.language,
                state.model,
                state.llm_provider,
            )
            for _ in range(state.num_outline_variants)
        ]
        outlines = await asyncio.gather(*tasks)

        outline_sessions = []
        for i, outline in enumerate(outlines):
            if outline:
                session = ParallelSession(
                    outline=outline,
                    metadata={"variant_number": i + 1, "phase": "outline_generation"},
                )
                outline_sessions.append(session)
                logger.info(f"Generated outline variant {i + 1}: {outline.title}")
            else:
                logger.warning(f"Failed to generate outline variant {i + 1}")

        if not outline_sessions:
            state.error = "Failed to generate any outlines"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.outline_sessions = outline_sessions
        logger.info(f"Successfully generated {len(outline_sessions)} outline variants")

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

        selected_session = state.get_selected_outline_session()
        if not selected_session or not selected_session.outline:
            state.error = "No outline selected for first half generation"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        tasks = [
            self.toolbox.first_half_generator.execute_async(
                selected_session.outline,
                state.language,
                state.model,
                state.llm_provider,
            )
            for _ in range(state.num_outline_variants)
        ]
        first_half_contents = await asyncio.gather(*tasks)
        valid_contents = [c for c in first_half_contents if c is not None]

        if not valid_contents:
            state.error = "Failed to generate first half candidates"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        best_first_half = await self.toolbox.best_first_half_selector.execute_async(
            selected_session.outline,
            valid_contents,
            state.language,
            state.model,
            state.llm_provider,
        )

        if not best_first_half:
            state.error = "Failed to select best first half"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        logger.info(f"Successfully generated first half ({len(best_first_half.content)} characters)")

        first_half_session = ParallelSession(
            parent_session_id=selected_session.session_id,
            outline=selected_session.outline,
            first_half=best_first_half.content,
            metadata={"phase": "first_half_generated"},
        )
        state.first_half_session = first_half_session

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
        logger.info(f"Generating {state.num_second_half_variants} parallel second half variants...")

        first_half_session = state.first_half_session
        if not first_half_session or not first_half_session.outline or not first_half_session.first_half:
            state.error = "No first half session available for second half generation"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        tasks = [
            self.toolbox.second_half_generator.execute_async(
                first_half_session.outline,
                first_half_session.first_half,
                state.language,
                state.model,
                state.llm_provider,
            )
            for _ in range(state.num_second_half_variants)
        ]
        second_halves = await asyncio.gather(*tasks)

        second_half_sessions = []
        for i, second_half in enumerate(second_halves):
            if second_half:
                session = ParallelSession(
                    parent_session_id=first_half_session.session_id,
                    outline=first_half_session.outline,
                    first_half=first_half_session.first_half,
                    second_half=second_half,
                    metadata={"variant_number": i + 1, "phase": "second_half_generated"},
                )
                second_half_sessions.append(session)
                logger.info(f"Generated second half variant {i + 1} ({len(second_half)} characters)")
            else:
                logger.warning(f"Failed to generate second half variant {i + 1}")

        if not second_half_sessions:
            state.error = "Failed to generate any second half variants"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.second_half_sessions = second_half_sessions
        logger.info(f"Successfully generated {len(second_half_sessions)} second half variants")

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
        logger.info("Reviewing all article variants...")

        second_half_sessions = state.second_half_sessions
        if not second_half_sessions:
            state.error = "No second half sessions available for review"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        tasks = []
        sessions_to_review = []

        for session in second_half_sessions:
            if session.outline and session.first_half and session.second_half:
                full_article = f"{session.first_half}\n\n{session.second_half}"
                task = self.toolbox.article_reviewer.execute_async(
                    state.theme,
                    session.outline,
                    full_article,
                    state.model,
                    state.llm_provider,
                )
                tasks.append(task)
                sessions_to_review.append(session)

        reviews = await asyncio.gather(*tasks)

        reviewed_sessions = []
        for session, review in zip(sessions_to_review, reviews):
            if review:
                reviewed_session = ParallelSession(
                    session_id=session.session_id,
                    parent_session_id=session.parent_session_id,
                    outline=session.outline,
                    first_half=session.first_half,
                    second_half=session.second_half,
                    review=review,
                    metadata={**session.metadata, "phase": "reviewed"},
                    created_at=session.created_at,
                )
                reviewed_sessions.append(reviewed_session)
                logger.info(f"Reviewed variant {session.metadata.get('variant_number', '?')}: Grade {review.grade}/5")
            else:
                logger.warning(f"Failed to review variant {session.metadata.get('variant_number', '?')}")

        if not reviewed_sessions:
            state.error = "Failed to review any articles"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.reviewed_sessions = reviewed_sessions
        logger.info(f"Successfully reviewed {len(reviewed_sessions)} article variants")

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
        logger.info("Regenerating second half variants based on previous feedback...")

        first_half_session = state.first_half_session
        if not first_half_session or not first_half_session.outline or not first_half_session.first_half:
            state.error = "No first half session available for regeneration"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        previous_attempts: list[tuple[str, ArticleReview]] = []
        for session in state.reviewed_sessions:
            if session.session_id in state.rejected_session_ids and session.second_half and session.review:
                previous_attempts.append((session.second_half, session.review))

        logger.info(f"Using feedback from {len(previous_attempts)} previous attempt(s)")

        tasks = [
            self.toolbox.second_half_regenerator.execute_async(
                first_half_session.outline,
                first_half_session.first_half,
                state.language,
                state.model,
                state.llm_provider,
                previous_attempts,
            )
            for _ in range(state.num_second_half_variants)
        ]
        second_halves = await asyncio.gather(*tasks)

        new_second_half_sessions = []
        for i, second_half in enumerate(second_halves):
            if second_half:
                session = ParallelSession(
                    parent_session_id=first_half_session.session_id,
                    outline=first_half_session.outline,
                    first_half=first_half_session.first_half,
                    second_half=second_half,
                    metadata={
                        "variant_number": i + 1,
                        "phase": "second_half_regenerated",
                        "iteration": state.review_loop_iteration,
                    },
                )
                new_second_half_sessions.append(session)
                logger.info(f"Regenerated second half variant {i + 1} ({len(second_half)} characters)")
            else:
                logger.warning(f"Failed to regenerate second half variant {i + 1}")

        if not new_second_half_sessions:
            state.error = "Failed to regenerate any second half variants"
            return NodeResult(
                node_id=self.node_id,
                success=False,
                output=state,
                error=state.error,
            )

        state.second_half_sessions = new_second_half_sessions
        logger.info(f"Successfully regenerated {len(new_second_half_sessions)} second half variants")

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

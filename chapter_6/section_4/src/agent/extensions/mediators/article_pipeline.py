"""Article generation pipeline mediator."""

from dataclasses import dataclass
from typing import Literal

import click
from src.agent.extensions.memory.pipeline import (
    PipelineMemory,
    PipelineMemoryCaretaker,
    PipelineState,
    create_initial_state,
)
from src.agent.extensions.nodes.pipeline import (
    ArticleReviewNode,
    FirstHalfGenerationNode,
    OutlineGenerationNode,
    SecondHalfGenerationNode,
    SecondHalfRegenerationNode,
)
from src.agent.extensions.tools.generation import GenerationToolBox
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import CompletedArticle
from src.service.helper import (
    get_human_approval,
    get_rollback_choice,
    print_article_preview,
    print_separator,
    save_article_files,
)

logger = make_logger(__name__)


@dataclass
class PipelineResult:
    """Result from pipeline execution."""

    success: bool
    article: CompletedArticle | None
    state: PipelineState
    error: str | None = None


class ArticlePipelineMediator:
    """Mediator for orchestrating article generation pipeline.

    This mediator coordinates multiple pipeline nodes using the agent
    framework components:
    - GenerationToolBox for LLM generation tools
    - PipelineMemory with phase-based rollback (Memento pattern)
    - Pipeline nodes for each generation phase

    Simplified single-session pipeline (no parallel worlds):
    - Phase 1: Generate single outline
    - Phase 2: Generate single first half
    - Phase 3: Generate single second half
    - Phase 4: Review article
    - Phase 5: Human approval (with optional regeneration loop)
    """

    def __init__(
        self,
        theme: str,
        language: Literal["en", "ja"],
        llm_provider: LLMProvider,
        model: str,
        output_directory: str,
        auto_select: bool = False,
    ):
        # Create initial state and memory
        initial_state = create_initial_state(
            theme=theme,
            language=language,
            llm_provider=llm_provider,
            model=model,
        )
        self.memory = PipelineMemory(initial_state)
        self.caretaker = PipelineMemoryCaretaker()

        # Initialize toolbox and nodes
        self.toolbox = GenerationToolBox()
        self._init_nodes()

        # Configuration
        self.output_directory = output_directory
        self.auto_select = auto_select
        self.max_iterations = 5

    def _init_nodes(self) -> None:
        self.outline_node = OutlineGenerationNode("outline_generation", self.toolbox)
        self.first_half_node = FirstHalfGenerationNode("first_half_generation", self.toolbox)
        self.second_half_node = SecondHalfGenerationNode("second_half_generation", self.toolbox)
        self.review_node = ArticleReviewNode("article_review", self.toolbox)
        self.regeneration_node = SecondHalfRegenerationNode("second_half_regeneration", self.toolbox)

    @property
    def state(self) -> PipelineState:
        return self.memory.state

    async def execute(self) -> PipelineResult:
        while True:
            current_phase = self.memory.get_current_phase()
            phase_name = self.memory.get_phase_name(current_phase)
            click.echo(f"\n📍 Current phase: {current_phase} - {phase_name}")

            # Phase 1: Generate outline
            if current_phase < 1:
                if not await self._execute_outline_generation():
                    return self._error_result()

            # Phase 2: Generate first half
            if current_phase < 2:
                if not await self._execute_first_half_generation():
                    return self._error_result()

                # Rollback option after first half
                if self._handle_rollback_option():
                    continue

            # Phase 3: Generate second half
            if current_phase < 3:
                if not await self._execute_second_half_generation():
                    return self._error_result()

            # Phase 4: Review article
            if current_phase < 4:
                if not await self._execute_article_review():
                    return self._error_result()

            # Phase 5: Human approval loop
            if current_phase < 5 or not self.state.human_approved:
                result = await self._execute_approval_loop()
                if not result.success:
                    return result

                # Rollback option after approval
                if self._handle_rollback_option():
                    continue

                if self.state.human_approved:
                    break
            else:
                # Already approved
                break

        # Save the final article
        final_article = self.memory.get_final_article()
        if final_article:
            self._save_article(final_article)
            return PipelineResult(success=True, article=final_article, state=self.state)

        return PipelineResult(
            success=False,
            article=None,
            state=self.state,
            error="Failed to get final article",
        )

    async def _execute_outline_generation(self) -> bool:
        print_separator()
        click.echo("📝 PHASE 1: Generating Article Outline")

        result = await self.outline_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        if self.state.outline:
            click.echo(f"✅ Generated outline: {self.state.outline.title}")
            click.echo(f"\nSummary: {self.state.outline.summary}")
            click.echo("\nStructure:")
            for i, section in enumerate(self.state.outline.structure, 1):
                click.echo(f"  {i}. {section}")

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_first_half_generation(self) -> bool:
        print_separator()
        click.echo("📝 PHASE 2: Generating First Half of Article")

        result = await self.first_half_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        if self.state.first_half:
            click.echo(f"✅ Generated first half ({len(self.state.first_half)} characters)")
            click.echo("\nPreview:")
            print_article_preview(self.state.first_half)

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_second_half_generation(self) -> bool:
        print_separator()
        click.echo("📝 PHASE 3: Generating Second Half of Article")

        result = await self.second_half_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        if self.state.second_half:
            click.echo(f"✅ Generated second half ({len(self.state.second_half)} characters)")

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_article_review(self) -> bool:
        print_separator()
        click.echo("⚖️  PHASE 4: Reviewing Article with LLM-as-a-Judge")

        result = await self.review_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        if self.state.review:
            click.echo(f"✅ Review completed: Grade {self.state.review.grade}/5")
            click.echo(f"\nReasoning: {self.state.review.reasoning}")
            if self.state.review.strengths:
                click.echo("\nStrengths:")
                for strength in self.state.review.strengths:
                    click.echo(f"  ✓ {strength}")
            if self.state.review.weaknesses:
                click.echo("\nWeaknesses:")
                for weakness in self.state.review.weaknesses:
                    click.echo(f"  ✗ {weakness}")

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_approval_loop(self) -> PipelineResult:
        iteration = self.state.review_loop_iteration
        human_approved = False
        final_article: CompletedArticle | None = None

        while not human_approved and iteration < self.max_iterations:
            iteration += 1

            # Get human approval
            completed_article = self.memory.get_final_article()
            if not completed_article:
                self.state.error = "Failed to create completed article"
                return self._error_result()

            print_separator()
            click.echo(f"✅ PHASE 5: Human-in-the-Loop - Approve or Reject Article (Iteration {iteration})")

            human_approved = get_human_approval(completed_article, self.auto_select)
            self.state.human_approved = human_approved

            if human_approved:
                final_article = completed_article
                click.echo("\n✅ Article approved! Proceeding to save...")
                break

            # Rejected - store feedback and regenerate
            click.echo("\n❌ Article rejected. Regenerating second half with feedback...")

            # Store previous attempt for feedback
            if self.state.second_half and self.state.review:
                if self.state.previous_feedback is None:
                    self.state.previous_feedback = []
                self.state.previous_feedback.append((self.state.second_half, self.state.review))

            self.state.review_loop_iteration = iteration

            # Clear second half and review for regeneration
            self.state.second_half = None
            self.state.review = None
            self.state.human_approved = None

            # Regenerate second half
            if not await self._execute_regeneration():
                return self._error_result()

            # Re-review
            if not await self._execute_article_review():
                return self._error_result()

            self.caretaker.save_phase(self.memory)

        if not human_approved:
            click.echo(f"\n⚠️  Maximum iterations ({self.max_iterations}) reached without approval")
            click.echo("Saving the last generated article...")
            final_article = self.memory.get_final_article()

        return PipelineResult(
            success=True,
            article=final_article,
            state=self.state,
        )

    async def _execute_regeneration(self) -> bool:
        print_separator()
        click.echo(f"🔄 Regenerating Second Half (Iteration {self.state.review_loop_iteration})")
        feedback_count = len(self.state.previous_feedback) if self.state.previous_feedback else 0
        click.echo(f"Using feedback from {feedback_count} previous attempt(s)...")

        result = await self.regeneration_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error during regeneration: {result.error}", err=True)
            return False

        if self.state.second_half:
            click.echo(f"✅ Regenerated second half ({len(self.state.second_half)} characters)")

        return True

    def _handle_rollback_option(self) -> bool:
        available_phases = self.memory.get_available_rollback_phases()
        rollback_phase = get_rollback_choice(available_phases, self.auto_select)

        if rollback_phase is not None:
            self.memory.forget_phases_after(rollback_phase)
            return True
        return False

    def _save_article(self, final_article: CompletedArticle) -> tuple[str, str]:
        print_separator()
        click.echo("💾 Saving Final Article")

        json_path, md_path = save_article_files(
            final_article,
            self.state.language,
            self.output_directory,
        )

        full_content = final_article.get_full_content()
        click.echo(
            f"""
✅ Article Generation Complete!

Article Details:
  Title: {final_article.outline.title}
  Grade: {final_article.review.grade if final_article.review else "N/A"}/5
  Total Length: {len(full_content)} characters
  Review Loop Iterations: {self.state.review_loop_iteration}

Files saved:
  📄 JSON: {json_path}
  📝 Markdown: {md_path}

Session Metadata:
  Session ID: {final_article.session_id}
  Created: {final_article.created_at}
"""
        )

        print_separator()
        click.echo("🎉 Article Generation Complete!")

        return json_path, md_path

    def _error_result(self) -> PipelineResult:
        return PipelineResult(
            success=False,
            article=None,
            state=self.state,
            error=self.state.error,
        )


async def run_article_pipeline(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
    output_directory: str,
    auto_select: bool = False,
) -> CompletedArticle | None:
    mediator = ArticlePipelineMediator(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        output_directory=output_directory,
        auto_select=auto_select,
    )

    result = await mediator.execute()

    if result.success:
        return result.article
    else:
        if result.error:
            click.echo(f"❌ Pipeline error: {result.error}", err=True)
        return None

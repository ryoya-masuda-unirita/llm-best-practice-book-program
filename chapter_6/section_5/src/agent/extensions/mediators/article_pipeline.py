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
    display_outlines,
    display_reviews,
    get_final_article_selection,
    get_human_approval,
    get_outline_selection,
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
    - PipelineMemory for pipeline state management
    - Pipeline nodes for each generation phase
    """

    def __init__(
        self,
        theme: str,
        language: Literal["en", "ja"],
        llm_provider: LLMProvider,
        model: str,
        output_directory: str,
        num_outline_variants: int = 3,
        num_second_half_variants: int = 3,
        auto_select: bool = False,
    ):
        initial_state = create_initial_state(
            theme=theme,
            language=language,
            llm_provider=llm_provider,
            model=model,
            num_outline_variants=num_outline_variants,
            num_second_half_variants=num_second_half_variants,
        )
        self.memory = PipelineMemory(initial_state)
        self.caretaker = PipelineMemoryCaretaker()
        self.toolbox = GenerationToolBox()
        self._init_nodes()
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

            if current_phase < 1:
                if not await self._execute_outline_generation():
                    return self._error_result()

            if current_phase < 2:
                self._execute_outline_selection()
                if self.state.error:
                    return self._error_result()

            if current_phase < 3:
                if not await self._execute_first_half_generation():
                    return self._error_result()

            if current_phase < 4:
                if not await self._execute_second_half_generation():
                    return self._error_result()

            if current_phase < 5:
                if not await self._execute_article_review():
                    return self._error_result()

            if current_phase < 7 or not self.state.human_approved:
                result = await self._execute_review_loop()
                if not result.success:
                    return result

                if self.state.human_approved:
                    break
            else:
                break

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
        click.echo("🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)")
        click.echo(f"Creating {self.state.num_outline_variants} different article outlines in parallel...")

        result = await self.outline_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        click.echo(f"✅ Generated {len(self.state.outline_sessions)} outline variants")
        self.caretaker.save_phase(self.memory)
        return True

    def _execute_outline_selection(self) -> None:
        print_separator()
        click.echo("👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline")

        outline_sessions = self.state.outline_sessions
        if not outline_sessions:
            self.state.error = "No outline sessions available"
            return

        display_outlines(outline_sessions)
        selected_idx = get_outline_selection(outline_sessions, self.auto_select)

        selected_session = outline_sessions[selected_idx]
        self.state.selected_outline_session_id = selected_session.session_id
        click.echo(f"✅ Selected: {selected_session.outline.title}")  # type: ignore
        self.caretaker.save_phase(self.memory)

    async def _execute_first_half_generation(self) -> bool:
        print_separator()
        click.echo("📝 PHASE 3: Generating First Half of Article")

        result = await self.first_half_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        first_half_session = self.state.first_half_session
        if first_half_session and first_half_session.first_half:
            click.echo(f"✅ Generated first half ({len(first_half_session.first_half)} characters)")
            click.echo("\nPreview:")
            print_article_preview(first_half_session.first_half)

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_second_half_generation(self) -> bool:
        print_separator()
        click.echo("🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)")
        click.echo(f"Creating {self.state.num_second_half_variants} different endings in parallel...")

        result = await self.second_half_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        click.echo(f"✅ Generated {len(self.state.second_half_sessions)} second half variants")
        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_article_review(self) -> bool:
        print_separator()
        click.echo("⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge")

        result = await self.review_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error: {result.error}", err=True)
            return False

        click.echo(f"✅ Reviewed {len(self.state.reviewed_sessions)} complete articles")
        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_review_loop(self) -> PipelineResult:
        iteration = self.state.review_loop_iteration
        human_approved = False
        final_article: CompletedArticle | None = None

        while not human_approved and iteration < self.max_iterations:
            iteration += 1

            completed_article = self._execute_article_selection(iteration)
            if not completed_article:
                return self._error_result()

            human_approved = self._execute_approval(completed_article)

            if human_approved:
                final_article = completed_article
                break

            if not await self._execute_regeneration(iteration):
                return self._error_result()

            if not await self._execute_article_review():
                return self._error_result()

        if not human_approved:
            click.echo(f"\n⚠️  Maximum iterations ({self.max_iterations}) reached without approval")
            click.echo("Saving the last selected article...")
            final_article = completed_article

        return PipelineResult(
            success=True,
            article=final_article,
            state=self.state,
        )

    def _execute_article_selection(self, iteration: int) -> CompletedArticle | None:
        print_separator()
        click.echo(f"👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article (Iteration {iteration})")

        reviewed_sessions = self.state.reviewed_sessions
        if not reviewed_sessions:
            self.state.error = "No reviewed sessions available"
            return None

        display_reviews(reviewed_sessions)
        best_idx = get_final_article_selection(reviewed_sessions, self.auto_select)

        final_session = reviewed_sessions[best_idx]
        self.state.final_selected_session_id = final_session.session_id

        completed_article = final_session.to_completed_article(self.state.language)
        if not completed_article:
            click.echo("❌ Failed to create completed article", err=True)
            return None

        self.caretaker.save_phase(self.memory)
        return completed_article

    def _execute_approval(self, completed_article: CompletedArticle) -> bool:
        print_separator()
        click.echo("✅ PHASE 7: Human-in-the-Loop - Approve or Reject Article")

        human_approved = get_human_approval(completed_article, self.auto_select)
        self.state.human_approved = human_approved

        if human_approved:
            click.echo("\n✅ Article approved! Proceeding to save...")
        else:
            click.echo("\n❌ Article rejected. Regenerating second half with feedback...")
            if self.state.final_selected_session_id:
                if self.state.final_selected_session_id not in self.state.rejected_session_ids:
                    self.state.rejected_session_ids.append(self.state.final_selected_session_id)

        self.caretaker.save_phase(self.memory)
        return human_approved

    async def _execute_regeneration(self, iteration: int) -> bool:
        self.state.review_loop_iteration = iteration

        print_separator()
        click.echo(f"🔄 PHASE 8: Regenerating Second Half Variants (Iteration {iteration})")
        click.echo(f"Using feedback from {len(self.state.rejected_session_ids)} rejected attempt(s)...")

        result = await self.regeneration_node.execute_async(self.state)

        if not result.success:
            click.echo(f"❌ Error during regeneration: {result.error}", err=True)
            return False

        click.echo(f"✅ Regenerated {len(self.state.second_half_sessions)} second half variants")
        self.caretaker.save_phase(self.memory)
        return True

    def _save_article(self, final_article: CompletedArticle) -> tuple[str, str, str]:
        print_separator()
        click.echo("💾 Saving Final Article")

        json_path, md_path, variants_dir = save_article_files(
            final_article,
            self.state.reviewed_sessions,
            self.state.language,
            self.output_directory,
        )

        click.echo(
            f"""
✅ Article Generation Complete!

Selected Article Details:
  Title: {final_article.outline.title}
  Grade: {final_article.review.grade if final_article.review else "N/A"}/5
  Total Length: {len(final_article.get_full_content())} characters
  Review Loop Iterations: {self.state.review_loop_iteration}

Files saved:
  📄 JSON: {json_path}
  📝 Markdown: {md_path}

Session Metadata:
  Session ID: {final_article.session_id}
  Created: {final_article.created_at}
  Outline variants generated: {len(self.state.outline_sessions)}
  Second half variants generated: {len(self.state.second_half_sessions)}
"""
        )

        click.echo(f"📁 All variants saved to: {variants_dir}")

        print_separator()
        click.echo("🎉 Parallel World Article Generation Complete!")

        return json_path, md_path, variants_dir

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
    num_outline_variants: int = 3,
    num_second_half_variants: int = 3,
    auto_select: bool = False,
) -> CompletedArticle | None:
    mediator = ArticlePipelineMediator(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        output_directory=output_directory,
        num_outline_variants=num_outline_variants,
        num_second_half_variants=num_second_half_variants,
        auto_select=auto_select,
    )

    result = await mediator.execute()

    if result.success:
        return result.article
    else:
        if result.error:
            click.echo(f"❌ Pipeline error: {result.error}", err=True)
        return None

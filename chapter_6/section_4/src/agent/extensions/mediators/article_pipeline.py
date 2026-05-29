"""Article generation pipeline mediator with Forget + Replay + Speculate."""

from dataclasses import dataclass
from typing import Any, Literal

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
from src.agent.extensions.replay.engine import ReplayEngine
from src.agent.extensions.replay.filter import ReplayFilter
from src.agent.extensions.replay.prompt_log import PromptLog, PromptType
from src.agent.extensions.speculative.branch_detector import BranchDetector
from src.agent.extensions.speculative.world_manager import WorldManager
from src.agent.extensions.tools.generation import GenerationToolBox
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import ArticleOutline, CompletedArticle
from src.service.helper import (
    get_human_approval,
    get_rollback_choice,
    get_user_requirements,
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

    This mediator integrates all three stages:
    - **Forget**: Checkpoint-based rollback via PipelineMemory
    - **Replay**: WAL-based prompt re-send via ReplayEngine
    - **Speculate**: Parallel-world execution via WorldManager

    Pipeline phases:
    - Phase 1: Generate outline(s) - with optional speculative branching
    - Phase 2: Generate first half
    - Phase 3: Generate second half
    - Phase 4: Review article (LLM-as-a-Judge)
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
        num_outlines: int = 1,
    ):
        # Create initial state and memory (Forget)
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

        # Replay components
        self.prompt_log = PromptLog()
        self.replay_filter = ReplayFilter()
        self.replay_engine = ReplayEngine(self.prompt_log, self.replay_filter)

        # Speculate components
        self.world_manager = WorldManager(max_parallel_worlds=3)
        self.branch_detector = BranchDetector(max_candidates=num_outlines)

        # Configuration
        self.output_directory = output_directory
        self.auto_select = auto_select
        self.num_outlines = num_outlines
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
        """Execute the full pipeline with Forget + Replay + Speculate."""
        while True:
            current_phase = self.memory.get_current_phase()
            phase_name = self.memory.get_phase_name(current_phase)
            click.echo(f"\n  Current phase: {current_phase} - {phase_name}")

            # Phase 1: Generate outline(s)
            if current_phase < 1:
                if self.num_outlines > 1:
                    # Speculate: generate multiple outlines and run parallel worlds
                    if not await self._execute_speculative_outline_generation():
                        return self._error_result()
                    # Speculative worlds may have filled phases 1-4;
                    # restart loop to re-read current_phase accurately
                    continue
                else:
                    # Standard: single outline
                    if not await self._execute_outline_generation():
                        return self._error_result()

                # Collect optional user requirements (logged in WAL for Replay)
                self._collect_user_requirements(phase=1)

            # Phase 2: Generate first half
            if current_phase < 2:
                if not await self._execute_first_half_generation():
                    return self._error_result()

                # Rollback + Replay option after first half
                if self._handle_rollback_with_replay():
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

                # Rollback + Replay option after approval
                if self._handle_rollback_with_replay():
                    continue

                if self.state.human_approved:
                    break
            else:
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

    # ── Phase execution methods ──────────────────────────────────────────

    async def _execute_outline_generation(self) -> bool:
        """Phase 1: Generate a single outline."""
        print_separator()
        click.echo("  PHASE 1: Generating Article Outline")

        result = await self.outline_node.execute_async(self.state)

        if not result.success:
            click.echo(f"  Error: {result.error}", err=True)
            return False

        if self.state.outline:
            click.echo(f"  Generated outline: {self.state.outline.title}")
            click.echo(f"\nSummary: {self.state.outline.summary}")
            click.echo("\nStructure:")
            for i, section in enumerate(self.state.outline.structure, 1):
                click.echo(f"  {i}. {section}")

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_speculative_outline_generation(self) -> bool:
        """Phase 1 (Speculate): Generate N outlines and run parallel worlds."""
        print_separator()
        click.echo(f"  PHASE 1 (Speculate): Generating {self.num_outlines} Outline Candidates")

        # Generate multiple outlines
        outlines = await self.outline_node.execute_multiple_async(
            self.state,
            self.num_outlines,
        )

        if not outlines:
            self.state.error = "Failed to generate any outline candidates"
            click.echo(f"  Error: {self.state.error}", err=True)
            return False

        click.echo(f"\n  Generated {len(outlines)} outline candidates:")
        for i, outline in enumerate(outlines, 1):
            click.echo(f"    {i}. {outline.title}")
            click.echo(f"       {outline.summary[:100]}...")

        if len(outlines) == 1:
            # Only one outline generated; use it directly
            self.state.outline = outlines[0]
            self.caretaker.save_phase(self.memory)
            return True

        # Collect user requirements BEFORE launching speculative worlds
        # so they can be passed to each world's generation context
        self._collect_user_requirements(phase=1)

        # Check if speculation is appropriate
        if self.branch_detector.should_speculate(1, outlines):
            selected = await self._run_speculative_worlds(outlines)
            if selected is None:
                self.state.error = "No speculative world completed successfully"
                return False
            return True
        else:
            # Use the first outline
            self.state.outline = outlines[0]
            self.caretaker.save_phase(self.memory)
            return True

    async def _run_speculative_worlds(
        self,
        outlines: list[ArticleOutline],
    ) -> ArticleOutline | None:
        """Fork parallel worlds, run pipeline in each, let user select best."""
        print_separator()
        click.echo("  SPECULATIVE EXECUTION: Running parallel worlds...")

        # Create worlds
        candidate_labels = [f"{o.title}" for o in outlines]
        worlds = self.world_manager.create_worlds(
            candidates=outlines,
            candidate_labels=candidate_labels,
            branch_phase=1,
            base_state=self.state,
        )

        # Define execution function for each world
        async def execute_world_pipeline(
            world_state: PipelineState,
            candidate: Any,
        ) -> PipelineResult:
            """Run phases 1-4 in an isolated world."""
            outline: ArticleOutline = candidate
            world_state.outline = outline

            # Create isolated nodes for this world
            toolbox = GenerationToolBox()
            first_half_node = FirstHalfGenerationNode("world_first_half", toolbox)
            second_half_node = SecondHalfGenerationNode("world_second_half", toolbox)
            review_node = ArticleReviewNode("world_review", toolbox)

            # Phase 2: First half
            result = await first_half_node.execute_async(world_state)
            if not result.success:
                return PipelineResult(success=False, article=None, state=world_state, error=result.error)

            # Phase 3: Second half
            result = await second_half_node.execute_async(world_state)
            if not result.success:
                return PipelineResult(success=False, article=None, state=world_state, error=result.error)

            # Phase 4: Review
            result = await review_node.execute_async(world_state)
            if not result.success:
                return PipelineResult(success=False, article=None, state=world_state, error=result.error)

            # Build completed article for preview
            article = CompletedArticle(
                outline=world_state.outline,
                first_half=world_state.first_half or "",
                second_half=world_state.second_half or "",
                review=world_state.review,
                language=world_state.language,
            )
            return PipelineResult(success=True, article=article, state=world_state)

        # Execute all worlds concurrently
        completed_worlds = await self.world_manager.execute_worlds(
            worlds,
            execute_world_pipeline,
        )

        # Display summaries
        self.world_manager.display_world_summaries(completed_worlds)

        # User selects best world
        selected_world = self.world_manager.select_world(
            completed_worlds,
            auto_select=self.auto_select,
        )

        if selected_world is None:
            return None

        # Apply selected world's state to the main pipeline (all phase fields)
        selected_state: PipelineState = selected_world.state
        self.state.outline = selected_state.outline
        self.state.first_half = selected_state.first_half
        self.state.second_half = selected_state.second_half
        self.state.review = selected_state.review
        self.state.error = selected_state.error

        # Cancel other worlds
        self.world_manager.cancel_unselected(completed_worlds, selected_world)

        click.echo(f"\n  Applied selected world: {selected_world.candidate_label}")
        self.caretaker.save_phase(self.memory)
        return selected_world.candidate

    async def _execute_first_half_generation(self) -> bool:
        """Phase 2: Generate the first half of the article."""
        print_separator()
        click.echo("  PHASE 2: Generating First Half of Article")

        result = await self.first_half_node.execute_async(self.state)

        if not result.success:
            click.echo(f"  Error: {result.error}", err=True)
            return False

        if self.state.first_half:
            click.echo(f"  Generated first half ({len(self.state.first_half)} characters)")
            click.echo("\nPreview:")
            print_article_preview(self.state.first_half)

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_second_half_generation(self) -> bool:
        """Phase 3: Generate the second half of the article."""
        print_separator()
        click.echo("  PHASE 3: Generating Second Half of Article")

        result = await self.second_half_node.execute_async(self.state)

        if not result.success:
            click.echo(f"  Error: {result.error}", err=True)
            return False

        if self.state.second_half:
            click.echo(f"  Generated second half ({len(self.state.second_half)} characters)")

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_article_review(self) -> bool:
        """Phase 4: Review the article with LLM-as-a-Judge."""
        print_separator()
        click.echo("  PHASE 4: Reviewing Article with LLM-as-a-Judge")

        result = await self.review_node.execute_async(self.state)

        if not result.success:
            click.echo(f"  Error: {result.error}", err=True)
            return False

        if self.state.review:
            click.echo(f"  Review completed: Grade {self.state.review.grade}/5")
            click.echo(f"\nReasoning: {self.state.review.reasoning}")
            if self.state.review.strengths:
                click.echo("\nStrengths:")
                for strength in self.state.review.strengths:
                    click.echo(f"  + {strength}")
            if self.state.review.weaknesses:
                click.echo("\nWeaknesses:")
                for weakness in self.state.review.weaknesses:
                    click.echo(f"  - {weakness}")

        self.caretaker.save_phase(self.memory)
        return True

    async def _execute_approval_loop(self) -> PipelineResult:
        """Phase 5: Human approval loop with regeneration."""
        iteration = self.state.review_loop_iteration
        human_approved = False
        final_article: CompletedArticle | None = None

        while not human_approved and iteration < self.max_iterations:
            iteration += 1

            completed_article = self.memory.get_final_article()
            if not completed_article:
                self.state.error = "Failed to create completed article"
                return self._error_result()

            print_separator()
            click.echo(f"  PHASE 5: Human-in-the-Loop - Approve or Reject Article (Iteration {iteration})")

            human_approved = get_human_approval(completed_article, self.auto_select)

            # Log the approval decision for potential replay
            self.prompt_log.append(
                phase=5,
                prompt_text="approve" if human_approved else "reject",
                prompt_type=PromptType.CONFIRMATION,
                depends_on_prior_response=True,
                response_text="approved" if human_approved else "rejected",
            )

            self.state.human_approved = human_approved

            if human_approved:
                final_article = completed_article
                click.echo("\n  Article approved! Proceeding to save...")
                break

            # Rejected - store feedback and regenerate
            click.echo("\n  Article rejected. Regenerating second half with feedback...")

            if self.state.second_half and self.state.review:
                if self.state.previous_feedback is None:
                    self.state.previous_feedback = []
                self.state.previous_feedback.append((self.state.second_half, self.state.review))

            self.state.review_loop_iteration = iteration
            self.state.second_half = None
            self.state.review = None
            self.state.human_approved = None

            if not await self._execute_regeneration():
                return self._error_result()

            if not await self._execute_article_review():
                return self._error_result()

            self.caretaker.save_phase(self.memory)

        if not human_approved:
            click.echo(f"\n  Maximum iterations ({self.max_iterations}) reached without approval")
            click.echo("Saving the last generated article...")
            final_article = self.memory.get_final_article()

        return PipelineResult(
            success=True,
            article=final_article,
            state=self.state,
        )

    async def _execute_regeneration(self) -> bool:
        """Regenerate second half based on feedback."""
        print_separator()
        click.echo(f"  Regenerating Second Half (Iteration {self.state.review_loop_iteration})")
        feedback_count = len(self.state.previous_feedback) if self.state.previous_feedback else 0
        click.echo(f"Using feedback from {feedback_count} previous attempt(s)...")

        result = await self.regeneration_node.execute_async(self.state)

        if not result.success:
            click.echo(f"  Error during regeneration: {result.error}", err=True)
            return False

        if self.state.second_half:
            click.echo(f"  Regenerated second half ({len(self.state.second_half)} characters)")

        return True

    # ── User requirements collection ────────────────────────────────────

    def _collect_user_requirements(self, phase: int) -> None:
        """Collect optional user requirements and log them in the WAL.

        These requirements are stored in PipelineState.user_requirements and
        passed as additional context to generation prompts. On rollback, the
        Replay engine re-applies them automatically.
        """
        requirement = get_user_requirements(phase, self.auto_select)
        if requirement:
            if self.state.user_requirements is None:
                self.state.user_requirements = []
            self.state.user_requirements.append(requirement)

            # Log in WAL for replay after future rollbacks
            self.prompt_log.append(
                phase=phase,
                prompt_text=requirement,
                prompt_type=PromptType.REQUIREMENT,
                depends_on_prior_response=False,
                response_text=None,
            )

            click.echo(f'  Requirement recorded: "{requirement}"')
            logger.info("User requirement logged at phase %d: %s", phase, requirement)

    # ── Rollback + Replay ────────────────────────────────────────────────

    def _handle_rollback_with_replay(self) -> bool:
        """Handle rollback option with automatic prompt replay.

        Implements the full Forget + Replay flow:
        1. Forget: rollback state to the target phase
        2. Replay: identify replayable prompts from WAL, re-apply REQUIREMENT
           prompts to state.user_requirements, show diff summary

        Returns True if a rollback was performed (caller should restart loop).
        """
        available_phases = self.memory.get_available_rollback_phases()
        rollback_phase = get_rollback_choice(available_phases, self.auto_select)

        if rollback_phase is None:
            return False

        # Capture pre-rollback requirements for diff
        pre_rollback_requirements = list(self.state.user_requirements or [])

        # Stage 1: Forget - rollback to the target phase
        self.memory.forget_phases_after(rollback_phase)

        # Stage 2: Replay - identify replayable prompts, then clear WAL, then re-apply
        replayable = self.replay_engine.get_replayable_entries(
            rollback_phase,
            auto_select=self.auto_select,
        )

        # Clear WAL entries after rollback phase BEFORE re-appending replayed ones
        # (prevents duplicate entries from appending then clearing the same phase)
        removed = self.prompt_log.clear_after_phase(rollback_phase)
        if removed > 0:
            logger.info("Cleared %d WAL entries after phase %d", removed, rollback_phase)

        if replayable:
            click.echo(f"\n  Replay: Re-applying {len(replayable)} valid prompt(s)...")

            # Clear user_requirements (will be rebuilt from replay)
            self.state.user_requirements = None
            replayed_requirements: list[str] = []

            for entry in replayable:
                if entry.prompt_type == PromptType.REQUIREMENT:
                    # Re-apply requirement to state
                    if self.state.user_requirements is None:
                        self.state.user_requirements = []
                    self.state.user_requirements.append(entry.prompt_text)
                    replayed_requirements.append(entry.prompt_text)
                    click.echo(f'    + Replayed: "{entry.prompt_text[:60]}"')

                    # Re-log in WAL for future rollbacks
                    self.prompt_log.append(
                        phase=entry.phase,
                        prompt_text=entry.prompt_text,
                        prompt_type=entry.prompt_type,
                        depends_on_prior_response=entry.depends_on_prior_response,
                        response_text=entry.response_text,
                    )

            # Show diff: what requirements were preserved across rollback
            if pre_rollback_requirements or replayed_requirements:
                click.echo("\n  Replay Diff:")
                if pre_rollback_requirements:
                    click.echo(f"    Before rollback: {len(pre_rollback_requirements)} requirement(s)")
                    for req in pre_rollback_requirements:
                        click.echo(f'      "{req[:60]}"')
                click.echo(f"    After replay: {len(replayed_requirements)} requirement(s) restored")
                for req in replayed_requirements:
                    click.echo(f'      "{req[:60]}"')
            click.echo("")
        else:
            click.echo("\n  No prompts to replay after rollback.\n")

        return True

    # ── Utilities ────────────────────────────────────────────────────────

    def _save_article(self, final_article: CompletedArticle) -> tuple[str, str]:
        print_separator()
        click.echo("  Saving Final Article")

        json_path, md_path = save_article_files(
            final_article,
            self.state.language,
            self.output_directory,
        )

        full_content = final_article.get_full_content()
        click.echo(
            f"""
  Article Generation Complete!

Article Details:
  Title: {final_article.outline.title}
  Grade: {final_article.review.grade if final_article.review else "N/A"}/5
  Total Length: {len(full_content)} characters
  Review Loop Iterations: {self.state.review_loop_iteration}
  Speculative Outlines: {self.num_outlines}

Files saved:
  JSON: {json_path}
  Markdown: {md_path}

Session Metadata:
  Session ID: {final_article.session_id}
  Created: {final_article.created_at}
"""
        )

        print_separator()
        click.echo("  Article Generation Complete!")

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
    num_outlines: int = 1,
) -> CompletedArticle | None:
    """Async entry point for the article generation pipeline."""
    mediator = ArticlePipelineMediator(
        theme=theme,
        language=language,
        llm_provider=llm_provider,
        model=model,
        output_directory=output_directory,
        auto_select=auto_select,
        num_outlines=num_outlines,
    )

    result = await mediator.execute()

    if result.success:
        return result.article
    else:
        if result.error:
            click.echo(f"  Pipeline error: {result.error}", err=True)
        return None

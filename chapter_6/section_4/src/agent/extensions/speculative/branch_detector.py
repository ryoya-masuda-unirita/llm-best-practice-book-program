"""Branch detector that identifies speculative execution opportunities."""

from typing import Any

from src.logger import make_logger

logger = make_logger(__name__)


class BranchDetector:
    """Identifies pipeline points where speculative execution is beneficial.

    Speculative execution is triggered when:
    - Multiple candidates exist (e.g., N outline options)
    - The phase is a known branch point
    - The number of candidates is within the allowed limit
    """

    # Phases where speculative branching is supported
    BRANCH_PHASES: dict[int, str] = {
        1: "Outline Generation",
    }

    def __init__(self, max_candidates: int = 3) -> None:
        self.max_candidates = max_candidates

    def should_speculate(
        self,
        phase: int,
        candidates: list[Any],
    ) -> bool:
        """Determine if speculative execution should be triggered.

        Args:
            phase: Current pipeline phase
            candidates: List of candidate options at this phase
        """
        if phase not in self.BRANCH_PHASES:
            logger.debug("Phase %d is not a branch point", phase)
            return False

        if len(candidates) <= 1:
            logger.debug("Only %d candidate(s); speculation not needed", len(candidates))
            return False

        if len(candidates) > self.max_candidates:
            logger.warning(
                "Too many candidates (%d > %d); limiting to %d",
                len(candidates),
                self.max_candidates,
                self.max_candidates,
            )

        logger.info(
            "Branch point detected at Phase %d (%s) with %d candidates",
            phase,
            self.BRANCH_PHASES[phase],
            min(len(candidates), self.max_candidates),
        )
        return True

    def get_branch_phase_name(self, phase: int) -> str | None:
        """Get the human-readable name for a branch phase."""
        return self.BRANCH_PHASES.get(phase)

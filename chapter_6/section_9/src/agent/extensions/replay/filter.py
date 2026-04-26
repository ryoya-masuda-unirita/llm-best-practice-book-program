"""Replay filter that classifies which prompts should be replayed after rollback."""

import re
from enum import Enum

from src.agent.extensions.replay.prompt_log import PromptLogEntry, PromptType
from src.logger import make_logger

logger = make_logger(__name__)


class ReplayDecision(Enum):
    """Decision for whether a prompt should be replayed."""

    REPLAY = "replay"
    SKIP = "skip"
    CONFIRM = "confirm"


# Multi-word patterns matched with simple substring
_MULTIWORD_PATTERNS = [
    "the same",
    "more detail",
    "explain further",
    "go on",
    "keep going",
]

# Single-word patterns matched with word boundaries
_WORD_BOUNDARY_PATTERNS = [
    "that",
    "it",
    "this",
    "those",
    "these",
    "above",
    "previous",
    "elaborate",
    "continue",
]

# Japanese patterns (no word boundary needed)
_JAPANESE_PATTERNS = [
    "それ",
    "これ",
    "あれ",
    "上記",
    "続き",
    "詳しく",
    "もう少し",
]

# Precompiled word-boundary regex for single-word English patterns
_WORD_BOUNDARY_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _WORD_BOUNDARY_PATTERNS) + r")\b",
    re.IGNORECASE,
)


class ReplayFilter:
    """Classifies prompts for replay decisions after rollback.

    Rules:
    - REQUIREMENT prompts -> REPLAY (explicit user requirements are always valid)
    - FEEDBACK prompts -> SKIP (yes/no responses to specific LLM outputs)
    - CONFIRMATION prompts -> SKIP (confirmations of specific states)
    - CONTEXT_DEPENDENT prompts -> CONFIRM (ask user before replaying)
    - Prompts that caused errors -> SKIP
    - Prompts with depends_on_prior_response=True -> CONFIRM
    """

    def classify(self, entry: PromptLogEntry, rollback_phase: int) -> ReplayDecision:
        """Classify a prompt log entry for replay decision."""
        # Never replay prompts that caused errors
        if entry.caused_error:
            logger.debug(f"Skipping entry {entry.index}: caused error")
            return ReplayDecision.SKIP

        # Never replay prompts from before or at the rollback phase
        if entry.phase <= rollback_phase:
            logger.debug(f"Skipping entry {entry.index}: phase {entry.phase} <= rollback phase {rollback_phase}")
            return ReplayDecision.SKIP

        # Classification based on prompt type
        if entry.prompt_type == PromptType.REQUIREMENT:
            if entry.depends_on_prior_response:
                logger.debug(f"Confirm entry {entry.index}: requirement but depends on prior response")
                return ReplayDecision.CONFIRM
            logger.debug(f"Replaying entry {entry.index}: explicit requirement")
            return ReplayDecision.REPLAY

        if entry.prompt_type == PromptType.FEEDBACK:
            logger.debug(f"Skipping entry {entry.index}: simple feedback")
            return ReplayDecision.SKIP

        if entry.prompt_type == PromptType.CONFIRMATION:
            logger.debug(f"Skipping entry {entry.index}: confirmation")
            return ReplayDecision.SKIP

        if entry.prompt_type == PromptType.CONTEXT_DEPENDENT:
            logger.debug(f"Confirm entry {entry.index}: context-dependent")
            return ReplayDecision.CONFIRM

        return ReplayDecision.SKIP

    @staticmethod
    def detect_prompt_type(prompt_text: str) -> PromptType:
        """Heuristically detect the type of a user prompt.

        This uses simple pattern matching. In production, this could be
        enhanced with LLM-based classification.
        """
        text_lower = prompt_text.lower().strip()

        # Simple feedback responses
        if text_lower in ("yes", "no", "y", "n", "ok", "はい", "いいえ"):
            return PromptType.FEEDBACK

        # Confirmation patterns
        if text_lower in ("approve", "reject", "accept", "decline", "承認", "却下"):
            return PromptType.CONFIRMATION

        # Check for context-dependent patterns
        if _is_context_dependent(text_lower):
            return PromptType.CONTEXT_DEPENDENT

        # Default: treat as a requirement (explicit user input)
        return PromptType.REQUIREMENT

    @staticmethod
    def detect_depends_on_prior(prompt_text: str) -> bool:
        """Detect if a prompt depends on the prior LLM response."""
        return _is_context_dependent(prompt_text.lower().strip())


def _is_context_dependent(text_lower: str) -> bool:
    """Check if text matches any context-dependent pattern."""
    # Multi-word substring matches
    for pattern in _MULTIWORD_PATTERNS:
        if pattern in text_lower:
            return True
    # Word-boundary matches for short English words
    if _WORD_BOUNDARY_RE.search(text_lower):
        return True
    # Japanese patterns (substring is fine)
    for pattern in _JAPANESE_PATTERNS:
        if pattern in text_lower:
            return True
    return False

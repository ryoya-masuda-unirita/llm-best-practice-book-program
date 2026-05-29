"""
Memory Service - User Memory Management for Learning AI Agent.

This module handles all memory-related operations:
1. Saving and loading user memory from JSON files
2. Managing memory files in the memory/ directory
3. Creating new memory instances
4. Adding feedback to existing memory

Memory files are stored as JSON in the memory/ directory, named:
    {user_id}_{timestamp}.json

The latest file for each user contains the complete, up-to-date memory.
"""

import json
from datetime import datetime
from pathlib import Path

from src.logger import make_logger
from src.model.model import (
    LearningProgress,
    TrainingFeedback,
    UserMemory,
    UserProfile,
)

logger = make_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

MEMORY_DIR = Path("memory")


# =============================================================================
# Private Helper Functions
# =============================================================================


def _ensure_memory_dir() -> Path:
    """Ensure the memory directory exists."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR


def _generate_memory_filename(user_id: str) -> str:
    """Generate a memory filename with user_id and timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{user_id}_{timestamp}.json"


def _get_user_memory_files(user_id: str) -> list[Path]:
    """Get all memory files for a user, sorted by timestamp (newest first)."""
    _ensure_memory_dir()
    pattern = f"{user_id}_*.json"
    files = list(MEMORY_DIR.glob(pattern))
    return sorted(files, reverse=True)


# =============================================================================
# Public Memory Functions
# =============================================================================


def save_memory(memory: UserMemory) -> Path:
    """Save user memory to a JSON file with timestamp."""
    _ensure_memory_dir()
    filename = _generate_memory_filename(memory.user_id)
    filepath = MEMORY_DIR / filename

    memory.updated_at = datetime.now().isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)

    logger.info(f"Memory saved: {filepath}")
    return filepath


def load_memory(user_id: str) -> UserMemory | None:
    """Load the latest memory for a user."""
    files = _get_user_memory_files(user_id)

    if not files:
        logger.info(f"No memory found for user: {user_id}")
        return None

    latest_file = files[0]
    logger.info(f"Loading memory from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return UserMemory.from_dict(data)


def load_memory_from_file(filepath: str | Path) -> UserMemory:
    """Load memory from a specific file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return UserMemory.from_dict(data)


def create_new_memory(profile: UserProfile) -> UserMemory:
    """Create a new memory for a user."""
    now = datetime.now().isoformat()
    return UserMemory(
        user_id=profile.user_id,
        created_at=now,
        updated_at=now,
        profile=profile,
        training_history=[],
        learned_patterns=[],
        progress=LearningProgress(),
    )


def list_user_memories() -> dict[str, list[Path]]:
    """List all users and their memory files."""
    _ensure_memory_dir()
    files = list(MEMORY_DIR.glob("*.json"))

    users: dict[str, list[Path]] = {}
    for f in files:
        # filename format: {user_id}_{timestamp}.json
        parts = f.stem.rsplit("_", 2)
        if len(parts) >= 3:
            user_id = "_".join(parts[:-2])
        else:
            user_id = parts[0]

        if user_id not in users:
            users[user_id] = []
        users[user_id].append(f)

    for user_id in users:
        users[user_id] = sorted(users[user_id], reverse=True)

    return users


def add_feedback_to_memory(
    feedback: TrainingFeedback,
    user_id: str,
) -> tuple[UserMemory, Path]:
    """Add feedback to user memory and save."""
    memory = load_memory(user_id)
    if memory is None:
        raise ValueError(f"No memory found for user: {user_id}")

    memory.add_feedback(feedback)
    logger.info(f"Added feedback: {feedback.feedback_id} for plan: {feedback.plan_id}")

    memory_path = save_memory(memory)

    return memory, memory_path

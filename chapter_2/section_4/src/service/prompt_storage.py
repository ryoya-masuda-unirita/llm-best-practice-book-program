"""Prompt storage service for LLMOps.

This module provides functionality to store prompt content separately from log streams,
as recommended in CLAUDE.md. This separation improves log readability and security.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.model.llmops_log import StorageType
from src.model.prompt_data import PromptData


class PromptStorage(ABC):
    """Abstract base class for prompt storage implementations."""

    @abstractmethod
    async def save_prompt(self, prompt_data: PromptData, mask_sensitive: bool = True) -> str:
        """Save prompt data and return the storage path/key."""
        pass

    @abstractmethod
    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]:
        """Retrieve prompt data by ID."""
        pass


class LocalFilePromptStorage(PromptStorage):
    """Local file system implementation of prompt storage.

    Stores prompts in a hierarchical directory structure partitioned by date
    for efficient searching: prompt_storage/YYYY/MM/DD/prompt_id.json
    """

    def __init__(self, base_dir: str = "prompt_storage"):
        """Initialize local file storage.

        Args:
            base_dir: Base directory for storing prompt files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_path(self, prompt_id: str, date: Optional[datetime] = None) -> Path:
        """Generate storage path for a prompt ID with date partitioning."""
        if date is None:
            date = datetime.utcnow()

        # Create date-based partitioning: YYYY/MM/DD
        year_dir = self.base_dir / str(date.year)
        month_dir = year_dir / f"{date.month:02d}"
        day_dir = month_dir / f"{date.day:02d}"

        # Create directories if they don't exist
        day_dir.mkdir(parents=True, exist_ok=True)

        return day_dir / f"{prompt_id}.json"

    async def save_prompt(self, prompt_data: PromptData, mask_sensitive: bool = True) -> str:
        """Save prompt data to local file system asynchronously.

        Args:
            prompt_data: The prompt data to save
            mask_sensitive: Whether to mask sensitive information

        Returns:
            The file path where the prompt was saved
        """
        if mask_sensitive:
            prompt_data.mask_sensitive_data()

        storage_path = self._get_storage_path(prompt_data.prompt_id)

        # Simulate async I/O (in production, use aiofiles)
        await asyncio.sleep(0)  # Yield control to event loop

        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump(prompt_data.model_dump(), f, indent=2, ensure_ascii=False)

        return str(storage_path)

    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]:
        """Retrieve prompt data from local file system.

        Args:
            prompt_id: The unique identifier of the prompt

        Returns:
            PromptData if found, None otherwise
        """
        # Search through date-partitioned directories
        # In production, consider maintaining an index for faster lookups
        for year_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue
                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir():
                        continue
                    prompt_file = day_dir / f"{prompt_id}.json"
                    if prompt_file.exists():
                        await asyncio.sleep(0)  # Yield control
                        with open(prompt_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        return PromptData(**data)

        return None


# Factory function to get storage instance
def get_prompt_storage(storage_type: StorageType = StorageType.LOCAL, **kwargs) -> PromptStorage:
    """Factory function to get prompt storage instance.

    Args:
        storage_type: Type of storage ('local', 's3', etc.)
        **kwargs: Additional arguments for storage initialization

    Returns:
        PromptStorage instance
    """
    if storage_type == StorageType.LOCAL:
        return LocalFilePromptStorage(**kwargs)
    # Future implementations: S3Storage, GCSStorage, etc.
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")

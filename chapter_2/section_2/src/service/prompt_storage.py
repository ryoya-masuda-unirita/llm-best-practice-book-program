"""Prompt storage service for LLMOps."""

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
    """Local file system implementation of prompt storage."""

    def __init__(self, base_dir: str = "prompt_storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_path(self, prompt_id: str, date: Optional[datetime] = None) -> Path:
        """Generate storage path for a prompt ID with date partitioning."""
        if date is None:
            date = datetime.utcnow()

        year_dir = self.base_dir / str(date.year)
        month_dir = year_dir / f"{date.month:02d}"
        day_dir = month_dir / f"{date.day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)

        return day_dir / f"{prompt_id}.json"

    async def save_prompt(self, prompt_data: PromptData, mask_sensitive: bool = True) -> str:
        """Save prompt data to local file system asynchronously."""
        if mask_sensitive:
            prompt_data.mask_sensitive_data()

        storage_path = self._get_storage_path(prompt_data.prompt_id)
        await asyncio.sleep(0)

        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump(prompt_data.model_dump(), f, indent=2, ensure_ascii=False)

        return str(storage_path)

    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]:
        """Retrieve prompt data from local file system."""
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
                        await asyncio.sleep(0)
                        with open(prompt_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        return PromptData(**data)

        return None


def get_prompt_storage(storage_type: StorageType = StorageType.LOCAL, **kwargs) -> PromptStorage:
    """Factory function to get prompt storage instance."""
    if storage_type == StorageType.LOCAL:
        return LocalFilePromptStorage(**kwargs)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")

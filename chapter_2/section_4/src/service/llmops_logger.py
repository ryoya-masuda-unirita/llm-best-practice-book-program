"""LLMOps structured logger."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from src.logger import make_logger
from src.model.llmops_log import LLMOpsLogEntry, StorageType
from src.model.prompt_data import PromptData
from src.service.prompt_storage import get_prompt_storage

logger = make_logger(__name__)


class LLMOpsLogger:
    """Structured logger for LLM operations with separate prompt storage."""

    def __init__(self, logger: logging.Logger, prompt_storage=None, enable_masking: bool = True):
        self.logger = logger
        self.prompt_storage = prompt_storage or get_prompt_storage(StorageType.LOCAL)
        self.enable_masking = enable_masking

    async def _store_prompt(self, prompt_data: PromptData) -> None:
        """Store prompt data asynchronously."""
        try:
            storage_path = await self.prompt_storage.save_prompt(prompt_data, mask_sensitive=self.enable_masking)
            self.logger.info(f"Prompt stored at: {storage_path}")
        except Exception as e:
            self.logger.error(f"Failed to store prompt {prompt_data.prompt_id}: {e}")

    @asynccontextmanager
    async def track_llm_request(
        self,
        model: str,
        prompt_content: Any,
        temperature: float | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        prompt_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Context manager to track LLM request timing and logging.

        Usage:
            async with llmops_logger.track_llm_request(model="gemini-2.5-flash", prompt_content=prompt) as tracking:
                response = await llm_client.generate(...)
                tracking["response"] = response
        """
        request_id = request_id or str(uuid4())
        prompt_id = prompt_id or str(uuid4())
        tracking: dict[str, Any] = {"request_id": request_id, "prompt_id": prompt_id, "response": None, "error": None}

        start_time = time.time()
        status_code = 200
        error_message = None
        level = "INFO"

        try:
            yield tracking
        except Exception as e:
            error_message = str(e)
            status_code = 500
            level = "ERROR"
            tracking["error"] = e
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000

            log_entry = LLMOpsLogEntry(
                request_id=request_id,
                prompt_id=prompt_id,
                user_id=user_id,
                model=model,
                temperature=temperature,
                latency_ms=latency_ms,
                status_code=status_code,
                error_message=error_message,
                level=level,
                metadata=metadata or {},
            )

            prompt_data = PromptData(
                prompt_id=prompt_id,
                prompt_content=prompt_content,
                response_content=tracking.get("response"),
                metadata={"request_id": request_id, **(metadata or {})},
            )
            await self._store_prompt(prompt_data)

            getattr(self.logger, level.lower())(log_entry.to_json_string())

    async def retrieve_prompt(self, prompt_id: str) -> PromptData | None:
        """Retrieve stored prompt by ID."""
        return await self.prompt_storage.retrieve_prompt(prompt_id)


def create_llmops_logger(
    logger_name: str = "llmops",
    log_level: int = logging.INFO,
    storage_type: StorageType = StorageType.LOCAL,
    enable_masking: bool = True,
    **storage_kwargs,
) -> LLMOpsLogger:
    """Factory function to create LLMOps logger."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return LLMOpsLogger(
        logger=logger, prompt_storage=get_prompt_storage(storage_type, **storage_kwargs), enable_masking=enable_masking
    )

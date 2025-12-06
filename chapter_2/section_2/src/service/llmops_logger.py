"""LLMOps structured logger."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from src.logger import make_logger
from src.model.llmops_log import LLMOpsLogEntry, LogLevel, StorageType
from src.model.prompt_data import PromptData
from src.service.prompt_storage import PromptStorage, get_prompt_storage

logger = make_logger(__name__)


class LLMOpsLogger:
    """Structured logger for LLM operations."""

    def __init__(
        self,
        logger: logging.Logger,
        prompt_storage: Optional[PromptStorage] = None,
        enable_masking: bool = True,
    ):
        self.logger = logger
        self.prompt_storage = prompt_storage or get_prompt_storage("local")
        self.enable_masking = enable_masking

    async def log_llm_request(
        self,
        request_id: str,
        prompt_id: str,
        model: str,
        prompt_content: Any,
        temperature: Optional[float] = None,
        response_content: Optional[Any] = None,
        user_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        level: LogLevel = LogLevel.INFO,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log an LLM request with structured format."""
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
            response_content=response_content,
            metadata={"request_id": request_id, **(metadata or {})},
        )

        await self._store_prompt_async(prompt_data)

        log_json = log_entry.to_json_string()
        log_method = getattr(self.logger, level.lower())
        log_method(log_json)

    async def _store_prompt_async(self, prompt_data: PromptData) -> None:
        """Store prompt data asynchronously."""
        try:
            storage_path = await self.prompt_storage.save_prompt(prompt_data, mask_sensitive=self.enable_masking)
            self.logger.info(f"Prompt stored successfully at: {storage_path}")
        except Exception as e:
            self.logger.error(f"Failed to store prompt {prompt_data.prompt_id}: {e}")

    @asynccontextmanager
    async def track_llm_request(
        self,
        model: str,
        prompt_content: Any,
        temperature: Optional[float] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        prompt_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[dict[str, str], None]:
        """Context manager to automatically track LLM request timing and logging."""
        request_id = request_id or str(uuid4())
        prompt_id = prompt_id or str(uuid4())
        tracking: dict[str, Any] = {
            "request_id": request_id,
            "prompt_id": prompt_id,
            "response": None,
            "error": None,
        }

        start_time = time.time()
        status_code = None
        error_message = None
        level = LogLevel.INFO

        try:
            yield tracking
            status_code = 200  # Success
        except Exception as e:
            error_message = str(e)
            status_code = 500
            level = LogLevel.ERROR
            tracking["error"] = e
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000

            await self.log_llm_request(
                request_id=request_id,
                prompt_id=prompt_id,
                model=model,
                temperature=temperature,
                prompt_content=prompt_content,
                response_content=tracking.get("response"),
                user_id=user_id,
                latency_ms=latency_ms,
                status_code=status_code,
                error_message=error_message,
                level=level,
                metadata=metadata,
            )

    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]:
        """Retrieve stored prompt by ID."""
        return await self.prompt_storage.retrieve_prompt(prompt_id)


def create_llmops_logger(
    logger_name: str = "llmops",
    log_level: int = logging.INFO,
    storage_type: StorageType = StorageType.LOCAL,
    enable_masking: bool = True,
    **storage_kwargs,
) -> LLMOpsLogger:
    """Factory function to create LLMOps logger with sensible defaults."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    prompt_storage = get_prompt_storage(storage_type, **storage_kwargs)

    return LLMOpsLogger(logger=logger, prompt_storage=prompt_storage, enable_masking=enable_masking)

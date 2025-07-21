import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from src.model import LLMProvider, LLMStructuredLog

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.DEBUG)  # type: ignore
if isinstance(LOG_LEVEL, str):
    LOG_LEVEL = LOG_LEVEL.upper()


class PrivacyMaskConfig:
    """Configuration for privacy masking."""

    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b\d{3}-\d{3}-\d{4}\b|\b\d{3}\.\d{3}\.\d{4}\b|\b\(\d{3}\)\s?\d{3}-\d{4}\b")
    CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    @classmethod
    def mask_sensitive_data(cls, text: str) -> str:
        """Mask sensitive information in text."""
        text = cls.EMAIL_PATTERN.sub("***EMAIL***", text)
        text = cls.PHONE_PATTERN.sub("***PHONE***", text)
        text = cls.CREDIT_CARD_PATTERN.sub("***CREDIT_CARD***", text)
        text = cls.SSN_PATTERN.sub("***SSN***", text)
        return text


class LLMStructuredLogger:
    """Structured logger for LLM operations with prompt storage."""

    def __init__(
        self,
        logs_base_dir: str = "./logs",
        prompts_base_dir: str = "./prompt_storage",
        enable_privacy_masking: bool = True,
        log_to_console: bool = True,
    ):
        self.logs_base_dir = Path(logs_base_dir)
        self.prompts_base_dir = Path(prompts_base_dir)
        self.enable_privacy_masking = enable_privacy_masking
        self.log_to_console = log_to_console

        self.logs_base_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_base_dir.mkdir(parents=True, exist_ok=True)

        self.console_logger = self._setup_console_logger() if log_to_console else None

    def _setup_console_logger(self) -> logging.Logger:
        """Setup console logger for structured logging."""
        logger = logging.getLogger("llm_structured_logger")
        logger.setLevel(LOG_LEVEL)

        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(LOG_LEVEL)
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [LLM] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _get_time_based_path(self, base_dir: Path, timestamp: datetime, filename: str) -> Path:
        """Generate time-based directory structure path."""
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d")
        hour = timestamp.strftime("%H")
        minute = timestamp.strftime("%M")
        second = timestamp.strftime("%S")

        dir_path = base_dir / year / month / day / hour / minute / second
        dir_path.mkdir(parents=True, exist_ok=True)

        return dir_path / filename

    async def _save_prompt_async(self, prompt_id: str, log_entry: LLMStructuredLog) -> None:
        """Save prompt data to storage asynchronously."""
        try:
            filename = f"prompt-{prompt_id}.json"
            file_path = self._get_time_based_path(self.prompts_base_dir, log_entry.timestamp, filename)

            prompt_data = {
                "prompt_id": prompt_id,
                "timestamp": log_entry.timestamp.isoformat(),
                "input_text": log_entry.input_text,
                "output_text": log_entry.output_text,
                "model": log_entry.model,
                "provider": log_entry.provider.value,
                "temperature": log_entry.temperature,
                "user_id": log_entry.user_id,
                "metadata": log_entry.metadata,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(prompt_data, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            if self.console_logger:
                self.console_logger.error(f"Failed to save prompt data: {e}")

    async def log_llm_request(
        self,
        model: str,
        provider: LLMProvider,
        input_text: str,
        output_text: str,
        temperature: float,
        latency_ms: int,
        status_code: int = 200,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log LLM request with structured format."""

        prompt_id = str(uuid4())
        timestamp = datetime.now()

        # Apply privacy masking if enabled
        masked_input = PrivacyMaskConfig.mask_sensitive_data(input_text) if self.enable_privacy_masking else input_text
        masked_output = (
            PrivacyMaskConfig.mask_sensitive_data(output_text) if self.enable_privacy_masking else output_text
        )

        # Create structured log entry
        log_entry = LLMStructuredLog(
            timestamp=timestamp,
            prompt_id=prompt_id,
            user_id=user_id,
            model=model,
            temperature=temperature,
            input_text=masked_input,
            output_text=masked_output,
            latency_ms=latency_ms,
            status_code=status_code,
            provider=provider,
            metadata=metadata,
        )

        # Log to console (structured JSON format)
        if self.console_logger:
            log_data = {
                "timestamp": timestamp.isoformat(),
                "prompt_id": prompt_id,
                "user_id": user_id,
                "model": model,
                "provider": provider.value,
                "temperature": temperature,
                "latency_ms": latency_ms,
                "status_code": status_code,
                "input_length": len(input_text),
                "output_length": len(output_text),
                "metadata": metadata,
            }
            self.console_logger.info(json.dumps(log_data, ensure_ascii=False))

        # Save to structured log file
        log_filename = f"llm-log-{timestamp.strftime('%Y%m%d-%H%M%S')}.jsonl"
        log_file_path = self._get_time_based_path(self.logs_base_dir, timestamp, log_filename)

        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry.model_dump(), ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            if self.console_logger:
                self.console_logger.error(f"Failed to write structured log: {e}")

        # Save prompt data asynchronously (without blocking)
        asyncio.create_task(self._save_prompt_async(prompt_id, log_entry))

        return prompt_id


def make_logger(name) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Global instance
llm_logger = LLMStructuredLogger()

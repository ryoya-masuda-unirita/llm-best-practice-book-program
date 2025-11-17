"""Prompt data model for LLMOps."""

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class PromptData(BaseModel):
    """Model for prompt data to be stored."""

    prompt_id: str
    prompt_content: Any
    response_content: Any = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)

    def mask_sensitive_data(self) -> None:
        """Mask potentially sensitive information in prompt and response content."""
        patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****"),  # SSN
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "***@***.***"),  # Email
            (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "****-****-****-****"),  # Credit card
        ]

        def mask_text(text: Any) -> Any:
            if isinstance(text, str):
                for pattern, replacement in patterns:
                    text = re.sub(pattern, replacement, text)
                return text
            elif isinstance(text, list):
                return [mask_text(item) for item in text]
            elif isinstance(text, dict):
                return {k: mask_text(v) for k, v in text.items()}
            return text

        self.prompt_content = mask_text(self.prompt_content)
        if self.response_content:
            self.response_content = mask_text(self.response_content)

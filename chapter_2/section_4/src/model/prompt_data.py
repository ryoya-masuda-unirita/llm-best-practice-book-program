"""Prompt data model for LLMOps."""

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PromptData(BaseModel):
    """Model for prompt data to be stored."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    prompt_id: str = Field(..., description="Unique identifier for the prompt")
    prompt_content: Any = Field(..., description="The actual prompt content (can be string or list of messages)")
    response_content: Optional[Any] = Field(None, description="The LLM response content")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp when prompt was created",
    )
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

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

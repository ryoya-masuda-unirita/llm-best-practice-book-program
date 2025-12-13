"""Module for generating and validating JSON schemas"""

import json
import os
from typing import Any, Protocol

from openai import OpenAI
from openai.types.responses import ResponseOutputMessage
from src.auto_structured_output.prompts import get_schema_extraction_messages, get_schema_retry_messages
from src.auto_structured_output.validators import SchemaValidator
from src.client.llm_client import OpenAIModel


class LLMClient(Protocol):
    """Protocol for LLM clients supporting chat completions"""

    def generate_content(self, model: str, messages: list[dict[str, str]]) -> str: ...


class SchemaGenerator:
    def __init__(self, max_retries: int = 3):
        self.basic_prediction_model = OpenAIModel(os.getenv("BASIC_PREDICTION_MODEL", OpenAIModel.GPT_4O))
        self.high_reasoning_model = OpenAIModel(os.getenv("HIGH_PREDICTION_MODEL", self.basic_prediction_model))
        self.max_retries = max_retries

    def extract_from_prompt(
        self,
        prompts: list[str],
        client: OpenAI,
        model: str,
        use_high_reasoning: bool = False,
    ) -> dict[str, Any]:
        """Extract schema from prompt(s) with automatic retry on validation failure.

        Multiple prompts generate a unified schema covering all use cases.
        Raises ValueError if validation fails after max_retries attempts.
        """
        messages = get_schema_extraction_messages(prompts, use_high_reasoning=use_high_reasoning)

        last_error = None
        last_schema = None

        for attempt in range(self.max_retries):
            try:
                schema = self._call_api(client, model, messages)
                last_schema = schema
                SchemaValidator.validate_schema(schema)
                return schema

            except ValueError as e:
                last_error = str(e)

                if attempt == self.max_retries - 1:
                    raise ValueError(
                        f"Failed to generate valid schema after {self.max_retries} attempts. Last error: {last_error}"
                    ) from e

                messages = get_schema_retry_messages(
                    original_prompt=prompts,
                    previous_schema=last_schema,
                    error_message=last_error,
                    use_high_reasoning=use_high_reasoning,
                )

        raise ValueError(f"Failed to generate valid schema. Last error: {last_error}")

    def _call_api(
        self,
        client: OpenAI,
        model: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        response = client.responses.create(  # type: ignore[call-overload]
            model=model,
            input=messages,  # type: ignore[arg-type]
            text={"format": {"type": "json_object"}},
        )

        _r = [o for o in response.output if isinstance(o, ResponseOutputMessage)][0]
        content = _r.content[0].text

        if not content:
            raise ValueError("Response from OpenAI API is empty")

        try:
            schema = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Response from LLM API is not valid JSON: {e}") from e

        return schema

    def validate_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return SchemaValidator.validate_schema(schema)

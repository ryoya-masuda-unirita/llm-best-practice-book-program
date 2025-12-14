"""
Base Agent Module for the Hierarchical AI Agent Architecture.

This module provides the abstract base class for all layer agents,
establishing common interfaces and utilities for JSON parsing and LLM invocation.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from src.client.llm_client import OpenAIModel
from src.config import config as global_config
from src.logger import make_logger

logger = make_logger(__name__)

# Type variable for parsed output
T = TypeVar("T")

# =============================================================================
# Constants
# =============================================================================

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


# =============================================================================
# JSON Parsing Utilities
# =============================================================================


def _try_fix_truncated_json(json_str: str) -> str:
    """Try to fix truncated JSON by adding missing closing brackets/braces."""
    open_braces = json_str.count("{") - json_str.count("}")
    open_brackets = json_str.count("[") - json_str.count("]")

    # Check for unterminated strings
    in_string = False
    escape_next = False
    for char in json_str:
        if escape_next:
            escape_next = False
        elif char == "\\":
            escape_next = True
        elif char == '"':
            in_string = not in_string

    if in_string:
        json_str += '"'

    return json_str + "]" * open_brackets + "}" * open_braces


def _extract_json_string(response: str) -> str:
    """Extract JSON string from LLM response using multiple strategies."""
    stripped = response.strip()

    # Strategy 1: Response starts with '{'
    if stripped.startswith("{"):
        return stripped

    # Strategy 2: Find ```json code block
    if match := re.search(r"```json\s*([\s\S]*?)```", response):
        return match.group(1).strip()

    # Strategy 3: Find first { and last }
    first_brace = response.find("{")
    last_brace = response.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        return response[first_brace : last_brace + 1]

    return stripped


def extract_json_from_response(response: str) -> dict:
    """Extract and parse JSON from LLM response."""
    if not response or not response.strip():
        raise ValueError("Empty response from LLM")

    json_str = _extract_json_string(response)
    if not json_str:
        raise ValueError(f"No JSON content found in response: {response[:200]}...")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("JSON parsing failed, attempting to fix truncated JSON...")
        fixed_json = _try_fix_truncated_json(json_str)
        try:
            return json.loads(fixed_json)
        except json.JSONDecodeError as e:
            logger.error(f"Original JSON (first 500 chars): {json_str[:500]}...")
            logger.error(f"Fixed JSON (last 200 chars): ...{fixed_json[-200:]}")
            raise e


# =============================================================================
# Base Agent Class
# =============================================================================


class BaseAgent(ABC):
    """
    Abstract base class for all hierarchical layer agents.

    Provides common utilities for LLM invocation, logging, JSON parsing,
    and error handling. Subclasses implement the `execute` method for
    layer-specific logic.
    """

    def __init__(self, layer_name: str, agent_name: str):
        self.layer_name = layer_name
        self.agent_name = agent_name
        self.logger = make_logger(f"{layer_name}.{agent_name}")

    # -------------------------------------------------------------------------
    # LLM Utilities
    # -------------------------------------------------------------------------

    def _get_model_from_config(self, config: RunnableConfig) -> str:
        """Extract model name from config with default fallback."""
        return config.get("configurable", {}).get("model", OpenAIModel.GPT_5_MINI)

    def _create_chat_model(self, config: RunnableConfig) -> ChatOpenAI:
        """Create a ChatOpenAI model instance from config."""
        return ChatOpenAI(
            model=self._get_model_from_config(config),
            openai_api_key=global_config.openai_api_key,
        )

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list:
        """Build message list for LLM invocation."""
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

    def _invoke_with_retry(self, model: ChatOpenAI, messages: list, config: RunnableConfig) -> str:
        """Invoke LLM with retry logic for transient failures."""
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = model.invoke(messages, config)
                if response.content and response.content.strip():
                    return response.content
                self.logger.warning(f"Empty response on attempt {attempt + 1}")
            except Exception as e:
                last_error = e
                self.logger.warning(f"Error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES - 1:
                self.logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)

        raise ValueError(f"{self.agent_name} failed after {MAX_RETRIES} attempts: {last_error}")

    # -------------------------------------------------------------------------
    # Parsing Utilities
    # -------------------------------------------------------------------------

    def _safe_enum_parse(self, enum_class, value: str, default):
        """Safely parse an enum value with fallback to default."""
        try:
            return enum_class(value)
        except ValueError:
            return default

    # -------------------------------------------------------------------------
    # Logging Utilities
    # -------------------------------------------------------------------------

    def _log_layer_start(self, description: str) -> None:
        """Log the start of layer execution."""
        self.logger.info("=" * 60)
        self.logger.info(f"{self.layer_name} LAYER - {self.agent_name}: {description}")
        self.logger.info("=" * 60)

    # -------------------------------------------------------------------------
    # Template Method for Common LLM Workflow
    # -------------------------------------------------------------------------

    def _invoke_and_parse(
        self,
        config: RunnableConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """
        Common workflow: build messages, invoke LLM with retry, parse JSON response.

        This template method encapsulates the repetitive pattern used by all agents.
        """
        model = self._create_chat_model(config)
        messages = self._build_messages(system_prompt, user_prompt)
        response_content = self._invoke_with_retry(model, messages, config)
        self.logger.info("Received response from LLM")
        return extract_json_from_response(response_content)

    def _handle_parse_error(self, error: Exception, response_content: str | None = None) -> None:
        """Log parsing errors with context."""
        self.logger.error(f"Failed to parse response: {error}")
        if response_content:
            self.logger.error(f"Raw response: {response_content[:500]}...")

    # -------------------------------------------------------------------------
    # Abstract Method
    # -------------------------------------------------------------------------

    @abstractmethod
    def execute(self, state: dict, config: RunnableConfig) -> dict:
        """
        Execute the agent's main logic.

        Args:
            state: Current hierarchical agent state
            config: Runtime configuration including model settings

        Returns:
            Updated state dictionary with agent outputs
        """
        pass

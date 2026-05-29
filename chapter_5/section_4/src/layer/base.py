"""
Base Agent Module for the Hierarchical AI Agent Architecture.

This module provides the abstract base class for all layer agents,
establishing common interfaces and utilities for LLM invocation with structured output.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from src.client.llm_client import OpenAIModel
from src.config import config as global_config
from src.logger import make_logger

logger = make_logger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


class BaseAgent(ABC):
    """
    Abstract base class for all hierarchical layer agents.

    Provides common utilities for LLM invocation with structured output,
    logging, and error handling. Subclasses implement the `execute` method
    for layer-specific logic.
    """

    def __init__(self, layer_name: str, agent_name: str):
        self.layer_name = layer_name
        self.agent_name = agent_name
        self.logger = make_logger(f"{layer_name}.{agent_name}")

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

    def _log_layer_start(self, description: str) -> None:
        """Log the start of layer execution."""
        self.logger.info("=" * 60)
        self.logger.info(f"{self.layer_name} LAYER - {self.agent_name}: {description}")
        self.logger.info("=" * 60)

    def _invoke_structured[T: BaseModel](
        self,
        config: RunnableConfig,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        """
        Invoke LLM with structured output and retry logic.

        Uses OpenAI's structured output mode to ensure the response
        conforms to the specified Pydantic model schema.
        """
        model = self._create_chat_model(config)
        structured_model = model.with_structured_output(response_model)
        messages = self._build_messages(system_prompt, user_prompt)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = structured_model.invoke(messages, config)
                if response is not None:
                    self.logger.info("Received structured response from LLM")
                    return response
                self.logger.warning(f"Empty response on attempt {attempt + 1}")
            except Exception as e:
                last_error = e
                self.logger.warning(f"Error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES - 1:
                self.logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)

        raise ValueError(f"{self.agent_name} failed after {MAX_RETRIES} attempts: {last_error}")

    async def _ainvoke_structured[T: BaseModel](
        self,
        config: RunnableConfig,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        """
        Async invoke LLM with structured output and retry logic.

        Uses OpenAI's structured output mode to ensure the response
        conforms to the specified Pydantic model schema.
        """
        model = self._create_chat_model(config)
        structured_model = model.with_structured_output(response_model)
        messages = self._build_messages(system_prompt, user_prompt)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await structured_model.ainvoke(messages, config)
                if response is not None:
                    self.logger.info("Received structured response from LLM")
                    return response
                self.logger.warning(f"Empty response on attempt {attempt + 1}")
            except Exception as e:
                last_error = e
                self.logger.warning(f"Error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES - 1:
                self.logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        raise ValueError(f"{self.agent_name} failed after {MAX_RETRIES} attempts: {last_error}")

    @abstractmethod
    def execute(self, state: dict, config: RunnableConfig) -> dict:
        """Execute the agent's main logic."""
        pass

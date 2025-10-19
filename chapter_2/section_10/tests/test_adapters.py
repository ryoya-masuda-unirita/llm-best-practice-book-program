"""Tests for LLM adapter implementations.

This module tests the OpenAI and Gemini adapters to ensure they correctly
implement the LLMClient interface and properly interact with their respective APIs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel
from src.client.adapters import GeminiAdapter, OpenAIAdapter
from src.client.base import LLMClient
from src.client.model import GeminiModel, LLMProvider, OpenAIModel


class MockResponse(BaseModel):
    """Mock response model for testing structured outputs."""

    message: str
    confidence: float


class TestOpenAIAdapter:
    """Test suite for OpenAIAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create an OpenAIAdapter instance for testing."""
        with patch("src.client.adapters.AsyncOpenAI") as mock_openai:
            adapter = OpenAIAdapter(model=OpenAIModel.GPT_4O)
            adapter._client = mock_openai.return_value
            return adapter

    def test_implements_llm_client_interface(self, adapter):
        """Verify OpenAIAdapter implements LLMClient interface."""
        assert isinstance(adapter, LLMClient)

    def test_initialization(self):
        """Test adapter initialization with model."""
        with patch("src.client.adapters.AsyncOpenAI") as mock_openai:
            adapter = OpenAIAdapter(model=OpenAIModel.GPT_4O)
            assert adapter._model == OpenAIModel.GPT_4O
            mock_openai.assert_called_once()

    def test_get_provider_name(self, adapter):
        """Test provider name retrieval."""
        assert adapter.get_provider_name() == LLMProvider.OPENAI

    def test_get_model_name(self, adapter):
        """Test model name retrieval."""
        assert adapter.get_model_name() == OpenAIModel.GPT_4O

    @pytest.mark.asyncio
    async def test_chat_success(self, adapter):
        """Test successful chat completion."""
        # Setup mock response
        mock_parsed = MockResponse(message="Hello", confidence=0.95)
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_result = MagicMock()
        mock_result.choices = [mock_choice]

        adapter._client.beta.chat.completions.parse = AsyncMock(return_value=mock_result)

        # Execute
        messages = [{"role": "user", "content": "Hello"}]
        result = await adapter.chat(messages, MockResponse)

        # Verify
        assert result == mock_parsed
        assert result.message == "Hello"
        assert result.confidence == 0.95
        adapter._client.beta.chat.completions.parse.assert_called_once_with(
            model=OpenAIModel.GPT_4O,
            messages=messages,
            response_format=MockResponse,
        )

    @pytest.mark.asyncio
    async def test_chat_with_additional_kwargs(self, adapter):
        """Test chat with additional parameters."""
        mock_parsed = MockResponse(message="Test", confidence=0.8)
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_result = MagicMock()
        mock_result.choices = [mock_choice]

        adapter._client.beta.chat.completions.parse = AsyncMock(return_value=mock_result)

        messages = [{"role": "user", "content": "Test"}]
        result = await adapter.chat(messages, MockResponse, temperature=0.7, max_tokens=100)

        assert result == mock_parsed
        adapter._client.beta.chat.completions.parse.assert_called_once_with(
            model=OpenAIModel.GPT_4O,
            messages=messages,
            response_format=MockResponse,
            temperature=0.7,
            max_tokens=100,
        )

    @pytest.mark.asyncio
    async def test_chat_api_error(self, adapter):
        """Test handling of API errors."""
        adapter._client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API Error"))

        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(Exception, match="API Error"):
            await adapter.chat(messages, MockResponse)


class TestGeminiAdapter:
    """Test suite for GeminiAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a GeminiAdapter instance for testing."""
        with patch("src.client.adapters.genai.Client") as mock_client:
            adapter = GeminiAdapter(model=GeminiModel.GEMINI_2_5_PRO)
            adapter._client = mock_client.return_value
            return adapter

    def test_implements_llm_client_interface(self, adapter):
        """Verify GeminiAdapter implements LLMClient interface."""
        assert isinstance(adapter, LLMClient)

    def test_initialization(self):
        """Test adapter initialization with model."""
        with patch("src.client.adapters.genai.Client") as mock_client:
            adapter = GeminiAdapter(model=GeminiModel.GEMINI_2_5_FLASH)
            assert adapter._model == GeminiModel.GEMINI_2_5_FLASH
            mock_client.assert_called_once()

    def test_get_provider_name(self, adapter):
        """Test provider name retrieval."""
        assert adapter.get_provider_name() == LLMProvider.GEMINI

    def test_get_model_name(self, adapter):
        """Test model name retrieval."""
        assert adapter.get_model_name() == GeminiModel.GEMINI_2_5_PRO

    @pytest.mark.asyncio
    async def test_chat_success_with_system_message(self, adapter):
        """Test successful chat completion with system instruction."""
        # Setup mock response
        mock_parsed = MockResponse(message="Response", confidence=0.9)
        mock_result = MagicMock()
        mock_result.parsed = mock_parsed

        adapter._client.aio.models.generate_content = AsyncMock(return_value=mock_result)

        # Execute with system and user messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        result = await adapter.chat(messages, MockResponse)

        # Verify
        assert result == mock_parsed
        call_args = adapter._client.aio.models.generate_content.call_args
        assert call_args.kwargs["model"] == GeminiModel.GEMINI_2_5_PRO
        assert call_args.kwargs["contents"] == "Hello"
        assert call_args.kwargs["config"].system_instruction == "You are a helpful assistant."
        assert call_args.kwargs["config"].response_mime_type == "application/json"
        assert call_args.kwargs["config"].response_schema == MockResponse

    @pytest.mark.asyncio
    async def test_chat_success_without_system_message(self, adapter):
        """Test chat completion without system instruction."""
        mock_parsed = MockResponse(message="Response", confidence=0.85)
        mock_result = MagicMock()
        mock_result.parsed = mock_parsed

        adapter._client.aio.models.generate_content = AsyncMock(return_value=mock_result)

        messages = [{"role": "user", "content": "Hello"}]
        result = await adapter.chat(messages, MockResponse)

        assert result == mock_parsed
        call_args = adapter._client.aio.models.generate_content.call_args
        assert call_args.kwargs["contents"] == "Hello"
        # System instruction should not be set
        assert (
            not hasattr(call_args.kwargs["config"], "system_instruction")
            or call_args.kwargs["config"].system_instruction is None
        )

    @pytest.mark.asyncio
    async def test_chat_with_multiple_user_messages(self, adapter):
        """Test that only the last user message is used."""
        mock_parsed = MockResponse(message="Response", confidence=0.9)
        mock_result = MagicMock()
        mock_result.parsed = mock_parsed

        adapter._client.aio.models.generate_content = AsyncMock(return_value=mock_result)

        messages = [
            {"role": "user", "content": "First message"},
            {"role": "user", "content": "Second message"},
        ]
        result = await adapter.chat(messages, MockResponse)

        assert result == mock_parsed
        call_args = adapter._client.aio.models.generate_content.call_args
        # Should use the last user message
        assert call_args.kwargs["contents"] == "Second message"

    @pytest.mark.asyncio
    async def test_chat_api_error(self, adapter):
        """Test handling of API errors."""
        adapter._client.aio.models.generate_content = AsyncMock(side_effect=Exception("Gemini API Error"))

        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(Exception, match="Gemini API Error"):
            await adapter.chat(messages, MockResponse)


class TestAdapterComparison:
    """Test suite comparing adapter behaviors."""

    @pytest.mark.asyncio
    async def test_both_adapters_return_basemodel(self):
        """Verify both adapters return Pydantic BaseModel instances."""
        with patch("src.client.adapters.AsyncOpenAI"):
            openai_adapter = OpenAIAdapter(model=OpenAIModel.GPT_4O)
            mock_parsed = MockResponse(message="OpenAI", confidence=0.9)
            mock_message = MagicMock()
            mock_message.parsed = mock_parsed
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_result = MagicMock()
            mock_result.choices = [mock_choice]
            openai_adapter._client.beta.chat.completions.parse = AsyncMock(return_value=mock_result)

            messages = [{"role": "user", "content": "Test"}]
            openai_result = await openai_adapter.chat(messages, MockResponse)
            assert isinstance(openai_result, BaseModel)

        with patch("src.client.adapters.genai.Client"):
            gemini_adapter = GeminiAdapter(model=GeminiModel.GEMINI_2_5_PRO)
            mock_parsed = MockResponse(message="Gemini", confidence=0.85)
            mock_result = MagicMock()
            mock_result.parsed = mock_parsed
            gemini_adapter._client.aio.models.generate_content = AsyncMock(return_value=mock_result)

            gemini_result = await gemini_adapter.chat(messages, MockResponse)
            assert isinstance(gemini_result, BaseModel)

    def test_both_adapters_have_consistent_interface(self):
        """Verify both adapters expose the same interface methods."""
        with patch("src.client.adapters.AsyncOpenAI"):
            openai_adapter = OpenAIAdapter(model=OpenAIModel.GPT_4O)

        with patch("src.client.adapters.genai.Client"):
            gemini_adapter = GeminiAdapter(model=GeminiModel.GEMINI_2_5_PRO)

        # Check both have the same public methods
        openai_methods = {m for m in dir(openai_adapter) if not m.startswith("_")}
        gemini_methods = {m for m in dir(gemini_adapter) if not m.startswith("_")}

        # Both should implement the same LLMClient interface
        required_methods = {"chat", "get_provider_name", "get_model_name"}
        assert required_methods.issubset(openai_methods)
        assert required_methods.issubset(gemini_methods)

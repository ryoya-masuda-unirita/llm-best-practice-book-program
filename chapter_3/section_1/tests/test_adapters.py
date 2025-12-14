"""Tests for LLM adapter implementations.

This module tests the OpenAI and Gemini adapters to ensure they correctly
implement the LLMClient interface and properly interact with their respective APIs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel
from src.client.adapters import AnthropicAdapter, GeminiAdapter, OpenAIAdapter
from src.client.base import LLMClient
from src.client.model import AnthropicModel, GeminiModel, LLMProvider, OpenAIModel
from src.prompt import make_prompt


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
        mock_parsed = MockResponse(message="Hello", confidence=0.95)
        mock_result = MagicMock()
        mock_result.output_parsed = mock_parsed

        adapter._client.responses.parse = AsyncMock(return_value=mock_result)

        messages = [{"role": "user", "content": "Hello"}]
        result = await adapter.chat(messages, MockResponse)

        assert result == mock_parsed
        assert result.message == "Hello"
        assert result.confidence == 0.95
        adapter._client.responses.parse.assert_called_once_with(
            model=OpenAIModel.GPT_4O,
            input=messages,
            text_format=MockResponse,
        )

    @pytest.mark.asyncio
    async def test_chat_with_additional_kwargs(self, adapter):
        """Test chat with additional parameters."""
        mock_parsed = MockResponse(message="Test", confidence=0.8)
        mock_result = MagicMock()
        mock_result.output_parsed = mock_parsed

        adapter._client.responses.parse = AsyncMock(return_value=mock_result)

        messages = [{"role": "user", "content": "Test"}]
        result = await adapter.chat(messages, MockResponse, temperature=0.7, max_tokens=100)

        assert result == mock_parsed
        adapter._client.responses.parse.assert_called_once_with(
            model=OpenAIModel.GPT_4O,
            input=messages,
            text_format=MockResponse,
            temperature=0.7,
            max_tokens=100,
        )

    @pytest.mark.asyncio
    async def test_chat_api_error(self, adapter):
        """Test handling of API errors."""
        adapter._client.responses.parse = AsyncMock(side_effect=Exception("API Error"))

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
        mock_parsed = MockResponse(message="Response", confidence=0.9)
        mock_result = MagicMock()
        mock_result.parsed = mock_parsed

        adapter._client.aio.models.generate_content = AsyncMock(return_value=mock_result)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        result = await adapter.chat(messages, MockResponse)

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


class TestAnthropicAdapter:
    """Test suite for AnthropicAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create an AnthropicAdapter instance for testing."""
        with patch("src.client.adapters.AsyncAnthropic") as mock_client:
            adapter = AnthropicAdapter(model=AnthropicModel.CLAUDE_SONNET_4_5)
            adapter._client = mock_client.return_value
            return adapter

    def test_implements_llm_client_interface(self, adapter):
        """Verify AnthropicAdapter implements LLMClient interface."""
        assert isinstance(adapter, LLMClient)

    def test_initialization(self):
        """Test adapter initialization with model."""
        with patch("src.client.adapters.AsyncAnthropic") as mock_client:
            adapter = AnthropicAdapter(model=AnthropicModel.CLAUDE_OPUS_4_1)
            assert adapter._model == AnthropicModel.CLAUDE_OPUS_4_1
            mock_client.assert_called_once()

    def test_get_provider_name(self, adapter):
        """Test provider name retrieval."""
        assert adapter.get_provider_name() == LLMProvider.ANTHROPIC

    def test_get_model_name(self, adapter):
        """Test model name retrieval."""
        assert adapter.get_model_name() == AnthropicModel.CLAUDE_SONNET_4_5

    @pytest.mark.asyncio
    async def test_chat_success(self, adapter):
        """Test successful chat completion."""
        mock_parsed = MockResponse(message="Response", confidence=0.92)
        mock_result = MagicMock()
        mock_result.parsed_output = mock_parsed

        adapter._client.beta.messages.parse = AsyncMock(return_value=mock_result)

        messages = [{"role": "user", "content": "Hello"}]
        result = await adapter.chat(messages, MockResponse)

        assert result == mock_parsed
        call_args = adapter._client.beta.messages.parse.call_args
        assert call_args.kwargs["model"] == AnthropicModel.CLAUDE_SONNET_4_5
        assert call_args.kwargs["messages"] == messages
        assert call_args.kwargs["output_format"] == MockResponse
        assert call_args.kwargs["max_tokens"] == 1024
        assert "structured-outputs-2025-11-13" in call_args.kwargs["betas"]

    @pytest.mark.asyncio
    async def test_chat_with_custom_max_tokens(self, adapter):
        """Test chat with custom max_tokens parameter."""
        mock_parsed = MockResponse(message="Test", confidence=0.88)
        mock_result = MagicMock()
        mock_result.parsed_output = mock_parsed

        adapter._client.beta.messages.parse = AsyncMock(return_value=mock_result)

        messages = [{"role": "user", "content": "Test"}]
        result = await adapter.chat(messages, MockResponse, max_tokens=2048)

        assert result == mock_parsed
        call_args = adapter._client.beta.messages.parse.call_args
        assert call_args.kwargs["max_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_chat_api_error(self, adapter):
        """Test handling of API errors."""
        adapter._client.beta.messages.parse = AsyncMock(side_effect=Exception("Anthropic API Error"))

        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(Exception, match="Anthropic API Error"):
            await adapter.chat(messages, MockResponse)


class TestAdapterComparison:
    """Test suite comparing adapter behaviors."""

    @pytest.mark.asyncio
    async def test_both_adapters_return_basemodel(self):
        """Verify both adapters return Pydantic BaseModel instances."""
        with patch("src.client.adapters.AsyncOpenAI"):
            openai_adapter = OpenAIAdapter(model=OpenAIModel.GPT_4O)
            mock_parsed = MockResponse(message="OpenAI", confidence=0.9)
            mock_result = MagicMock()
            mock_result.output_parsed = mock_parsed
            openai_adapter._client.responses.parse = AsyncMock(return_value=mock_result)

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
        required_methods = {"chat", "get_provider_name", "get_model_name", "aclose"}
        assert required_methods.issubset(openai_methods)
        assert required_methods.issubset(gemini_methods)


class TestMakePrompt:
    """Test suite for the unified make_prompt function."""

    def test_make_prompt_openai(self):
        """Test make_prompt returns correct format for OpenAI."""
        prompt = make_prompt(LLMProvider.OPENAI)
        assert isinstance(prompt, list)
        assert len(prompt) == 2
        assert prompt[0]["role"] == "system"
        assert prompt[1]["role"] == "user"
        assert "content" in prompt[0]
        assert "content" in prompt[1]

    def test_make_prompt_gemini(self):
        """Test make_prompt returns correct format for Gemini."""
        prompt = make_prompt(LLMProvider.GEMINI)
        assert isinstance(prompt, tuple)
        assert len(prompt) == 2
        system_prompt, user_prompt = prompt
        assert isinstance(system_prompt, str)
        assert isinstance(user_prompt, str)
        assert len(system_prompt) > 0
        assert len(user_prompt) > 0

    def test_make_prompt_anthropic(self):
        """Test make_prompt returns correct format for Anthropic."""
        prompt = make_prompt(LLMProvider.ANTHROPIC)
        assert isinstance(prompt, list)
        assert len(prompt) == 1
        assert prompt[0]["role"] == "user"
        assert "content" in prompt[0]

    def test_make_prompt_unsupported_provider(self):
        """Test make_prompt raises error for unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            make_prompt("unsupported_provider")

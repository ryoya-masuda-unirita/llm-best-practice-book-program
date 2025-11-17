"""Unit tests for streaming service functions."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.genai.types import GenerateContentConfig
from src.service.streaming_service import stream_gemini_response, stream_openai_response


@pytest.mark.unit
class TestStreamOpenAIResponse:
    """Tests for stream_openai_response function."""

    @pytest.mark.asyncio
    async def test_successful_streaming(self, mock_openai_client):
        """Test successful OpenAI streaming response."""
        with patch("src.service.streaming_service.openai_client", mock_openai_client):
            chunks = []
            async for chunk in stream_openai_response(prompt="Hello"):
                chunks.append(chunk)

            assert chunks == ["Hello", " ", "World", "!"]

    @pytest.mark.asyncio
    async def test_streaming_with_custom_model(self, mock_openai_client):
        """Test streaming with custom model parameter."""
        with patch("src.service.streaming_service.openai_client", mock_openai_client):
            chunks = []
            async for chunk in stream_openai_response(
                prompt="Test",
                model="gpt-4o",
            ):
                chunks.append(chunk)

            # Verify the client was called with correct parameters
            mock_openai_client.chat.completions.create.assert_called_once()
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "gpt-4o"
            assert call_args.kwargs["stream"] is True
            assert call_args.kwargs["temperature"] == 1.0

    @pytest.mark.asyncio
    async def test_streaming_with_default_model(self, mock_openai_client):
        """Test streaming with default model."""
        with patch("src.service.streaming_service.openai_client", mock_openai_client):
            async for _ in stream_openai_response(prompt="Test"):
                pass

            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_empty_chunks_are_skipped(self):
        """Test that empty chunks are skipped."""

        mock_client = Mock()

        class MockDelta:
            def __init__(self, content):
                self.content = content

        class MockChoice:
            def __init__(self, content):
                self.delta = MockDelta(content)

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(content)]

        async def mock_stream_generator():
            yield MockChunk("Hello")
            yield MockChunk(None)  # Empty chunk
            yield MockChunk("")  # Empty string
            yield MockChunk("World")

        async def mock_create(*args, **kwargs):
            return mock_stream_generator()

        mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("src.service.streaming_service.openai_client", mock_client):
            chunks = []
            async for chunk in stream_openai_response(prompt="Test"):
                chunks.append(chunk)

            assert chunks == ["Hello", "World"]

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_openai_client_with_error):
        """Test error handling in streaming."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client_with_error,
        ):
            chunks = []
            async for chunk in stream_openai_response(prompt="Test"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "ERROR" in chunks[0]
            assert "OpenAI API error" in chunks[0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "prompt",
        [
            "Hello, world!",
            "こんにちは",
            "What is AI?" * 100,
            "Single word",
        ],
    )
    async def test_various_prompts(self, mock_openai_client, prompt):
        """Test streaming with various prompt formats."""
        with patch("src.service.streaming_service.openai_client", mock_openai_client):
            chunks = []
            async for chunk in stream_openai_response(prompt=prompt):
                chunks.append(chunk)

            # Verify that chunks were generated
            assert len(chunks) > 0

            # Verify the prompt was passed correctly
            call_args = mock_openai_client.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == prompt

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model",
        [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-5",
        ],
    )
    async def test_various_models(self, mock_openai_client, model):
        """Test streaming with various model names."""
        with patch("src.service.streaming_service.openai_client", mock_openai_client):
            async for _ in stream_openai_response(prompt="Test", model=model):
                pass

            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == model


@pytest.mark.unit
class TestStreamGeminiResponse:
    """Tests for stream_gemini_response function."""

    @pytest.mark.asyncio
    async def test_successful_streaming(self, mock_gemini_client):
        """Test successful Gemini streaming response."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            chunks = []
            async for chunk in stream_gemini_response(prompt="こんにちは"):
                chunks.append(chunk)

            assert chunks == ["こんにちは", "世界"]

    @pytest.mark.asyncio
    async def test_streaming_with_custom_model(self, mock_gemini_client):
        """Test streaming with custom model parameter."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            chunks = []
            async for chunk in stream_gemini_response(
                prompt="Test",
                model="gemini-2.5-pro",
            ):
                chunks.append(chunk)

            # Verify the client was called with correct parameters
            mock_gemini_client.models.generate_content_stream.assert_called_once()
            call_args = mock_gemini_client.models.generate_content_stream.call_args
            assert call_args.kwargs["model"] == "gemini-2.5-pro"
            assert call_args.kwargs["contents"] == "Test"

    @pytest.mark.asyncio
    async def test_streaming_with_default_model(self, mock_gemini_client):
        """Test streaming with default model."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            async for _ in stream_gemini_response(prompt="Test"):
                pass

            call_args = mock_gemini_client.models.generate_content_stream.call_args
            assert call_args.kwargs["model"] == "gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_streaming_with_system_instruction(self, mock_gemini_client):
        """Test streaming with system instruction."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            system_instruction = "You are a helpful assistant"
            async for _ in stream_gemini_response(
                prompt="Test",
                system_instruction=system_instruction,
            ):
                pass

            call_args = mock_gemini_client.models.generate_content_stream.call_args
            config = call_args.kwargs["config"]

            assert isinstance(config, GenerateContentConfig)
            assert config.system_instruction == system_instruction
            assert config.temperature == 2.0

    @pytest.mark.asyncio
    async def test_streaming_without_system_instruction(self, mock_gemini_client):
        """Test streaming without system instruction."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            async for _ in stream_gemini_response(prompt="Test"):
                pass

            call_args = mock_gemini_client.models.generate_content_stream.call_args
            config = call_args.kwargs["config"]

            assert isinstance(config, GenerateContentConfig)
            assert config.temperature == 2.0

    @pytest.mark.asyncio
    async def test_empty_chunks_are_skipped(self):
        """Test that empty chunks are skipped."""
        mock_client = Mock()

        class MockChunk:
            def __init__(self, text):
                self.text = text

        def mock_iter():
            yield MockChunk("Hello")
            yield MockChunk(None)  # Empty chunk
            yield MockChunk("")  # Empty string
            yield MockChunk("World")

        mock_response = Mock()
        mock_response.__iter__ = lambda self: mock_iter()
        mock_client.models.generate_content_stream.return_value = mock_response

        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_client,
        ):
            chunks = []
            async for chunk in stream_gemini_response(prompt="Test"):
                chunks.append(chunk)

            assert chunks == ["Hello", "World"]

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_gemini_client_with_error):
        """Test error handling in streaming."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client_with_error,
        ):
            chunks = []
            async for chunk in stream_gemini_response(prompt="Test"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "ERROR" in chunks[0]
            assert "Gemini API error" in chunks[0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "prompt",
        [
            "Hello, world!",
            "こんにちは、世界",
            "What is AI?" * 100,
            "Single word",
        ],
    )
    async def test_various_prompts(self, mock_gemini_client, prompt):
        """Test streaming with various prompt formats."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            chunks = []
            async for chunk in stream_gemini_response(prompt=prompt):
                chunks.append(chunk)

            # Verify that chunks were generated
            assert len(chunks) > 0

            # Verify the prompt was passed correctly
            call_args = mock_gemini_client.models.generate_content_stream.call_args
            assert call_args.kwargs["contents"] == prompt

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "model",
        [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash-lite",
        ],
    )
    async def test_various_models(self, mock_gemini_client, model):
        """Test streaming with various model names."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            async for _ in stream_gemini_response(prompt="Test", model=model):
                pass

            call_args = mock_gemini_client.models.generate_content_stream.call_args
            assert call_args.kwargs["model"] == model

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "system_instruction",
        [
            "You are a helpful assistant",
            "You are a nutritionist",
            "Be concise and direct",
            None,
        ],
    )
    async def test_various_system_instructions(
        self,
        mock_gemini_client,
        system_instruction,
    ):
        """Test streaming with various system instructions."""
        with patch(
            "src.service.streaming_service.google_genai_client",
            mock_gemini_client,
        ):
            async for _ in stream_gemini_response(
                prompt="Test",
                system_instruction=system_instruction,
            ):
                pass

            call_args = mock_gemini_client.models.generate_content_stream.call_args
            config = call_args.kwargs["config"]

            if system_instruction:
                assert config.system_instruction == system_instruction
            else:
                # When None, system_instruction should not be set in config
                # or should be None/empty
                pass

"""Unit tests for streaming service functions."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.service.streaming_service import stream_openai_response


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

            mock_openai_client.chat.completions.create.assert_called_once()
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "gpt-4o"
            assert call_args.kwargs["stream"] is True

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

            assert len(chunks) > 0
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

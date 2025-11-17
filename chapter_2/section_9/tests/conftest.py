"""Pytest configuration and shared fixtures."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """FastAPI TestClient fixture."""
    from src.api.app import app

    return TestClient(app)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()

    # Mock chunk structure
    class MockDelta:
        def __init__(self, content):
            self.content = content

    class MockChoice:
        def __init__(self, content):
            self.delta = MockDelta(content)

    class MockChunk:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    # Create async generator function
    async def mock_stream_generator():
        for content in ["Hello", " ", "World", "!"]:
            yield MockChunk(content)

    # Wrap the create method in AsyncMock to track calls
    async def mock_create(*args, **kwargs):
        return mock_stream_generator()

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)

    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing."""
    mock_client = Mock()

    # Mock chunk structure
    class MockChunk:
        def __init__(self, text):
            self.text = text

    # Set up iteration
    def mock_iter():
        for text in ["こんにちは", "世界"]:
            yield MockChunk(text)

    mock_response = Mock()
    mock_response.__iter__ = lambda self: mock_iter()

    mock_client.models.generate_content_stream.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_openai_client_with_error():
    """Mock OpenAI client that raises an error."""
    mock_client = Mock()

    async def mock_create(*args, **kwargs):
        raise Exception("OpenAI API error")

    mock_client.chat.completions.create = mock_create

    return mock_client


@pytest.fixture
def mock_gemini_client_with_error():
    """Mock Gemini client that raises an error."""
    mock_client = Mock()

    def mock_generate(*args, **kwargs):
        raise Exception("Gemini API error")

    mock_client.models.generate_content_stream = mock_generate

    return mock_client


@pytest.fixture
def sample_stream_request():
    """Sample streaming request data."""
    return {
        "prompt": "Hello, world!",
        "provider": "gemini",
        "model": None,
        "system_instruction": None,
    }


@pytest.fixture
def sample_openai_request():
    """Sample OpenAI request data."""
    return {
        "prompt": "What is AI?",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "system_instruction": None,
    }


@pytest.fixture
def sample_gemini_request():
    """Sample Gemini request data."""
    return {
        "prompt": "こんにちは",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "system_instruction": "You are a helpful assistant",
    }

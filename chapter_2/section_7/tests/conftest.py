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
        for content in ["Hello", " ", "World", "!"]:
            yield MockChunk(content)

    async def mock_create(*args, **kwargs):
        return mock_stream_generator()

    mock_client.chat.completions.create = AsyncMock(side_effect=mock_create)

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
def sample_stream_request():
    """Sample streaming request data."""
    return {
        "prompt": "Hello, world!",
        "provider": "openai",
        "model": None,
    }


@pytest.fixture
def sample_openai_request():
    """Sample OpenAI request data."""
    return {
        "prompt": "What is AI?",
        "provider": "openai",
        "model": "gpt-4o-mini",
    }

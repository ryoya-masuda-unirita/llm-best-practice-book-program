"""Pytest configuration and shared fixtures for LLMOps tests."""

import logging
import shutil
import tempfile

import pytest

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for prompt storage tests."""
    temp_path = tempfile.mkdtemp(prefix="prompt_storage_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for generated files."""
    temp_path = tempfile.mkdtemp(prefix="output_")
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_logger():
    """Create a real logger instance for testing (not a mock)."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


@pytest.fixture
def sample_prompt_content():
    """Sample prompt content for testing."""
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "Tell me a story about a robot.",
        },
    ]


@pytest.fixture
def sample_response_content():
    """Sample response content for testing."""
    return {
        "text": "Once upon a time, there was a robot named Rob...",
        "finish_reason": "stop",
        "tokens": 150,
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "provider": "openai",
        "model_version": "gpt-5.4-mini",
        "response_format": "json",
    }


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio coroutine")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        if "asyncio" in item.keywords:
            item.add_marker(pytest.mark.asyncio)

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from src.client.wrapper_client import (
    AsyncChatCompletionsWrapper,
    AsyncModelsWrapper,
    AsyncResponsesWrapper,
    ChatCompletionsWrapper,
    ModelsWrapper,
    ResponsesWrapper,
)


@pytest.fixture
def log_dir(tmp_path):
    """Create a temporary log directory."""
    return str(tmp_path / "test_logs")


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI response."""
    response = Mock()
    response.id = "chatcmpl-123"
    response.model = "gpt-4"
    response.choices = [
        Mock(
            message=Mock(role="assistant", content="Hello! How can I help you?"),
            finish_reason="stop",
            index=0,
        )
    ]
    response.usage = Mock(
        prompt_tokens=10,
        completion_tokens=8,
        total_tokens=18,
    )
    return response


@pytest.fixture
def mock_genai_response():
    """Create a mock genai response."""
    response = Mock()
    response.text = "Hello! How can I help you?"

    candidate = Mock()
    candidate.content = Mock()
    candidate.content.parts = [Mock(text="Hello! How can I help you?")]
    candidate.content.role = "model"
    candidate.finish_reason = "STOP"
    candidate.safety_ratings = []

    response.candidates = [candidate]
    response.usage_metadata = Mock(
        prompt_token_count=10,
        candidates_token_count=8,
        total_token_count=18,
    )
    return response


@pytest.fixture
def mock_openai_responses_response():
    """Create a mock OpenAI responses API response."""
    response = Mock()
    response.id = "resp-123"
    response.model = "gpt-4o"
    response.output_text = "Here is the response to your input."
    response.usage = Mock(
        prompt_tokens=15,
        completion_tokens=10,
        total_tokens=25,
    )
    return response


def test_chat_completions_wrapper_create(log_dir, mock_openai_response):
    """Test ChatCompletionsWrapper with create method."""
    # Create mock completions object
    mock_completions = Mock()
    mock_completions.create.return_value = mock_openai_response

    # Create wrapper
    wrapper = ChatCompletionsWrapper(mock_completions, log_dir)

    # Make request
    response = wrapper.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    # Verify response
    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-4"
    assert response.usage.total_tokens == 18

    # Verify log file was created
    log_files = list(Path(log_dir).glob("openai_*.json"))
    assert len(log_files) == 1

    # Verify log content
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "chat.completions.create"
    assert log_data["request"]["model"] == "gpt-4"
    assert log_data["request"]["messages"] == [{"role": "user", "content": "Hello"}]
    assert log_data["request"]["temperature"] == 0.7
    assert log_data["response"]["id"] == "chatcmpl-123"
    assert log_data["response"]["usage"]["total_tokens"] == 18


@pytest.mark.asyncio
async def test_async_chat_completions_wrapper_create(log_dir, mock_openai_response):
    """Test AsyncChatCompletionsWrapper with create method."""
    # Create mock completions object
    mock_completions = Mock()
    mock_completions.create = AsyncMock(return_value=mock_openai_response)

    # Create wrapper
    wrapper = AsyncChatCompletionsWrapper(mock_completions, log_dir)

    # Make request
    response = await wrapper.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    # Verify response
    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-4"
    assert response.usage.total_tokens == 18

    # Verify log file was created
    log_files = list(Path(log_dir).glob("async_openai_*.json"))
    assert len(log_files) == 1

    # Verify log content
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "chat.completions.create"
    assert log_data["request"]["model"] == "gpt-4"
    assert log_data["response"]["usage"]["total_tokens"] == 18


def test_models_wrapper_generate_content(log_dir, mock_genai_response):
    """Test ModelsWrapper with generate_content method."""
    # Create mock models object
    mock_models = Mock()
    mock_models.generate_content.return_value = mock_genai_response

    # Create wrapper
    wrapper = ModelsWrapper(mock_models, log_dir)

    # Make request
    response = wrapper.generate_content(
        model="gemini-2.5-pro",
        contents="Hello",
    )

    # Verify response
    assert response.text == "Hello! How can I help you?"
    assert response.usage_metadata.total_token_count == 18

    # Verify log file was created
    log_files = list(Path(log_dir).glob("genai_*.json"))
    assert len(log_files) == 1

    # Verify log content
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "models.generate_content"
    assert log_data["request"]["model"] == "gemini-2.5-pro"
    assert log_data["request"]["contents"] == "Hello"
    assert log_data["response"]["text"] == "Hello! How can I help you?"
    assert log_data["response"]["usage_metadata"]["total_token_count"] == 18


def test_log_directory_creation(tmp_path):
    """Test that log directory is created automatically."""
    log_dir = str(tmp_path / "auto_created_logs")

    # Create mock completions object
    mock_completions = Mock()

    # Create wrapper - this should create the directory
    ChatCompletionsWrapper(mock_completions, log_dir)

    # Verify directory exists
    assert Path(log_dir).exists()


def test_wrapper_delegates_attributes():
    """Test that wrapper delegates unknown attributes to wrapped object."""
    # Create mock with a custom attribute
    mock_completions = Mock()
    mock_completions.custom_method = Mock(return_value="custom_result")

    # Create wrapper
    wrapper = ChatCompletionsWrapper(mock_completions, "usage_logs")

    # Access custom attribute through wrapper
    result = wrapper.custom_method()
    assert result == "custom_result"


def test_multiple_requests_create_separate_logs(log_dir, mock_openai_response):
    """Test that multiple requests create separate log files."""
    # Create mock completions object
    mock_completions = Mock()
    mock_completions.create.return_value = mock_openai_response

    # Create wrapper
    wrapper = ChatCompletionsWrapper(mock_completions, log_dir)

    # Make multiple requests
    for i in range(3):
        wrapper.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Hello {i}"}],
        )

    # Verify multiple log files were created
    log_files = list(Path(log_dir).glob("openai_*.json"))
    assert len(log_files) == 3


def test_log_captures_all_parameters(log_dir, mock_openai_response):
    """Test that log captures various request parameters."""
    # Create mock completions object
    mock_completions = Mock()
    mock_completions.create.return_value = mock_openai_response

    # Create wrapper
    wrapper = ChatCompletionsWrapper(mock_completions, log_dir)

    # Make request with many parameters
    wrapper.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.8,
        max_tokens=100,
        top_p=0.9,
        stream=False,
        frequency_penalty=0.5,
        presence_penalty=0.3,
    )

    # Verify log content
    log_files = list(Path(log_dir).glob("openai_*.json"))
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["request"]["temperature"] == 0.8
    assert log_data["request"]["max_tokens"] == 100
    assert log_data["request"]["top_p"] == 0.9
    assert log_data["request"]["stream"] is False
    assert log_data["request"]["parameters"]["frequency_penalty"] == 0.5
    assert log_data["request"]["parameters"]["presence_penalty"] == 0.3


def test_responses_wrapper_create(log_dir, mock_openai_responses_response):
    """Test ResponsesWrapper with create method."""
    # Create mock responses object
    mock_responses = Mock()
    mock_responses.create.return_value = mock_openai_responses_response

    # Create wrapper
    wrapper = ResponsesWrapper(mock_responses, log_dir)

    # Make request
    response = wrapper.create(
        model="gpt-4o",
        input="Write a story",
        tools=[{"type": "web_search_preview"}],
    )

    # Verify response
    assert response.id == "resp-123"
    assert response.model == "gpt-4o"
    assert response.output_text == "Here is the response to your input."
    assert response.usage.total_tokens == 25

    # Verify log file was created
    log_files = list(Path(log_dir).glob("openai_responses_*.json"))
    assert len(log_files) == 1

    # Verify log content
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "responses.create"
    assert log_data["request"]["model"] == "gpt-4o"
    assert log_data["request"]["input"] == "Write a story"
    assert log_data["request"]["tools"] == [{"type": "web_search_preview"}]
    assert log_data["response"]["id"] == "resp-123"
    assert log_data["response"]["output_text"] == "Here is the response to your input."
    assert log_data["response"]["usage"]["total_tokens"] == 25


@pytest.mark.asyncio
async def test_async_responses_wrapper_create(log_dir, mock_openai_responses_response):
    """Test AsyncResponsesWrapper with create method."""
    # Create mock responses object
    mock_responses = Mock()
    mock_responses.create = AsyncMock(return_value=mock_openai_responses_response)

    # Create wrapper
    wrapper = AsyncResponsesWrapper(mock_responses, log_dir)

    # Make request
    response = await wrapper.create(
        model="gpt-4o",
        input="Write a story",
        tools=[{"type": "web_search_preview"}],
    )

    # Verify response
    assert response.id == "resp-123"
    assert response.model == "gpt-4o"
    assert response.output_text == "Here is the response to your input."
    assert response.usage.total_tokens == 25

    # Verify log file was created
    log_files = list(Path(log_dir).glob("async_openai_responses_*.json"))
    assert len(log_files) == 1

    # Verify log content
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "responses.create"
    assert log_data["request"]["model"] == "gpt-4o"
    assert log_data["response"]["usage"]["total_tokens"] == 25


@pytest.mark.asyncio
async def test_async_models_wrapper_generate_content(log_dir, mock_genai_response):
    """Test AsyncModelsWrapper with generate_content method."""
    # Create mock models object
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=mock_genai_response)

    # Create wrapper
    wrapper = AsyncModelsWrapper(mock_models, log_dir)

    # Make request
    response = await wrapper.generate_content(
        model="gemini-2.5-pro",
        contents="Hello async",
    )

    # Verify response
    assert response.text == "Hello! How can I help you?"
    assert response.usage_metadata.total_token_count == 18

    # Verify log file was created
    log_files = list(Path(log_dir).glob("async_genai_*.json"))
    assert len(log_files) == 1

    # Verify log content
    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "aio.models.generate_content"
    assert log_data["request"]["model"] == "gemini-2.5-pro"
    assert log_data["request"]["contents"] == "Hello async"
    assert log_data["response"]["text"] == "Hello! How can I help you?"
    assert log_data["response"]["usage_metadata"]["total_token_count"] == 18

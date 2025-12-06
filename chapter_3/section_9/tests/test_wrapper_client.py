import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from src.client.gemini_wrapper_client import AsyncModelsWrapper, ModelsWrapper
from src.client.openai_wrapper_client import (
    AsyncChatCompletionsWrapper,
    AsyncResponsesWrapper,
    ChatCompletionsWrapper,
    ResponsesWrapper,
)


@pytest.fixture
def log_dir(tmp_path):
    return str(tmp_path / "test_logs")


@pytest.fixture
def mock_openai_response():
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
    mock_completions = Mock()
    mock_completions.create.return_value = mock_openai_response

    wrapper = ChatCompletionsWrapper(mock_completions, log_dir)
    response = wrapper.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-4"
    assert response.usage.total_tokens == 18

    log_files = list(Path(log_dir).glob("openai_*.json"))
    assert len(log_files) == 1

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
    mock_completions = Mock()
    mock_completions.create = AsyncMock(return_value=mock_openai_response)

    wrapper = AsyncChatCompletionsWrapper(mock_completions, log_dir)
    response = await wrapper.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-4"
    assert response.usage.total_tokens == 18

    log_files = list(Path(log_dir).glob("async_openai_*.json"))
    assert len(log_files) == 1

    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "chat.completions.create"
    assert log_data["request"]["model"] == "gpt-4"
    assert log_data["response"]["usage"]["total_tokens"] == 18


def test_models_wrapper_generate_content(log_dir, mock_genai_response):
    mock_models = Mock()
    mock_models.generate_content.return_value = mock_genai_response

    wrapper = ModelsWrapper(mock_models, log_dir)
    response = wrapper.generate_content(
        model="gemini-2.5-pro",
        contents="Hello",
    )

    assert response.text == "Hello! How can I help you?"
    assert response.usage_metadata.total_token_count == 18

    log_files = list(Path(log_dir).glob("genai_*.json"))
    assert len(log_files) == 1

    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "models.generate_content"
    assert log_data["request"]["model"] == "gemini-2.5-pro"
    assert log_data["request"]["contents"] == "Hello"
    assert log_data["response"]["text"] == "Hello! How can I help you?"
    assert log_data["response"]["usage_metadata"]["total_token_count"] == 18


def test_log_directory_creation(tmp_path):
    log_dir = str(tmp_path / "auto_created_logs")
    mock_completions = Mock()
    ChatCompletionsWrapper(mock_completions, log_dir)
    assert Path(log_dir).exists()


def test_wrapper_delegates_attributes():
    mock_completions = Mock()
    mock_completions.custom_method = Mock(return_value="custom_result")

    wrapper = ChatCompletionsWrapper(mock_completions, "usage_logs")
    result = wrapper.custom_method()
    assert result == "custom_result"


def test_multiple_requests_create_separate_logs(log_dir, mock_openai_response):
    mock_completions = Mock()
    mock_completions.create.return_value = mock_openai_response

    wrapper = ChatCompletionsWrapper(mock_completions, log_dir)
    for i in range(3):
        wrapper.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Hello {i}"}],
        )

    log_files = list(Path(log_dir).glob("openai_*.json"))
    assert len(log_files) == 3


def test_log_captures_all_parameters(log_dir, mock_openai_response):
    mock_completions = Mock()
    mock_completions.create.return_value = mock_openai_response

    wrapper = ChatCompletionsWrapper(mock_completions, log_dir)
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
    mock_responses = Mock()
    mock_responses.create.return_value = mock_openai_responses_response

    wrapper = ResponsesWrapper(mock_responses, log_dir)
    response = wrapper.create(
        model="gpt-4o",
        input="Write a story",
        tools=[{"type": "web_search_preview"}],
    )

    assert response.id == "resp-123"
    assert response.model == "gpt-4o"
    assert response.output_text == "Here is the response to your input."
    assert response.usage.total_tokens == 25

    log_files = list(Path(log_dir).glob("openai_responses_*.json"))
    assert len(log_files) == 1

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
    mock_responses = Mock()
    mock_responses.create = AsyncMock(return_value=mock_openai_responses_response)

    wrapper = AsyncResponsesWrapper(mock_responses, log_dir)
    response = await wrapper.create(
        model="gpt-4o",
        input="Write a story",
        tools=[{"type": "web_search_preview"}],
    )

    assert response.id == "resp-123"
    assert response.model == "gpt-4o"
    assert response.output_text == "Here is the response to your input."
    assert response.usage.total_tokens == 25

    log_files = list(Path(log_dir).glob("async_openai_responses_*.json"))
    assert len(log_files) == 1

    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "responses.create"
    assert log_data["request"]["model"] == "gpt-4o"
    assert log_data["response"]["usage"]["total_tokens"] == 25


@pytest.mark.asyncio
async def test_async_models_wrapper_generate_content(log_dir, mock_genai_response):
    mock_models = Mock()
    mock_models.generate_content = AsyncMock(return_value=mock_genai_response)

    wrapper = AsyncModelsWrapper(mock_models, log_dir)
    response = await wrapper.generate_content(
        model="gemini-2.5-pro",
        contents="Hello async",
    )

    assert response.text == "Hello! How can I help you?"
    assert response.usage_metadata.total_token_count == 18

    log_files = list(Path(log_dir).glob("async_genai_*.json"))
    assert len(log_files) == 1

    with open(log_files[0]) as f:
        log_data = json.load(f)

    assert log_data["method"] == "aio.models.generate_content"
    assert log_data["request"]["model"] == "gemini-2.5-pro"
    assert log_data["request"]["contents"] == "Hello async"
    assert log_data["response"]["text"] == "Hello! How can I help you?"
    assert log_data["response"]["usage_metadata"]["total_token_count"] == 18

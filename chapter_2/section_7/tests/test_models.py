"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError
from src.client.llm_client import LLMProvider, OpenAIModel
from src.model.model import HealthResponse, StreamRequest


@pytest.mark.unit
class TestStreamRequest:
    """Tests for StreamRequest model."""

    def test_valid_request_with_defaults(self):
        """Test creating a valid request with default values."""
        request = StreamRequest(prompt="Hello")

        assert request.prompt == "Hello"
        assert request.provider == LLMProvider.OPENAI
        assert request.model is None

    def test_valid_openai_provider(self):
        """Test OpenAI provider."""
        request = StreamRequest(prompt="Test", provider="openai")
        assert request.provider == LLMProvider.OPENAI

        request = StreamRequest(prompt="Test", provider=LLMProvider.OPENAI)
        assert request.provider == LLMProvider.OPENAI

    @pytest.mark.parametrize(
        "model",
        [
            "gpt-4o-mini",
            "gpt-4o",
            OpenAIModel.GPT_4O_MINI,
            OpenAIModel.GPT_4O,
        ],
    )
    def test_valid_openai_models(self, model):
        """Test various valid OpenAI model formats."""
        request = StreamRequest(
            prompt="Test",
            provider=LLMProvider.OPENAI,
            model=model,
        )
        assert request.model is not None

    def test_empty_prompt_raises_error(self):
        """Test that empty prompt raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamRequest(prompt="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "string_too_short"
        assert "prompt" in errors[0]["loc"]

    def test_missing_prompt_raises_error(self):
        """Test that missing prompt raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamRequest()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "prompt" in errors[0]["loc"]

    def test_invalid_provider_raises_error(self):
        """Test that invalid provider raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StreamRequest(prompt="Test", provider="invalid")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "provider" in errors[0]["loc"]

    @pytest.mark.parametrize(
        "prompt",
        [
            "Hello, world!",
            "こんにちは、世界！",
            "What is AI?" * 100,  # Long prompt
            "1",  # Single character
            " " * 10 + "test",  # Leading whitespace
        ],
    )
    def test_various_valid_prompts(self, prompt):
        """Test various valid prompt formats."""
        request = StreamRequest(prompt=prompt)
        assert request.prompt == prompt

    def test_extra_fields_are_ignored(self):
        """Test that extra fields are ignored due to extra='ignore'."""
        request = StreamRequest(
            prompt="Test",
            unknown_field="should be ignored",
        )

        assert request.prompt == "Test"
        assert not hasattr(request, "unknown_field")

    def test_model_dict_output(self):
        """Test model_dump output format."""
        request = StreamRequest(
            prompt="Hello",
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
        )

        data = request.model_dump()

        assert data["prompt"] == "Hello"
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o"

    def test_model_json_output(self):
        """Test model_dump_json output."""
        request = StreamRequest(prompt="Test")
        json_str = request.model_dump_json()

        assert isinstance(json_str, str)
        assert "Test" in json_str
        assert "openai" in json_str


@pytest.mark.unit
class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_valid_health_response(self):
        """Test creating a valid health response."""
        response = HealthResponse(
            status="healthy",
            message="API is running",
        )

        assert response.status == "healthy"
        assert response.message == "API is running"

    def test_missing_status_raises_error(self):
        """Test that missing status raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            HealthResponse(message="Test")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "status" in errors[0]["loc"]

    def test_missing_message_raises_error(self):
        """Test that missing message raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            HealthResponse(status="healthy")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "message" in errors[0]["loc"]

    @pytest.mark.parametrize(
        "status,message",
        [
            ("healthy", "All systems operational"),
            ("degraded", "Some services unavailable"),
            ("unhealthy", "Critical error"),
            ("", "Empty status is allowed"),
        ],
    )
    def test_various_status_values(self, status, message):
        """Test various status and message combinations."""
        response = HealthResponse(status=status, message=message)

        assert response.status == status
        assert response.message == message

    def test_model_dict_output(self):
        """Test model_dump output format."""
        response = HealthResponse(
            status="healthy",
            message="API is running",
        )

        data = response.model_dump()

        assert data == {
            "status": "healthy",
            "message": "API is running",
        }

    def test_model_json_output(self):
        """Test model_dump_json output."""
        response = HealthResponse(
            status="healthy",
            message="API is running",
        )
        json_str = response.model_dump_json()

        assert isinstance(json_str, str)
        assert "healthy" in json_str
        assert "API is running" in json_str

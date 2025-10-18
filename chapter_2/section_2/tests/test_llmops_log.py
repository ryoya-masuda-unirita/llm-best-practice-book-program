"""Tests for LLMOps structured log models."""

import json
import tempfile
from datetime import datetime

import pytest
from src.model.llmops_log import LLMOpsLogEntry, LogLevel


class TestLogLevel:
    """Tests for LogLevel enum."""

    @pytest.mark.parametrize(
        "level,expected_value",
        [
            (LogLevel.INFO, "INFO"),
            (LogLevel.DEBUG, "DEBUG"),
            (LogLevel.ERROR, "ERROR"),
            (LogLevel.WARNING, "WARNING"),
        ],
    )
    def test_log_level_values(self, level, expected_value):
        """Test LogLevel enum values."""
        assert level == expected_value
        assert isinstance(level, str)


class TestLLMOpsLogEntry:
    """Tests for LLMOpsLogEntry model."""

    @pytest.mark.parametrize(
        "request_id,prompt_id,model,temperature",
        [
            ("req-001", "prompt-001", "gpt-4o-mini", 0.7),
            ("req-002", "prompt-002", "gemini-2.5-flash", 1.0),
            ("req-003", "prompt-003", "claude-3-sonnet", 0.5),
            ("req-004", "prompt-004", "gpt-4", 2.0),
        ],
    )
    def test_create_log_entry_with_required_fields(self, request_id, prompt_id, model, temperature):
        """Test creating log entry with required fields."""
        log_entry = LLMOpsLogEntry(
            request_id=request_id,
            prompt_id=prompt_id,
            model=model,
            temperature=temperature,
        )

        assert log_entry.request_id == request_id
        assert log_entry.prompt_id == prompt_id
        assert log_entry.model == model
        assert log_entry.temperature == temperature
        assert log_entry.level == LogLevel.INFO  # Default level
        assert log_entry.user_id is None
        assert log_entry.latency_ms is None
        assert log_entry.status_code is None
        assert log_entry.error_message is None
        assert log_entry.metadata == {}

    @pytest.mark.parametrize(
        "user_id,latency_ms,status_code",
        [
            ("user-001", 123.45, 200),
            ("user-002", 456.78, 200),
            ("user-003", 999.99, 500),
            (None, 100.0, 429),
        ],
    )
    def test_create_log_entry_with_optional_fields(self, user_id, latency_ms, status_code):
        """Test creating log entry with optional fields."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
            user_id=user_id,
            latency_ms=latency_ms,
            status_code=status_code,
            error_message="Test error" if status_code >= 400 else None,
            level=LogLevel.ERROR if status_code >= 400 else LogLevel.INFO,
            metadata={"test_key": "test_value"},
        )

        assert log_entry.user_id == user_id
        assert log_entry.latency_ms == latency_ms
        assert log_entry.status_code == status_code

    def test_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
        )

        assert log_entry.timestamp is not None
        # Verify timestamp is valid ISO 8601 format
        parsed_time = datetime.fromisoformat(log_entry.timestamp)
        assert isinstance(parsed_time, datetime)

    @pytest.mark.parametrize(
        "temperature,should_fail",
        [
            (0.0, False),
            (0.5, False),
            (1.0, False),
            (2.0, False),
            (-0.1, True),  # Below minimum
            (2.1, True),  # Above maximum
            (3.0, True),  # Way above maximum
        ],
    )
    def test_temperature_validation(self, temperature, should_fail):
        """Test temperature parameter validation."""
        if should_fail:
            with pytest.raises(Exception):  # Pydantic validation error
                LLMOpsLogEntry(
                    request_id="req-001",
                    prompt_id="prompt-001",
                    model="gpt-4o-mini",
                    temperature=temperature,
                )
        else:
            log_entry = LLMOpsLogEntry(
                request_id="req-001",
                prompt_id="prompt-001",
                model="gpt-4o-mini",
                temperature=temperature,
            )
            assert log_entry.temperature == temperature

    @pytest.mark.parametrize(
        "latency_ms,should_fail",
        [
            (0.0, False),
            (100.0, False),
            (1000.5, False),
            (-0.1, True),  # Negative latency
            (-100.0, True),
        ],
    )
    def test_latency_validation(self, latency_ms, should_fail):
        """Test latency_ms parameter validation."""
        if should_fail:
            with pytest.raises(Exception):  # Pydantic validation error
                LLMOpsLogEntry(
                    request_id="req-001",
                    prompt_id="prompt-001",
                    model="gpt-4o-mini",
                    temperature=0.7,
                    latency_ms=latency_ms,
                )
        else:
            log_entry = LLMOpsLogEntry(
                request_id="req-001",
                prompt_id="prompt-001",
                model="gpt-4o-mini",
                temperature=0.7,
                latency_ms=latency_ms,
            )
            assert log_entry.latency_ms == latency_ms

    def test_to_json_string(self):
        """Test converting log entry to JSON string."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
            user_id="user-001",
            latency_ms=123.45,
            status_code=200,
            metadata={"provider": "openai"},
        )

        json_str = log_entry.to_json_string()
        assert isinstance(json_str, str)

        # Parse back to verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["request_id"] == "req-001"
        assert parsed["prompt_id"] == "prompt-001"
        assert parsed["model"] == "gpt-4o-mini"
        assert parsed["temperature"] == 0.7
        assert parsed["user_id"] == "user-001"
        assert parsed["latency_ms"] == 123.45
        assert parsed["status_code"] == 200
        assert parsed["metadata"]["provider"] == "openai"

    def test_to_json_string_excludes_none_values(self):
        """Test that None values are excluded from JSON output."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
        )

        json_str = log_entry.to_json_string()
        parsed = json.loads(json_str)

        # These fields should not be present when None
        assert "user_id" not in parsed
        assert "latency_ms" not in parsed
        assert "status_code" not in parsed
        assert "error_message" not in parsed

    def test_save_to_file(self):
        """Test saving log entry to a file."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
            user_id="user-001",
            latency_ms=123.45,
            status_code=200,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            file_path = f.name

        log_entry.save_to_file(file_path)

        # Read back and verify
        with open(file_path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert loaded_data["request_id"] == "req-001"
        assert loaded_data["prompt_id"] == "prompt-001"
        assert loaded_data["model"] == "gpt-4o-mini"

    @pytest.mark.parametrize(
        "metadata",
        [
            {"key1": "value1"},
            {"provider": "openai", "response_format": "json"},
            {"nested": {"key": "value"}},
            {},
        ],
    )
    def test_metadata_field(self, metadata):
        """Test metadata field with various structures."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
            metadata=metadata,
        )

        assert log_entry.metadata == metadata

    @pytest.mark.parametrize(
        "level",
        [
            LogLevel.INFO,
            LogLevel.DEBUG,
            LogLevel.ERROR,
            LogLevel.WARNING,
        ],
    )
    def test_log_levels(self, level):
        """Test different log levels."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
            level=level,
        )

        assert log_entry.level == level

    def test_json_serialization_with_special_characters(self):
        """Test JSON serialization with special characters (ensure_ascii=False)."""
        log_entry = LLMOpsLogEntry(
            request_id="req-001",
            prompt_id="prompt-001",
            model="gpt-4o-mini",
            temperature=0.7,
            metadata={"message": "日本語テスト", "emoji": "🤖"},
        )

        json_str = log_entry.to_json_string()
        parsed = json.loads(json_str)

        assert parsed["metadata"]["message"] == "日本語テスト"
        assert parsed["metadata"]["emoji"] == "🤖"

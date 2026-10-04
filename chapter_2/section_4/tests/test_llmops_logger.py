"""Tests for LLMOps structured logger."""

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.model.llmops_log import LogLevel
from src.model.prompt_data import PromptData
from src.service.llmops_logger import LLMOpsLogger, create_llmops_logger
from src.service.prompt_storage import LocalFilePromptStorage


@pytest.mark.asyncio
class TestLLMOpsLogger:
    """Tests for LLMOpsLogger class."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        logger = MagicMock(spec=logging.Logger)
        return logger

    @pytest.fixture
    def storage(self, temp_storage_dir):
        """Create storage instance."""
        return LocalFilePromptStorage(base_dir=temp_storage_dir)

    @pytest.fixture
    def llmops_logger(self, mock_logger, storage):
        """Create LLMOpsLogger instance for testing."""
        return LLMOpsLogger(logger=mock_logger, prompt_storage=storage, enable_masking=False)

    async def test_logger_initialization(self, mock_logger, storage):
        """Test LLMOpsLogger initialization."""
        logger = LLMOpsLogger(logger=mock_logger, prompt_storage=storage, enable_masking=True)

        assert logger.logger == mock_logger
        assert logger.prompt_storage == storage
        assert logger.enable_masking is True

    async def test_logger_initialization_with_defaults(self, mock_logger):
        """Test initialization with default storage."""
        temp_dir = tempfile.mkdtemp(prefix="test_init_defaults_")
        try:
            temp_storage = LocalFilePromptStorage(base_dir=temp_dir)
            logger = LLMOpsLogger(logger=mock_logger, prompt_storage=temp_storage)

            assert logger.logger == mock_logger
            assert logger.prompt_storage is not None
            assert logger.enable_masking is True
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "request_id,prompt_id,model,temperature",
        [
            ("req-001", "p-001", "openai.gpt-5.4", 0.7),
            ("req-002", "p-002", "gemini-2.5-flash", 1.0),
            ("req-003", "p-003", "global.anthropic.claude-sonnet-4-6", 0.5),
        ],
    )
    async def test_log_llm_request_basic(self, llmops_logger, mock_logger, request_id, prompt_id, model, temperature):
        """Test basic LLM request logging."""
        prompt_content = "Test prompt"

        await llmops_logger.log_llm_request(
            request_id=request_id,
            prompt_id=prompt_id,
            model=model,
            temperature=temperature,
            prompt_content=prompt_content,
        )

        await asyncio.sleep(0.1)

        assert mock_logger.info.called

        json_calls = [call for call in mock_logger.info.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON log call"

        log_call_args = json_calls[-1][0][0]
        log_data = json.loads(log_call_args)

        assert log_data["request_id"] == request_id
        assert log_data["prompt_id"] == prompt_id
        assert log_data["model"] == model
        assert log_data["temperature"] == temperature

    @pytest.mark.parametrize(
        "level,expected_method",
        [
            (LogLevel.INFO, "info"),
            (LogLevel.DEBUG, "debug"),
            (LogLevel.ERROR, "error"),
            (LogLevel.WARNING, "warning"),
        ],
    )
    async def test_log_llm_request_different_levels(self, llmops_logger, mock_logger, level, expected_method):
        """Test logging at different levels."""
        await llmops_logger.log_llm_request(
            request_id="req-001",
            prompt_id="p-001",
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test",
            level=level,
        )

        await asyncio.sleep(0.1)

        log_method = getattr(mock_logger, expected_method)
        assert log_method.called, f"Expected {expected_method} to be called"

        json_calls = [call for call in log_method.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, f"Expected at least one JSON log call to {expected_method}"

    async def test_log_llm_request_with_all_fields(self, llmops_logger, mock_logger):
        """Test logging with all optional fields populated."""
        await llmops_logger.log_llm_request(
            request_id="req-001",
            prompt_id="p-001",
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test prompt",
            response_content="test response",
            user_id="user-001",
            latency_ms=123.45,
            status_code=200,
            error_message=None,
            level=LogLevel.INFO,
            metadata={"provider": "openai"},
        )

        log_call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)

        assert log_data["user_id"] == "user-001"
        assert log_data["latency_ms"] == 123.45
        assert log_data["status_code"] == 200
        assert log_data["metadata"]["provider"] == "openai"

    async def test_log_llm_request_stores_prompt_async(self, llmops_logger, storage):
        """Test that prompt content is stored asynchronously."""
        prompt_id = "test-prompt-001"

        await llmops_logger.log_llm_request(
            request_id="req-001",
            prompt_id=prompt_id,
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test prompt content",
            response_content="test response content",
        )

        await asyncio.sleep(0.1)

        retrieved = await storage.retrieve_prompt(prompt_id)
        assert retrieved is not None
        assert retrieved.prompt_id == prompt_id
        assert retrieved.prompt_content == "test prompt content"
        assert retrieved.response_content == "test response content"

    async def test_log_llm_request_error_handling(self, mock_logger):
        """Test error handling when prompt storage fails."""
        bad_storage = AsyncMock(spec=LocalFilePromptStorage)
        bad_storage.save_prompt = AsyncMock(side_effect=Exception("Storage failed"))

        logger = LLMOpsLogger(logger=mock_logger, prompt_storage=bad_storage, enable_masking=False)

        await logger.log_llm_request(
            request_id="req-001",
            prompt_id="p-001",
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test",
        )

        await asyncio.sleep(0.1)

        assert mock_logger.error.called

    async def test_track_llm_request_context_manager_success(self, llmops_logger, mock_logger):
        """Test track_llm_request context manager with successful request."""
        async with llmops_logger.track_llm_request(
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test prompt",
            user_id="user-001",
        ) as tracking:
            tracking["response"] = "test response"

        await asyncio.sleep(0.1)

        assert mock_logger.info.called

        json_calls = [call for call in mock_logger.info.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON log call"

        log_call_args = json_calls[-1][0][0]
        log_data = json.loads(log_call_args)

        assert log_data["model"] == "openai.gpt-5.4"
        assert log_data["temperature"] == 0.7
        assert log_data["user_id"] == "user-001"
        assert log_data["status_code"] == 200
        assert log_data["latency_ms"] is not None
        assert log_data["latency_ms"] > 0

    async def test_track_llm_request_auto_generates_ids(self, llmops_logger, mock_logger):
        """Test that request_id and prompt_id are auto-generated."""
        async with llmops_logger.track_llm_request(
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test",
        ) as tracking:
            request_id = tracking["request_id"]
            prompt_id = tracking["prompt_id"]

        assert request_id is not None
        assert prompt_id is not None
        assert isinstance(request_id, str)
        assert isinstance(prompt_id, str)

    async def test_track_llm_request_with_custom_ids(self, llmops_logger, mock_logger):
        """Test providing custom request_id and prompt_id."""
        custom_request_id = "custom-req-123"
        custom_prompt_id = "custom-prompt-456"

        async with llmops_logger.track_llm_request(
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test",
            request_id=custom_request_id,
            prompt_id=custom_prompt_id,
        ) as tracking:
            assert tracking["request_id"] == custom_request_id
            assert tracking["prompt_id"] == custom_prompt_id

    async def test_track_llm_request_measures_latency(self, llmops_logger, mock_logger):
        """Test that latency is automatically measured."""
        async with llmops_logger.track_llm_request(
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test",
        ):
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.1)

        log_call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)

        assert "latency_ms" in log_data
        assert log_data["latency_ms"] >= 50  # At least 50ms

    async def test_track_llm_request_error_handling(self, llmops_logger, mock_logger):
        """Test context manager error handling."""
        with pytest.raises(ValueError):
            async with llmops_logger.track_llm_request(
                model="openai.gpt-5.4",
                temperature=0.7,
                prompt_content="test",
            ) as _:
                raise ValueError("Simulated error")

        await asyncio.sleep(0.1)

        assert mock_logger.error.called

        json_calls = [call for call in mock_logger.error.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON error log call"

        log_call_args = json_calls[-1][0][0]
        log_data = json.loads(log_call_args)

        assert log_data["status_code"] == 500
        assert log_data["error_message"] == "Simulated error"
        assert log_data["level"] == "ERROR"

    @pytest.mark.parametrize(
        "exception_type,error_message",
        [
            (ValueError, "Value error occurred"),
            (RuntimeError, "Runtime error occurred"),
            (TypeError, "Type error occurred"),
        ],
    )
    async def test_track_llm_request_different_exceptions(
        self, llmops_logger, mock_logger, exception_type, error_message
    ):
        """Test handling different exception types."""
        with pytest.raises(exception_type):
            async with llmops_logger.track_llm_request(
                model="openai.gpt-5.4",
                temperature=0.7,
                prompt_content="test",
            ):
                raise exception_type(error_message)

        await asyncio.sleep(0.1)

        json_calls = [call for call in mock_logger.error.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON error log call"

        log_call_args = json_calls[-1][0][0]
        log_data = json.loads(log_call_args)

        assert log_data["error_message"] == error_message

    async def test_track_llm_request_with_metadata(self, llmops_logger, mock_logger):
        """Test track_llm_request with custom metadata."""
        metadata = {"provider": "openai", "version": "1.0", "experiment_id": "exp-123"}

        async with llmops_logger.track_llm_request(
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="test",
            metadata=metadata,
        ):
            pass

        await asyncio.sleep(0.1)

        log_call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)

        assert log_data["metadata"] == metadata

    async def test_retrieve_prompt(self, llmops_logger, storage):
        """Test retrieving stored prompt."""
        prompt_data = PromptData(
            prompt_id="test-retrieve-001",
            prompt_content="Test content",
            response_content="Test response",
        )
        await storage.save_prompt(prompt_data, mask_sensitive=False)

        retrieved = await llmops_logger.retrieve_prompt("test-retrieve-001")

        assert retrieved is not None
        assert retrieved.prompt_id == "test-retrieve-001"
        assert retrieved.prompt_content == "Test content"

    async def test_retrieve_nonexistent_prompt(self, llmops_logger):
        """Test retrieving a prompt that doesn't exist."""
        retrieved = await llmops_logger.retrieve_prompt("nonexistent-id")

        assert retrieved is None

    async def test_masking_enabled(self, mock_logger, temp_storage_dir):
        """Test that masking is applied when enabled."""
        storage = LocalFilePromptStorage(base_dir=temp_storage_dir)
        logger = LLMOpsLogger(logger=mock_logger, prompt_storage=storage, enable_masking=True)

        prompt_id = "test-masking-001"

        await logger.log_llm_request(
            request_id="req-001",
            prompt_id=prompt_id,
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="Email: test@example.com",
        )

        await asyncio.sleep(0.1)

        retrieved = await storage.retrieve_prompt(prompt_id)
        assert retrieved is not None
        assert "***@***.***" in retrieved.prompt_content
        assert "test@example.com" not in retrieved.prompt_content

    async def test_masking_disabled(self, mock_logger, temp_storage_dir):
        """Test that masking is not applied when disabled."""
        storage = LocalFilePromptStorage(base_dir=temp_storage_dir)
        logger = LLMOpsLogger(logger=mock_logger, prompt_storage=storage, enable_masking=False)

        prompt_id = "test-no-masking-001"

        await logger.log_llm_request(
            request_id="req-001",
            prompt_id=prompt_id,
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="Email: test@example.com",
        )

        await asyncio.sleep(0.1)

        retrieved = await storage.retrieve_prompt(prompt_id)
        assert retrieved is not None
        assert "test@example.com" in retrieved.prompt_content


class TestCreateLLMOpsLogger:
    """Tests for create_llmops_logger factory function."""

    def test_create_logger_with_defaults(self):
        """Test creating logger with default parameters."""
        temp_dir = tempfile.mkdtemp(prefix="test_logger_defaults_")
        try:
            logger = create_llmops_logger(storage_type="local", base_dir=temp_dir)

            assert isinstance(logger, LLMOpsLogger)
            assert logger.logger is not None
            assert logger.prompt_storage is not None
            assert logger.enable_masking is True
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "logger_name,log_level",
        [
            ("test_logger_1", logging.INFO),
            ("test_logger_2", logging.DEBUG),
            ("test_logger_3", logging.WARNING),
        ],
    )
    def test_create_logger_with_custom_params(self, logger_name, log_level):
        """Test creating logger with custom parameters."""
        temp_dir = tempfile.mkdtemp(prefix=f"test_logger_{logger_name}_")
        try:
            logger = create_llmops_logger(
                logger_name=logger_name, log_level=log_level, storage_type="local", base_dir=temp_dir
            )

            assert logger.logger.name == logger_name
            assert logger.logger.level == log_level
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_logger_with_custom_storage_dir(self):
        """Test creating logger with custom storage directory."""
        custom_dir = tempfile.mkdtemp(prefix="test_custom_storage_")
        try:
            logger = create_llmops_logger(storage_type="local", base_dir=custom_dir)

            assert isinstance(logger.prompt_storage, LocalFilePromptStorage)
            assert logger.prompt_storage.base_dir == Path(custom_dir)
        finally:
            if Path(custom_dir).exists():
                shutil.rmtree(custom_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "enable_masking",
        [True, False],
    )
    def test_create_logger_masking_option(self, enable_masking):
        """Test creating logger with masking enabled/disabled."""
        temp_dir = tempfile.mkdtemp(prefix=f"test_masking_{enable_masking}_")
        try:
            logger = create_llmops_logger(enable_masking=enable_masking, storage_type="local", base_dir=temp_dir)

            assert logger.enable_masking == enable_masking
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_logger_adds_handler_if_needed(self):
        """Test that handler is added if logger has no handlers."""
        logger_name = "test_no_handlers"
        temp_dir = tempfile.mkdtemp(prefix="test_handlers_")
        try:
            logger = create_llmops_logger(logger_name=logger_name, storage_type="local", base_dir=temp_dir)

            assert len(logger.logger.handlers) > 0
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def test_logger_uses_simple_format(self):
        """Test that logger uses simple format for JSON output."""
        logger_name = "test_format"
        temp_dir = tempfile.mkdtemp(prefix="test_format_")
        try:
            logger = create_llmops_logger(logger_name=logger_name, storage_type="local", base_dir=temp_dir)

            handler = logger.logger.handlers[0]
            formatter = handler.formatter

            assert formatter._fmt == "%(message)s"
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
class TestLLMOpsLoggerIntegration:
    """Integration tests for LLMOpsLogger with real components."""

    @pytest.fixture
    def temp_storage_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    async def test_end_to_end_logging_workflow(self, temp_storage_dir):
        """Test complete logging workflow from request to retrieval."""
        logger = create_llmops_logger(
            logger_name="integration_test",
            storage_type="local",
            base_dir=temp_storage_dir,
            enable_masking=False,
        )

        prompt_id = None

        async with logger.track_llm_request(
            model="openai.gpt-5.4",
            temperature=0.7,
            prompt_content="What is the meaning of life?",
            user_id="integration-user",
            metadata={"test": "integration"},
        ) as tracking:
            await asyncio.sleep(0.01)
            tracking["response"] = "42"
            prompt_id = tracking["prompt_id"]

        await asyncio.sleep(0.2)

        retrieved = await logger.retrieve_prompt(prompt_id)

        assert retrieved is not None
        assert retrieved.prompt_content == "What is the meaning of life?"
        assert retrieved.response_content == "42"
        assert retrieved.metadata["test"] == "integration"

    async def test_concurrent_logging(self, temp_storage_dir):
        """Test logging multiple requests concurrently."""
        logger = create_llmops_logger(
            logger_name="concurrent_test",
            storage_type="local",
            base_dir=temp_storage_dir,
        )

        async def log_request(i):
            async with logger.track_llm_request(
                model="openai.gpt-5.4",
                temperature=0.7,
                prompt_content=f"Prompt {i}",
                user_id=f"user-{i}",
            ) as tracking:
                tracking["response"] = f"Response {i}"
                return tracking["prompt_id"]

        prompt_ids = await asyncio.gather(*[log_request(i) for i in range(5)])

        await asyncio.sleep(0.3)

        for i, prompt_id in enumerate(prompt_ids):
            retrieved = await logger.retrieve_prompt(prompt_id)
            assert retrieved is not None
            assert f"Prompt {i}" in retrieved.prompt_content

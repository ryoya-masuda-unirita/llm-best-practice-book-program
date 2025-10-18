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
        # Cleanup
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
        # Use tempfile to avoid creating default "prompt_storage" directory
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
            ("req-001", "p-001", "gpt-4o-mini", 0.7),
            ("req-002", "p-002", "gemini-2.5-flash", 1.0),
            ("req-003", "p-003", "claude-3-sonnet", 0.5),
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

        # Wait for async storage to complete
        await asyncio.sleep(0.1)

        # Verify logger.info was called (at least once for the log entry, possibly more for storage)
        assert mock_logger.info.called

        # Find the call with the structured log JSON
        json_calls = [call for call in mock_logger.info.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON log call"

        # Verify the logged JSON contains expected fields
        log_call_args = json_calls[-1][0][0]  # Get the last JSON call
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
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="test",
            level=level,
        )

        # Wait for async storage to complete
        await asyncio.sleep(0.1)

        # Verify the appropriate logging method was called
        log_method = getattr(mock_logger, expected_method)
        assert log_method.called, f"Expected {expected_method} to be called"

        # Find the structured log JSON call
        json_calls = [call for call in log_method.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, f"Expected at least one JSON log call to {expected_method}"

    async def test_log_llm_request_with_all_fields(self, llmops_logger, mock_logger):
        """Test logging with all optional fields populated."""
        await llmops_logger.log_llm_request(
            request_id="req-001",
            prompt_id="p-001",
            model="gpt-4o-mini",
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
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="test prompt content",
            response_content="test response content",
        )

        # Wait for async task to complete
        await asyncio.sleep(0.1)

        # Verify prompt was stored
        retrieved = await storage.retrieve_prompt(prompt_id)
        assert retrieved is not None
        assert retrieved.prompt_id == prompt_id
        assert retrieved.prompt_content == "test prompt content"
        assert retrieved.response_content == "test response content"

    async def test_log_llm_request_error_handling(self, mock_logger):
        """Test error handling when prompt storage fails."""
        # Create a mock storage that will fail
        bad_storage = AsyncMock(spec=LocalFilePromptStorage)
        bad_storage.save_prompt = AsyncMock(side_effect=Exception("Storage failed"))

        logger = LLMOpsLogger(logger=mock_logger, prompt_storage=bad_storage, enable_masking=False)

        # This should not raise an error (errors are logged)
        await logger.log_llm_request(
            request_id="req-001",
            prompt_id="p-001",
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="test",
        )

        # Wait for async task
        await asyncio.sleep(0.1)

        # Verify error was logged
        assert mock_logger.error.called

    async def test_track_llm_request_context_manager_success(self, llmops_logger, mock_logger):
        """Test track_llm_request context manager with successful request."""
        async with llmops_logger.track_llm_request(
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="test prompt",
            user_id="user-001",
        ) as tracking:
            # Simulate LLM response
            tracking["response"] = "test response"

        # Wait for async logging
        await asyncio.sleep(0.1)

        # Verify logging was called
        assert mock_logger.info.called

        # Find the structured log JSON call
        json_calls = [call for call in mock_logger.info.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON log call"

        # Verify log data (get the last JSON call)
        log_call_args = json_calls[-1][0][0]
        log_data = json.loads(log_call_args)

        assert log_data["model"] == "gpt-4o-mini"
        assert log_data["temperature"] == 0.7
        assert log_data["user_id"] == "user-001"
        assert log_data["status_code"] == 200
        assert log_data["latency_ms"] is not None
        assert log_data["latency_ms"] > 0

    async def test_track_llm_request_auto_generates_ids(self, llmops_logger, mock_logger):
        """Test that request_id and prompt_id are auto-generated."""
        async with llmops_logger.track_llm_request(
            model="gpt-4o-mini",
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
            model="gpt-4o-mini",
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
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="test",
        ):
            # Simulate some work
            await asyncio.sleep(0.05)  # 50ms

        await asyncio.sleep(0.1)

        # Verify latency was recorded
        log_call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)

        assert "latency_ms" in log_data
        assert log_data["latency_ms"] >= 50  # At least 50ms

    async def test_track_llm_request_error_handling(self, llmops_logger, mock_logger):
        """Test context manager error handling."""
        with pytest.raises(ValueError):
            async with llmops_logger.track_llm_request(
                model="gpt-4o-mini",
                temperature=0.7,
                prompt_content="test",
            ) as _:
                raise ValueError("Simulated error")

        await asyncio.sleep(0.1)

        # Verify error was logged
        assert mock_logger.error.called

        # Find the structured log JSON call
        json_calls = [call for call in mock_logger.error.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON error log call"

        # Verify error details in log
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
                model="gpt-4o-mini",
                temperature=0.7,
                prompt_content="test",
            ):
                raise exception_type(error_message)

        await asyncio.sleep(0.1)

        # Find the structured log JSON call
        json_calls = [call for call in mock_logger.error.call_args_list if call[0][0].startswith("{")]
        assert len(json_calls) > 0, "Expected at least one JSON error log call"

        log_call_args = json_calls[-1][0][0]
        log_data = json.loads(log_call_args)

        assert log_data["error_message"] == error_message

    async def test_track_llm_request_with_metadata(self, llmops_logger, mock_logger):
        """Test track_llm_request with custom metadata."""
        metadata = {"provider": "openai", "version": "1.0", "experiment_id": "exp-123"}

        async with llmops_logger.track_llm_request(
            model="gpt-4o-mini",
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
        # Store a prompt first
        prompt_data = PromptData(
            prompt_id="test-retrieve-001",
            prompt_content="Test content",
            response_content="Test response",
        )
        await storage.save_prompt(prompt_data, mask_sensitive=False)

        # Retrieve it through the logger
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
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="Email: test@example.com",
        )

        await asyncio.sleep(0.1)

        # Retrieve and verify masking was applied
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
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="Email: test@example.com",
        )

        await asyncio.sleep(0.1)

        # Retrieve and verify no masking
        retrieved = await storage.retrieve_prompt(prompt_id)
        assert retrieved is not None
        assert "test@example.com" in retrieved.prompt_content


class TestCreateLLMOpsLogger:
    """Tests for create_llmops_logger factory function."""

    def test_create_logger_with_defaults(self):
        """Test creating logger with default parameters."""
        # Use tempfile to avoid creating default "prompt_storage" directory
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
        # Use tempfile to avoid creating default "prompt_storage" directory
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
        # Use tempfile to create a temporary directory
        custom_dir = tempfile.mkdtemp(prefix="test_custom_storage_")
        try:
            logger = create_llmops_logger(storage_type="local", base_dir=custom_dir)

            assert isinstance(logger.prompt_storage, LocalFilePromptStorage)
            assert logger.prompt_storage.base_dir == Path(custom_dir)
        finally:
            # Cleanup
            if Path(custom_dir).exists():
                shutil.rmtree(custom_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "enable_masking",
        [True, False],
    )
    def test_create_logger_masking_option(self, enable_masking):
        """Test creating logger with masking enabled/disabled."""
        # Use tempfile to avoid creating default "prompt_storage" directory
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
        # Use tempfile to avoid creating default "prompt_storage" directory
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
        # Use tempfile to avoid creating default "prompt_storage" directory
        temp_dir = tempfile.mkdtemp(prefix="test_format_")
        try:
            logger = create_llmops_logger(logger_name=logger_name, storage_type="local", base_dir=temp_dir)

            # Get the handler's formatter
            handler = logger.logger.handlers[0]
            formatter = handler.formatter

            # Format should be simple "%(message)s" for JSON logs
            assert formatter._fmt == "%(message)s"
        finally:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
class TestLLMOpsLoggerIntegration:
    """Integration tests for LLMOpsLogger with real components."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
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

        # Simulate LLM request
        async with logger.track_llm_request(
            model="gpt-4o-mini",
            temperature=0.7,
            prompt_content="What is the meaning of life?",
            user_id="integration-user",
            metadata={"test": "integration"},
        ) as tracking:
            # Simulate processing
            await asyncio.sleep(0.01)
            tracking["response"] = "42"
            prompt_id = tracking["prompt_id"]

        # Wait for async operations
        await asyncio.sleep(0.2)

        # Retrieve and verify
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
                model="gpt-4o-mini",
                temperature=0.7,
                prompt_content=f"Prompt {i}",
                user_id=f"user-{i}",
            ) as tracking:
                tracking["response"] = f"Response {i}"
                return tracking["prompt_id"]

        # Run 5 concurrent requests
        prompt_ids = await asyncio.gather(*[log_request(i) for i in range(5)])

        # Wait for async storage
        await asyncio.sleep(0.3)

        # Verify all were stored
        for i, prompt_id in enumerate(prompt_ids):
            retrieved = await logger.retrieve_prompt(prompt_id)
            assert retrieved is not None
            assert f"Prompt {i}" in retrieved.prompt_content

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.api_core import exceptions as google_exceptions
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
from src.client.llm_client import GeminiModel, OpenAIModel
from src.service.request_llm import (
    BASE_BACKOFF_SECONDS,
    JITTER_MAX,
    JITTER_MIN,
    MAX_BACKOFF_SECONDS,
    batch_request_gemini,
    batch_request_openai,
    calculate_backoff_with_jitter,
    request_gemini,
    request_openai,
    retry_with_exponential_backoff,
    should_retry_error,
)


class TestCalculateBackoffWithJitter:
    """Tests for calculate_backoff_with_jitter function."""

    def test_exponential_growth(self):
        """Test that backoff time grows exponentially."""
        backoff_0 = calculate_backoff_with_jitter(0)
        backoff_1 = calculate_backoff_with_jitter(1)
        backoff_2 = calculate_backoff_with_jitter(2)

        # Check that the base values are roughly doubling (accounting for jitter)
        # Attempt 0: 1s, Attempt 1: 2s, Attempt 2: 4s
        assert backoff_0 >= BASE_BACKOFF_SECONDS * (1 + JITTER_MIN)
        assert backoff_1 >= BASE_BACKOFF_SECONDS * 2 * (1 + JITTER_MIN)
        assert backoff_2 >= BASE_BACKOFF_SECONDS * 4 * (1 + JITTER_MIN)

    def test_max_backoff_limit(self):
        """Test that backoff doesn't exceed maximum."""
        # Very high attempt number should cap at MAX_BACKOFF_SECONDS
        backoff = calculate_backoff_with_jitter(100)
        assert backoff <= MAX_BACKOFF_SECONDS * (1 + JITTER_MAX)

    def test_jitter_applied(self):
        """Test that jitter adds randomness."""
        # Multiple calls should produce different results
        backoffs = [calculate_backoff_with_jitter(1) for _ in range(10)]
        assert len(set(backoffs)) > 1, "Jitter should produce different values"

    def test_custom_base(self):
        """Test with custom base backoff time."""
        custom_base = 2.0
        backoff = calculate_backoff_with_jitter(0, base=custom_base)
        assert backoff >= custom_base * (1 + JITTER_MIN)


class TestShouldRetryError:
    """Tests for should_retry_error function."""

    def test_rate_limit_error_without_retry_after(self):
        """Test RateLimitError without Retry-After header."""
        mock_response = MagicMock()
        mock_response.headers = {}
        error = RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True
        assert retry_after is None

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with Retry-After header."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "60"}
        error = RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True
        assert retry_after == 60

    def test_timeout_error(self):
        """Test APITimeoutError is retryable."""
        error = APITimeoutError("Request timeout")
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True
        assert retry_after is None

    def test_connection_error(self):
        """Test APIConnectionError is retryable."""
        error = APIConnectionError(request=MagicMock())
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True
        assert retry_after is None

    def test_server_error_500(self):
        """Test HTTP 500 error is retryable."""
        error = APIError("Internal server error", request=MagicMock(), body=None)
        error.status_code = 500
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True

    def test_bad_request_400(self):
        """Test HTTP 400 error is not retryable."""
        error = APIError("Bad request", request=MagicMock(), body=None)
        error.status_code = 400
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is False

    def test_unauthorized_401(self):
        """Test HTTP 401 error is not retryable."""
        error = APIError("Unauthorized", request=MagicMock(), body=None)
        error.status_code = 401
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is False

    def test_gemini_resource_exhausted(self):
        """Test Google ResourceExhausted error is retryable."""
        error = google_exceptions.ResourceExhausted("Quota exceeded")
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True

    def test_gemini_service_unavailable(self):
        """Test Google ServiceUnavailable error is retryable."""
        error = google_exceptions.ServiceUnavailable("Service temporarily unavailable")
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True

    def test_unknown_error(self):
        """Test unknown errors are not retryable."""
        error = ValueError("Unknown error")
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is False


class TestRetryWithExponentialBackoff:
    """Tests for retry_with_exponential_backoff decorator."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test that function succeeds on first try without retries."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test that function succeeds after multiple retries."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APITimeoutError("Timeout")
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that function fails after max retries."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=2)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            raise APITimeoutError("Timeout")

        with pytest.raises(APITimeoutError):
            await mock_function()
        assert call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Test that non-retryable errors fail immediately."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=3)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            error = APIError("Bad request", request=MagicMock(), body=None)
            error.status_code = 400
            raise error

        with pytest.raises(APIError):
            await mock_function()
        assert call_count == 1  # No retries for 400 error

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self):
        """Test that decorator respects Retry-After header."""
        call_count = 0

        @retry_with_exponential_backoff(max_retries=2)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                mock_response = MagicMock()
                mock_response.headers = {"Retry-After": "1"}
                raise RateLimitError("Rate limit", response=mock_response, body=None)
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await mock_function()
            assert result == "success"
            # Should sleep for 1 second (from Retry-After header)
            mock_sleep.assert_called_once()
            assert mock_sleep.call_args[0][0] == 1


class TestRequestOpenAI:
    """Tests for request_openai function."""

    @pytest.mark.asyncio
    async def test_successful_request(self, sample_character_request, sample_character_response, mock_llmops_logger):
        """Test successful OpenAI request."""
        mock_result = MagicMock()
        mock_result.choices = [MagicMock()]
        mock_result.choices[0].message.parsed = sample_character_response

        with patch("src.service.request_llm.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_result)

            result = await request_openai(
                character_request=sample_character_request,
                model=OpenAIModel.GPT_4O_MINI,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
            )

            assert result == sample_character_response
            mock_client.beta.chat.completions.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_retry(self, sample_character_request, sample_character_response, mock_llmops_logger):
        """Test OpenAI request that succeeds after retry."""
        mock_result = MagicMock()
        mock_result.choices = [MagicMock()]
        mock_result.choices[0].message.parsed = sample_character_response

        call_count = 0

        async def mock_parse(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APITimeoutError("Timeout")
            return mock_result

        with patch("src.service.request_llm.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(side_effect=mock_parse)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await request_openai(
                    character_request=sample_character_request,
                    model=OpenAIModel.GPT_4O_MINI,
                    llmops_logger=mock_llmops_logger,
                    user_id="test_user",
                )

                assert result == sample_character_response
                assert call_count == 2


class TestRequestGemini:
    """Tests for request_gemini function."""

    @pytest.mark.asyncio
    async def test_successful_request(self, sample_character_request, sample_character_response, mock_llmops_logger):
        """Test successful Gemini request."""
        mock_result = MagicMock()
        mock_result.parsed = sample_character_response

        with patch("src.service.request_llm.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_result)

            result = await request_gemini(
                character_request=sample_character_request,
                model=GeminiModel.GEMINI_2_5_FLASH,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
            )

            assert result == sample_character_response
            mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_retry(self, sample_character_request, sample_character_response, mock_llmops_logger):
        """Test Gemini request that succeeds after retry."""
        mock_result = MagicMock()
        mock_result.parsed = sample_character_response

        call_count = 0

        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise google_exceptions.ServiceUnavailable("Service unavailable")
            return mock_result

        with patch("src.service.request_llm.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await request_gemini(
                    character_request=sample_character_request,
                    model=GeminiModel.GEMINI_2_5_FLASH,
                    llmops_logger=mock_llmops_logger,
                    user_id="test_user",
                )

                assert result == sample_character_response
                assert call_count == 2


class TestBatchRequestOpenAI:
    """Tests for batch_request_openai function."""

    @pytest.mark.asyncio
    async def test_successful_batch(self, sample_character_requests, sample_character_response, mock_llmops_logger):
        """Test successful batch processing with OpenAI."""
        mock_result = MagicMock()
        mock_result.choices = [MagicMock()]
        mock_result.choices[0].message.parsed = sample_character_response

        with patch("src.service.request_llm.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_result)

            results = await batch_request_openai(
                character_requests=sample_character_requests,
                model=OpenAIModel.GPT_4O_MINI,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            assert len(results) == 3
            assert all(r == sample_character_response for r in results)

    @pytest.mark.asyncio
    async def test_batch_with_partial_failures(
        self, sample_character_requests, sample_character_response, mock_llmops_logger
    ):
        """Test batch processing with some failures."""
        mock_result = MagicMock()
        mock_result.choices = [MagicMock()]
        mock_result.choices[0].message.parsed = sample_character_response

        call_count = 0

        async def mock_parse(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on second request permanently (non-retryable error)
            if call_count == 2:
                error = APIError("Bad request", response=None, body=None)
                error.status_code = 400
                raise error
            return mock_result

        with patch("src.service.request_llm.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(side_effect=mock_parse)

            results = await batch_request_openai(
                character_requests=sample_character_requests,
                model=OpenAIModel.GPT_4O_MINI,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            # Should have 2 successful results (1st and 3rd requests)
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_batch_respects_parallelism(
        self, sample_character_requests, sample_character_response, mock_llmops_logger
    ):
        """Test that batch processing respects parallelism limit."""
        mock_result = MagicMock()
        mock_result.choices = [MagicMock()]
        mock_result.choices[0].message.parsed = sample_character_response

        concurrent_calls = 0
        max_concurrent_calls = 0

        async def mock_parse(*args, **kwargs):
            nonlocal concurrent_calls, max_concurrent_calls
            concurrent_calls += 1
            max_concurrent_calls = max(max_concurrent_calls, concurrent_calls)
            await asyncio.sleep(0.1)  # Simulate API call
            concurrent_calls -= 1
            return mock_result

        with patch("src.service.request_llm.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(side_effect=mock_parse)

            await batch_request_openai(
                character_requests=sample_character_requests,
                model=OpenAIModel.GPT_4O_MINI,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            # Max concurrent calls should not exceed parallelism limit
            assert max_concurrent_calls <= 2


class TestBatchRequestGemini:
    """Tests for batch_request_gemini function."""

    @pytest.mark.asyncio
    async def test_successful_batch(self, sample_character_requests, sample_character_response, mock_llmops_logger):
        """Test successful batch processing with Gemini."""
        mock_result = MagicMock()
        mock_result.parsed = sample_character_response

        with patch("src.service.request_llm.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_result)

            results = await batch_request_gemini(
                character_requests=sample_character_requests,
                model=GeminiModel.GEMINI_2_5_FLASH,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            assert len(results) == 3
            assert all(r == sample_character_response for r in results)

    @pytest.mark.asyncio
    async def test_batch_with_partial_failures(
        self, sample_character_requests, sample_character_response, mock_llmops_logger
    ):
        """Test batch processing with some failures."""
        mock_result = MagicMock()
        mock_result.parsed = sample_character_response

        call_count = 0

        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on second request permanently
            if call_count == 2:
                raise ValueError("Invalid input")
            return mock_result

        with patch("src.service.request_llm.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

            results = await batch_request_gemini(
                character_requests=sample_character_requests,
                model=GeminiModel.GEMINI_2_5_FLASH,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            # Should have 2 successful results (1st and 3rd requests)
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_batch_respects_parallelism(
        self, sample_character_requests, sample_character_response, mock_llmops_logger
    ):
        """Test that batch processing respects parallelism limit."""
        mock_result = MagicMock()
        mock_result.parsed = sample_character_response

        concurrent_calls = 0
        max_concurrent_calls = 0

        async def mock_generate(*args, **kwargs):
            nonlocal concurrent_calls, max_concurrent_calls
            concurrent_calls += 1
            max_concurrent_calls = max(max_concurrent_calls, concurrent_calls)
            await asyncio.sleep(0.1)  # Simulate API call
            concurrent_calls -= 1
            return mock_result

        with patch("src.service.request_llm.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate)

            await batch_request_gemini(
                character_requests=sample_character_requests,
                model=GeminiModel.GEMINI_2_5_FLASH,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            # Max concurrent calls should not exceed parallelism limit
            assert max_concurrent_calls <= 2

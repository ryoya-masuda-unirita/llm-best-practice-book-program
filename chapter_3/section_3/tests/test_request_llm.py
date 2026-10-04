import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx2
import pytest
from src.client.llm_client import AnthropicModel
from src.service.request_llm import (
    BASE_BACKOFF_SECONDS,
    JITTER_MAX,
    JITTER_MIN,
    MAX_BACKOFF_SECONDS,
    batch_request_anthropic,
    calculate_backoff_with_jitter,
    request_anthropic,
    retry_with_exponential_backoff,
    should_retry_error,
)


def make_status_error(error_class: type[anthropic.APIStatusError], status_code: int) -> anthropic.APIStatusError:
    """Build an Anthropic API error with the given HTTP status code."""
    request = httpx2.Request("POST", "https://bedrock-runtime.us-east-1.amazonaws.com")
    response = httpx2.Response(status_code, request=request)
    return error_class("error", response=response, body=None)


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

    def test_anthropic_rate_limit(self):
        """Test Anthropic RateLimitError (429) is retryable."""
        error = make_status_error(anthropic.RateLimitError, 429)
        should_retry, retry_after = should_retry_error(error)
        assert should_retry is True

    def test_anthropic_server_error(self):
        """Test Anthropic InternalServerError (503) is retryable."""
        error = make_status_error(anthropic.InternalServerError, 503)
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
                raise make_status_error(anthropic.InternalServerError, 503)
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
            raise make_status_error(anthropic.InternalServerError, 503)

        with pytest.raises(anthropic.InternalServerError):
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
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            await mock_function()
        assert call_count == 1  # No retries for non-retryable errors


class TestRequestAnthropic:
    """Tests for request_anthropic function."""

    @pytest.mark.asyncio
    async def test_successful_request(self, sample_character_request, sample_character_response, mock_llmops_logger):
        """Test successful Anthropic request."""
        mock_result = MagicMock()
        mock_result.parsed_output = sample_character_response

        with patch("src.service.request_llm.anthropic_client") as mock_client:
            mock_client.messages.parse = AsyncMock(return_value=mock_result)

            result = await request_anthropic(
                character_request=sample_character_request,
                model=AnthropicModel.CLAUDE_HAIKU_4_5,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
            )

            assert result == sample_character_response
            mock_client.messages.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_with_retry(self, sample_character_request, sample_character_response, mock_llmops_logger):
        """Test Anthropic request that succeeds after retry."""
        mock_result = MagicMock()
        mock_result.parsed_output = sample_character_response

        call_count = 0

        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise make_status_error(anthropic.InternalServerError, 503)
            return mock_result

        with patch("src.service.request_llm.anthropic_client") as mock_client:
            mock_client.messages.parse = AsyncMock(side_effect=mock_generate)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await request_anthropic(
                    character_request=sample_character_request,
                    model=AnthropicModel.CLAUDE_HAIKU_4_5,
                    llmops_logger=mock_llmops_logger,
                    user_id="test_user",
                )

                assert result == sample_character_response
                assert call_count == 2


class TestBatchRequestAnthropic:
    """Tests for batch_request_anthropic function."""

    @pytest.mark.asyncio
    async def test_successful_batch(self, sample_character_requests, sample_character_response, mock_llmops_logger):
        """Test successful batch processing with Anthropic."""
        mock_result = MagicMock()
        mock_result.parsed_output = sample_character_response

        with patch("src.service.request_llm.anthropic_client") as mock_client:
            mock_client.messages.parse = AsyncMock(return_value=mock_result)

            results = await batch_request_anthropic(
                character_requests=sample_character_requests,
                model=AnthropicModel.CLAUDE_HAIKU_4_5,
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
        mock_result.parsed_output = sample_character_response

        call_count = 0

        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on second request permanently
            if call_count == 2:
                raise ValueError("Invalid input")
            return mock_result

        with patch("src.service.request_llm.anthropic_client") as mock_client:
            mock_client.messages.parse = AsyncMock(side_effect=mock_generate)

            results = await batch_request_anthropic(
                character_requests=sample_character_requests,
                model=AnthropicModel.CLAUDE_HAIKU_4_5,
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
        mock_result.parsed_output = sample_character_response

        concurrent_calls = 0
        max_concurrent_calls = 0

        async def mock_generate(*args, **kwargs):
            nonlocal concurrent_calls, max_concurrent_calls
            concurrent_calls += 1
            max_concurrent_calls = max(max_concurrent_calls, concurrent_calls)
            await asyncio.sleep(0.1)  # Simulate API call
            concurrent_calls -= 1
            return mock_result

        with patch("src.service.request_llm.anthropic_client") as mock_client:
            mock_client.messages.parse = AsyncMock(side_effect=mock_generate)

            await batch_request_anthropic(
                character_requests=sample_character_requests,
                model=AnthropicModel.CLAUDE_HAIKU_4_5,
                llmops_logger=mock_llmops_logger,
                user_id="test_user",
                parallelism=2,
            )

            # Max concurrent calls should not exceed parallelism limit
            assert max_concurrent_calls <= 2

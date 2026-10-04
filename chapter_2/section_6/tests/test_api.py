"""Unit tests for FastAPI endpoints."""

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_200(self, test_client):
        """Test health check returns 200 OK."""
        response = test_client.get("/health")

        assert response.status_code == 200

    def test_health_check_response_structure(self, test_client):
        """Test health check response structure."""
        response = test_client.get("/health")
        data = response.json()

        assert "status" in data
        assert "message" in data

    def test_health_check_response_values(self, test_client):
        """Test health check response values."""
        response = test_client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["message"] == "LLM Streaming API is running"

    def test_health_check_content_type(self, test_client):
        """Test health check content type."""
        response = test_client.get("/health")

        assert response.headers["content-type"] == "application/json"


@pytest.mark.unit
class TestStreamEndpoint:
    """Tests for /stream endpoint."""

    def test_stream_endpoint_requires_prompt(self, test_client):
        """Test that stream endpoint requires prompt field."""
        response = test_client.post(
            "/stream",
            json={"provider": "openai"},
        )

        assert response.status_code == 422

    def test_stream_endpoint_rejects_empty_prompt(self, test_client):
        """Test that stream endpoint rejects empty prompt."""
        response = test_client.post(
            "/stream",
            json={"prompt": "", "provider": "openai"},
        )

        assert response.status_code == 422

    def test_stream_endpoint_accepts_openai_provider(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test stream endpoint accepts OpenAI provider."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream",
                json={"prompt": "Test", "provider": "openai"},
            )

            assert response.status_code == 200

    def test_stream_endpoint_openai_default(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test stream endpoint uses OpenAI as default provider."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream",
                json={"prompt": "Test"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_stream_endpoint_openai_response(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test stream endpoint with OpenAI provider."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream",
                json={
                    "prompt": "Hello",
                    "provider": "openai",
                    "model": "openai.gpt-5.4",
                },
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"

    def test_stream_endpoint_streaming_headers(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test stream endpoint sets correct streaming headers."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream",
                json={"prompt": "Test", "provider": "openai"},
            )

            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"
            assert response.headers["x-accel-buffering"] == "no"

    def test_stream_endpoint_openai_with_custom_model(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test stream endpoint with custom OpenAI model."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream",
                json={
                    "prompt": "Test",
                    "provider": "openai",
                    "model": "openai.gpt-5.4",
                },
            )

            assert response.status_code == 200

    @pytest.mark.parametrize(
        "request_data",
        [
            {"prompt": "Hello", "provider": "openai"},
            {"prompt": "こんにちは", "provider": "openai"},
            {"prompt": "Long prompt" * 100, "provider": "openai"},
        ],
    )
    def test_stream_endpoint_various_requests(
        self,
        test_client,
        mock_openai_client,
        request_data,
    ):
        """Test stream endpoint with various request formats."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post("/stream", json=request_data)

            assert response.status_code == 200


@pytest.mark.unit
class TestStreamOpenAIEndpoint:
    """Tests for /stream/openai endpoint."""

    def test_stream_openai_endpoint_success(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test OpenAI-specific endpoint success."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream/openai",
                json={"prompt": "Hello"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_stream_openai_endpoint_with_model(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test OpenAI endpoint with custom model."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream/openai",
                json={"prompt": "Test", "model": "openai.gpt-5.4"},
            )

            assert response.status_code == 200

    def test_stream_openai_endpoint_requires_prompt(self, test_client):
        """Test OpenAI endpoint requires prompt."""
        response = test_client.post("/stream/openai", json={})

        assert response.status_code == 422

    def test_stream_openai_endpoint_streaming_headers(
        self,
        test_client,
        mock_openai_client,
    ):
        """Test OpenAI endpoint sets correct streaming headers."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream/openai",
                json={"prompt": "Test"},
            )

            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"
            assert response.headers["x-accel-buffering"] == "no"

    @pytest.mark.parametrize(
        "model",
        ["openai.gpt-5.4", "openai.gpt-5.4", "openai.gpt-5.4", None],
    )
    def test_stream_openai_endpoint_various_models(
        self,
        test_client,
        mock_openai_client,
        model,
    ):
        """Test OpenAI endpoint with various models."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            request_data = {"prompt": "Test"}
            if model is not None:
                request_data["model"] = model

            response = test_client.post("/stream/openai", json=request_data)

            assert response.status_code == 200


@pytest.mark.unit
class TestCORSMiddleware:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self, test_client, mock_openai_client):
        """Test CORS headers are present in response."""
        with patch(
            "src.service.streaming_service.openai_client",
            mock_openai_client,
        ):
            response = test_client.post(
                "/stream",
                json={"prompt": "Test"},
                headers={"Origin": "http://localhost:3000"},
            )

            assert "access-control-allow-origin" in response.headers

    def test_cors_allows_all_origins(self, test_client):
        """Test CORS allows all origins (development mode)."""
        response = test_client.get(
            "/health",
            headers={"Origin": "http://example.com"},
        )

        assert response.headers.get("access-control-allow-origin") == "*"

    def test_cors_allows_credentials(self, test_client):
        """Test CORS allows credentials."""
        response = test_client.options(
            "/stream",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling in endpoints."""

    def test_invalid_json_returns_422(self, test_client):
        """Test invalid JSON returns 422 error."""
        response = test_client.post(
            "/stream",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "invalid_data",
        [
            {},  # Missing prompt
            {"prompt": ""},  # Empty prompt
            {"prompt": "test", "provider": "invalid"},  # Invalid provider
        ],
    )
    def test_invalid_request_data(self, test_client, invalid_data):
        """Test various invalid request data scenarios."""
        response = test_client.post("/stream", json=invalid_data)

        assert response.status_code == 422

"""Tests for LLMClientFactory.

This module tests the Factory pattern implementation that creates
appropriate LLM client adapters based on provider and model specifications.
"""

from unittest.mock import patch

import pytest
from src.client.adapters import AnthropicAdapter, OpenAIAdapter  # , GeminiAdapter
from src.client.base import LLMClient
from src.client.factory import LLMClientFactory
from src.client.model import AnthropicModel, LLMProvider, OpenAIModel  # , GeminiModel


class TestLLMClientFactory:
    """Test suite for LLMClientFactory."""

    def test_get_supported_providers(self):
        """Test retrieval of supported provider list."""
        providers = LLMClientFactory.get_supported_providers()
        assert isinstance(providers, list)
        assert LLMProvider.OPENAI in providers
        # assert LLMProvider.GEMINI in providers
        assert LLMProvider.ANTHROPIC in providers
        assert len(providers) == 2

    def test_get_supported_models_openai(self):
        """Test retrieval of OpenAI supported models."""
        models = LLMClientFactory.get_supported_models(LLMProvider.OPENAI)
        assert isinstance(models, list)
        assert OpenAIModel.GPT_5_4 in models
        assert OpenAIModel.GPT_5_4 in models
        assert len(models) > 0

    # def test_get_supported_models_gemini(self):
    #     """Test retrieval of Gemini supported models."""
    #     models = LLMClientFactory.get_supported_models(LLMProvider.GEMINI)
    #     assert isinstance(models, list)
    #     assert GeminiModel.GEMINI_2_5_PRO in models
    #     assert GeminiModel.GEMINI_2_5_FLASH in models
    #     assert len(models) > 0

    def test_get_supported_models_anthropic(self):
        """Test retrieval of Anthropic supported models."""
        models = LLMClientFactory.get_supported_models(LLMProvider.ANTHROPIC)
        assert isinstance(models, list)
        assert AnthropicModel.CLAUDE_SONNET_4_6 in models
        assert AnthropicModel.CLAUDE_SONNET_4_6 in models
        assert len(models) > 0

    def test_get_supported_models_unknown_provider(self):
        """Test error handling for unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClientFactory.get_supported_models("unknown_provider")

    def test_get_supported_models_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        models_lower = LLMClientFactory.get_supported_models("openai")
        models_upper = LLMClientFactory.get_supported_models("OPENAI")
        models_mixed = LLMClientFactory.get_supported_models("OpenAI")

        assert models_lower == models_upper == models_mixed

    def test_is_valid_combination_valid_openai(self):
        """Test valid OpenAI provider-model combination."""
        assert LLMClientFactory.is_valid_combination(LLMProvider.OPENAI, OpenAIModel.GPT_5_4)
        assert LLMClientFactory.is_valid_combination(LLMProvider.OPENAI, OpenAIModel.GPT_5_4)

    # def test_is_valid_combination_valid_gemini(self):
    #     """Test valid Gemini provider-model combination."""
    #     assert LLMClientFactory.is_valid_combination(LLMProvider.GEMINI, GeminiModel.GEMINI_2_5_PRO)
    #     assert LLMClientFactory.is_valid_combination(LLMProvider.GEMINI, GeminiModel.GEMINI_2_5_FLASH)

    def test_is_valid_combination_valid_anthropic(self):
        """Test valid Anthropic provider-model combination."""
        assert LLMClientFactory.is_valid_combination(LLMProvider.ANTHROPIC, AnthropicModel.CLAUDE_SONNET_4_6)
        assert LLMClientFactory.is_valid_combination(LLMProvider.ANTHROPIC, AnthropicModel.CLAUDE_SONNET_4_6)

    def test_is_valid_combination_invalid_provider(self):
        """Test invalid provider returns False."""
        assert not LLMClientFactory.is_valid_combination("invalid_provider", OpenAIModel.GPT_5_4)

    def test_is_valid_combination_invalid_model_for_provider(self):
        """Test invalid model for provider returns False."""
        # Try to use an Anthropic model with OpenAI provider
        assert not LLMClientFactory.is_valid_combination(LLMProvider.OPENAI, AnthropicModel.CLAUDE_SONNET_4_6)
        # Try to use an OpenAI model with Anthropic provider
        assert not LLMClientFactory.is_valid_combination(LLMProvider.ANTHROPIC, OpenAIModel.GPT_5_4)

    def test_is_valid_combination_case_insensitive(self):
        """Test that validation is case-insensitive for provider."""
        assert LLMClientFactory.is_valid_combination("openai", OpenAIModel.GPT_5_4)
        assert LLMClientFactory.is_valid_combination("OPENAI", OpenAIModel.GPT_5_4)

    @patch("src.client.factory.OpenAIAdapter")
    def test_create_client_openai(self, mock_adapter):
        """Test creation of OpenAI client."""
        LLMClientFactory.create_client(LLMProvider.OPENAI, OpenAIModel.GPT_5_4)
        mock_adapter.assert_called_once_with(model=OpenAIModel.GPT_5_4)

    # @patch("src.client.factory.GeminiAdapter")
    # def test_create_client_gemini(self, mock_adapter):
    #     """Test creation of Gemini client."""
    #     LLMClientFactory.create_client(LLMProvider.GEMINI, GeminiModel.GEMINI_2_5_PRO)
    #     mock_adapter.assert_called_once_with(model=GeminiModel.GEMINI_2_5_PRO)

    @patch("src.client.factory.OpenAIAdapter")
    def test_create_client_openai_different_models(self, mock_adapter):
        """Test creation of OpenAI clients with different models."""
        for model in [OpenAIModel.GPT_5_4, OpenAIModel.GPT_5_4]:
            LLMClientFactory.create_client(LLMProvider.OPENAI, model)

        assert mock_adapter.call_count == 2

    # @patch("src.client.factory.GeminiAdapter")
    # def test_create_client_gemini_different_models(self, mock_adapter):
    #     """Test creation of Gemini clients with different models."""
    #     for model in [GeminiModel.GEMINI_2_5_PRO, GeminiModel.GEMINI_2_5_FLASH]:
    #         LLMClientFactory.create_client(LLMProvider.GEMINI, model)
    #
    #     assert mock_adapter.call_count == 2

    @patch("src.client.factory.AnthropicAdapter")
    def test_create_client_anthropic(self, mock_adapter):
        """Test creation of Anthropic client."""
        LLMClientFactory.create_client(LLMProvider.ANTHROPIC, AnthropicModel.CLAUDE_SONNET_4_6)
        mock_adapter.assert_called_once_with(model=AnthropicModel.CLAUDE_SONNET_4_6)

    @patch("src.client.factory.AnthropicAdapter")
    def test_create_client_anthropic_different_models(self, mock_adapter):
        """Test creation of Anthropic clients with different models."""
        for model in [AnthropicModel.CLAUDE_SONNET_4_6, AnthropicModel.CLAUDE_SONNET_4_6]:
            LLMClientFactory.create_client(LLMProvider.ANTHROPIC, model)

        assert mock_adapter.call_count == 2

    def test_create_client_unknown_provider(self):
        """Test error handling for unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClientFactory.create_client("unknown_provider", "some-model")

    def test_create_client_invalid_model_for_provider(self):
        """Test error handling for invalid model for provider."""
        # Try to use an Anthropic model with OpenAI provider
        with pytest.raises(ValueError, match="Invalid model"):
            LLMClientFactory.create_client(LLMProvider.OPENAI, AnthropicModel.CLAUDE_SONNET_4_6)

        # Try to use an OpenAI model with Anthropic provider
        with pytest.raises(ValueError, match="Invalid model"):
            LLMClientFactory.create_client(LLMProvider.ANTHROPIC, OpenAIModel.GPT_5_4)

    def test_create_client_case_insensitive_provider(self):
        """Test that provider parameter is case-insensitive."""
        with patch("src.client.factory.OpenAIAdapter") as mock_adapter:
            LLMClientFactory.create_client("openai", OpenAIModel.GPT_5_4)
            mock_adapter.assert_called_once()

        with patch("src.client.factory.OpenAIAdapter") as mock_adapter:
            LLMClientFactory.create_client("OPENAI", OpenAIModel.GPT_5_4)
            mock_adapter.assert_called_once()

    @patch("src.client.factory.OpenAIAdapter")
    def test_create_client_returns_llm_client_interface(self, mock_adapter):
        """Test that created client implements LLMClient interface."""
        # Setup mock to return an instance that looks like LLMClient
        mock_instance = mock_adapter.return_value
        mock_instance.chat = lambda: None
        mock_instance.get_provider_name = lambda: LLMProvider.OPENAI
        mock_instance.get_model_name = lambda: OpenAIModel.GPT_5_4

        client = LLMClientFactory.create_client(LLMProvider.OPENAI, OpenAIModel.GPT_5_4)

        # Verify the client has the expected interface methods
        assert hasattr(client, "chat")
        assert hasattr(client, "get_provider_name")
        assert hasattr(client, "get_model_name")


class TestFactoryIntegration:
    """Integration tests for LLMClientFactory with actual adapters."""

    def test_create_openai_adapter_integration(self):
        """Test creating actual OpenAI adapter instance."""
        with patch("src.client.adapters.AsyncOpenAI"):
            client = LLMClientFactory.create_client(LLMProvider.OPENAI, OpenAIModel.GPT_5_4)
            assert isinstance(client, OpenAIAdapter)
            assert isinstance(client, LLMClient)
            assert client.get_provider_name() == LLMProvider.OPENAI
            assert client.get_model_name() == OpenAIModel.GPT_5_4

    # def test_create_gemini_adapter_integration(self):
    #     """Test creating actual Gemini adapter instance."""
    #     with patch("src.client.adapters.genai.Client"):
    #         client = LLMClientFactory.create_client(LLMProvider.GEMINI, GeminiModel.GEMINI_2_5_FLASH)
    #         assert isinstance(client, GeminiAdapter)
    #         assert isinstance(client, LLMClient)
    #         assert client.get_provider_name() == LLMProvider.GEMINI
    #         assert client.get_model_name() == GeminiModel.GEMINI_2_5_FLASH

    def test_multiple_clients_from_factory(self):
        """Test creating multiple different clients from factory."""
        with patch("src.client.adapters.AsyncOpenAI"), patch("src.client.adapters.AsyncAnthropicBedrock"):
            openai_client = LLMClientFactory.create_client(LLMProvider.OPENAI, OpenAIModel.GPT_5_4)
            anthropic_client = LLMClientFactory.create_client(LLMProvider.ANTHROPIC, AnthropicModel.CLAUDE_SONNET_4_6)

            # Verify they are different types
            assert type(openai_client) is not type(anthropic_client)
            assert isinstance(openai_client, OpenAIAdapter)
            assert isinstance(anthropic_client, AnthropicAdapter)

            # But both implement the same interface
            assert isinstance(openai_client, LLMClient)
            assert isinstance(anthropic_client, LLMClient)


class TestFactoryProviderModelsMapping:
    """Test the PROVIDER_MODELS class variable."""

    def test_provider_models_contains_all_providers(self):
        """Test that PROVIDER_MODELS contains all expected providers."""
        assert LLMProvider.OPENAI in LLMClientFactory.PROVIDER_MODELS
        # assert LLMProvider.GEMINI in LLMClientFactory.PROVIDER_MODELS

    def test_provider_models_openai_contains_models(self):
        """Test that OpenAI models are properly registered."""
        openai_models = LLMClientFactory.PROVIDER_MODELS[LLMProvider.OPENAI]
        assert OpenAIModel.GPT_5_4 in openai_models
        assert OpenAIModel.GPT_5_4 in openai_models
        # Check that it matches the enum
        assert openai_models == OpenAIModel.list_str()

    # def test_provider_models_gemini_contains_models(self):
    #     """Test that Gemini models are properly registered."""
    #     gemini_models = LLMClientFactory.PROVIDER_MODELS[LLMProvider.GEMINI]
    #     assert GeminiModel.GEMINI_2_5_PRO in gemini_models
    #     assert GeminiModel.GEMINI_2_5_FLASH in gemini_models
    #     # Check that it matches the enum
    #     assert gemini_models == GeminiModel.list_str()

    def test_provider_models_is_dict(self):
        """Test that PROVIDER_MODELS is a dictionary."""
        assert isinstance(LLMClientFactory.PROVIDER_MODELS, dict)

    def test_provider_models_values_are_lists(self):
        """Test that all values in PROVIDER_MODELS are lists."""
        for provider, models in LLMClientFactory.PROVIDER_MODELS.items():
            assert isinstance(models, list)
            assert len(models) > 0

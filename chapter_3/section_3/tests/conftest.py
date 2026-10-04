from unittest.mock import AsyncMock, MagicMock

import pytest
from src.model.model import CharacterPersonality, CharacterRequest, CharacterResponse, Gender


@pytest.fixture
def sample_character_request():
    """Fixture for a sample character request."""
    return CharacterRequest(
        gender=Gender.FEMALE,
        age=25,
        additional_instructions="謎めいた過去を持つ熟練の弓使いのキャラクターを作成してください。",
    )


@pytest.fixture
def sample_character_requests():
    """Fixture for multiple character requests."""
    return [
        CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="謎めいた過去を持つ熟練の弓使いのキャラクターを作成してください。",
        ),
        CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="贖罪を求める勇敢な騎士のキャラクターを設計してください。",
        ),
        CharacterRequest(
            gender=Gender.MALE,
            age=18,
            additional_instructions="自分の価値を証明したいと熱望する若い魔法使いのキャラクターを開発してください。",
        ),
    ]


@pytest.fixture
def sample_character_response():
    """Fixture for a sample character response."""
    return CharacterResponse(
        first_name="Aria",
        last_name="Moonwhisper",
        gender=Gender.FEMALE,
        age=25,
        personalities=[
            CharacterPersonality(
                short_personality="Mysterious",
                description="A skilled archer with a mysterious past who rarely speaks of her origins.",
            ),
            CharacterPersonality(
                short_personality="Determined",
                description="Shows unwavering focus when pursuing her goals.",
            ),
            CharacterPersonality(
                short_personality="Compassionate",
                description="Despite her reserved nature, she deeply cares for those in need.",
            ),
        ],
    )


@pytest.fixture
def mock_llmops_logger():
    """Fixture for a mock LLMOpsLogger."""
    logger = MagicMock()
    logger.track_llm_request = MagicMock()

    # Create a mock context manager
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value={})
    mock_context.__aexit__ = AsyncMock(return_value=None)

    logger.track_llm_request.return_value = mock_context

    return logger


@pytest.fixture
def mock_openai_client():
    """Fixture for a mock OpenAI client."""
    client = MagicMock()
    client.beta = MagicMock()
    client.beta.chat = MagicMock()
    client.beta.chat.completions = MagicMock()
    client.beta.chat.completions.parse = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Fixture for a mock Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.parse = AsyncMock()
    return client

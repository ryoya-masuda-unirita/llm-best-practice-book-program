"""Shared fixtures for testing."""

import shutil
import tempfile

import pytest
from src.model.model import CharacterPersonality, CharacterResponse, Gender


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_character_response():
    """Create a sample CharacterResponse for testing."""
    return CharacterResponse(
        first_name="太郎",
        last_name="山田",
        gender=Gender.MALE,
        age=30,
        personalities=[
            CharacterPersonality(short_personality="誠実", description="常に正直で、約束を守る信頼できる人物。"),
            CharacterPersonality(
                short_personality="勤勉", description="目標に向かって努力を惜しまず、計画的に物事を進めることができる。"
            ),
            CharacterPersonality(
                short_personality="思慮深い", description="行動する前に慎重に考え、状況を分析してから判断を下す。"
            ),
        ],
    )


@pytest.fixture
def sample_prompt():
    """Create a sample prompt for testing."""
    return [
        {"role": "system", "content": "You are a creative character generator."},
        {"role": "user", "content": "Generate a unique fictional character."},
    ]


@pytest.fixture
def mock_config(mocker):
    """Mock the config module."""
    mock_cfg = mocker.MagicMock()
    mock_cfg.llm_request_timeout = 10.0
    mock_cfg.cache_ttl = 3600
    return mock_cfg

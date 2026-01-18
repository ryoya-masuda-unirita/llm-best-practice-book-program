"""Pytest configuration and shared fixtures for tests."""

import pytest
from src.model.llm_as_a_judge_model import EvaluationCriterion, JudgeRequest, JudgeResponse
from src.model.model import CharacterPersonality, CharacterRequest, CharacterResponse, Gender


@pytest.fixture
def sample_character_request() -> CharacterRequest:
    """Sample character request for testing."""
    return CharacterRequest(
        gender=Gender.FEMALE,
        age=25,
        additional_instructions="Generate a wizard from a fantasy world.",
    )


@pytest.fixture
def sample_character_response() -> CharacterResponse:
    """Sample character response for testing."""
    return CharacterResponse(
        first_name="Elena",
        last_name="Stormweaver",
        gender=Gender.FEMALE,
        age=25,
        personalities=[
            CharacterPersonality(
                short_personality="Curious",
                description="Possesses an insatiable thirst for unknown magic and ancient knowledge. Always immersed in research of new spells.",
            ),
            CharacterPersonality(
                short_personality="Calm and Collected",
                description="Can make logical decisions without being shaken even in critical situations. Rarely swayed by emotions.",
            ),
            CharacterPersonality(
                short_personality="Secretive",
                description="Does not speak much about her past or true power. Opens up little by little only to those she trusts.",
            ),
        ],
    )


@pytest.fixture
def sample_judge_request(sample_character_response: CharacterResponse) -> JudgeRequest:
    """Sample judge request for testing."""
    return JudgeRequest(
        question="Generate a 25-year-old female wizard character from a fantasy world.",
        response=sample_character_response.model_dump_json(indent=2, ensure_ascii=False),
        context=None,
    )


@pytest.fixture
def sample_judge_response() -> JudgeResponse:
    """Sample judge response for testing."""
    return JudgeResponse(
        evaluations=[
            EvaluationCriterion(
                criterion_name="accuracy",
                score=4,
                reasoning="The specified age (25) and gender (female) are accurately reflected. The fantasy wizard setting is appropriately expressed.",
            ),
            EvaluationCriterion(
                criterion_name="comprehensiveness",
                score=5,
                reasoning="All elements including name, gender, age, and three personality traits are included, with both short and detailed descriptions.",
            ),
            EvaluationCriterion(
                criterion_name="clarity",
                score=4,
                reasoning="Each personality trait is clearly described and the character's individuality is easy to understand.",
            ),
        ],
        overall_score=4.33,
        summary="High-quality character generation that meets specified conditions and appropriately expresses the fantasy wizard concept.",
    )


@pytest.fixture
def low_quality_character_response() -> CharacterResponse:
    """Low quality character response for testing (missing required elements)."""
    return CharacterResponse(
        first_name="John",
        last_name="Smith",
        gender=Gender.MALE,
        age=30,
        personalities=[
            CharacterPersonality(
                short_personality="Normal",
                description="An ordinary person with no particular characteristics.",
            ),
            CharacterPersonality(
                short_personality="Normal",
                description="Average personality.",
            ),
            CharacterPersonality(
                short_personality="Normal",
                description="A regular person.",
            ),
        ],
    )


@pytest.fixture
def low_quality_judge_response() -> JudgeResponse:
    """Low quality judge response for testing (below threshold)."""
    return JudgeResponse(
        evaluations=[
            EvaluationCriterion(
                criterion_name="accuracy",
                score=2,
                reasoning="Generated a 30-year-old male generic character completely different from specified conditions (25-year-old female fantasy wizard).",
            ),
            EvaluationCriterion(
                criterion_name="comprehensiveness",
                score=3,
                reasoning="Required fields exist but fantasy elements are completely missing.",
            ),
            EvaluationCriterion(
                criterion_name="clarity",
                score=2,
                reasoning="All personality traits use vague expression 'Normal', showing no character individuality.",
            ),
        ],
        overall_score=2.33,
        summary="Low-quality generation result that does not meet specified conditions and lacks creativity.",
    )

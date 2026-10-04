"""Pytest fixtures for prompt profiler tests."""

from datetime import datetime, timezone

import pytest
from src.model.llm_as_a_judge_model import EvaluationCriterion, JudgeResponse
from src.model.model import CharacterPersonality, CharacterRequest, CharacterResponse, Gender
from src.model.profiler_metrics import AlertThreshold, MetricStatus, ProfilerMetrics


@pytest.fixture
def sample_character_request() -> CharacterRequest:
    return CharacterRequest(
        gender=Gender.FEMALE,
        age=25,
        additional_instructions="Generate a wizard from a fantasy world.",
    )


@pytest.fixture
def sample_character_response() -> CharacterResponse:
    return CharacterResponse(
        first_name="Luna",
        last_name="Starweaver",
        gender=Gender.FEMALE,
        age=25,
        personalities=[
            CharacterPersonality(
                short_personality="Curious",
                description="Luna possesses an insatiable curiosity about the arcane arts and ancient mysteries. She spends countless hours poring over dusty tomes and experimenting with new spells.",
            ),
            CharacterPersonality(
                short_personality="Compassionate",
                description="Despite her scholarly nature, Luna has a deep well of empathy for others. She often uses her magical abilities to help those in need, never expecting anything in return.",
            ),
            CharacterPersonality(
                short_personality="Determined",
                description="Once Luna sets her mind to a goal, nothing can deter her. Her determination has seen her through countless challenges and dangerous magical experiments.",
            ),
        ],
    )


@pytest.fixture
def low_quality_character_response() -> CharacterResponse:
    return CharacterResponse(
        first_name="X",
        last_name="Y",
        gender=Gender.MALE,
        age=50,
        personalities=[
            CharacterPersonality(
                short_personality="A",
                description="A",
            ),
            CharacterPersonality(
                short_personality="B",
                description="B",
            ),
            CharacterPersonality(
                short_personality="C",
                description="C",
            ),
        ],
    )


@pytest.fixture
def sample_judge_response() -> JudgeResponse:
    return JudgeResponse(
        evaluations=[
            EvaluationCriterion(
                criterion_name="accuracy",
                score=4,
                reasoning="The character meets the requested gender and age requirements with appropriate fantasy elements.",
            ),
            EvaluationCriterion(
                criterion_name="comprehensiveness",
                score=4,
                reasoning="All required fields are present including detailed personality descriptions.",
            ),
            EvaluationCriterion(
                criterion_name="clarity",
                score=5,
                reasoning="The response is well-structured and easy to understand.",
            ),
        ],
        overall_score=4.33,
        summary="A well-crafted fantasy character with rich personality traits.",
    )


@pytest.fixture
def low_quality_judge_response() -> JudgeResponse:
    return JudgeResponse(
        evaluations=[
            EvaluationCriterion(
                criterion_name="accuracy",
                score=2,
                reasoning="The character does not meet the gender and age requirements.",
            ),
            EvaluationCriterion(
                criterion_name="comprehensiveness",
                score=2,
                reasoning="Personality descriptions are too brief and lack detail.",
            ),
            EvaluationCriterion(
                criterion_name="clarity",
                score=3,
                reasoning="The structure is correct but content is minimal.",
            ),
        ],
        overall_score=2.33,
        summary="A poorly developed character that fails to meet requirements.",
    )


@pytest.fixture
def sample_profiler_metrics() -> ProfilerMetrics:
    return ProfilerMetrics(
        prompt_id="character_generation",
        request_id="test-request-001",
        prompt_name="Character Generation",
        latency_ms=1500.0,
        input_tokens=500,
        output_tokens=200,
        total_tokens=700,
        model="openai.gpt-5.4",
        provider="openai",
        status=MetricStatus.SUCCESS,
        status_code=200,
        quality_score=4.0,
        estimated_cost_usd=0.0004,
    )


@pytest.fixture
def sample_metrics_list() -> list[ProfilerMetrics]:
    base_time = datetime.now(timezone.utc)

    metrics = []
    for i in range(10):
        metrics.append(
            ProfilerMetrics(
                prompt_id="character_generation",
                request_id=f"test-request-{i:03d}",
                prompt_name="Character Generation",
                timestamp=(base_time).isoformat(),
                latency_ms=1000.0 + (i * 100),
                input_tokens=500 + (i * 10),
                output_tokens=200 + (i * 5),
                total_tokens=700 + (i * 15),
                model="openai.gpt-5.4",
                provider="openai",
                status=MetricStatus.SUCCESS if i < 9 else MetricStatus.ERROR,
                status_code=200 if i < 9 else 500,
                quality_score=3.0 + (i * 0.2) if i < 9 else None,
                estimated_cost_usd=0.0003 + (i * 0.0001),
            )
        )
    return metrics


@pytest.fixture
def mixed_prompt_metrics() -> list[ProfilerMetrics]:
    base_time = datetime.now(timezone.utc)

    metrics = []
    prompt_ids = ["prompt_a", "prompt_b", "prompt_c"]

    for i, prompt_id in enumerate(prompt_ids):
        for j in range(5):
            metrics.append(
                ProfilerMetrics(
                    prompt_id=prompt_id,
                    request_id=f"{prompt_id}-{j:03d}",
                    prompt_name=f"Prompt {prompt_id.upper()}",
                    timestamp=base_time.isoformat(),
                    latency_ms=1000.0 + (i * 500) + (j * 50),
                    input_tokens=500 + (i * 100),
                    output_tokens=200 + (j * 10),
                    total_tokens=700 + (i * 100) + (j * 10),
                    model="openai.gpt-5.4",
                    provider="openai",
                    status=MetricStatus.SUCCESS,
                    status_code=200,
                    quality_score=3.5 + (i * 0.3),
                    estimated_cost_usd=0.0005,
                )
            )
    return metrics


@pytest.fixture
def alert_thresholds() -> AlertThreshold:
    return AlertThreshold(
        latency_warning_ms=2000.0,
        latency_critical_ms=5000.0,
        latency_relative_warning=1.5,
        latency_relative_critical=2.0,
        token_warning=5000,
        token_critical=10000,
        quality_warning=3.0,
        quality_critical=2.0,
        cost_warning_usd=0.05,
        cost_critical_usd=0.2,
        success_rate_warning=0.95,
        success_rate_critical=0.90,
    )

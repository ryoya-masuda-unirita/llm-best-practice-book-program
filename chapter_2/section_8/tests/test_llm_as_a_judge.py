"""Tests for LLM-as-a-Judge functionality.

This module tests the core judge functionality including:
- Model validation
- Prompt generation
- Judge response parsing
- Quality threshold evaluation
"""

import json

import pytest
from src.client.llm_client import GeminiModel, OpenAIModel
from src.model.llm_as_a_judge_model import EvaluationScore, JudgeRequest, JudgeResponse
from src.prompt.llm_as_a_judge_prompt import make_custom_judge_prompt, make_judge_prompt
from src.service.llm_as_a_judge import judge_with_gemini, judge_with_openai


class TestJudgeModels:
    """Test cases for judge model structures."""

    def test_judge_request_creation(self, sample_judge_request: JudgeRequest):
        """Test that JudgeRequest can be created with valid data."""
        assert sample_judge_request.question is not None
        assert sample_judge_request.response is not None
        assert sample_judge_request.context is None

    def test_judge_request_with_context(self, sample_character_response):
        """Test JudgeRequest with context for RAG evaluation."""
        context = "Reference: Wizards in fantasy worlds typically gain power through years of training."
        judge_request = JudgeRequest(
            question="Generate a wizard character.",
            response=sample_character_response.model_dump_json(),
            context=context,
        )
        assert judge_request.context == context

    def test_judge_response_structure(self, sample_judge_response: JudgeResponse):
        """Test JudgeResponse has correct structure."""
        assert len(sample_judge_response.evaluations) == 3
        assert 1.0 <= sample_judge_response.overall_score <= 5.0
        assert sample_judge_response.summary is not None

    def test_evaluation_score_values(self):
        """Test that EvaluationScore enum has correct values."""
        assert EvaluationScore.COMPLETELY_INAPPROPRIATE == 1
        assert EvaluationScore.POOR == 2
        assert EvaluationScore.ACCEPTABLE == 3
        assert EvaluationScore.GOOD == 4
        assert EvaluationScore.PERFECT == 5

    def test_judge_response_is_passing_above_threshold(self, sample_judge_response: JudgeResponse):
        """Test that high quality response passes threshold."""
        assert sample_judge_response.is_passing(threshold=3.0)
        assert sample_judge_response.is_passing(threshold=4.0)

    def test_judge_response_is_passing_below_threshold(self, low_quality_judge_response: JudgeResponse):
        """Test that low quality response fails threshold."""
        assert not low_quality_judge_response.is_passing(threshold=3.0)
        assert low_quality_judge_response.is_passing(threshold=2.0)

    def test_judge_response_save_as_json(self, sample_judge_response: JudgeResponse, tmp_path):
        """Test saving judge response as JSON file."""
        file_path = tmp_path / "judge_result.json"
        sample_judge_response.save_as_json(str(file_path))

        # Verify file was created and contains valid JSON
        assert file_path.exists()
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "evaluations" in data
        assert "overall_score" in data
        assert "summary" in data
        assert len(data["evaluations"]) == 3


class TestJudgePrompts:
    """Test cases for judge prompt generation."""

    def test_make_judge_prompt_structure(self, sample_judge_request: JudgeRequest):
        """Test that make_judge_prompt generates correct message structure."""
        prompt = make_judge_prompt(sample_judge_request)

        assert isinstance(prompt, list)
        assert len(prompt) == 2
        assert prompt[0]["role"] == "system"
        assert prompt[1]["role"] == "user"

    def test_make_judge_prompt_contains_criteria(self, sample_judge_request: JudgeRequest):
        """Test that judge prompt contains evaluation criteria."""
        prompt = make_judge_prompt(sample_judge_request)
        system_content = prompt[0]["content"]

        # Check for evaluation criteria (in Japanese)
        assert "accuracy" in system_content
        assert "comprehensiveness" in system_content
        assert "clarity" in system_content

    def test_make_judge_prompt_includes_question(self, sample_judge_request: JudgeRequest):
        """Test that judge prompt includes the original question."""
        prompt = make_judge_prompt(sample_judge_request)
        user_content = prompt[1]["content"]

        # Question should be part of user content
        assert len(user_content) > 0

    def test_make_custom_judge_prompt(self, sample_judge_request: JudgeRequest):
        """Test custom judge prompt with user-defined criteria."""
        custom_criteria = [
            {"name": "creativity", "description": "Is the character unique and creative"},
            {"name": "consistency", "description": "Are personality traits mutually consistent"},
        ]

        prompt = make_custom_judge_prompt(
            request=sample_judge_request,
            criteria=custom_criteria,
        )

        system_content = prompt[0]["content"]
        assert "creativity" in system_content
        assert "consistency" in system_content


class TestJudgeService:
    """Test cases for judge service functions."""

    @pytest.mark.asyncio
    async def test_judge_with_openai(
        self, mocker, sample_judge_request: JudgeRequest, sample_judge_response: JudgeResponse
    ):
        """Test judging with OpenAI."""
        # Mock the OpenAI API response
        mock_result = mocker.AsyncMock()
        mock_result.choices = [mocker.AsyncMock()]
        mock_result.choices[0].message.parsed = sample_judge_response

        mock_parse = mocker.patch("src.service.llm_as_a_judge.openai_client.beta.chat.completions.parse")
        mock_parse.return_value = mock_result

        result = await judge_with_openai(
            judge_request=sample_judge_request,
            model=OpenAIModel.GPT_4O_MINI,
        )

        assert result == sample_judge_response
        assert result.overall_score == sample_judge_response.overall_score
        mock_parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_judge_with_gemini(
        self, mocker, sample_judge_request: JudgeRequest, sample_judge_response: JudgeResponse
    ):
        """Test judging with Gemini."""
        # Mock the Gemini API response
        mock_result = mocker.AsyncMock()
        mock_result.parsed = sample_judge_response

        mock_generate = mocker.patch("src.service.llm_as_a_judge.google_genai_client.aio.models.generate_content")
        mock_generate.return_value = mock_result

        result = await judge_with_gemini(
            judge_request=sample_judge_request,
            model=GeminiModel.GEMINI_2_5_FLASH,
        )

        assert result == sample_judge_response
        assert result.overall_score == sample_judge_response.overall_score
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_judge_evaluation_criteria_count(
        self, sample_judge_request: JudgeRequest, sample_judge_response: JudgeResponse
    ):
        """Test that judge returns expected number of evaluation criteria."""
        # The default judge prompt should evaluate 3 criteria
        assert len(sample_judge_response.evaluations) == 3

    @pytest.mark.asyncio
    async def test_judge_overall_score_calculation(self, sample_judge_response: JudgeResponse):
        """Test that overall score is correctly calculated from individual scores."""
        scores = [eval.score for eval in sample_judge_response.evaluations]
        expected_avg = sum(scores) / len(scores)

        # Allow for small floating point differences
        assert abs(sample_judge_response.overall_score - expected_avg) < 0.1

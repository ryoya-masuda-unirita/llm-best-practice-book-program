"""Prompt unit tests using LLM-as-a-Judge pattern."""

import json

import pytest
from src.client.llm_client import OpenAIModel
from src.model.llm_as_a_judge_model import JudgeRequest
from src.model.model import CharacterRequest, CharacterResponse, Gender
from src.prompt.llm_as_a_judge_prompt import make_custom_judge_prompt
from src.prompt.prompt import make_prompt
from src.service.llm_as_a_judge import judge_with_openai
from src.service.request_llm import request_with_judge


class TestCharacterPromptStructure:
    """Test that character generation prompts produce correctly structured outputs."""

    def test_prompt_includes_required_fields(self, sample_character_request: CharacterRequest):
        """Test that prompt specifies all required output fields."""
        prompt = make_prompt(sample_character_request)
        system_content = prompt[0]["content"]

        assert "first_name" in system_content
        assert "last_name" in system_content
        assert "gender" in system_content
        assert "age" in system_content
        assert "personalities" in system_content

    def test_prompt_specifies_personality_count(self, sample_character_request: CharacterRequest):
        """Test that prompt requires exactly 3 personality traits."""
        prompt = make_prompt(sample_character_request)
        system_content = prompt[0]["content"]

        assert "3" in system_content

    def test_prompt_enforces_json_format(self, sample_character_request: CharacterRequest):
        """Test that prompt requires JSON output format."""
        prompt = make_prompt(sample_character_request)
        system_content = prompt[0]["content"]

        assert "JSON" in system_content

    def test_prompt_includes_request_parameters(self, sample_character_request: CharacterRequest):
        """Test that prompt includes user-specified parameters."""
        prompt = make_prompt(sample_character_request)
        system_content = prompt[0]["content"]

        assert sample_character_request.gender.value in system_content
        assert str(sample_character_request.age) in system_content


class TestCharacterOutputQuality:
    """Test output quality using LLM-as-a-Judge."""

    @pytest.mark.asyncio
    async def test_generated_character_meets_quality_threshold(
        self, mocker, sample_character_response: CharacterResponse, sample_judge_response
    ):
        """Test that generated character meets minimum quality threshold using judge."""
        judge_request = JudgeRequest(
            question="Generate a 25-year-old female wizard character from a fantasy world.",
            response=sample_character_response.model_dump_json(indent=2, ensure_ascii=False),
            context=None,
        )

        mock_result = mocker.AsyncMock()
        mock_result.choices = [mocker.AsyncMock()]
        mock_result.choices[0].message.parsed = sample_judge_response

        mock_parse = mocker.patch("src.service.llm_as_a_judge.openai_client.beta.chat.completions.parse")
        mock_parse.return_value = mock_result

        judge_response = await judge_with_openai(
            judge_request=judge_request,
            model=OpenAIModel.GPT_4O_MINI,
        )

        assert judge_response.is_passing(threshold=3.0), "Generated character should meet minimum quality threshold"
        assert judge_response.overall_score >= 4.0, "Generated character should achieve good quality score"

    @pytest.mark.asyncio
    async def test_low_quality_output_detected(
        self, mocker, low_quality_character_response: CharacterResponse, low_quality_judge_response
    ):
        """Test that low quality outputs are properly detected by judge."""
        judge_request = JudgeRequest(
            question="Generate a 25-year-old female wizard character from a fantasy world.",
            response=low_quality_character_response.model_dump_json(indent=2, ensure_ascii=False),
            context=None,
        )

        mock_result = mocker.AsyncMock()
        mock_result.choices = [mocker.AsyncMock()]
        mock_result.choices[0].message.parsed = low_quality_judge_response

        mock_parse = mocker.patch("src.service.llm_as_a_judge.openai_client.beta.chat.completions.parse")
        mock_parse.return_value = mock_result

        judge_response = await judge_with_openai(
            judge_request=judge_request,
            model=OpenAIModel.GPT_4O_MINI,
        )

        assert not judge_response.is_passing(threshold=3.0), "Low quality output should fail quality threshold"
        assert judge_response.overall_score < 3.0, "Low quality output should have low score"


class TestRepresentativeInputs:
    """Test prompt behavior with representative input cases."""

    @pytest.mark.asyncio
    async def test_young_female_fantasy_character(self):
        """Test young female fantasy character (primary use case)."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="Generate a wizard from a fantasy world.",
        )
        prompt = make_prompt(request)

        assert len(prompt) == 2
        assert "female" in prompt[0]["content"]
        assert "25" in prompt[0]["content"]

    @pytest.mark.asyncio
    async def test_elderly_male_realistic_character(self):
        """Test elderly male realistic character (different demographics)."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=75,
            additional_instructions="Generate a retired teacher from the modern world.",
        )
        prompt = make_prompt(request)

        system_content = prompt[0]["content"]
        assert "male" in system_content
        assert "75" in system_content

    @pytest.mark.asyncio
    async def test_young_adult_no_additional_instructions(self):
        """Test young adult with no additional instructions (minimal input)."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=20,
            additional_instructions="",
        )
        prompt = make_prompt(request)

        assert len(prompt) == 2
        assert prompt[0]["role"] == "system"
        assert prompt[1]["role"] == "user"


class TestCustomJudgeCriteria:
    """Test using custom evaluation criteria for domain-specific requirements."""

    @pytest.mark.asyncio
    async def test_fantasy_character_creativity(self, sample_character_response: CharacterResponse):
        """Test fantasy character creativity using custom criteria."""
        custom_criteria = [
            {
                "name": "creativity",
                "description": "Is the character unique and creative, not using common tropes",
            },
            {
                "name": "fantasy_elements",
                "description": "Does it contain magic or special abilities fitting the fantasy world",
            },
            {
                "name": "consistency",
                "description": "Are personality traits and settings mutually consistent",
            },
        ]

        judge_request = JudgeRequest(
            question="Generate a wizard character from a fantasy world.",
            response=sample_character_response.model_dump_json(indent=2, ensure_ascii=False),
        )

        prompt = make_custom_judge_prompt(request=judge_request, criteria=custom_criteria)

        system_content = prompt[0]["content"]
        assert "creativity" in system_content
        assert "fantasy_elements" in system_content
        assert "consistency" in system_content


class TestRegressionDetection:
    """Tests for detecting quality regressions when prompts are modified."""

    @pytest.mark.asyncio
    async def test_output_contains_all_required_fields(self, sample_character_response: CharacterResponse):
        """Verify all required fields are present in output."""
        response_dict = sample_character_response.model_dump()

        assert "first_name" in response_dict
        assert "last_name" in response_dict
        assert "gender" in response_dict
        assert "age" in response_dict
        assert "personalities" in response_dict

        assert isinstance(response_dict["personalities"], list)
        assert len(response_dict["personalities"]) == 3

    @pytest.mark.asyncio
    async def test_personality_traits_have_descriptions(self, sample_character_response: CharacterResponse):
        """Verify personality traits include both short and detailed descriptions."""
        for personality in sample_character_response.personalities:
            assert personality.short_personality is not None
            assert len(personality.short_personality) > 0
            assert personality.description is not None
            assert len(personality.description) > 0
            assert len(personality.description) > len(personality.short_personality)

    @pytest.mark.asyncio
    async def test_output_is_valid_json_serializable(self, sample_character_response: CharacterResponse):
        """Verify output can be serialized to valid JSON."""
        json_output = sample_character_response.model_dump_json(indent=2, ensure_ascii=False)

        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_generated_names_are_not_empty(self, sample_character_response: CharacterResponse):
        """Verify generated names are non-empty strings."""
        assert len(sample_character_response.first_name) > 0
        assert len(sample_character_response.last_name) > 0
        assert sample_character_response.first_name != ""
        assert sample_character_response.last_name != ""

    @pytest.mark.asyncio
    async def test_age_matches_requested_age(self, sample_character_response: CharacterResponse):
        """Verify output age matches requested age."""
        assert sample_character_response.age == 25

    @pytest.mark.asyncio
    async def test_gender_matches_requested_gender(self, sample_character_response: CharacterResponse):
        """Verify output gender matches requested gender."""
        assert sample_character_response.gender == Gender.FEMALE


class TestEndToEndWithJudge:
    """End-to-end tests combining character generation and judgment."""

    @pytest.mark.asyncio
    async def test_full_generation_and_evaluation_workflow(self):
        """Full workflow test: Generate character and evaluate with judge."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="Generate a wizard from a fantasy world.",
        )

        character_response, judge_response = await request_with_judge(
            character_request=request,
            model=OpenAIModel.GPT_4O_MINI,
            provider="openai",
        )

        assert character_response is not None
        assert character_response.gender == Gender.FEMALE
        assert character_response.age == 25
        assert len(character_response.personalities) == 3

        assert judge_response is not None
        assert judge_response.overall_score >= 3.0, "Generated character should meet quality threshold"
        assert len(judge_response.evaluations) == 3

    @pytest.mark.asyncio
    async def test_elderly_male_realistic_character_workflow(self):
        """Full workflow test: Generate elderly male realistic character and evaluate."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=75,
            additional_instructions="Generate a retired teacher from the modern world.",
        )

        character_response, judge_response = await request_with_judge(
            character_request=request,
            model=OpenAIModel.GPT_4O_MINI,
            provider="openai",
        )

        assert character_response is not None
        assert character_response.gender == Gender.MALE
        assert character_response.age == 75
        assert len(character_response.personalities) == 3
        assert len(character_response.first_name) > 0
        assert len(character_response.last_name) > 0

        assert judge_response is not None
        assert judge_response.overall_score >= 3.0, "Generated character should meet quality threshold"
        assert len(judge_response.evaluations) == 3
        for evaluation in judge_response.evaluations:
            assert evaluation.score >= 1
            assert evaluation.score <= 5

    @pytest.mark.asyncio
    async def test_minimal_instructions_workflow(self):
        """Full workflow test: Generate character with minimal instructions."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=30,
            additional_instructions="",
        )

        character_response, judge_response = await request_with_judge(
            character_request=request,
            model=OpenAIModel.GPT_4O_MINI,
            provider="openai",
        )

        assert character_response is not None
        assert character_response.gender == Gender.FEMALE
        assert character_response.age == 30
        assert len(character_response.personalities) == 3

        for personality in character_response.personalities:
            assert len(personality.short_personality) > 0
            assert len(personality.description) > 0
            assert len(personality.description) > len(personality.short_personality)

        assert judge_response is not None
        assert judge_response.overall_score >= 2.5, (
            "Even with minimal instructions, should generate acceptable character"
        )
        assert len(judge_response.evaluations) == 3

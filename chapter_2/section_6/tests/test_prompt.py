"""Comprehensive tests for prompt.py module."""

import json

import pytest
from src.model.model import CharacterRequest, CharacterResponse, Gender
from src.prompt.prompt import _template_engine, make_prompt
from src.service.template_engine import TemplateValidationError


class TestMakePrompt:
    """Tests for make_prompt function."""

    def test_make_prompt_with_male_character(self):
        """Test make_prompt generates correct prompt for male character."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="This character is a detective.",
        )

        messages = make_prompt(request)

        assert isinstance(messages, list)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "male" in messages[1]["content"]
        assert "30" in messages[1]["content"]
        assert "detective" in messages[1]["content"]

    def test_make_prompt_with_female_character(self):
        """Test make_prompt generates correct prompt for female character."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="This character is an artist.",
        )

        messages = make_prompt(request)

        assert isinstance(messages, list)
        assert len(messages) == 2
        assert "female" in messages[1]["content"]
        assert "25" in messages[1]["content"]
        assert "artist" in messages[1]["content"]

    def test_make_prompt_without_additional_instructions(self):
        """Test make_prompt with None additional_instructions."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=40,
            additional_instructions=None,
        )

        messages = make_prompt(request)

        assert isinstance(messages, list)
        assert len(messages) == 2
        assert "male" in messages[1]["content"]
        assert "40" in messages[1]["content"]

    def test_make_prompt_with_empty_additional_instructions(self):
        """Test make_prompt with empty string additional_instructions."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=35,
            additional_instructions="",
        )

        messages = make_prompt(request)

        assert isinstance(messages, list)
        assert len(messages) == 2
        assert "female" in messages[1]["content"]
        assert "35" in messages[1]["content"]

    def test_make_prompt_includes_response_schema(self):
        """Test that make_prompt includes the response schema in system prompt."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Test",
        )

        messages = make_prompt(request)
        system_content = messages[0]["content"]

        assert "first_name" in system_content
        assert "last_name" in system_content
        assert "gender" in system_content
        assert "age" in system_content
        assert "personalities" in system_content

    def test_make_prompt_response_schema_is_valid_json(self):
        """Test that the response schema embedded in prompt is valid JSON."""
        CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Test",
        )

        params = CharacterResponse.detailed_model()
        response_schema = json.dumps(params, indent=2, ensure_ascii=False)

        parsed = json.loads(response_schema)
        assert isinstance(parsed, dict)
        assert "first_name" in parsed
        assert "last_name" in parsed
        assert "gender" in parsed
        assert "age" in parsed
        assert "personalities" in parsed

    def test_make_prompt_with_minimum_age(self):
        """Test make_prompt with minimum valid age (0)."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=0,
            additional_instructions="Newborn character",
        )

        messages = make_prompt(request)
        assert "0" in messages[1]["content"]

    def test_make_prompt_with_maximum_age(self):
        """Test make_prompt with maximum valid age (100)."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=100,
            additional_instructions="Centenarian character",
        )

        messages = make_prompt(request)
        assert "100" in messages[1]["content"]

    def test_make_prompt_with_special_characters_in_instructions(self):
        """Test make_prompt handles special characters in additional_instructions."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=28,
            additional_instructions="Character with special chars: こんにちは! 🎉 <>&",
        )

        messages = make_prompt(request)
        assert "こんにちは! 🎉 <>&" in messages[1]["content"]

    def test_make_prompt_with_long_additional_instructions(self):
        """Test make_prompt handles long additional_instructions."""
        long_instruction = "This is a very long instruction. " * 50
        request = CharacterRequest(
            gender=Gender.MALE,
            age=45,
            additional_instructions=long_instruction,
        )

        messages = make_prompt(request)
        assert long_instruction in messages[1]["content"]

    def test_make_prompt_with_multiline_additional_instructions(self):
        """Test make_prompt handles multiline additional_instructions."""
        multiline_instruction = """This character is complex:
        - Line 1: trait one
        - Line 2: trait two
        - Line 3: trait three"""

        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=32,
            additional_instructions=multiline_instruction,
        )

        messages = make_prompt(request)
        assert "trait one" in messages[1]["content"]
        assert "trait two" in messages[1]["content"]
        assert "trait three" in messages[1]["content"]


class TestMakePromptWithMocking:
    """Tests for make_prompt with mocking to isolate behavior."""

    def test_make_prompt_calls_template_engine_correctly(self, mocker):
        """Test that make_prompt calls template engine with correct parameters."""
        mock_render = mocker.patch.object(
            _template_engine,
            "render_prompt_messages",
            return_value=[
                {"role": "system", "content": "mocked system"},
                {"role": "user", "content": "mocked user"},
            ],
        )

        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Test instruction",
        )

        result = make_prompt(request)

        assert mock_render.called
        assert mock_render.call_count == 1

        call_args = mock_render.call_args
        assert call_args.kwargs["template_name"] == "character_generation.yaml"
        assert call_args.kwargs["validate"] is True

        variables = call_args.kwargs["variables"]
        assert variables["gender"] == "male"
        assert variables["age"] == 30
        assert variables["additional_instructions"] == "Test instruction"
        assert "response_schema" in variables

        assert result == [
            {"role": "system", "content": "mocked system"},
            {"role": "user", "content": "mocked user"},
        ]

    def test_make_prompt_handles_template_validation_error(self, mocker):
        """Test that make_prompt propagates TemplateValidationError."""
        mocker.patch.object(
            _template_engine,
            "render_prompt_messages",
            side_effect=TemplateValidationError("Missing variables"),
        )

        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="Test",
        )

        with pytest.raises(TemplateValidationError) as exc_info:
            make_prompt(request)
        assert "Missing variables" in str(exc_info.value)

    def test_make_prompt_converts_gender_enum_to_value(self, mocker):
        """Test that gender enum is correctly converted to string value."""
        mock_render = mocker.patch.object(
            _template_engine,
            "render_prompt_messages",
            return_value=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
        )

        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=28,
            additional_instructions="",
        )

        make_prompt(request)

        variables = mock_render.call_args.kwargs["variables"]
        assert variables["gender"] == "female"
        assert isinstance(variables["gender"], str)

    def test_make_prompt_handles_none_additional_instructions(self, mocker):
        """Test that None additional_instructions is converted to empty string."""
        mock_render = mocker.patch.object(
            _template_engine,
            "render_prompt_messages",
            return_value=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
        )

        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions=None,
        )

        make_prompt(request)

        variables = mock_render.call_args.kwargs["variables"]
        assert variables["additional_instructions"] == ""

    def test_make_prompt_preserves_non_none_additional_instructions(self, mocker):
        """Test that non-None additional_instructions is preserved."""
        mock_render = mocker.patch.object(
            _template_engine,
            "render_prompt_messages",
            return_value=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
        )

        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Keep this",
        )

        make_prompt(request)

        variables = mock_render.call_args.kwargs["variables"]
        assert variables["additional_instructions"] == "Keep this"


class TestCharacterResponseIntegration:
    """Integration tests with CharacterResponse model."""

    def test_detailed_model_structure(self):
        """Test that detailed_model returns expected structure."""
        detailed = CharacterResponse.detailed_model()

        assert isinstance(detailed, dict)
        assert "first_name" in detailed
        assert "last_name" in detailed
        assert "gender" in detailed
        assert "age" in detailed
        assert "personalities" in detailed
        assert isinstance(detailed["personalities"], list)
        assert len(detailed["personalities"]) == 3

        for i, personality in enumerate(detailed["personalities"]):
            assert "short_personality" in personality
            assert "description" in personality
            assert f"personality {i + 1}" in personality["short_personality"]

    def test_detailed_model_serializable_to_json(self):
        """Test that detailed_model output can be serialized to JSON."""
        detailed = CharacterResponse.detailed_model()
        json_str = json.dumps(detailed, ensure_ascii=False)

        parsed = json.loads(json_str)
        assert parsed == detailed

    def test_make_prompt_uses_detailed_model(self, mocker):
        """Test that make_prompt uses CharacterResponse.detailed_model."""
        mock_detailed = mocker.patch.object(CharacterResponse, "detailed_model", return_value={"mocked": "schema"})

        mock_render = mocker.patch.object(
            _template_engine,
            "render_prompt_messages",
            return_value=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
        )

        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Test",
        )

        make_prompt(request)

        assert mock_detailed.called

        variables = mock_render.call_args.kwargs["variables"]
        assert "response_schema" in variables
        schema_dict = json.loads(variables["response_schema"])
        assert schema_dict == {"mocked": "schema"}


class TestPromptEdgeCases:
    """Edge case tests for prompt generation."""

    def test_make_prompt_return_type(self):
        """Test that make_prompt returns the correct type."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Test",
        )

        result = make_prompt(request)

        assert isinstance(result, list)
        for message in result:
            assert isinstance(message, dict)
            assert "role" in message
            assert "content" in message
            assert isinstance(message["role"], str)
            assert isinstance(message["content"], str)

    def test_make_prompt_system_message_contains_instructions(self):
        """Test that system message contains character generation instructions."""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="Test",
        )

        messages = make_prompt(request)
        system_content = messages[0]["content"]

        assert "キャラクター" in system_content or "character" in system_content.lower()

    def test_make_prompt_is_deterministic(self):
        """Test that make_prompt produces same output for same input."""
        request = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Same request",
        )

        result1 = make_prompt(request)
        result2 = make_prompt(request)

        assert result1 == result2

    def test_make_prompt_with_different_requests_produces_different_outputs(self):
        """Test that different requests produce different prompts."""
        request1 = CharacterRequest(
            gender=Gender.MALE,
            age=30,
            additional_instructions="Detective",
        )

        request2 = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="Artist",
        )

        result1 = make_prompt(request1)
        result2 = make_prompt(request2)

        assert result1[1]["content"] != result2[1]["content"]
        assert "30" in result1[1]["content"]
        assert "25" in result2[1]["content"]
        assert "Detective" in result1[1]["content"]
        assert "Artist" in result2[1]["content"]

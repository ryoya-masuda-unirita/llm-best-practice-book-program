"""Comprehensive tests for TemplateEngine class."""

import pytest
import yaml
from jinja2 import TemplateNotFound
from src.service.template_engine import TemplateEngine, TemplateValidationError


class TestTemplateEngineInitialization:
    """Tests for TemplateEngine initialization."""

    def test_init_with_existing_directory(self, temp_template_dir):
        """Test initialization with a valid template directory."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        assert engine.template_dir == temp_template_dir
        assert engine.env is not None

    def test_init_with_nonexistent_directory(self, tmp_path):
        """Test initialization with non-existent directory raises error."""
        nonexistent_dir = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError) as exc_info:
            TemplateEngine(template_dir=nonexistent_dir)
        assert "Template directory not found" in str(exc_info.value)

    def test_init_with_string_path(self, temp_template_dir):
        """Test initialization with string path instead of Path object."""
        engine = TemplateEngine(template_dir=str(temp_template_dir))
        assert engine.template_dir.exists()


class TestGetTemplateVariables:
    """Tests for get_template_variables method."""

    def test_get_variables_from_simple_template(self, temp_template_dir):
        """Test extracting variables from a simple template."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = engine.get_template_variables("simple.yaml")
        assert variables == {"name"}

    def test_get_variables_from_template_with_loop(self, temp_template_dir):
        """Test extracting variables from template with loops."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = engine.get_template_variables("with_loop.yaml")
        assert variables == {"items"}

    def test_get_variables_from_template_with_conditional(self, temp_template_dir):
        """Test extracting variables from template with conditionals."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = engine.get_template_variables("with_conditional.yaml")
        assert variables == {"required", "optional"}

    def test_get_variables_from_multi_var_template(self, temp_template_dir):
        """Test extracting variables from template with multiple variables."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = engine.get_template_variables("multi_var.yaml")
        assert variables == {"name", "age", "city", "role"}

    def test_get_variables_from_nonexistent_template(self, temp_template_dir):
        """Test that nonexistent template raises TemplateNotFound."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        with pytest.raises(TemplateNotFound) as exc_info:
            engine.get_template_variables("nonexistent.yaml")
        assert "Template not found" in str(exc_info.value)


class TestValidateVariables:
    """Tests for validate_variables method."""

    def test_validate_with_all_required_variables(self, temp_template_dir):
        """Test validation passes when all required variables are provided."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"name": "Alice"}
        # Should not raise any exception
        engine.validate_variables("simple.yaml", variables)

    def test_validate_with_missing_variables(self, temp_template_dir):
        """Test validation fails when required variables are missing."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {}  # Missing 'name'
        with pytest.raises(TemplateValidationError) as exc_info:
            engine.validate_variables("simple.yaml", variables)
        assert "Missing required variables" in str(exc_info.value)
        assert "name" in str(exc_info.value)

    def test_validate_with_extra_variables(self, temp_template_dir):
        """Test validation passes when extra variables are provided."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"name": "Alice", "extra": "value"}
        # Should not raise - extra variables are OK
        engine.validate_variables("simple.yaml", variables)

    def test_validate_multi_var_template_partial_variables(self, temp_template_dir):
        """Test validation fails when only some variables are provided."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"name": "Alice", "age": 30}  # Missing 'city' and 'role'
        with pytest.raises(TemplateValidationError) as exc_info:
            engine.validate_variables("multi_var.yaml", variables)
        assert "city" in str(exc_info.value)
        assert "role" in str(exc_info.value)


class TestRenderTemplate:
    """Tests for render_template method."""

    def test_render_simple_template(self, temp_template_dir):
        """Test rendering a simple template."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"name": "Alice"}
        result = engine.render_template("simple.yaml", variables)

        assert isinstance(result, dict)
        assert result["system_prompt"] == "You are a helpful assistant."
        assert result["user_prompt"] == "Hello Alice!"

    def test_render_template_with_loop(self, temp_template_dir):
        """Test rendering template with loops."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"items": ["apple", "banana", "cherry"]}
        result = engine.render_template("with_loop.yaml", variables)

        assert "apple" in result["user_prompt"]
        assert "banana" in result["user_prompt"]
        assert "cherry" in result["user_prompt"]

    def test_render_template_with_conditional_true(self, temp_template_dir):
        """Test rendering template with conditional (condition is true)."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"required": "value", "optional": "extra"}
        result = engine.render_template("with_conditional.yaml", variables)

        assert "Required: value" in result["user_prompt"]
        assert "Optional: extra" in result["user_prompt"]

    def test_render_template_with_conditional_false(self, temp_template_dir):
        """Test rendering template with conditional (condition is false)."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"required": "value"}
        result = engine.render_template("with_conditional.yaml", variables, validate=False)

        assert "Required: value" in result["user_prompt"]
        assert "Optional:" not in result["user_prompt"]

    def test_render_template_with_validation_enabled(self, temp_template_dir):
        """Test that validation is enforced when enabled."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {}  # Missing required 'name'

        with pytest.raises(TemplateValidationError):
            engine.render_template("simple.yaml", variables, validate=True)

    def test_render_template_with_validation_disabled(self, temp_template_dir):
        """Test that validation can be disabled."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        # With validation disabled, missing variables are rendered as empty strings
        variables = {}

        # With validation disabled, Jinja2 renders undefined variables as empty strings
        # So this should succeed (no exception) but the variable will be empty
        result = engine.render_template("simple.yaml", variables, validate=False)

        # The template has {{ name }}, which will be rendered as empty string
        assert result["user_prompt"] == "Hello !"

    def test_render_multi_var_template(self, temp_template_dir):
        """Test rendering template with multiple variables."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"name": "Alice", "age": 30, "city": "Tokyo", "role": "data scientist"}
        result = engine.render_template("multi_var.yaml", variables)

        assert result["system_prompt"] == "You are a data scientist."
        assert "Alice" in result["user_prompt"]
        assert "30" in result["user_prompt"]
        assert "Tokyo" in result["user_prompt"]


class TestRenderPromptMessages:
    """Tests for render_prompt_messages method."""

    def test_render_prompt_messages_default_keys(self, temp_template_dir):
        """Test rendering template to message format with default keys."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"name": "Alice"}
        messages = engine.render_prompt_messages("simple.yaml", variables)

        assert isinstance(messages, list)
        assert len(messages) == 2

        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."

        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello Alice!"

    def test_render_prompt_messages_custom_keys(self, temp_template_dir, tmp_path):
        """Test rendering with custom system/user keys."""
        # Create a template with custom keys
        templates_dir = tmp_path / "custom_templates"
        templates_dir.mkdir()

        custom_template = {
            "custom_system": "System message",
            "custom_user": "User message",
        }
        (templates_dir / "custom.yaml").write_text(yaml.dump(custom_template))

        engine = TemplateEngine(template_dir=templates_dir)
        messages = engine.render_prompt_messages(
            "custom.yaml",
            {},
            system_key="custom_system",
            user_key="custom_user",
            validate=False,
        )

        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System message"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User message"

    def test_render_prompt_messages_missing_system_key(self, temp_template_dir, tmp_path):
        """Test that missing system_prompt key raises error."""
        # Create template without system_prompt
        templates_dir = tmp_path / "incomplete_templates"
        templates_dir.mkdir()

        incomplete_template = {"user_prompt": "Only user"}
        (templates_dir / "incomplete.yaml").write_text(yaml.dump(incomplete_template))

        engine = TemplateEngine(template_dir=templates_dir)
        with pytest.raises(TemplateValidationError) as exc_info:
            engine.render_prompt_messages("incomplete.yaml", {}, validate=False)
        assert "Template missing key: system_prompt" in str(exc_info.value)

    def test_render_prompt_messages_missing_user_key(self, temp_template_dir, tmp_path):
        """Test that missing user_prompt key raises error."""
        # Create template without user_prompt
        templates_dir = tmp_path / "incomplete_templates2"
        templates_dir.mkdir()

        incomplete_template = {"system_prompt": "Only system"}
        (templates_dir / "incomplete.yaml").write_text(yaml.dump(incomplete_template))

        engine = TemplateEngine(template_dir=templates_dir)
        with pytest.raises(TemplateValidationError) as exc_info:
            engine.render_prompt_messages("incomplete.yaml", {}, validate=False)
        assert "Template missing key: user_prompt" in str(exc_info.value)

    def test_render_prompt_messages_with_validation(self, temp_template_dir):
        """Test that validation is enforced in render_prompt_messages."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {}  # Missing required 'name'

        with pytest.raises(TemplateValidationError) as exc_info:
            engine.render_prompt_messages("simple.yaml", variables, validate=True)
        assert "Missing required variables" in str(exc_info.value)

    def test_render_prompt_messages_complex_template(self, temp_template_dir):
        """Test rendering complex template with multiple variables and loops."""
        engine = TemplateEngine(template_dir=temp_template_dir)
        variables = {"items": ["apple", "banana", "cherry"]}
        messages = engine.render_prompt_messages("with_loop.yaml", variables)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "apple" in messages[1]["content"]
        assert "banana" in messages[1]["content"]
        assert "cherry" in messages[1]["content"]


class TestTemplateEngineEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_template_directory(self, tmp_path):
        """Test engine works with empty template directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        engine = TemplateEngine(template_dir=empty_dir)
        assert engine.env is not None

    def test_template_with_special_characters(self, tmp_path):
        """Test template with special characters in variables."""
        templates_dir = tmp_path / "special"
        templates_dir.mkdir()

        special_template = {
            "system_prompt": "System",
            "user_prompt": "Special chars: {{ text }}",
        }
        (templates_dir / "special.yaml").write_text(yaml.dump(special_template))

        engine = TemplateEngine(template_dir=templates_dir)
        variables = {"text": "こんにちは! 🎉 <>&"}
        messages = engine.render_prompt_messages("special.yaml", variables)

        assert "こんにちは! 🎉 <>&" in messages[1]["content"]

    def test_template_with_none_value(self, tmp_path):
        """Test template with None as variable value."""
        templates_dir = tmp_path / "none_test"
        templates_dir.mkdir()

        template = {
            "system_prompt": "System",
            "user_prompt": "Value: {{ value }}",
        }
        (templates_dir / "none.yaml").write_text(yaml.dump(template))

        engine = TemplateEngine(template_dir=templates_dir)
        variables = {"value": None}
        messages = engine.render_prompt_messages("none.yaml", variables)

        # Jinja2 renders None as empty string
        assert messages[1]["content"] == "Value: None" or messages[1]["content"] == "Value: "

    def test_template_with_numeric_values(self, tmp_path):
        """Test template with numeric variable values."""
        templates_dir = tmp_path / "numeric"
        templates_dir.mkdir()

        template = {
            "system_prompt": "System",
            "user_prompt": "Number: {{ num }}, Float: {{ flt }}",
        }
        (templates_dir / "numeric.yaml").write_text(yaml.dump(template))

        engine = TemplateEngine(template_dir=templates_dir)
        variables = {"num": 42, "flt": 3.14}
        messages = engine.render_prompt_messages("numeric.yaml", variables)

        assert "42" in messages[1]["content"]
        assert "3.14" in messages[1]["content"]

    def test_template_with_boolean_values(self, tmp_path):
        """Test template with boolean variable values."""
        templates_dir = tmp_path / "boolean"
        templates_dir.mkdir()

        template = {
            "system_prompt": "System",
            "user_prompt": "{% if flag %}Yes{% else %}No{% endif %}",
        }
        (templates_dir / "boolean.yaml").write_text(yaml.dump(template))

        engine = TemplateEngine(template_dir=templates_dir)

        # Test with True
        variables_true = {"flag": True}
        messages_true = engine.render_prompt_messages("boolean.yaml", variables_true)
        assert "Yes" in messages_true[1]["content"]

        # Test with False
        variables_false = {"flag": False}
        messages_false = engine.render_prompt_messages("boolean.yaml", variables_false, validate=False)
        assert "No" in messages_false[1]["content"]

    def test_template_with_nested_data_structures(self, tmp_path):
        """Test template with nested dictionaries and lists."""
        templates_dir = tmp_path / "nested"
        templates_dir.mkdir()

        template = {
            "system_prompt": "System",
            "user_prompt": "{% for item in data %}\n- {{ item.name }}: {{ item.value }}\n{% endfor %}",
        }
        (templates_dir / "nested.yaml").write_text(yaml.dump(template))

        engine = TemplateEngine(template_dir=templates_dir)
        variables = {
            "data": [
                {"name": "first", "value": 1},
                {"name": "second", "value": 2},
            ]
        }
        messages = engine.render_prompt_messages("nested.yaml", variables)

        assert "first: 1" in messages[1]["content"]
        assert "second: 2" in messages[1]["content"]

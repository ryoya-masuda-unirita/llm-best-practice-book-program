"""Shared pytest fixtures for all tests."""

import pytest
import yaml


@pytest.fixture
def temp_template_dir(tmp_path):
    """Create a temporary directory with sample templates."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    simple_template = {
        "system_prompt": "You are a helpful assistant.",
        "user_prompt": "Hello {{ name }}!",
    }
    (templates_dir / "simple.yaml").write_text(yaml.dump(simple_template))

    loop_template = {
        "system_prompt": "Process the following items.",
        "user_prompt": "Items:\n{% for item in items %}\n- {{ item }}\n{% endfor %}",
    }
    (templates_dir / "with_loop.yaml").write_text(yaml.dump(loop_template))

    conditional_template = {
        "system_prompt": "System message",
        "user_prompt": "Required: {{ required }}\n{% if optional %}Optional: {{ optional }}{% endif %}",
    }
    (templates_dir / "with_conditional.yaml").write_text(yaml.dump(conditional_template))

    multi_var_template = {
        "system_prompt": "You are a {{ role }}.",
        "user_prompt": "Name: {{ name }}\nAge: {{ age }}\nCity: {{ city }}",
    }
    (templates_dir / "multi_var.yaml").write_text(yaml.dump(multi_var_template))

    return templates_dir


@pytest.fixture
def sample_variables():
    """Sample variables for template rendering."""
    return {
        "name": "Alice",
        "age": 30,
        "city": "Tokyo",
        "role": "data scientist",
        "items": ["apple", "banana", "cherry"],
        "required": "value",
        "optional": "extra",
    }

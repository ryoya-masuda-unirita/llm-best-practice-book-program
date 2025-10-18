import json
from pathlib import Path

from src.model.model import CharacterRequest, CharacterResponse

# Direct import to avoid circular dependency with src.service.__init__
from src.service.template_engine import TemplateEngine

# Initialize template engine with the templates directory
_template_dir = Path(__file__).parent.parent.parent / "templates"
_template_engine = TemplateEngine(template_dir=_template_dir)


def make_prompt(
    character_request: CharacterRequest,
) -> list:
    """
    Generate a structured prompt using template-based approach.

    This function demonstrates the structured template prompting practice by:
    1. Separating prompt logic from code (templates stored in YAML)
    2. Using Jinja2 for dynamic variable injection
    3. Validating that all required variables are provided

    Args:
        character_request: Request containing character generation parameters

    Returns:
        List of message dictionaries for LLM API
    """
    # Prepare the response schema for the template
    params = CharacterResponse.detailed_model()
    response_schema = json.dumps(params, indent=2, ensure_ascii=False)

    # Define variables to inject into the template
    template_variables = {
        "response_schema": response_schema,
        "gender": character_request.gender.value,
        "age": character_request.age,
        "additional_instructions": character_request.additional_instructions or "",
    }

    # Render the template with validation
    return _template_engine.render_prompt_messages(
        template_name="character_generation.yaml",
        variables=template_variables,
        validate=True,
    )

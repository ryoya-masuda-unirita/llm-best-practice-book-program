import json
from pathlib import Path

from src.model.model import CharacterRequest, CharacterResponse
from src.service.template_engine import TemplateEngine

_template_dir = Path(__file__).parent.parent.parent / "templates"
_template_engine = TemplateEngine(template_dir=_template_dir)


def make_prompt(
    character_request: CharacterRequest,
) -> list:
    """Generate a structured prompt using template-based approach."""
    params = CharacterResponse.detailed_model()
    response_schema = json.dumps(params, indent=2, ensure_ascii=False)

    template_variables = {
        "response_schema": response_schema,
        "gender": character_request.gender.value,
        "age": character_request.age,
        "additional_instructions": character_request.additional_instructions or "",
    }

    return _template_engine.render_prompt_messages(
        template_name="character_generation.yaml",
        variables=template_variables,
        validate=True,
    )

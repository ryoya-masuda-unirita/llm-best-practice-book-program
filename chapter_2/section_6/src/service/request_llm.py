"""LLM request service with template engine integration."""

import json
from pathlib import Path
from typing import Any

import yaml

from src.client.llm_client import OpenAIModel, openai_client
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.service.template_engine import TemplateEngine

logger = make_logger(__name__)


def resolve_template_path(
    template_name: str | None = None,
    template_path: Path | None = None,
    template_dir: Path | None = None,
    default_template_engine: TemplateEngine | None = None,
) -> tuple[Path, str, TemplateEngine]:
    """Resolve template path and return the path, name, and appropriate engine."""
    if template_dir is None:
        raise ValueError("template_dir must be provided")

    if default_template_engine is None:
        default_template_engine = TemplateEngine(template_dir=template_dir)

    if template_path:
        # Use provided path directly
        final_template_path = template_path
        if not final_template_path.is_absolute():
            # If relative, resolve against templates directory
            final_template_path = template_dir / final_template_path
        template_name_for_engine = final_template_path.name

        # Create appropriate template engine
        if final_template_path.parent != template_dir:
            temp_engine = TemplateEngine(template_dir=final_template_path.parent)
        else:
            temp_engine = default_template_engine

    elif template_name:
        # Legacy: use template name
        template_name_for_engine = template_name
        temp_engine = default_template_engine
        final_template_path = template_dir / template_name

    else:
        # Default
        template_name_for_engine = "character_generation.yaml"
        temp_engine = default_template_engine
        final_template_path = template_dir / template_name_for_engine

    return final_template_path, template_name_for_engine, temp_engine


def load_variables(
    variables_file: str | None = None,
    variables_path: Path | None = None,
    variables_dir: Path | None = None,
) -> dict[str, Any]:
    """Load variables from file or return default variables."""
    if variables_path:
        with open(variables_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    elif variables_file:
        # Legacy: use variables file name
        if variables_dir is None:
            raise ValueError("variables_dir must be provided when using variables_file")
        variables_file_path = variables_dir / variables_file
        with open(variables_file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    else:
        # Default variables for character generation
        return {
            "gender": "male",
            "age": 25,
            "additional_instructions": "このキャラクターは冒険好きで、好奇心旺盛です。",
        }


def prepare_character_variables(base_variables: dict[str, Any]) -> dict[str, Any]:
    """Prepare variables for character generation by adding response schema."""
    variables = base_variables.copy()
    params = CharacterResponse.detailed_model()
    variables["response_schema"] = json.dumps(params, indent=2, ensure_ascii=False)

    return variables


def render_prompt_from_template(
    template_path: Path,
    template_name: str,
    template_engine: TemplateEngine,
    variables: dict[str, Any],
) -> list[dict[str, str]]:
    """Render prompt messages from template."""
    logger.info(f"Using template: {template_path}")
    logger.info(f"Variables: gender={variables.get('gender', 'N/A')}, age={variables.get('age', 'N/A')}")

    return template_engine.render_prompt_messages(
        template_name=template_name,
        variables=variables,
        validate=True,
    )


async def execute_llm_request(
    model: OpenAIModel,
    messages: list[dict[str, str]],
) -> CharacterResponse:
    """Execute LLM request and parse response."""
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed


async def request_openai(
    model: OpenAIModel,
    template_name: str | None = None,
    variables_file: str | None = None,
    template_path: Path | None = None,
    variables_path: Path | None = None,
    template_dir: Path | None = None,
    variables_dir: Path | None = None,
    template_engine: TemplateEngine | None = None,
) -> CharacterResponse:
    """Request OpenAI API using template engine."""
    if template_dir is None:
        raise ValueError("template_dir must be provided")

    final_template_path, template_name_for_engine, temp_engine = resolve_template_path(
        template_name=template_name,
        template_path=template_path,
        template_dir=template_dir,
        default_template_engine=template_engine,
    )

    base_variables = load_variables(
        variables_file=variables_file,
        variables_path=variables_path,
        variables_dir=variables_dir,
    )

    variables = prepare_character_variables(base_variables)

    messages = render_prompt_from_template(
        template_path=final_template_path,
        template_name=template_name_for_engine,
        template_engine=temp_engine,
        variables=variables,
    )

    return await execute_llm_request(
        model=model,
        messages=messages,
    )

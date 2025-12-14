"""
LLM request service with template engine integration.

This module provides functions for making requests to OpenAI API
using the template engine for prompt management.
"""

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
    """
    Resolve template path and return the path, name, and appropriate engine.

    Args:
        template_name: Template file name (deprecated)
        template_path: Path to template file
        template_dir: Directory containing templates
        default_template_engine: Default template engine instance

    Returns:
        Tuple of (resolved_path, template_name_for_engine, template_engine)

    Raises:
        ValueError: If template_dir is not provided when needed
    """
    if template_dir is None:
        raise ValueError("template_dir must be provided")

    if default_template_engine is None:
        default_template_engine = TemplateEngine(template_dir=template_dir)

    if template_path:
        final_template_path = template_path
        if not final_template_path.is_absolute():
            final_template_path = template_dir / final_template_path
        template_name_for_engine = final_template_path.name

        if final_template_path.parent != template_dir:
            temp_engine = TemplateEngine(template_dir=final_template_path.parent)
        else:
            temp_engine = default_template_engine

    elif template_name:
        template_name_for_engine = template_name
        temp_engine = default_template_engine
        final_template_path = template_dir / template_name

    else:
        template_name_for_engine = "character_generation.yaml"
        temp_engine = default_template_engine
        final_template_path = template_dir / template_name_for_engine

    return final_template_path, template_name_for_engine, temp_engine


def load_variables(
    variables_file: str | None = None,
    variables_path: Path | None = None,
    variables_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Load variables from file or return default variables.

    Args:
        variables_file: Variables file name (deprecated)
        variables_path: Path to variables file
        variables_dir: Directory containing variables files

    Returns:
        Dictionary of variables

    Raises:
        ValueError: If variables_dir is not provided when variables_file is used
    """
    if variables_path:
        with open(variables_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    elif variables_file:
        if variables_dir is None:
            raise ValueError("variables_dir must be provided when using variables_file")
        variables_file_path = variables_dir / variables_file
        with open(variables_file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    else:
        return {
            "gender": "male",
            "age": 25,
            "additional_instructions": "このキャラクターは冒険好きで、好奇心旺盛です。",
        }


def prepare_character_variables(base_variables: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare variables for character generation by adding response schema.

    Args:
        base_variables: Base variables dictionary

    Returns:
        Variables with response schema added
    """
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
    """
    Render prompt messages from template.

    Args:
        template_path: Path to template file
        template_name: Template file name for engine
        template_engine: TemplateEngine instance to use
        variables: Variables to inject into template

    Returns:
        List of message dictionaries for LLM API
    """
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
    """
    Execute LLM request and parse response.

    Args:
        model: OpenAI model to use
        messages: Messages to send to LLM

    Returns:
        Parsed CharacterResponse

    """
    result = await openai_client.responses.parse(
        model=model,
        input=messages,
        text_format=CharacterResponse,
    )
    return result.output_parsed


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
    """
    Request OpenAI API using template engine.

    This is the main entry point for making LLM requests with templates.
    It orchestrates the template resolution, variable loading, prompt rendering,
    and LLM request execution.

    Args:
        model: OpenAI model to use
        template_name: Name of the template file (deprecated, use template_path)
        variables_file: Variables file name (deprecated, use variables_path)
        template_path: Path to template file (absolute or relative to templates/)
        variables_path: Path to variables file (absolute or relative to variables/)
        temperature: Temperature parameter for LLM (default: 1.0)
        template_dir: Directory containing templates (required)
        variables_dir: Directory containing variables files
        template_engine: TemplateEngine instance (optional, created if not provided)

    Returns:
        CharacterResponse: Parsed character response

    Raises:
        ValueError: If template_dir is not provided

    Note:
        If both template_name and template_path are provided, template_path takes precedence.
        Same for variables_file and variables_path.

    """
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

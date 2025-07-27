import asyncio
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from google.genai.types import GenerateContentConfig

from src.llms import google_genai_client, openai_client
from src.logger import make_logger
from src.model import CharacterResponse, LLMProvider
from src.prompt import get_template_info, make_prompt
from src.template_engine import template_engine

logger = make_logger(__name__)


async def request_openai(template_name: str = "character_generation", **template_vars) -> CharacterResponse:
    prompt = make_prompt(template_name, **template_vars)
    result = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=prompt,
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed


async def request_gemini(template_name: str = "character_generation", **template_vars) -> CharacterResponse:
    prompt = make_prompt(template_name, **template_vars)
    result = await google_genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,
            temperature=2.0,
        ),
    )
    logger.info(result)
    return result.parsed


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.group()
def main():
    """Character generation CLI tool."""
    pass


@main.command(name="list-templates")
def list_templates_cmd():
    """List all available prompt templates."""
    templates = template_engine.list_available_templates()
    logger.info("Available templates:")
    for tmpl in templates:
        logger.info(f"  - {tmpl}")


@main.command(name="template-info")
@click.option(
    "--template",
    "-t",
    type=str,
    required=True,
    help="Name of the template to show information for.",
    default="character_generation",
)
def template_info_cmd(template: str):
    """Show information about a specific template."""
    info = get_template_info(template)
    if info:
        logger.info(f"Template: {info['name']}")
        logger.info(f"Description: {info['description']}")
        logger.info(f"Version: {info['version']}")
        logger.info("Variables:")
        for var_name, var_info in info["variables"].items():
            logger.info(f"  - {var_name} ({var_info['type']}): {var_info['description']}")
            if not var_info["required"]:
                logger.info(f"    Default: {var_info['default']}")
    else:
        logger.info(f"Template '{template}' not found")


@main.command(name="list-variables")
def list_variables_cmd():
    """List all available variable files."""
    variable_files = template_engine.list_variable_files()
    if variable_files:
        logger.info("Available variable files:")
        for var_file in variable_files:
            logger.info(f"  - {var_file}")
    else:
        logger.info("No variable files found in 'variables/' directory")


@main.command(name="generate")
@click.option(
    "--template",
    "-t",
    default="character_generation",
    help="Prompt template to use.",
)
@click.option(
    "--variable-file",
    "-v",
    required=True,
    type=click.Path(exists=True),
    help="YAML file containing template variables.",
)
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
)
@async_cmd
async def generate_cmd(
    template: str,
    variable_file: str,
    llm_provider: LLMProvider = LLMProvider.GEMINI,
):
    """Generate a character using the specified LLM provider and template."""
    logger.info(f"LLM provider: {llm_provider.value}")
    logger.info(f"Template: {template}")

    # Load variables from file if provided, otherwise use CLI options
    logger.info(f"Loading variables from: {variable_file}")
    try:
        template_vars = template_engine.load_variables_from_file(variable_file)
        logger.info(f"Loaded variables: {list(template_vars.keys())}")
    except Exception as e:
        logger.error(f"Failed to load variable file: {e}")
        return

    if llm_provider == LLMProvider.OPENAI:
        result = await request_openai(template, **template_vars)
    elif llm_provider == LLMProvider.GEMINI:
        result = await request_gemini(template, **template_vars)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    # Include variable file name in output if used
    var_suffix = f"_{Path(variable_file).stem}"
    result.save_as_json(f"outputs/{llm_provider.value}_{template}{var_suffix}_{uuid4().hex}.json")


if __name__ == "__main__":
    main()

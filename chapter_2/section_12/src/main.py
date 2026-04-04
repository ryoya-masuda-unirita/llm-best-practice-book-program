import asyncio
import os
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.service import request_openai
from src.service.template_engine import TemplateEngine

logger = make_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

TEMPLATE_DIR = PROJECT_ROOT / "templates"
VARIABLES_DIR = PROJECT_ROOT / "variables"

TEMPLATE_ENGINE = TemplateEngine(template_dir=TEMPLATE_DIR)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str()),
    required=True,
    default=OpenAIModel.GPT_5_4,
    help="The OpenAI model to use for the request.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@click.option(
    "--template",
    "-t",
    type=click.Path(exists=False, path_type=str),
    required=False,
    default="templates/character_generation.yaml",
    help="Template file path (relative to project root or absolute). Default: templates/character_generation.yaml",
)
@click.option(
    "--variables",
    "-v",
    type=click.Path(exists=False, path_type=str),
    required=False,
    default=None,
    help="Variables file path (relative to project root or absolute). If not specified, uses default values.",
)
@async_cmd
async def main(
    model: str,
    output_directory: str = "outputs",
    template: str = "templates/character_generation.yaml",
    variables: str | None = None,
):
    template_path = Path(template)
    if not template_path.is_absolute():
        template_path = PROJECT_ROOT / template_path

    variables_path = None
    if variables:
        variables_path = Path(variables)
        if not variables_path.is_absolute():
            variables_path = PROJECT_ROOT / variables_path

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    if variables_path and not variables_path.exists():
        raise FileNotFoundError(f"Variables file not found: {variables_path}")

    logger.info(f"""Model: {model}
Output directory: {output_directory}
Template: {template_path}
Variables: {variables_path or "default"}""")

    if model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}'. Must be one of {OpenAIModel.list_str()}")

    os.makedirs(output_directory, exist_ok=True)

    result = await request_openai(
        model=model,
        template_path=template_path,
        variables_path=variables_path,
        template_dir=TEMPLATE_DIR,
        variables_dir=VARIABLES_DIR,
        template_engine=TEMPLATE_ENGINE,
    )

    file_name = f"openai_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"""File saved to {file_path}""")


if __name__ == "__main__":
    main()

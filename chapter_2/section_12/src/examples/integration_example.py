"""
Integration Example: Adding Prompt Logging to Existing Application

This example shows how to integrate prompt logging into the existing
character generation CLI application with minimal changes.

Key points:
- Non-invasive integration
- Backward compatible
- Optional logging (can be disabled via flag)
- Minimal performance overhead
"""

import asyncio
import os
from functools import wraps
from pathlib import Path
from uuid import uuid4

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.prompt_log import (
    EvaluationCriteria,
    EvaluationStatus,
    PromptCategory,
    PromptMetadata,
)
from src.service.prompt_service import PromptManagementService
from src.service.request_llm import request_openai
from src.service.template_engine import TemplateEngine

logger = make_logger(__name__)


PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
VARIABLES_DIR = PROJECT_ROOT / "variables"
STORAGE_DIR = PROJECT_ROOT / "prompt_storage"

TEMPLATE_ENGINE = TemplateEngine(template_dir=TEMPLATE_DIR)

_prompt_service = None


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def get_prompt_service() -> PromptManagementService:
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptManagementService(storage_dir=STORAGE_DIR)
    return _prompt_service


def create_execution_metadata(model: str) -> PromptMetadata:
    return PromptMetadata(
        model_name=model,
        temperature=1.0,
        use_case="RPG character generation",
        category=PromptCategory.CHARACTER_GENERATION,
        tags=["rpg", "character", "fantasy"],
        user_id="cli_user",
    )


def log_execution(
    prompt_service: PromptManagementService,
    result,
    metadata: PromptMetadata,
    template_path: Path,
) -> str:
    log_id = prompt_service.log_prompt_execution(
        prompt_text=f"Generate character using template {template_path.name}",
        messages=[
            {"role": "system", "content": "You are a creative RPG character designer."},
            {"role": "user", "content": f"Generate character from template {template_path.name}"},
        ],
        response_text=str(result.model_dump()),
        metadata=metadata,
        parsed_response=result.model_dump(),
        template_name=template_path.name,
        template_version="1.0.0",
    )

    logger.info(f"Logged execution: {log_id}")
    return log_id


def evaluate_result(
    prompt_service: PromptManagementService,
    log_id: str,
    result,
):
    all_fields_present = all(
        [
            result.first_name,
            result.last_name,
            result.gender,
            result.age,
            result.personalities,
        ]
    )

    evaluation = EvaluationCriteria(
        accuracy=0.8,
        completeness=1.0 if all_fields_present else 0.7,
        relevance=0.85,
        task_completed=all_fields_present,
    )

    status = EvaluationStatus.SUCCESS if all_fields_present else EvaluationStatus.PARTIAL

    prompt_service.evaluate_prompt(
        log_id=log_id,
        evaluation=evaluation,
        status=status,
    )

    score = evaluation.accuracy + evaluation.completeness + evaluation.relevance
    logger.info(f"Auto-evaluated: {status} (score: {score:.2f})")


async def execute_with_logging(
    model: str,
    template_path: Path,
    variables_path: Path | None,
    enable_logging: bool,
    auto_evaluate: bool,
) -> tuple:
    result = await request_openai(
        model=model,
        template_path=template_path,
        variables_path=variables_path,
        template_dir=TEMPLATE_DIR,
        variables_dir=VARIABLES_DIR,
        template_engine=TEMPLATE_ENGINE,
    )

    log_id = None

    if enable_logging:
        prompt_service = get_prompt_service()
        metadata = create_execution_metadata(model)
        log_id = log_execution(prompt_service, result, metadata, template_path)

        if auto_evaluate:
            evaluate_result(prompt_service, log_id, result)

    return result, log_id


def resolve_paths(
    template: str,
    variables: str | None,
) -> tuple[Path, Path | None]:
    template_path = Path(template)
    if not template_path.is_absolute():
        template_path = PROJECT_ROOT / template_path

    variables_path = None
    if variables:
        variables_path = Path(variables)
        if not variables_path.is_absolute():
            variables_path = PROJECT_ROOT / variables_path

    return template_path, variables_path


def validate_paths(template_path: Path, variables_path: Path | None):
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    if variables_path and not variables_path.exists():
        raise FileNotFoundError(f"Variables file not found: {variables_path}")


def log_configuration(
    model: str,
    output_directory: str,
    template_path: Path,
    variables_path: Path | None,
    enable_logging: bool,
    auto_evaluate: bool,
):
    logger.info(
        f"""Model: {model}
Output directory: {output_directory}
Template: {template_path}
Variables: {variables_path or "default"}
Logging: {"enabled" if enable_logging else "disabled"}
Auto-evaluate: {"enabled" if auto_evaluate else "disabled"}"""
    )


def save_result(result, output_directory: str) -> str:
    file_name = f"openai_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"File saved to {file_path}")
    return file_path


def display_result(result):
    print("\n" + "=" * 80)
    print("CHARACTER GENERATION RESULT")
    print("=" * 80)
    print(f"Name: {result.first_name} {result.last_name}")
    print(f"Gender: {result.gender}")
    print(f"Age: {result.age}")

    if result.personalities:
        print(f"Personality: {result.personalities[0].short_personality}")
        print(f"Description: {result.personalities[0].description[:100]}...")

    print("=" * 80 + "\n")


def display_catalog_summary(prompt_service: PromptManagementService):
    catalog = prompt_service.get_catalog_summary()
    print("Catalog Summary:")
    print(f"  Total templates: {catalog['total_templates']}")
    print(f"  Total anti-patterns: {catalog['total_antipatterns']}")
    print(f"  Total template uses: {catalog['total_template_uses']}")
    print(f"  Average success rate: {catalog['average_success_rate']:.1%}")


def display_success_rates(prompt_service: PromptManagementService):
    success_rates = prompt_service.get_success_rates()
    if success_rates:
        print("\nSuccess Rates by Category:")
        for category, rate in success_rates.items():
            print(f"  {category}: {rate:.1%}")


def display_cost_analysis(prompt_service: PromptManagementService):
    cost = prompt_service.get_cost_analysis()
    if cost["total_cost_usd"] > 0:
        print("\nCost Analysis:")
        print(f"  Total cost: ${cost['total_cost_usd']:.4f}")
        print(f"  Total tokens: {cost['total_input_tokens'] + cost['total_output_tokens']:,}")


def display_improvement_suggestions(prompt_service: PromptManagementService):
    suggestions = prompt_service.get_improvement_suggestions()
    if suggestions:
        print(f"\nImprovement Suggestions: {len(suggestions)}")
        for i, suggestion in enumerate(suggestions[:3], 1):
            print(f"  {i}. [{suggestion['severity'].upper()}] {suggestion['type']}")


def display_statistics(prompt_service: PromptManagementService):
    print("\n" + "=" * 80)
    print("PROMPT ANALYTICS STATISTICS")
    print("=" * 80 + "\n")

    display_catalog_summary(prompt_service)
    display_success_rates(prompt_service)
    display_cost_analysis(prompt_service)
    display_improvement_suggestions(prompt_service)

    print("=" * 80 + "\n")


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
@click.option(
    "--enable-logging/--no-logging",
    default=True,
    help="Enable prompt logging for analysis and reuse. Default: enabled",
)
@click.option(
    "--auto-evaluate/--no-auto-evaluate",
    default=False,
    help="Automatically evaluate the result. Default: disabled",
)
@click.option(
    "--show-stats",
    is_flag=True,
    help="Show prompt analytics statistics after execution.",
)
@async_cmd
async def main(
    model: str,
    output_directory: str = "outputs",
    template: str = "templates/character_generation.yaml",
    variables: str | None = None,
    enable_logging: bool = True,
    auto_evaluate: bool = False,
    show_stats: bool = False,
):
    """
    Generate RPG characters with optional prompt logging and analytics.

    This is an enhanced version of the original CLI that adds:
    - Prompt logging for analysis
    - Automatic evaluation
    - Analytics and statistics

    All new features are optional and backward compatible.
    """
    template_path, variables_path = resolve_paths(template, variables)
    validate_paths(template_path, variables_path)

    log_configuration(
        model,
        output_directory,
        template_path,
        variables_path,
        enable_logging,
        auto_evaluate,
    )

    if model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}'. Must be one of {OpenAIModel.list_str()}")

    os.makedirs(output_directory, exist_ok=True)

    result, log_id = await execute_with_logging(
        model=model,
        template_path=template_path,
        variables_path=variables_path,
        enable_logging=enable_logging,
        auto_evaluate=auto_evaluate,
    )

    save_result(result, output_directory)
    display_result(result)

    if enable_logging:
        print(f"✓ Execution logged: {log_id}")

    if show_stats and enable_logging:
        prompt_service = get_prompt_service()
        display_statistics(prompt_service)


if __name__ == "__main__":
    main()

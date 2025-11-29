import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.service.llm_pipeline_service import run_dinner_advisor

logger = make_logger(__name__)


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
    required=False,
    default=OpenAIModel.GPT_4O,
    help="The model to use for the request.",
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
    "--request",
    "-r",
    type=str,
    required=True,
    help="Your dinner request in natural language.",
)
@async_cmd
async def main(
    model: str,
    output_directory: str,
    request: str,
):
    """
    Dinner Menu Advisor - A ReAct AI Agent

    This agent recommends dinner menus based on your request.
    It uses tools to search recipes, check nutrition, find seasonal ingredients,
    and estimate cooking times.

    REQUEST: Your dinner request in natural language.

    Examples:

        python -m src.main -r "今日は疲れているので簡単な料理がいい"

        python -m src.main -r "健康的な和食を作りたい"

        python -m src.main -r "30分以内で作れるイタリアン"
    """
    logger.info(f"""Dinner Menu Advisor
Model: {model}
Request: {request}
Output directory: {output_directory}
""")

    os.makedirs(output_directory, exist_ok=True)

    # Run the dinner advisor ReAct agent
    result = await run_dinner_advisor(
        user_request=request,
        model=model,
    )

    if result is None:
        raise ValueError("Dinner advisor failed. Check logs for details.")

    # Save the recommendation
    base_name = f"dinner_recommendation_{uuid4().hex}"
    md_file_path = os.path.join(output_directory, f"{base_name}.md")

    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info(f"Recommendation saved: {md_file_path}")


if __name__ == "__main__":
    main()

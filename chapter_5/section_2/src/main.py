import asyncio
import os
from functools import wraps
from uuid import uuid4

import click
from src.client.llm_client import GeminiModel
from src.logger import make_logger
from src.service.multi_agent_service import run_contract_review

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
    type=click.Choice(GeminiModel.list_str()),
    required=False,
    default=GeminiModel.GEMINI_2_5_PRO,
    help="The Google Gemini model to use for the review.",
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
    "--contract-file",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to the contract file to review (markdown format).",
)
@click.option(
    "--template-file",
    "-t",
    type=click.Path(exists=True),
    required=True,
    help="Path to the standard contract template file (markdown format).",
)
@async_cmd
async def main(
    model: str,
    output_directory: str,
    contract_file: str,
    template_file: str,
):
    """
    Contract Review Multi-Agent System

    This system reviews contract documents using multiple specialized AI agents:

    1. Document Parser Agent - Parses contract into structured clauses
    2. Clause Classifier Agent - Categorizes each clause
    3. Risk Assessment Agent - Evaluates risk levels
    4. Diff Checker Agent - Compares with standard template
    5. Amendment Proposer Agent - Suggests modifications for high-risk clauses
    6. Report Generator Agent - Creates comprehensive review report

    Examples:

        python -m src.main -c example/sample_nda.md -t example/standard_nda_template.md

        python -m src.main -m claude-sonnet-4-6 -c contract.md -t template.md -od reports
    """
    logger.info(f"""Contract Review Multi-Agent System
Model: {model}
Contract file: {contract_file}
Template file: {template_file}
Output directory: {output_directory}
""")

    with open(contract_file, encoding="utf-8") as f:
        contract_text = f.read()

    with open(template_file, encoding="utf-8") as f:
        standard_template = f.read()

    os.makedirs(output_directory, exist_ok=True)

    result = await run_contract_review(
        contract_text=contract_text,
        standard_template=standard_template,
        model=model,
    )

    if result is None:
        raise ValueError("Contract review failed. Check logs for details.")

    base_name = f"contract_review_{uuid4().hex}"
    md_file_path = os.path.join(output_directory, f"{base_name}.md")

    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info(f"Review report saved: {md_file_path}")


if __name__ == "__main__":
    main()

"""
CLI entry point for the Contract Risk Compliance Pipeline.

This module provides a command-line interface for evaluating contract
documents for risk compliance using a pipeline AI agent architecture.
"""

import asyncio
import os
from functools import wraps
from pathlib import Path

import click
from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.service.contract_pipeline_service import run_contract_compliance_pipeline

logger = make_logger(__name__)


def async_cmd(func):
    """Decorator to run async click commands."""

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
    default=OpenAIModel.GPT_4O_MINI,
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
    "--contract-file",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to the contract document file (markdown or text).",
)
@async_cmd
async def main(
    model: str,
    output_directory: str,
    contract_file: str,
):
    """
    Contract Risk Compliance Pipeline - A Pipeline AI Agent System

    This system evaluates contract documents for risk compliance using a
    pipeline AI agent architecture with three stages:

    \b
    1. Extraction Stage: Parse contract structure (chapters, sections)
    2. Risk Scoring Stage: Evaluate risk for each section
    3. Report Stage: Generate comprehensive compliance report

    The pipeline processes each stage sequentially, with each stage's output
    becoming the input for the next stage.

    Examples:

    \b
        # Evaluate a contract file
        python -m src.main -c data/contract_0.md

        # With custom model
        python -m src.main -c data/contract_0.md -m gpt-4o

        # With custom output directory
        python -m src.main -c data/contract_0.md -od reports
    """
    logger.info(
        f"Contract Risk Compliance Pipeline\n"
        f"Model: {model}\n"
        f"Contract file: {contract_file}\n"
        f"Output directory: {output_directory}"
    )

    os.makedirs(output_directory, exist_ok=True)

    report = await run_contract_compliance_pipeline(
        contract_file_path=contract_file,
        model=model,
    )

    if report is None:
        raise ValueError("Contract pipeline failed. Check logs for details.")

    output_path = Path(output_directory) / f"compliance_report_{report.report_id}.md"
    output_path.write_text(report.to_markdown(), encoding="utf-8")
    logger.info(f"Report saved: {output_path}")
    logger.info(f"\nCompliance report saved to: {output_path}")
    logger.info(f"Overall Status: {report.executive_summary.overall_status}")
    logger.info(f"Risk Score: {report.executive_summary.overall_risk_score}/100")


if __name__ == "__main__":
    main()

import asyncio
from functools import wraps
from pathlib import Path

import click
from src.client.llm_client import AnthropicModel
from src.logger import make_logger
from src.service import extract_document_structure, save_extraction_results

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
    type=click.Choice(AnthropicModel.list_str()),
    required=True,
    help="The Anthropic model to use for analysis.",
)
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    required=True,
    help="Path to the input document (text or markdown).",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(),
    required=False,
    default="outputs",
    help="The directory to save output files.",
)
@async_cmd
async def main(
    model: str,
    input_file: str,
    output_directory: str = "outputs",
):
    """Analyze and extract document structure using LLM-generated scripts."""
    logger.info(f"""Model: {model}
Input file: {input_file}
Output directory: {output_directory}""")

    if model not in AnthropicModel.list_str():
        raise ValueError(f"Invalid model '{model}'.")

    document_content = Path(input_file).read_text(encoding="utf-8")
    logger.info(f"Document loaded: {len(document_content)} characters")

    extraction_result = await extract_document_structure(
        model=model,
        document_content=document_content,
    )

    if extraction_result.success:
        save_extraction_results(
            extraction_result=extraction_result,
            input_file=input_file,
            output_directory=output_directory,
            model=model,
        )
        logger.info("Document structure extraction completed successfully!")
    else:
        logger.error("Failed to extract document structure.")
        if extraction_result.error:
            logger.error(f"Last error: {extraction_result.error}")
        raise click.ClickException("Document structure extraction failed.")


if __name__ == "__main__":
    main()

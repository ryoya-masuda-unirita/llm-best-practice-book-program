import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel, google_genai_client
from src.logger import make_logger
from src.service import run_document_analysis_pipeline

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    required=True,
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    required=True,
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
    "--document-path",
    "-dp",
    type=click.Path(exists=True),
    required=True,
    help="Path to the markdown document to analyze.",
)
@async_cmd
async def main(
    llm_provider: LLMProvider,
    model: str,
    document_path: str,
    output_directory: str = "outputs",
):
    logger.info(f"""LLM provider: {llm_provider.value}
Model: {model}
Document path: {document_path}
Output directory: {output_directory}
""")

    if llm_provider == LLMProvider.OPENAI and model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.GEMINI and model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    # Run document analysis pipeline
    if not document_path:
        raise ValueError("Document path is required for pipeline mode. Use --document-path option.")

    result = await run_document_analysis_pipeline(
        document_path=document_path,
        llm_provider=llm_provider,
        model=model,
    )

    if result is None:
        raise ValueError("Document analysis pipeline failed. Check logs for details.")

    # Save both JSON and Markdown outputs
    base_name = f"{llm_provider.value}_analysis_{uuid4().hex}"
    json_file_path = os.path.join(output_directory, f"{base_name}.json")
    md_file_path = os.path.join(output_directory, f"{base_name}.md")

    result.save_as_json(json_file_path)
    result.save_as_markdown(md_file_path)

    logger.info(f"""Analysis results saved:
JSON: {json_file_path}
Markdown: {md_file_path}""")

    # Clean up Google Gemini client session
    if llm_provider == LLMProvider.GEMINI:
        await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()

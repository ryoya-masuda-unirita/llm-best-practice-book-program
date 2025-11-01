import asyncio
import json
import os
from functools import wraps

import click

from src.client.llm_client import GeminiEmbeddingModel, GeminiModel, LLMProvider, OpenAIEmbeddingModel, OpenAIModel
from src.logger import make_logger
from src.service.rag_pipeline import RAGPipeline

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.group()
def cli():
    """RAG System CLI - A modular RAG system using strategy pattern."""
    pass


@cli.command()
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    required=True,
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
)
@click.option(
    "--data-directory",
    "-d",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="data",
    help="Directory containing documents to index.",
)
@click.option(
    "--chunker-model",
    "-cm",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    default=OpenAIModel.GPT_5_MINI,
    help="Model for semantic chunking.",
)
@click.option(
    "--embedding-model",
    "-em",
    type=click.Choice(OpenAIEmbeddingModel.list_str() + GeminiEmbeddingModel.list_str()),
    default=OpenAIEmbeddingModel.TEXT_EMBEDDING_3_SMALL,
    help="Model for creating embeddings.",
)
@async_cmd
async def index(
    llm_provider: LLMProvider,
    data_directory: str,
    chunker_model: str,
    embedding_model: str,
):
    """Index documents from the data directory."""
    logger.info(f"Indexing documents from: {data_directory}")

    if (
        llm_provider == LLMProvider.OPENAI
        and chunker_model not in OpenAIModel.list_str()
        and embedding_model not in OpenAIEmbeddingModel.list_str()
    ):
        raise ValueError(
            f"Invalid model '{chunker_model}' and '{embedding_model}' for provider '{llm_provider.value}'."
        )
    if (
        llm_provider == LLMProvider.GEMINI
        and chunker_model not in GeminiModel.list_str()
        and embedding_model not in GeminiEmbeddingModel.list_str()
    ):
        raise ValueError(
            f"Invalid model '{chunker_model}' and '{embedding_model}' for provider '{llm_provider.value}'."
        )

    pipeline = RAGPipeline(data_directory=data_directory, chunker_model=chunker_model, embedding_model=embedding_model)

    await pipeline.index_documents()

    logger.info("Indexing completed successfully")


@cli.command()
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    required=True,
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
)
@click.option(
    "--data-directory",
    "-d",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="data",
    help="Directory containing documents to index.",
)
@click.option(
    "--question",
    "-q",
    type=str,
    required=True,
    help="Question to ask the RAG system.",
)
@click.option(
    "--chunker-model",
    "-cm",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    default=OpenAIModel.GPT_5_MINI,
    help="Model for semantic chunking.",
)
@click.option(
    "--embedding-model",
    "-em",
    type=click.Choice(OpenAIEmbeddingModel.list_str() + GeminiEmbeddingModel.list_str()),
    default=OpenAIEmbeddingModel.TEXT_EMBEDDING_3_SMALL,
    help="Model for creating embeddings.",
)
@click.option(
    "--generator-model",
    "-gm",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    default=OpenAIModel.GPT_5_MINI,
    help="Model for answer generation.",
)
@click.option(
    "--top-k",
    "-k",
    type=int,
    default=5,
    help="Number of top chunks to retrieve.",
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(),
    required=False,
    help="Optional file path to save the answer as JSON.",
)
@async_cmd
async def query(
    llm_provider: LLMProvider,
    data_directory: str,
    question: str,
    chunker_model: str,
    embedding_model: str,
    generator_model: str,
    top_k: int,
    output_file: str | None,
):
    """Query the RAG system with a question."""
    logger.info(f"Processing query: {question}")

    if (
        llm_provider == LLMProvider.OPENAI
        and chunker_model not in OpenAIModel.list_str()
        and embedding_model not in OpenAIEmbeddingModel.list_str()
    ):
        raise ValueError(
            f"Invalid model '{chunker_model}' and '{embedding_model}' for provider '{llm_provider.value}'."
        )
    if (
        llm_provider == LLMProvider.GEMINI
        and chunker_model not in GeminiModel.list_str()
        and embedding_model not in GeminiEmbeddingModel.list_str()
    ):
        raise ValueError(
            f"Invalid model '{chunker_model}' and '{embedding_model}' for provider '{llm_provider.value}'."
        )

    pipeline = RAGPipeline(
        data_directory=data_directory,
        chunker_model=chunker_model,
        embedding_model=embedding_model,
        generator_model=generator_model,
        top_k=top_k,
    )

    await pipeline.index_documents()

    answer = await pipeline.query(question)

    logger.info("\n" + "=" * 80)
    logger.info(f"Question: {answer.question}")
    logger.info("=" * 80)
    logger.info(f"\nAnswer:\n{answer.answer}")
    logger.info("\n" + "-" * 80)
    logger.info(f"Sources: {', '.join(answer.source_chunks)}")
    logger.info("=" * 80 + "\n")

    if output_file:
        # Handle case where output_file is a directory
        if output_file.endswith("/") or output_file.endswith("\\"):
            output_file = os.path.join(output_file, "answer.json")
        elif os.path.exists(output_file) and os.path.isdir(output_file):
            output_file = os.path.join(output_file, "answer.json")

        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(answer.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info(f"Answer saved to {output_file}")


if __name__ == "__main__":
    cli()

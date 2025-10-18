import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.llmops_log import StorageType
from src.model.model import CharacterRequests
from src.service.llmops_logger import create_llmops_logger
from src.service.request_llm import batch_request_gemini, batch_request_openai

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--request-file",
    "-rf",
    type=click.Path(exists=True),
    required=True,
    help="Path to the YAML file containing character generation requests.",
)
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    default=LLMProvider.GEMINI,
    required=True,
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
    default="outputs",
    required=False,
    help="The directory to save output files.",
)
@click.option(
    "--parallelism",
    "-p",
    type=int,
    default=5,
    help="Number of parallel requests to make.",
)
@click.option(
    "--user-id",
    "-u",
    type=str,
    default="default_user",
    help="User ID for logging purposes.",
)
@click.option(
    "--storage-type",
    "-st",
    type=click.Choice(StorageType),
    default=StorageType.LOCAL,
    help="The storage type for prompt logging.",
)
@async_cmd
async def main(
    request_file: str,
    llm_provider: LLMProvider,
    model: str,
    output_directory: str = "outputs",
    parallelism: int = 5,
    user_id: str = "default_user",
    storage_type: StorageType = StorageType.LOCAL,
):
    logger.info(f"""Request file: {request_file}
LLM provider: {llm_provider.value}
Model: {model}
Output directory: {output_directory}
Parallelism: {parallelism}
User ID: {user_id}
Storage type: {storage_type.value}""")

    if llm_provider == LLMProvider.OPENAI and model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.GEMINI and model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")

    # Load character requests from YAML file
    logger.info(f"Loading character requests from {request_file}")
    character_requests_data = CharacterRequests.load_from_yaml(request_file)
    character_requests = character_requests_data.requests
    logger.info(f"Loaded {len(character_requests)} character requests")

    os.makedirs(output_directory, exist_ok=True)

    # Process requests in batch
    llmops_logger = create_llmops_logger(logger_name="llmops", storage_type=storage_type)
    if llm_provider == LLMProvider.OPENAI:
        results = await batch_request_openai(
            character_requests=character_requests,
            model=model,
            llmops_logger=llmops_logger,
            user_id=user_id,
            parallelism=parallelism,
        )
    elif llm_provider == LLMProvider.GEMINI:
        results = await batch_request_gemini(
            character_requests=character_requests,
            model=model,
            llmops_logger=llmops_logger,
            user_id=user_id,
            parallelism=parallelism,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    # Save results to individual JSON files
    logger.info(f"Saving {len(results)} character responses to {output_directory}")
    for i, result in enumerate(results):
        file_name = f"{llm_provider.value}_{i + 1:03d}_{uuid4().hex[:8]}.json"
        file_path = os.path.join(output_directory, file_name)
        result.save_as_json(file_path)
        logger.info(f"Saved character {i + 1} to {file_path}")

    logger.info(f"Batch processing complete. Generated {len(results)} characters.")


if __name__ == "__main__":
    main()

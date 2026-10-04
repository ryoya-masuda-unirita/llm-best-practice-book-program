import asyncio
import os
from functools import wraps
from uuid import uuid4

import click
from src.client.llm_client import AnthropicModel, LLMProvider, OpenAIModel  # , GeminiModel
from src.logger import make_logger
from src.model.llmops_log import StorageType
from src.service import request_anthropic, request_openai  # , request_gemini
from src.service.llmops_logger import create_llmops_logger

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
    default=LLMProvider.ANTHROPIC,
    required=True,
    help="The LLM provider to use.",
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str() + AnthropicModel.list_str()),  # + GeminiModel.list_str()
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
    llm_provider: LLMProvider,
    model: str,
    output_directory: str = "outputs",
    user_id: str = "default_user",
    storage_type: StorageType = StorageType.LOCAL,
):
    logger.info(f"""LLM provider: {llm_provider.value}
Model: {model}
Output directory: {output_directory}
User ID: {user_id}
Storage type: {storage_type.value}""")

    if llm_provider == LLMProvider.OPENAI and model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    # if llm_provider == LLMProvider.GEMINI and model not in GeminiModel.list_str():
    #     raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.ANTHROPIC and model not in AnthropicModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    llmops_logger = create_llmops_logger(logger_name="llmops", storage_type=storage_type)
    if llm_provider == LLMProvider.OPENAI:
        result = await request_openai(model=model, llmops_logger=llmops_logger, user_id=user_id)
    # elif llm_provider == LLMProvider.GEMINI:
    #     result = await request_gemini(model=model, llmops_logger=llmops_logger, user_id=user_id)
    elif llm_provider == LLMProvider.ANTHROPIC:
        result = await request_anthropic(model=model, llmops_logger=llmops_logger, user_id=user_id)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    file_name = f"{llm_provider.value}_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"""File saved to {file_path}""")


if __name__ == "__main__":
    main()

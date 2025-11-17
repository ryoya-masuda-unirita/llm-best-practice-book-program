import asyncio
import os
from functools import wraps
from typing import Optional
from uuid import uuid4

import click

from src.client.llm_client import (
    GeminiModel,
    LLMProvider,
    OpenAIModel,
    get_gemini_embedding,
    get_openai_embedding,
    google_genai_client,
)
from src.client.llm_request_wrapper import LLMRequestWrapper
from src.config import config
from src.logger import make_logger
from src.model.model import Gender
from src.prompt.prompt import make_prompt
from src.service.cache_manager import CacheManager, SemanticCacheManager
from src.service.fallback_coordinator import FallbackCoordinator, FallbackStrategy

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option(
    "--gender",
    "-g",
    type=click.Choice(Gender),
    default=Gender.FEMALE,
    help="The gender of the character to generate.",
    required=True,
)
@click.option(
    "--age",
    "-a",
    type=click.IntRange(0, 100),
    default=25,
    help="The age of the character to generate.",
    required=True,
)
@click.option(
    "--additional-instructions",
    "-ai",
    type=str,
    default="",
    help="Additional instructions for character generation.",
    required=False,
)
@click.option(
    "--llm-provider",
    "-lp",
    type=click.Choice(LLMProvider),
    default=LLMProvider.GEMINI,
    help="The LLM provider to use.",
    required=True,
)
@click.option(
    "--model",
    "-m",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    required=True,
    help="The model to use for the request.",
)
@click.option(
    "--fallback-strategy",
    "-fs",
    type=click.Choice(FallbackStrategy),
    default=FallbackStrategy.ALTERNATIVE_PROVIDER,
    help="The fallback strategy to use.",
    required=True,
)
@click.option(
    "--alternative-model",
    "-am",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    required=False,
    help="The alternative model to use for fallback requests.",
)
@click.option(
    "--output-directory",
    "-od",
    required=False,
    type=click.Path(),
    default="outputs",
    help="The directory to save output files.",
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=None,
    help=f"Request timeout in seconds (default: {config.llm_request_timeout}s from config)",
    required=True,
)
@click.option(
    "--disable-fallback",
    "-df",
    is_flag=True,
    default=False,
    help="Disable fallback mechanisms (use only primary provider)",
)
@async_cmd
async def main(
    gender: Gender,
    age: int,
    additional_instructions: str,
    llm_provider: LLMProvider,
    model: str,
    fallback_strategy: FallbackStrategy,
    alternative_model: str | None,
    output_directory: str = "outputs",
    timeout: float | None = None,
    disable_fallback: bool = False,
):
    logger.info(f"""Starting character generation with the following parameters:
Gender: {gender}
Age: {age}
Additional instruction: {additional_instructions}

LLM Parameters:
LLM provider: {llm_provider}
Model: {model}
Fallback strategy: {fallback_strategy}
Alternative model: {alternative_model}
Output directory: {output_directory}
Timeout: {timeout if timeout else config.llm_request_timeout}s
Fallback enabled: {not disable_fallback}""")

    os.makedirs(output_directory, exist_ok=True)

    cache_manager: Optional[CacheManager] = None
    if fallback_strategy == FallbackStrategy.PARAMETER_CACHE:
        # Initialize cache managers based on fallback strategy
        cache_manager = CacheManager(
            cache_dir=".cache",
            ttl=config.cache_ttl,
        )

    semantic_cache_manager: Optional[SemanticCacheManager] = None
    if fallback_strategy == FallbackStrategy.SEMANTIC_CACHE:
        # Choose embedding function based on primary provider
        if llm_provider == LLMProvider.OPENAI:
            embedding_func = get_openai_embedding
        else:  # GEMINI
            embedding_func = get_gemini_embedding

        semantic_cache_manager = SemanticCacheManager(
            cache_dir=".semantic_cache",
            ttl=config.cache_ttl,
            similarity_threshold=0.95,
            embedding_func=embedding_func,
        )
        logger.info(f"Initialized semantic cache with {llm_provider.value} embeddings (threshold: 0.95)")

    # Initialize fallback coordinator
    fallback_coordinator = FallbackCoordinator(
        fallback_strategy=fallback_strategy,
        cache_manager=cache_manager,
        semantic_cache_manager=semantic_cache_manager,
        timeout=timeout,
    )

    wrapper = LLMRequestWrapper(fallback_coordinator=fallback_coordinator)

    prompt = make_prompt(
        gender=gender,
        age=age,
        additional_instructions=additional_instructions,
    )

    # Make request with or without fallback
    if llm_provider == LLMProvider.OPENAI:
        if model not in OpenAIModel.list_str():
            raise ValueError(f"Model {model} is not a valid OpenAI model.")
        if alternative_model not in GeminiModel.list_str():
            raise ValueError(f"Alternative model {alternative_model} is not a valid Gemini model.")

        result, strategy, error_reason = await wrapper.request_openai(
            prompt=prompt,
            model=OpenAIModel(model),
            alternative_model=GeminiModel(alternative_model),
            with_fallback=not disable_fallback,
        )
    elif llm_provider == LLMProvider.GEMINI:
        if model not in GeminiModel.list_str():
            raise ValueError(f"Model {model} is not a valid Gemini model.")
        if alternative_model not in OpenAIModel.list_str():
            raise ValueError(f"Alternative model {alternative_model} is not a valid OpenAI model.")

        result, strategy, error_reason = await wrapper.request_gemini(
            prompt=prompt,
            model=GeminiModel(model),
            alternative_model=OpenAIModel(alternative_model),
            with_fallback=not disable_fallback,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    # Log fallback information if applicable
    if strategy:
        logger.info(f"Response obtained via fallback strategy: {strategy.value}")
        if error_reason:
            logger.warning(f"Primary provider failed due to: {error_reason}")

    # Save result
    file_name = f"{llm_provider.value}_{uuid4().hex}.json"
    file_path = os.path.join(output_directory, file_name)
    result.save_as_json(file_path)
    logger.info(f"""File saved to {file_path}""")

    # Log statistics
    fallback_coordinator.log_stats()

    await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()

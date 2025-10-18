import asyncio
import os
from functools import wraps
from uuid import uuid4

import click

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import CharacterRequest, Gender
from src.prompt.prompt import make_prompt
from src.service import request_with_judge

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
    "--judge-provider",
    "-jp",
    type=click.Choice(LLMProvider),
    required=False,
    help="The LLM provider to use for judgment (defaults to same as generation provider).",
)
@click.option(
    "--judge-model",
    "-jm",
    type=click.Choice(OpenAIModel.list_str() + GeminiModel.list_str()),
    required=False,
    help="The model to use for judgment (defaults to same as generation model).",
)
@async_cmd
async def main(
    gender: Gender,
    age: int,
    additional_instructions: str,
    llm_provider: LLMProvider,
    model: str,
    output_directory: str = "outputs",
    judge_provider: LLMProvider | None = None,
    judge_model: str | None = None,
):
    # Determine judge provider and model
    effective_judge_provider = judge_provider if judge_provider else llm_provider
    effective_judge_model = judge_model if judge_model else model

    logger.info(f"""Character Generation Request:
Gender: {gender.value}
Age: {age}
Additional Instructions: {additional_instructions}

Generation LLM: {llm_provider.value} / {model}
Judge LLM: {effective_judge_provider.value} / {effective_judge_model}
Output directory: {output_directory}""")

    # Validate generation model
    if llm_provider == LLMProvider.OPENAI and model not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
    if llm_provider == LLMProvider.GEMINI and model not in GeminiModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")

    # Validate judge model if specified
    if judge_provider and judge_model:
        if judge_provider == LLMProvider.OPENAI and judge_model not in OpenAIModel.list_str():
            raise ValueError(f"Invalid judge model '{judge_model}' for provider '{judge_provider.value}'.")
        if judge_provider == LLMProvider.GEMINI and judge_model not in GeminiModel.list_str():
            raise ValueError(f"Invalid judge model '{judge_model}' for provider '{judge_provider.value}'.")

    os.makedirs(output_directory, exist_ok=True)

    character_request = CharacterRequest(gender=gender, age=age, additional_instructions=additional_instructions)
    prompt = make_prompt(character_request=character_request)

    # Always use LLM-as-a-Judge workflow
    character_result, judge_result = await request_with_judge(
        prompt=prompt,
        model=model,
        provider=llm_provider.value,
        judge_model=judge_model,
        judge_provider=judge_provider.value if judge_provider else None,
    )

    # Save character result
    key = uuid4().hex

    character_file_name = f"{key}_{llm_provider.value}_character.json"
    character_file_path = os.path.join(output_directory, character_file_name)
    character_result.save_as_json(character_file_path)
    logger.info(f"""Character file saved to {character_file_path}""")

    # Save judge result (use judge provider if specified, otherwise generation provider)
    judge_file_name = f"{key}_{effective_judge_provider.value}_judge.json"
    judge_file_path = os.path.join(output_directory, judge_file_name)
    judge_result.save_as_json(judge_file_path)
    logger.info(f"""Judge evaluation saved to {judge_file_path}""")
    logger.info(f"""Overall evaluation score: {judge_result.overall_score:.2f}/5.0""")

    if not judge_result.is_passing():
        logger.warning("The generated character did not meet the quality threshold (3.0/5.0)")


if __name__ == "__main__":
    main()

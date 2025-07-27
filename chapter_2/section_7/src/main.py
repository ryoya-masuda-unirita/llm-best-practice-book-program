import asyncio
import json
from functools import wraps
from uuid import uuid4

import click
from google.genai.types import GenerateContentConfig

from src.judge import evaluate_character_response
from src.llms import google_genai_client, openai_client
from src.logger import make_logger
from src.model import CharacterResponse, LLMProvider
from src.prompt import make_prompt

logger = make_logger(__name__)


async def request_openai() -> CharacterResponse:
    prompt = make_prompt()
    result = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=prompt,
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed


async def request_gemini() -> CharacterResponse:
    prompt = make_prompt()
    result = await google_genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,
            temperature=2.0,
        ),
    )
    logger.info(result)
    return result.parsed


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
    default=LLMProvider.GEMINI,
    help="The LLM provider to use for character generation.",
)
@click.option(
    "--judge-provider",
    "-jp",
    type=click.Choice(LLMProvider),
    default=LLMProvider.GEMINI,
    help="The LLM provider to use for evaluation (judge).",
)
@click.option(
    "--enable-judge",
    "--judge",
    is_flag=True,
    default=False,
    help="Enable LLM-as-a-Judge evaluation after generation.",
)
@async_cmd
async def main(
    llm_provider: LLMProvider = LLMProvider.GEMINI,
    judge_provider: LLMProvider = LLMProvider.GEMINI,
    enable_judge: bool = False,
):
    logger.info(f"Character generation provider: {llm_provider.value}")
    if enable_judge:
        logger.info(f"Judge provider: {judge_provider.value}")

    # Generate character
    if llm_provider == LLMProvider.OPENAI:
        result = await request_openai()
    elif llm_provider == LLMProvider.GEMINI:
        result = await request_gemini()
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    # Prepare output data
    output_id = uuid4().hex
    output_data = {"generation": {"provider": llm_provider.value, "result": result.model_dump()}}

    # Evaluate with LLM-as-a-Judge if enabled
    if enable_judge:
        logger.info("Starting LLM-as-a-Judge evaluation...")

        # Get the original prompt content for evaluation
        prompt_messages = make_prompt()
        original_prompt = f"System: {prompt_messages[0]['content']}\n\nUser: {prompt_messages[1]['content']}"

        try:
            evaluation = await evaluate_character_response(
                character_response=result, original_prompt=original_prompt, judge_provider=judge_provider
            )

            # Add evaluation to output data
            output_data["evaluation"] = {"judge_provider": judge_provider.value, "result": evaluation.model_dump()}

            # Display evaluation summary
            logger.info("Evaluation Summary:")
            logger.info(f"  - Accuracy: {evaluation.accuracy_score}/5")
            logger.info(f"  - Completeness: {evaluation.completeness_score}/5")
            logger.info(f"  - Clarity: {evaluation.clarity_score}/5")
            logger.info(f"  - Average Score: {evaluation.average_score:.2f}/5")
            logger.info(f"  - Feedback: {evaluation.feedback}")

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise

    # Save combined result
    output_file = f"outputs/{llm_provider.value}_{output_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

    logger.info(f"Results saved to: {output_file}")
    if enable_judge:
        logger.info("File contains both character generation and evaluation results")


if __name__ == "__main__":
    main()

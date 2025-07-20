import asyncio
from functools import wraps
from uuid import uuid4

import click
from google.genai.types import GenerateContentConfig

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
    help="The LLM provider to use.",
)
@async_cmd
async def main(
    llm_provider: LLMProvider = LLMProvider.GEMINI,
):
    logger.info(f"LLM provider: {llm_provider.value}")

    if llm_provider == LLMProvider.OPENAI:
        result = await request_openai()
    elif llm_provider == LLMProvider.GEMINI:
        result = await request_gemini()
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider.value}")

    result.save_as_json(f"{llm_provider.value}_{uuid4().hex}.json")


if __name__ == "__main__":
    main()

from google.genai.types import GenerateContentConfig
from src.client.llm_client import (
    AnthropicModel,
    GeminiModel,
    OpenAIModel,
    anthropic_client,
    google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.prompt.prompt import make_anthropic_prompt, make_gemini_prompt, make_openai_prompt

logger = make_logger(__name__)


async def request_openai(model: OpenAIModel) -> CharacterResponse:
    prompt = make_openai_prompt()
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    logger.info(result)
    return result.output_parsed


async def request_gemini(model: GeminiModel) -> CharacterResponse:
    system_prompt, user_prompt = make_gemini_prompt()
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=CharacterResponse,
        ),
    )
    logger.info(result)
    return result.parsed


async def request_anthropic(model: AnthropicModel) -> CharacterResponse:
    prompt = make_anthropic_prompt()
    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=1024,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=CharacterResponse,
    )

    logger.info(result)
    return result.parsed_output

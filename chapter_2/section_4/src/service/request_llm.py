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
from src.service.llmops_logger import LLMOpsLogger

logger = make_logger(__name__)


async def request_openai(
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    prompt = make_openai_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "openai", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=CharacterResponse,
        )
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        return result.output_parsed


async def request_gemini(
    model: GeminiModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    system_prompt, user_prompt = make_gemini_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=[system_prompt, user_prompt],
        user_id=user_id,
        metadata={"provider": "gemini", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=user_prompt,
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=CharacterResponse,
            ),
        )
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        await google_genai_client.aio.aclose()
        return result.parsed


async def request_anthropic(
    model: AnthropicModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    prompt = make_anthropic_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "gemini", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await anthropic_client.beta.messages.parse(
            model=model,
            max_tokens=1024,
            betas=["structured-outputs-2025-11-13"],
            messages=prompt,
            output_format=CharacterResponse,
        )
        tracking["response"] = result.parsed_output.model_dump() if result.parsed_output else None
        return result.parsed_output

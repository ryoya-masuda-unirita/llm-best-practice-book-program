from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.prompt.prompt import make_prompt
from src.service.llmops_logger import LLMOpsLogger

logger = make_logger(__name__)


async def request_openai(
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Request character generation from OpenAI with structured logging."""
    prompt = make_prompt()
    temperature = 1.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "openai", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=temperature,
        )
        parsed_response = result.choices[0].message.parsed
        tracking["response"] = parsed_response.model_dump() if parsed_response else None
        return parsed_response


async def request_gemini(
    model: GeminiModel, llmops_logger: LLMOpsLogger, user_id: str = "default_user"
) -> CharacterResponse:
    """Request character generation from Gemini with structured logging."""
    prompt = make_prompt()
    temperature = 2.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "gemini", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=temperature,
            ),
        )
        logger.info(result)
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        return result.parsed

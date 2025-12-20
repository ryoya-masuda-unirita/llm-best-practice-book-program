from google.genai.types import GenerateContentConfig
from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_gemini_prompt, make_openai_prompt

logger = make_logger(__name__)


async def request_openai(character_request: CharacterRequest, model: OpenAIModel) -> CharacterResponse:
    prompt = make_openai_prompt(character_request)
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    logger.info(result)
    return result.output_parsed


async def request_gemini(character_request: CharacterRequest, model: GeminiModel) -> CharacterResponse:
    system_prompt, user_prompt = make_gemini_prompt(character_request)
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

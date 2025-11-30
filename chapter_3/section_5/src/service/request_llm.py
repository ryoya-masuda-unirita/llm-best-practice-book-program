from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


async def request_gemini(model: GeminiModel, prompt: list[dict]) -> CharacterResponse:
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,
        ),
    )
    logger.info(result)
    return result.parsed

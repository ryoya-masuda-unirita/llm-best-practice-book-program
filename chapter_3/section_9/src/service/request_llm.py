from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.prompt.prompt import make_prompt

logger = make_logger(__name__)


async def request_openai(model: OpenAIModel) -> CharacterResponse:
    prompt = make_prompt()
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    return result.output_parsed


async def request_gemini(model: GeminiModel) -> CharacterResponse:
    prompt = make_prompt()
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

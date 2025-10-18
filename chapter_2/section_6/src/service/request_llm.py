from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse, Gender
from src.prompt.prompt import make_prompt

logger = make_logger(__name__)


async def request_openai(model: OpenAIModel) -> CharacterResponse:
    # Create a sample character request for demonstration
    character_request = CharacterRequest(
        gender=Gender.MALE,
        age=25,
        additional_instructions="このキャラクターは冒険好きで、好奇心旺盛です。",
    )
    prompt = make_prompt(character_request)
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed


async def request_gemini(model: GeminiModel) -> CharacterResponse:
    # Create a sample character request for demonstration
    character_request = CharacterRequest(
        gender=Gender.FEMALE,
        age=30,
        additional_instructions="このキャラクターは知的で、洞察力に優れています。",
    )
    prompt = make_prompt(character_request)
    result = await google_genai_client.aio.models.generate_content(
        model=model,
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

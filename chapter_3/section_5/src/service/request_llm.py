from src.client.llm_client import OpenAIModel, openai_client
from src.model.model import CharacterResponse


async def request_openai(model: OpenAIModel, prompt: list[dict]) -> CharacterResponse:
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    return result.output_parsed

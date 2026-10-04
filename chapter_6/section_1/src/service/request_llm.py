from src.client.llm_client import AnthropicModel, OpenAIModel, anthropic_client, openai_client
from src.logger import make_logger
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_anthropic_prompt, make_openai_prompt

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


async def request_anthropic(character_request: CharacterRequest, model: AnthropicModel) -> CharacterResponse:
    system_prompt, user_prompt = make_anthropic_prompt(character_request)
    result = await anthropic_client.messages.parse(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        output_format=CharacterResponse,
    )
    logger.info(result)
    return result.parsed_output

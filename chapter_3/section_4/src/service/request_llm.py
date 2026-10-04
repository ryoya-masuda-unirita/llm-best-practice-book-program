from src.client.llm_client import AnthropicModel, anthropic_client
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


async def request_anthropic(model: AnthropicModel, prompt: list[dict]) -> CharacterResponse:
    result = await anthropic_client.messages.parse(
        model=model,
        max_tokens=4096,
        system=prompt[0]["content"],
        messages=[{"role": "user", "content": prompt[-1]["content"]}],
        output_format=CharacterResponse,
    )
    logger.info(result)
    return result.parsed_output

from src.client.gateway_client import gateway_client
from src.client.llm_client import AnthropicModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


async def _request_llm(provider: LLMProvider, model: str, prompt: list[dict]) -> CharacterResponse:
    """Request character generation from an LLM provider via the gateway."""
    content, processing_time_ms, request_id = await gateway_client.generate(
        provider=provider.value,
        model=model,
        prompt=prompt,
        response_format=CharacterResponse.model_json_schema(),
        client_id="llm_server",
    )

    logger.info(f"Received response from gateway: request_id={request_id}, time={processing_time_ms:.2f}ms")

    return CharacterResponse.model_validate(content)


async def request_openai(model: OpenAIModel, prompt: list[dict]) -> CharacterResponse:
    """Request character generation from OpenAI via the gateway."""
    return await _request_llm(LLMProvider.OPENAI, model, prompt)


async def request_anthropic(model: AnthropicModel, prompt: list[dict]) -> CharacterResponse:
    """Request character generation from Anthropic via the gateway."""
    return await _request_llm(LLMProvider.ANTHROPIC, model, prompt)

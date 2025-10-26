from src.client.gateway_client import gateway_client
from src.client.llm_client import GeminiModel, OpenAIModel
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


async def request_openai(model: OpenAIModel, prompt: list[dict]) -> CharacterResponse:
    """Request character generation from OpenAI via the gateway.

    Args:
        model: OpenAI model to use
        prompt: Prompt messages

    Returns:
        Parsed character response
    """
    content, processing_time_ms, request_id = await gateway_client.generate(
        provider="openai",
        model=model,
        prompt=prompt,
        response_format=CharacterResponse.model_json_schema(),
        client_id="llm_server",
    )

    logger.info(f"Received response from gateway: request_id={request_id}, time={processing_time_ms:.2f}ms")

    # Parse the response into CharacterResponse
    return CharacterResponse.model_validate(content)


async def request_gemini(model: GeminiModel, prompt: list[dict]) -> CharacterResponse:
    """Request character generation from Gemini via the gateway.

    Args:
        model: Gemini model to use
        prompt: Prompt messages

    Returns:
        Parsed character response
    """
    content, processing_time_ms, request_id = await gateway_client.generate(
        provider="gemini",
        model=model,
        prompt=prompt,
        response_format=CharacterResponse.model_json_schema(),
        client_id="llm_server",
    )

    logger.info(f"Received response from gateway: request_id={request_id}, time={processing_time_ms:.2f}ms")

    # Parse the response into CharacterResponse
    return CharacterResponse.model_validate(content)

from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse
from src.model.model import CharacterResponse
from src.service.llm_as_a_judge import judge_with_gemini, judge_with_openai

logger = make_logger(__name__)


async def request_openai(prompt: list, model: OpenAIModel) -> CharacterResponse:
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed


async def request_gemini(prompt: list, model: GeminiModel) -> CharacterResponse:
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


async def request_with_judge(
    prompt: list,
    model: OpenAIModel | GeminiModel,
    provider: str,
    judge_model: OpenAIModel | GeminiModel | None = None,
    judge_provider: str | None = None,
) -> tuple[CharacterResponse, JudgeResponse]:
    """
    Request character generation and evaluate it using LLM-as-a-Judge.

    Args:
        prompt: The prompt for character generation
        model: The model to use for character generation
        provider: The provider for character generation ("openai" or "gemini")
        judge_model: The model to use for evaluation (defaults to same as generation model)
        judge_provider: The provider for evaluation (defaults to same as generation provider)

    Returns:
        Tuple of (CharacterResponse, JudgeResponse)
    """

    # Step 1: Generate character
    logger.info("Step 1: Generating character...")
    if provider == "openai":
        character_response = await request_openai(prompt=prompt, model=model)
    elif provider == "gemini":
        character_response = await request_gemini(prompt=prompt, model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    logger.info("Character generation completed.")

    # Step 2: Evaluate the generated character using LLM-as-a-Judge
    logger.info("Step 2: Evaluating character with LLM-as-a-Judge...")

    # Use same model/provider for judgment if not specified
    if judge_model is None:
        judge_model = model
    if judge_provider is None:
        judge_provider = provider

    # Create a judge request
    # Extract the user prompt from the messages
    user_prompt = next((msg["content"] for msg in prompt if msg["role"] == "user"), "キャラクターを生成してください。")

    judge_request = JudgeRequest(
        question=user_prompt,
        response=character_response.model_dump_json(indent=2, ensure_ascii=False),
        context=None,  # No reference context for creative generation
    )

    # Get judgment
    if judge_provider == "openai":
        judge_response = await judge_with_openai(judge_request=judge_request, model=judge_model)
    elif judge_provider == "gemini":
        judge_response = await judge_with_gemini(judge_request=judge_request, model=judge_model)
    else:
        raise ValueError(f"Unsupported judge provider: {judge_provider}")

    logger.info(f"Evaluation completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return character_response, judge_response

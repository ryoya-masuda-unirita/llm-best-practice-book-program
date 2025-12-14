from google.genai.types import GenerateContentConfig

from src.client.llm_client import (
    AnthropicModel,
    GeminiModel,
    LLMProvider,
    OpenAIModel,
    anthropic_client,
    google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service.llm_as_a_judge import judge_with_anthropic, judge_with_gemini, judge_with_openai

logger = make_logger(__name__)


async def request_openai(prompt: list, model: OpenAIModel) -> CharacterResponse:
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    logger.info(result)
    return result.output_parsed


async def request_gemini(prompt: tuple[str, str], model: GeminiModel) -> CharacterResponse:
    system_prompt, user_prompt = prompt
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=CharacterResponse,
            temperature=2.0,
        ),
    )
    logger.info(result)
    return result.parsed


async def request_anthropic(prompt: list, model: AnthropicModel) -> CharacterResponse:
    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=1024,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=CharacterResponse,
    )

    logger.info(result)
    return result.parsed_output


async def request_with_judge(
    character_request: CharacterRequest,
    model: OpenAIModel | GeminiModel | AnthropicModel,
    provider: str,
    judge_model: OpenAIModel | GeminiModel | AnthropicModel | None = None,
    judge_provider: str | None = None,
) -> tuple[CharacterResponse, JudgeResponse]:
    logger.info("Generating prompt...")
    prompt = make_prompt(character=character_request, provider=LLMProvider(provider))

    logger.info("Generating character...")
    if provider == LLMProvider.OPENAI:
        character_response = await request_openai(prompt=prompt, model=model)
    elif provider == LLMProvider.GEMINI:
        character_response = await request_gemini(prompt=prompt, model=model)
    elif provider == LLMProvider.ANTHROPIC:
        character_response = await request_anthropic(prompt=prompt, model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    logger.info("Character generation completed.")

    logger.info("Evaluating character with LLM-as-a-Judge...")

    if judge_model is None:
        judge_model = model
    if judge_provider is None:
        judge_provider = provider

    if isinstance(prompt, tuple):
        user_prompt = prompt[1]  # Gemini format: (system, user)
    else:
        user_prompt = next(
            (msg["content"] for msg in prompt if msg["role"] == "user"), "キャラクターを生成してください。"
        )

    request_params_str = f"""Gender: {character_request.gender.value}
Age: {character_request.age}
Additional Instructions: {character_request.additional_instructions or "None"}"""

    judge_request = JudgeRequest(
        question=user_prompt,
        response=character_response.model_dump_json(indent=2, ensure_ascii=False),
        context=None,
        request_parameters=request_params_str,
    )

    if judge_provider == LLMProvider.OPENAI:
        judge_response = await judge_with_openai(judge_request=judge_request, model=judge_model)
    elif judge_provider == LLMProvider.GEMINI:
        judge_response = await judge_with_gemini(judge_request=judge_request, model=judge_model)
    elif judge_provider == LLMProvider.ANTHROPIC:
        judge_response = await judge_with_anthropic(judge_request=judge_request, model=judge_model)
    else:
        raise ValueError(f"Unsupported judge provider: {judge_provider}")

    logger.info(f"Evaluation completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return character_response, judge_response

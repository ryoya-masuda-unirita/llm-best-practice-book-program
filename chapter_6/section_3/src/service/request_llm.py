import asyncio
from dataclasses import dataclass

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
from src.config import config
from src.logger import make_logger
from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service.llm_as_a_judge import judge_with_anthropic, judge_with_gemini, judge_with_openai

logger = make_logger(__name__)


@dataclass
class CandidateResult:
    candidate: CharacterResponse
    judge_result: JudgeResponse
    index: int


class AllCandidatesBelowThresholdError(Exception):
    pass


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


async def generate_single_candidate(
    prompt: list | tuple[str, str],
    model: OpenAIModel | GeminiModel | AnthropicModel,
    provider: str,
    index: int,
) -> CharacterResponse:
    logger.info(f"Generating candidate {index + 1}...")

    if provider == LLMProvider.OPENAI:
        return await request_openai(prompt=prompt, model=model)
    elif provider == LLMProvider.GEMINI:
        return await request_gemini(prompt=prompt, model=model)
    elif provider == LLMProvider.ANTHROPIC:
        return await request_anthropic(prompt=prompt, model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


async def evaluate_candidate(
    candidate: CharacterResponse,
    character_request: CharacterRequest,
    prompt: list | tuple[str, str],
    judge_model: OpenAIModel | GeminiModel | AnthropicModel,
    judge_provider: str,
    index: int,
) -> CandidateResult:
    logger.info(f"Evaluating candidate {index + 1} with LLM-as-a-Judge...")

    if isinstance(prompt, tuple):
        user_prompt = prompt[1]
    else:
        user_prompt = next(
            (msg["content"] for msg in prompt if msg["role"] == "user"), "キャラクターを生成してください。"
        )

    request_params_str = f"""Gender: {character_request.gender.value}
Age: {character_request.age}
Additional Instructions: {character_request.additional_instructions or "None"}"""

    judge_request = JudgeRequest(
        question=user_prompt,
        response=candidate.model_dump_json(indent=2, ensure_ascii=False),
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

    logger.info(f"Candidate {index + 1} score: {judge_response.overall_score:.2f}/5.0")

    return CandidateResult(candidate=candidate, judge_result=judge_response, index=index)


async def generate_and_evaluate_candidate(
    prompt: list | tuple[str, str],
    model: OpenAIModel | GeminiModel | AnthropicModel,
    provider: str,
    character_request: CharacterRequest,
    judge_model: OpenAIModel | GeminiModel | AnthropicModel,
    judge_provider: str,
    index: int,
) -> CandidateResult:
    candidate = await generate_single_candidate(prompt=prompt, model=model, provider=provider, index=index)
    return await evaluate_candidate(
        candidate=candidate,
        character_request=character_request,
        prompt=prompt,
        judge_model=judge_model,
        judge_provider=judge_provider,
        index=index,
    )


async def request_with_best_of_n(
    character_request: CharacterRequest,
    model: OpenAIModel | GeminiModel | AnthropicModel,
    provider: str,
    judge_model: OpenAIModel | GeminiModel | AnthropicModel | None = None,
    judge_provider: str | None = None,
    num_candidates: int | None = None,
    quality_threshold: float | None = None,
    max_retries: int | None = None,
) -> tuple[CharacterResponse, JudgeResponse]:
    if num_candidates is None:
        num_candidates = config.num_candidates
    if quality_threshold is None:
        quality_threshold = config.quality_threshold
    if max_retries is None:
        max_retries = config.max_retries
    if judge_model is None:
        judge_model = model
    if judge_provider is None:
        judge_provider = provider

    logger.info(f"Starting Best-of-{num_candidates} generation with threshold {quality_threshold:.1f}")
    logger.info(f"Generation: {provider}/{model}, Judge: {judge_provider}/{judge_model}")

    prompt = make_prompt(character=character_request, provider=LLMProvider(provider))

    for retry in range(max_retries):
        if retry > 0:
            logger.warning(f"Retry {retry}/{max_retries}: All candidates below threshold, regenerating...")

        tasks = [
            generate_and_evaluate_candidate(
                prompt=prompt,
                model=model,
                provider=provider,
                character_request=character_request,
                judge_model=judge_model,
                judge_provider=judge_provider,
                index=i,
            )
            for i in range(num_candidates)
        ]

        results: list[CandidateResult] = await asyncio.gather(*tasks)

        passing_candidates = [r for r in results if r.judge_result.is_passing(threshold=quality_threshold)]

        if passing_candidates:
            best_candidate = max(passing_candidates, key=lambda r: r.judge_result.overall_score)
            logger.info(
                f"Selected candidate {best_candidate.index + 1} with score {best_candidate.judge_result.overall_score:.2f}/5.0"
            )
            return best_candidate.candidate, best_candidate.judge_result

        scores = [r.judge_result.overall_score for r in results]
        logger.warning(f"All {num_candidates} candidates below threshold. Scores: {scores}")

    logger.error(f"All {max_retries} retry attempts exhausted. Returning best available candidate.")
    best_overall = max(results, key=lambda r: r.judge_result.overall_score)
    logger.warning(
        f"Fallback: Using candidate {best_overall.index + 1} with score {best_overall.judge_result.overall_score:.2f}/5.0 (below threshold)"
    )
    return best_overall.candidate, best_overall.judge_result


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
        user_prompt = prompt[1]
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

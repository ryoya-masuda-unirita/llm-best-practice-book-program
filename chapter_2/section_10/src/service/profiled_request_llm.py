"""Profiled LLM request service with performance monitoring."""

from typing import Optional

# from google.genai.types import GenerateContentConfig
from src.client.llm_client import (
    AnthropicModel,
    # GeminiModel,
    LLMProvider,
    OpenAIModel,
    anthropic_client,
    # google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse
from src.model.model import CharacterRequest, CharacterResponse
from src.prompt.prompt import make_prompt
from src.service.llm_as_a_judge import judge_with_anthropic, judge_with_openai  # , judge_with_gemini
from src.service.prompt_profiler import PromptProfiler, get_default_profiler

logger = make_logger(__name__)


async def profiled_request_openai(
    prompt: list,
    model: OpenAIModel,
    prompt_id: str = "character_generation",
    profiler: Optional[PromptProfiler] = None,
) -> CharacterResponse:
    """Request character generation from OpenAI with profiling."""
    profiler = profiler or get_default_profiler()

    async with profiler.profile(
        prompt_id=prompt_id,
        model=model,
        provider="openai",
        prompt_name="Character Generation (OpenAI)",
    ) as ctx:
        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=CharacterResponse,
        )

        if hasattr(result, "usage"):
            ctx["input_tokens"] = result.usage.input_tokens
            ctx["output_tokens"] = result.usage.output_tokens
        else:
            ctx["input_tokens"] = sum(len(m.get("content", "")) // 4 for m in prompt)
            ctx["output_tokens"] = len(result.output_parsed.model_dump_json()) // 4

        ctx["response"] = result.output_parsed
        logger.info(result)

    return result.output_parsed


# async def profiled_request_gemini(
#     prompt: tuple[str, str],
#     model: GeminiModel,
#     prompt_id: str = "character_generation",
#     profiler: Optional[PromptProfiler] = None,
# ) -> CharacterResponse:
#     """Request character generation from Gemini with profiling."""
#     profiler = profiler or get_default_profiler()
#     system_prompt, user_prompt = prompt
#
#     async with profiler.profile(
#         prompt_id=prompt_id,
#         model=model,
#         provider="gemini",
#         prompt_name="Character Generation (Gemini)",
#     ) as ctx:
#         result = await google_genai_client.aio.models.generate_content(
#             model=model,
#             contents=user_prompt,
#             config=GenerateContentConfig(
#                 system_instruction=system_prompt,
#                 response_mime_type="application/json",
#                 response_schema=CharacterResponse,
#                 temperature=2.0,
#             ),
#         )
#
#         if hasattr(result, "usage_metadata"):
#             ctx["input_tokens"] = result.usage_metadata.prompt_token_count or 0
#             ctx["output_tokens"] = result.usage_metadata.candidates_token_count or 0
#         else:
#             ctx["input_tokens"] = (len(system_prompt) + len(user_prompt)) // 4
#             ctx["output_tokens"] = len(result.text) // 4 if result.text else 0
#
#         ctx["response"] = result.parsed
#         logger.info(result)
#
#     return result.parsed


async def profiled_request_anthropic(
    prompt: list,
    model: AnthropicModel,
    prompt_id: str = "character_generation",
    profiler: Optional[PromptProfiler] = None,
) -> CharacterResponse:
    """Request character generation from Anthropic with profiling."""
    profiler = profiler or get_default_profiler()

    async with profiler.profile(
        prompt_id=prompt_id,
        model=model,
        provider="anthropic",
        prompt_name="Character Generation (Anthropic)",
    ) as ctx:
        result = await anthropic_client.messages.parse(
            model=model,
            max_tokens=1024,
            messages=prompt,
            output_format=CharacterResponse,
        )

        if hasattr(result, "usage"):
            ctx["input_tokens"] = result.usage.input_tokens
            ctx["output_tokens"] = result.usage.output_tokens
        else:
            ctx["input_tokens"] = sum(len(m.get("content", "")) // 4 for m in prompt)
            ctx["output_tokens"] = len(result.parsed_output.model_dump_json()) // 4

        ctx["response"] = result.parsed_output
        logger.info(result)

    return result.parsed_output


async def profiled_request_with_judge(
    character_request: CharacterRequest,
    model: OpenAIModel | AnthropicModel,
    provider: str,
    judge_model: OpenAIModel | AnthropicModel | None = None,
    judge_provider: str | None = None,
    profiler: Optional[PromptProfiler] = None,
) -> tuple[CharacterResponse, JudgeResponse]:
    """Request character generation and evaluate it using LLM-as-a-Judge, with profiling."""
    profiler = profiler or get_default_profiler()

    logger.info("Generating prompt...")
    prompt = make_prompt(character=character_request, provider=LLMProvider(provider))

    logger.info("Generating character...")
    prompt_id = f"character_generation_{provider}"

    if provider == LLMProvider.OPENAI:
        character_response = await profiled_request_openai(
            prompt=prompt,
            model=model,
            prompt_id=prompt_id,
            profiler=profiler,
        )
    # elif provider == LLMProvider.GEMINI:
    #     character_response = await profiled_request_gemini(
    #         prompt=prompt,
    #         model=model,
    #         prompt_id=prompt_id,
    #         profiler=profiler,
    #     )
    elif provider == LLMProvider.ANTHROPIC:
        character_response = await profiled_request_anthropic(
            prompt=prompt,
            model=model,
            prompt_id=prompt_id,
            profiler=profiler,
        )
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
            (msg["content"] for msg in prompt if msg["role"] == "user"),
            "キャラクターを生成してください。",
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

    judge_prompt_id = f"llm_as_a_judge_{judge_provider}"

    async with profiler.profile(
        prompt_id=judge_prompt_id,
        model=str(judge_model),
        provider=judge_provider,
        prompt_name=f"LLM-as-a-Judge ({judge_provider})",
    ) as ctx:
        if judge_provider == LLMProvider.OPENAI:
            judge_response = await judge_with_openai(judge_request=judge_request, model=judge_model)
        # elif judge_provider == LLMProvider.GEMINI:
        #     judge_response = await judge_with_gemini(judge_request=judge_request, model=judge_model)
        elif judge_provider == LLMProvider.ANTHROPIC:
            judge_response = await judge_with_anthropic(judge_request=judge_request, model=judge_model)
        else:
            raise ValueError(f"Unsupported judge provider: {judge_provider}")

        ctx["quality_score"] = judge_response.overall_score
        ctx["quality_details"] = {
            "evaluations": [e.model_dump() for e in judge_response.evaluations],
            "summary": judge_response.summary,
        }

        ctx["input_tokens"] = len(judge_request.question + judge_request.response) // 4
        ctx["output_tokens"] = len(judge_response.model_dump_json()) // 4

    logger.info(f"Evaluation completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    generation_metrics = await profiler.get_metrics(prompt_id=prompt_id, limit=1)
    if generation_metrics:
        last_metric = generation_metrics[-1]
        await profiler.record_metrics(
            prompt_id=f"{prompt_id}_with_quality",
            model=str(model),
            provider=provider,
            latency_ms=last_metric.latency_ms,
            input_tokens=last_metric.input_tokens,
            output_tokens=last_metric.output_tokens,
            quality_score=judge_response.overall_score,
            quality_details={
                "evaluations": [e.model_dump() for e in judge_response.evaluations],
                "summary": judge_response.summary,
            },
        )

    return character_response, judge_response


async def get_profiler_summary(profiler: Optional[PromptProfiler] = None) -> dict:
    """Get a summary of collected profiler metrics."""
    from src.service.metrics_analyzer import MetricsAnalyzer
    from src.service.profiler_reporter import ProfilerReporter

    profiler = profiler or get_default_profiler()
    metrics = await profiler.get_metrics()

    if not metrics:
        return {"message": "No metrics collected yet"}

    analyzer = MetricsAnalyzer()
    reporter = ProfilerReporter(analyzer)

    return reporter.generate_json_report(metrics)

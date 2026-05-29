"""LLM-as-a-Judge service for evaluating LLM responses."""

from google.genai.types import GenerateContentConfig
from src.client.llm_client import (
    AnthropicModel,
    GeminiModel,
    OpenAIModel,
    anthropic_client,
    google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse
from src.prompt.llm_as_a_judge_prompt import (
    make_anthropic_judge_prompt,
    make_gemini_judge_prompt,
    make_openai_judge_prompt,
)

logger = make_logger(__name__)


async def judge_with_openai(
    judge_request: JudgeRequest,
    model: OpenAIModel,
) -> JudgeResponse:
    """Evaluate a response using OpenAI as the judge."""
    prompt = make_openai_judge_prompt(judge_request)

    logger.info(f"Requesting judgment from OpenAI model: {model}")

    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=JudgeResponse,
    )

    judge_response = result.output_parsed
    logger.info(f"Judgment completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return judge_response


async def judge_with_gemini(
    judge_request: JudgeRequest,
    model: GeminiModel,
) -> JudgeResponse:
    """Evaluate a response using Gemini as the judge."""
    system_prompt, user_prompt = make_gemini_judge_prompt(judge_request)

    logger.info(f"Requesting judgment from Gemini model: {model}")

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=JudgeResponse,
            temperature=0.0,
        ),
    )

    judge_response = result.parsed
    logger.info(f"Judgment completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return judge_response


async def judge_with_anthropic(
    judge_request: JudgeRequest,
    model: AnthropicModel,
) -> JudgeResponse:
    """Evaluate a response using Anthropic as the judge."""
    prompt = make_anthropic_judge_prompt(judge_request)

    logger.info(f"Requesting judgment from Anthropic model: {model}")

    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=JudgeResponse,
    )

    judge_response = result.parsed_output
    logger.info(f"Judgment completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return judge_response

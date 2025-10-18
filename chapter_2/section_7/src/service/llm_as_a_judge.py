"""LLM-as-a-Judge service for evaluating LLM responses."""

from google.genai.types import GenerateContentConfig

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.llm_as_a_judge_model import JudgeRequest, JudgeResponse
from src.prompt.llm_as_a_judge_prompt import make_judge_prompt

logger = make_logger(__name__)


async def judge_with_openai(
    judge_request: JudgeRequest,
    model: OpenAIModel,
) -> JudgeResponse:
    """
    Evaluate a response using OpenAI as the judge.

    Args:
        judge_request: The request containing question, response, and optional context
        model: The OpenAI model to use for evaluation

    Returns:
        JudgeResponse with evaluation results
    """
    prompt = make_judge_prompt(judge_request)

    logger.info(f"Requesting judgment from OpenAI model: {model}")

    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=JudgeResponse,
    )

    judge_response = result.choices[0].message.parsed
    logger.info(f"Judgment completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return judge_response


async def judge_with_gemini(
    judge_request: JudgeRequest,
    model: GeminiModel,
) -> JudgeResponse:
    """
    Evaluate a response using Gemini as the judge.

    Args:
        judge_request: The request containing question, response, and optional context
        model: The Gemini model to use for evaluation

    Returns:
        JudgeResponse with evaluation results
    """
    prompt = make_judge_prompt(judge_request)

    logger.info(f"Requesting judgment from Gemini model: {model}")

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=JudgeResponse,
        ),
    )

    judge_response = result.parsed
    logger.info(f"Judgment completed. Overall score: {judge_response.overall_score:.2f}/5.0")

    return judge_response

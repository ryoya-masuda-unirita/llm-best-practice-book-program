import json

from src.client.llm_client import GeminiModel, google_genai_client
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


def submit_gemini_batch(
    model: GeminiModel,
    prompts: list[tuple[str, str]],
) -> str:
    """
    Submit a batch job to Gemini batch API.

    Args:
        model: Gemini model to use
        prompts: List of (system_prompt, user_prompt) tuples

    Returns:
        Batch job name for tracking
    """
    inline_requests = [
        {
            "contents": [
                {"parts": [{"text": user_prompt}], "role": "user"},
            ],
            "config": {
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": CharacterResponse,
            },
        }
        for system_prompt, user_prompt in prompts
    ]

    inline_batch_job = google_genai_client.batches.create(
        model=f"models/{model}",
        src=inline_requests,
        config={"display_name": "character-generation-batch"},
    )

    logger.info(f"Submitted batch job: {inline_batch_job.name}")
    return inline_batch_job.name


def get_gemini_batch_status(batch_job_name: str) -> str:
    """
    Get the status of a Gemini batch job.

    Args:
        batch_job_name: The batch job name returned from submit_gemini_batch

    Returns:
        Job state name (e.g., "JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED")
    """
    batch_job = google_genai_client.batches.get(name=batch_job_name)
    return batch_job.state.name


def get_gemini_batch_results(batch_job_name: str) -> list[CharacterResponse | None]:
    """
    Get results from a completed Gemini batch job.

    Args:
        batch_job_name: The batch job name returned from submit_gemini_batch

    Returns:
        List of CharacterResponse objects (or None for failed requests)

    Raises:
        RuntimeError: If the job has not succeeded
    """
    batch_job = google_genai_client.batches.get(name=batch_job_name)

    if batch_job.state.name != "JOB_STATE_SUCCEEDED":
        raise RuntimeError(f"Cannot get results: job state is {batch_job.state.name}")

    results: list[CharacterResponse | None] = []
    for idx, inline_response in enumerate(batch_job.dest.inlined_responses):
        try:
            if inline_response.response and inline_response.response.candidates:
                text = inline_response.response.candidates[0].content.parts[0].text
                response = json.loads(text)
                result = CharacterResponse(**response)
                results.append(result)
            else:
                logger.warning(f"Task {idx}: No response or candidates in inline_response")
                results.append(None)
        except (json.JSONDecodeError, IndexError, AttributeError, KeyError) as e:
            logger.warning(f"Task {idx}: Failed to parse response: {e}")
            results.append(None)
        except Exception as e:
            logger.warning(f"Task {idx}: Unexpected error parsing response: {e}")
            results.append(None)

    return results

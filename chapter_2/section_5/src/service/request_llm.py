import json
import time

from src.client.llm_client import (
    GeminiModel,
    google_genai_client,
)
from src.logger import make_logger
from src.model.model import CharacterResponse
from src.prompt.prompt import make_gemini_prompt

logger = make_logger(__name__)


def request_gemini(
    model: GeminiModel,
    num: int = 10,
) -> list[CharacterResponse]:
    system_prompt, user_prompt = make_gemini_prompt()

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
        for _ in range(num)
    ]

    inline_batch_job = google_genai_client.batches.create(
        model=f"models/{model}",
        src=inline_requests,
        config={"display_name": "structured-output-job-1"},
    )

    logger.info(f"Triggered job name: {inline_batch_job.name}")

    while True:
        batch_job_inline = google_genai_client.batches.get(name=inline_batch_job.name)
        if batch_job_inline.state.name in ("JOB_STATE_SUCCEEDED",):
            logger.info(f"""Batch job status: {batch_job_inline.state.name}""")
            break
        if batch_job_inline.state.name in (
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
        ):
            raise RuntimeError(f"Batch job failed with state: {batch_job_inline.state.name}")
        logger.info(f"Job not finished. Current state: {batch_job_inline.state.name}. Waiting 5 seconds...")
        time.sleep(5)

    results: list[CharacterResponse] = []
    for i, inline_response in enumerate(batch_job_inline.dest.inlined_responses):
        if inline_response.response:
            response = json.loads(inline_response.response.text)
            result = CharacterResponse(**response)
            results.append(result)

    return results

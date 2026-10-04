from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable
from uuid import uuid4

from src.client.llm_client import (
    anthropic_client,
    # google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


# ---------------------------------------------------------------------------
# Batch runner
#
# Bedrock経由では各社のBatch API（OpenAI Batch API / Anthropic Message Batches）を
# 利用できない。Bedrock独自のバッチ推論はS3とIAMロールが必要で、1ジョブ100件以上
# という下限もあるため、ここでは通常のリクエストを並列に実行して同じ
# submit / status / results のインターフェイスを提供する。
# ---------------------------------------------------------------------------

BATCH_MAX_WORKERS = 5

_executor = ThreadPoolExecutor(max_workers=BATCH_MAX_WORKERS)
_batches: dict[str, list[Future]] = {}


def _submit_batch(request_func: Callable[[str, object], CharacterResponse], model: str, prompts: list) -> str:
    batch_id = f"batch_{uuid4().hex}"
    _batches[batch_id] = [_executor.submit(request_func, model, prompt) for prompt in prompts]
    return batch_id


def _is_batch_done(batch_id: str) -> bool:
    return all(future.done() for future in _batches[batch_id])


def _collect_batch_results(batch_id: str, provider_name: str) -> list[CharacterResponse | None]:
    results: list[CharacterResponse | None] = []
    for idx, future in enumerate(_batches.pop(batch_id)):
        try:
            results.append(future.result())
        except Exception as e:
            logger.warning(f"{provider_name} task {idx}: Request failed: {e}")
            results.append(None)
    return results


# # ---------------------------------------------------------------------------
# # Gemini Batch API
# # ---------------------------------------------------------------------------
#
#
# def submit_gemini_batch(
#     model: str,
#     prompts: list[tuple[str, str]],
# ) -> str:
#     inline_requests = [
#         {
#             "contents": [
#                 {"parts": [{"text": user_prompt}], "role": "user"},
#             ],
#             "config": {
#                 "system_instruction": system_prompt,
#                 "response_mime_type": "application/json",
#                 "response_schema": CharacterResponse,
#             },
#         }
#         for system_prompt, user_prompt in prompts
#     ]
#
#     inline_batch_job = google_genai_client.batches.create(
#         model=f"models/{model}",
#         src=inline_requests,
#         config={"display_name": "character-generation-batch"},
#     )
#
#     logger.info(f"Submitted Gemini batch job: {inline_batch_job.name}")
#     return inline_batch_job.name
#
#
# def get_gemini_batch_status(batch_job_name: str) -> str:
#     batch_job = google_genai_client.batches.get(name=batch_job_name)
#     return batch_job.state.name
#
#
# def get_gemini_batch_results(batch_job_name: str) -> list[CharacterResponse | None]:
#     batch_job = google_genai_client.batches.get(name=batch_job_name)
#
#     if batch_job.state.name != "JOB_STATE_SUCCEEDED":
#         raise RuntimeError(f"Cannot get results: job state is {batch_job.state.name}")
#
#     results: list[CharacterResponse | None] = []
#     for idx, inline_response in enumerate(batch_job.dest.inlined_responses):
#         try:
#             if inline_response.response and inline_response.response.candidates:
#                 text = inline_response.response.candidates[0].content.parts[0].text
#                 response = json.loads(text)
#                 result = CharacterResponse(**response)
#                 results.append(result)
#             else:
#                 logger.warning(f"Gemini task {idx}: No response or candidates")
#                 results.append(None)
#         except (json.JSONDecodeError, IndexError, AttributeError, KeyError) as e:
#             logger.warning(f"Gemini task {idx}: Failed to parse response: {e}")
#             results.append(None)
#         except Exception as e:
#             logger.warning(f"Gemini task {idx}: Unexpected error: {e}")
#             results.append(None)
#
#     return results


# ---------------------------------------------------------------------------
# OpenAI (via Amazon Bedrock)
# ---------------------------------------------------------------------------


def _request_openai(model: str, messages: list[dict]) -> CharacterResponse:
    result = openai_client.responses.parse(
        model=model,
        input=messages,
        text_format=CharacterResponse,
    )
    return result.output_parsed


def submit_openai_batch(
    model: str,
    prompts: list[list[dict]],
) -> str:
    batch_id = _submit_batch(_request_openai, model, prompts)

    logger.info(f"Submitted OpenAI batch job: {batch_id}")
    return batch_id


def get_openai_batch_status(batch_id: str) -> str:
    if batch_id not in _batches:
        return "failed"
    return "completed" if _is_batch_done(batch_id) else "in_progress"


def get_openai_batch_results(batch_id: str) -> list[CharacterResponse | None]:
    status = get_openai_batch_status(batch_id)

    if status != "completed":
        raise RuntimeError(f"Cannot get results: batch status is {status}")

    return _collect_batch_results(batch_id, "OpenAI")


# ---------------------------------------------------------------------------
# Anthropic (via Amazon Bedrock)
# ---------------------------------------------------------------------------


def _request_anthropic(model: str, prompt: tuple[str, list[dict]]) -> CharacterResponse:
    system_text, messages = prompt
    result = anthropic_client.messages.parse(
        model=model,
        max_tokens=4096,
        system=system_text,
        messages=messages,
        output_format=CharacterResponse,
    )
    return result.parsed_output


def submit_anthropic_batch(
    model: str,
    prompts: list[tuple[str, list[dict]]],
) -> str:
    batch_id = _submit_batch(_request_anthropic, model, prompts)

    logger.info(f"Submitted Anthropic batch job: {batch_id}")
    return batch_id


def get_anthropic_batch_status(batch_id: str) -> str:
    return "ended" if _is_batch_done(batch_id) else "in_progress"


def get_anthropic_batch_results(batch_id: str) -> list[CharacterResponse | None]:
    return _collect_batch_results(batch_id, "Anthropic")

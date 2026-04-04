import io
import json

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from src.client.llm_client import (
    anthropic_client,
    google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.model import CharacterResponse

logger = make_logger(__name__)


# ---------------------------------------------------------------------------
# Gemini Batch API
# ---------------------------------------------------------------------------


def submit_gemini_batch(
    model: str,
    prompts: list[tuple[str, str]],
) -> str:
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

    logger.info(f"Submitted Gemini batch job: {inline_batch_job.name}")
    return inline_batch_job.name


def get_gemini_batch_status(batch_job_name: str) -> str:
    batch_job = google_genai_client.batches.get(name=batch_job_name)
    return batch_job.state.name


def get_gemini_batch_results(batch_job_name: str) -> list[CharacterResponse | None]:
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
                logger.warning(f"Gemini task {idx}: No response or candidates")
                results.append(None)
        except (json.JSONDecodeError, IndexError, AttributeError, KeyError) as e:
            logger.warning(f"Gemini task {idx}: Failed to parse response: {e}")
            results.append(None)
        except Exception as e:
            logger.warning(f"Gemini task {idx}: Unexpected error: {e}")
            results.append(None)

    return results


# ---------------------------------------------------------------------------
# OpenAI Batch API
# ---------------------------------------------------------------------------


def submit_openai_batch(
    model: str,
    prompts: list[list[dict]],
) -> str:
    lines = []
    for idx, messages in enumerate(prompts):
        request_obj = {
            "custom_id": f"task-{idx}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
        }
        lines.append(json.dumps(request_obj, ensure_ascii=False))

    jsonl_content = "\n".join(lines)
    buffer = io.BytesIO(jsonl_content.encode("utf-8"))
    buffer.name = "batch_requests.jsonl"

    uploaded_file = openai_client.files.create(file=buffer, purpose="batch")
    logger.info(f"Uploaded OpenAI batch file: {uploaded_file.id}")

    batch = openai_client.batches.create(
        input_file_id=uploaded_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )

    logger.info(f"Submitted OpenAI batch job: {batch.id}")
    return batch.id


def get_openai_batch_status(batch_id: str) -> str:
    batch = openai_client.batches.retrieve(batch_id)
    return batch.status


def get_openai_batch_results(batch_id: str) -> list[CharacterResponse | None]:
    batch = openai_client.batches.retrieve(batch_id)

    if batch.status != "completed":
        raise RuntimeError(f"Cannot get results: batch status is {batch.status}")

    if not batch.output_file_id:
        raise RuntimeError("No output file available for completed batch")

    content = openai_client.files.content(batch.output_file_id)
    result_lines = content.text.strip().split("\n")

    indexed_results: list[tuple[int, CharacterResponse | None]] = []
    for line in result_lines:
        try:
            entry = json.loads(line)
            custom_id = entry.get("custom_id", "")
            idx = int(custom_id.replace("task-", "")) if custom_id.startswith("task-") else len(indexed_results)

            response_body = entry.get("response", {}).get("body", {})
            choices = response_body.get("choices", [])
            if choices:
                message_content = choices[0].get("message", {}).get("content", "")
                parsed = json.loads(message_content)
                indexed_results.append((idx, CharacterResponse(**parsed)))
            else:
                logger.warning(f"OpenAI task {custom_id}: No choices in response")
                indexed_results.append((idx, None))
        except (json.JSONDecodeError, IndexError, KeyError, ValueError) as e:
            logger.warning(f"OpenAI result line parse error: {e}")
            indexed_results.append((len(indexed_results), None))
        except Exception as e:
            logger.warning(f"OpenAI result unexpected error: {e}")
            indexed_results.append((len(indexed_results), None))

    indexed_results.sort(key=lambda x: x[0])
    return [r for _, r in indexed_results]


# ---------------------------------------------------------------------------
# Anthropic Batch API
# ---------------------------------------------------------------------------


def submit_anthropic_batch(
    model: str,
    prompts: list[tuple[str, list[dict]]],
) -> str:
    requests = []
    for idx, (system_text, messages) in enumerate(prompts):
        requests.append(
            Request(
                custom_id=f"task-{idx}",
                params=MessageCreateParamsNonStreaming(
                    model=model,
                    max_tokens=1024,
                    system=system_text,
                    messages=messages,
                ),
            )
        )

    batch = anthropic_client.messages.batches.create(requests=requests)

    logger.info(f"Submitted Anthropic batch job: {batch.id}")
    return batch.id


def get_anthropic_batch_status(batch_id: str) -> str:
    batch = anthropic_client.messages.batches.retrieve(batch_id)
    return batch.processing_status


def _extract_json_text(content_blocks: list) -> str:
    """Extract JSON text from Anthropic message content blocks."""
    for block in content_blocks:
        if hasattr(block, "text") and block.text:
            text = block.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first line (```json or ```) and last line (```)
                lines = [line for line in lines if not line.strip().startswith("```")]
                text = "\n".join(lines).strip()
            if text.startswith("{"):
                return text
    return ""


def get_anthropic_batch_results(batch_id: str) -> list[CharacterResponse | None]:
    indexed_results: list[tuple[int, CharacterResponse | None]] = []

    for entry in anthropic_client.messages.batches.results(batch_id):
        custom_id = entry.custom_id
        idx = int(custom_id.replace("task-", "")) if custom_id.startswith("task-") else len(indexed_results)

        try:
            if entry.result.type == "succeeded":
                text = _extract_json_text(entry.result.message.content)
                if not text:
                    logger.warning(f"Anthropic task {custom_id}: No JSON text found in response")
                    indexed_results.append((idx, None))
                    continue
                parsed = json.loads(text)
                indexed_results.append((idx, CharacterResponse(**parsed)))
            else:
                logger.warning(f"Anthropic task {custom_id}: result type={entry.result.type}")
                indexed_results.append((idx, None))
        except (json.JSONDecodeError, IndexError, AttributeError, KeyError) as e:
            logger.warning(f"Anthropic task {custom_id}: Failed to parse: {e}")
            indexed_results.append((idx, None))
        except Exception as e:
            logger.warning(f"Anthropic task {custom_id}: Unexpected error: {e}")
            indexed_results.append((idx, None))

    indexed_results.sort(key=lambda x: x[0])
    return [r for _, r in indexed_results]

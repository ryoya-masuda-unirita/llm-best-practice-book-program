"""
Data Analysis LLM Application

A CLI for analyzing school data using Gemini with function calling.
Demonstrates the ID reference pattern and composite functions for efficient LLM tool usage.
"""

import asyncio
import json
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

import click
from google.genai import types
from src.client import GeminiModel, google_genai_client
from src.logger import make_logger
from src.service.request_llm import SessionResultCache, process_with_tool_chain

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def content_to_dict(content: types.Content) -> dict:
    """Convert a Content object to a JSON-serializable dict."""
    parts_data = []
    for part in content.parts:
        part_dict = {}
        if part.text:
            part_dict["text"] = part.text
        if part.function_call:
            part_dict["function_call"] = {
                "name": part.function_call.name,
                "args": dict(part.function_call.args) if part.function_call.args else {},
            }
        if part.function_response:
            part_dict["function_response"] = {
                "name": part.function_response.name,
                "response": part.function_response.response,
            }
        parts_data.append(part_dict)

    return {
        "role": content.role,
        "parts": parts_data,
    }


def serialize_session_context(
    session_id: str,
    model: str,
    query: str,
    conversation_history: list[types.Content],
    session_cache: SessionResultCache,
    response_text: str,
    start_time: datetime,
    end_time: datetime,
) -> dict:
    """Serialize session context to a JSON-serializable dict."""
    return {
        "session_id": session_id,
        "model": model,
        "query": query,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "conversation_history": [content_to_dict(c) for c in conversation_history],
        "session_cache": {
            "result_ids": list(session_cache.results.keys()),
            "results": session_cache.results,
        },
        "response_length": len(response_text),
    }


def save_session_outputs(
    output_dir: Path,
    session_id: str,
    session_context: dict,
    response_text: str,
) -> tuple[Path, Path]:
    """Save session log (JSON) and result (Markdown) to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / f"{session_id}_session_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(session_context, f, ensure_ascii=False, indent=2)

    result_path = output_dir / f"{session_id}_result.md"
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(response_text)

    return log_path, result_path


@click.command()
@click.option(
    "--model",
    "-m",
    type=click.Choice(GeminiModel.list_str()),
    required=False,
    default=GeminiModel.GEMINI_2_5_FLASH,
    help="The Gemini model to use for analysis.",
)
@click.option(
    "--query",
    "-q",
    type=str,
    required=True,
    help="The query to analyze.",
)
@click.option(
    "--output-directory",
    "-od",
    type=click.Path(path_type=Path),
    required=False,
    default=None,
    help="Directory to save session log (JSON) and result (Markdown). Files are named with UUID prefix.",
)
@async_cmd
async def main(model: str, query: str, output_directory: Path | None):
    """
    Data analysis assistant powered by Gemini.

    Analyzes school data including student records, test scores,
    grade reports, and curriculum information.
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()

    logger.info(f"Session ID: {session_id}")
    logger.info(f"Starting data analysis with model: {model}")
    logger.info(f"Query: {query}")

    conversation_history: list[types.Content] = []
    session_cache = SessionResultCache()

    response, conversation_history, session_cache = await process_with_tool_chain(
        model=model,
        user_message=query,
        conversation_history=conversation_history,
        session_cache=session_cache,
    )

    end_time = datetime.now()

    click.echo(response)

    if output_directory:
        session_context = serialize_session_context(
            session_id=session_id,
            model=model,
            query=query,
            conversation_history=conversation_history,
            session_cache=session_cache,
            response_text=response,
            start_time=start_time,
            end_time=end_time,
        )

        log_path, result_path = save_session_outputs(
            output_dir=output_directory,
            session_id=session_id,
            session_context=session_context,
            response_text=response,
        )

        click.echo(f"\nSession log saved: {log_path}")
        click.echo(f"Result saved: {result_path}")

    await google_genai_client.aio.aclose()


if __name__ == "__main__":
    main()

"""
Data Analysis LLM Application

A CLI for analyzing school data using Anthropic with function calling.
Demonstrates the ID reference pattern and composite functions for efficient LLM tool usage.
"""

import asyncio
import json
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

import click
from anthropic.types import MessageParam
from src.client import AnthropicModel, anthropic_client
from src.logger import make_logger
from src.service.request_llm import SessionResultCache, process_with_tool_chain

logger = make_logger(__name__)


def async_cmd(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def content_to_dict(content: MessageParam) -> dict:
    """Convert a conversation message to a JSON-serializable dict."""
    blocks = content["content"]
    if isinstance(blocks, str):
        return {"role": content["role"], "parts": [{"text": blocks}]}

    parts_data = []
    for block in blocks:
        part_dict = {}
        if isinstance(block, dict):
            if block.get("type") == "tool_result":
                part_dict["function_response"] = {
                    "tool_use_id": block["tool_use_id"],
                    "response": json.loads(block["content"]),
                }
        elif block.type == "text":
            part_dict["text"] = block.text
        elif block.type == "tool_use":
            part_dict["function_call"] = {
                "name": block.name,
                "args": dict(block.input) if block.input else {},
            }
        parts_data.append(part_dict)

    return {
        "role": content["role"],
        "parts": parts_data,
    }


def serialize_session_context(
    session_id: str,
    model: str,
    query: str,
    conversation_history: list[MessageParam],
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
    type=click.Choice(AnthropicModel.list_str()),
    required=False,
    default=AnthropicModel.CLAUDE_HAIKU_4_5,
    help="The Anthropic model to use for analysis.",
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
    Data analysis assistant powered by Anthropic.

    Analyzes school data including student records, test scores,
    grade reports, and curriculum information.
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()

    logger.info(f"Session ID: {session_id}")
    logger.info(f"Starting data analysis with model: {model}")
    logger.info(f"Query: {query}")

    conversation_history: list[MessageParam] = []
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

    await anthropic_client.close()


if __name__ == "__main__":
    main()

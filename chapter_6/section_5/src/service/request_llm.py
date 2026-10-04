"""
Service layer for LLM requests with function calling support.

This module handles the interaction with Anthropic API, including
function call execution and response processing.

Implements the ID reference pattern from CLAUDE.md:
- Store full tool results in a session cache (not in LLM context)
- Pass only summary + result_id to LLM context
- LLM can retrieve detailed data when needed via get_result_details
"""

import json
from dataclasses import dataclass, field

from anthropic.types import MessageParam, ToolUseBlock
from src.client import AnthropicModel, anthropic_client
from src.logger import make_logger
from src.prompt import get_system_prompt, get_tools
from src.service.tools import TOOL_FUNCTIONS

logger = make_logger(__name__)


@dataclass
class SessionResultCache:
    """
    Session-level cache for storing tool call results.

    This implements the ID reference pattern where full results are stored
    separately from the LLM context. The LLM receives only summaries and
    result IDs, and can request detailed data when needed.

    Attributes:
        results: Dict mapping result_id to full result data
        max_size: Maximum number of results to cache (oldest are evicted)
    """

    results: dict[str, dict] = field(default_factory=dict)
    max_size: int = 100

    def store(self, result_id: str, data: dict) -> None:
        """Store result data by ID, evicting oldest if at capacity."""
        if len(self.results) >= self.max_size:
            oldest_key = next(iter(self.results))
            del self.results[oldest_key]
            logger.debug(f"Evicted oldest result from cache: {oldest_key}")

        self.results[result_id] = data
        logger.debug(f"Cached result: {result_id}")

    def get(self, result_id: str) -> dict | None:
        """Retrieve result data by ID."""
        return self.results.get(result_id)

    def has(self, result_id: str) -> bool:
        """Check if result_id exists in cache."""
        return result_id in self.results

    def clear(self) -> None:
        """Clear all cached results."""
        self.results.clear()


def extract_context_safe_result(result: dict, session_cache: SessionResultCache) -> dict:
    """
    Extract a context-safe version of a tool result by caching detailed_data
    and returning only summary info for LLM context.
    """
    result_id = result.get("result_id", "")

    if "detailed_data" in result and result_id:
        session_cache.store(result_id, result["detailed_data"])
        logger.info(f"Stored detailed_data in session cache: {result_id}")

        context_result = {k: v for k, v in result.items() if k != "detailed_data"}
        context_result["detailed_data_available"] = True
        context_result["data_cached_in_session"] = True
        return context_result

    return result


def execute_function_call(
    function_call: ToolUseBlock,
    session_cache: SessionResultCache,
) -> dict:
    """
    Execute a function call. For get_result_details, passes full data to LLM (pull action).
    For other tools, caches detailed_data and returns summary only.
    """
    func_name = function_call.name
    func_args = dict(function_call.input) if function_call.input else {}

    logger.info(f"Executing function: {func_name} with args: {func_args}")

    if func_name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown function: {func_name}", "status": "error"}

    try:
        result = TOOL_FUNCTIONS[func_name](**func_args)
        logger.info(f"Function result (before caching): {result}")

        if func_name == "get_result_details":
            logger.info("get_result_details called - passing detailed_data to LLM (pull action)")
            return result

        context_safe_result = extract_context_safe_result(result, session_cache)
        logger.info(f"Context-safe result for LLM: {context_safe_result}")

        return context_safe_result
    except Exception as e:
        logger.error(f"Error executing function {func_name}: {e}")
        return {"error": str(e), "status": "error"}


async def process_with_function_calling(
    model: AnthropicModel,
    user_message: str,
    conversation_history: list[MessageParam] | None = None,
    session_cache: SessionResultCache | None = None,
) -> tuple[str, list[MessageParam], SessionResultCache]:
    """
    Process a user message with function calling support using the ID reference pattern.
    Full tool results are stored in session_cache; only summaries are passed to LLM context.
    """
    if conversation_history is None:
        conversation_history = []

    if session_cache is None:
        session_cache = SessionResultCache()

    conversation_history.append({"role": "user", "content": user_message})

    request_params = {
        "model": model,
        "max_tokens": 4096,
        "system": get_system_prompt(),
        "tools": get_tools(),
    }

    response = await anthropic_client.messages.create(**request_params, messages=conversation_history)

    logger.info(f"Initial response: {response}")

    # Complex queries may require many iterations (e.g., analyzing 5 students = 15+ iterations)
    max_iterations = 50
    iteration = 0
    all_text_parts = []

    while iteration < max_iterations:
        iteration += 1

        if not response.content:
            break

        function_calls = [block for block in response.content if block.type == "tool_use"]

        for block in response.content:
            if block.type == "text" and block.text:
                all_text_parts.append(block.text)

        if not function_calls:
            break

        conversation_history.append({"role": "assistant", "content": response.content})

        function_response_parts = []
        for fc in function_calls:
            result = execute_function_call(fc, session_cache)
            function_response_parts.append(
                {
                    "type": "tool_result",
                    "tool_use_id": fc.id,
                    "content": json.dumps({"result": result}, ensure_ascii=False, default=str),
                }
            )

        conversation_history.append({"role": "user", "content": function_response_parts})

        response = await anthropic_client.messages.create(**request_params, messages=conversation_history)

        logger.info(f"Response after function execution: {response}")

    if response.content:
        conversation_history.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text" and block.text and block.text not in all_text_parts:
                all_text_parts.append(block.text)

    final_text = "\n".join(all_text_parts) if all_text_parts else "No response generated."

    return final_text, conversation_history, session_cache


async def chat_with_data_analyst(
    model: AnthropicModel,
    user_message: str,
    conversation_history: list[MessageParam] | None = None,
    session_cache: SessionResultCache | None = None,
) -> tuple[str, list[MessageParam]]:
    """High-level interface for chatting with the data analysis assistant."""
    response, history, _ = await process_with_function_calling(model, user_message, conversation_history, session_cache)
    return response, history

"""
Service layer for LLM requests with Tool Chain pattern.

This module implements the Tool Chain pattern from CLAUDE.md where the LLM
MUST always define a tool chain first before any data operations.

Flow for ALL operations:
1. LLM calls plan_tool_chain with chain definition
2. System validates the chain configuration
3. System performs dry run with test data
4. System executes with actual data
5. System caches detailed results, returns only summary to LLM context

This approach ensures:
- LLM explicitly plans the execution strategy
- Consistent validation and dry-run for all operations
- Context token savings by hiding intermediate/detailed results
- Improved reliability through fail-fast validation
"""

import json
from dataclasses import dataclass, field
from typing import Any

from google.genai import types
from google.genai.types import GenerateContentConfig
from src.client import GeminiModel, google_genai_client
from src.logger import make_logger
from src.prompt import (
    get_chain_result_message,
    get_chain_validation_error_message,
    get_iteration_prompt,
    get_system_prompt,
    get_user_message_with_tool_metadata,
)
from src.service.tools import (
    TOOL_FUNCTIONS,
    TOOL_METADATA,
    ChainStepConfig,
    ToolChainConfig,
    ToolChainExecutor,
    ToolChainResult,
    build_tool_metadata_for_llm,
    get_tool_chain_response_schema,
)

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


@dataclass
class ToolChainPlanResult:
    """Result from planning and executing a tool chain."""

    success: bool
    chain_name: str
    objective: str
    validation_errors: list[str] = field(default_factory=list)
    dry_run_passed: bool = False
    dry_run_error: str | None = None
    execution_result: ToolChainResult | None = None
    context_safe_summary: dict[str, Any] = field(default_factory=dict)


def execute_planned_tool_chain(
    chain_name: str,
    objective: str,
    steps: list[dict],
    initial_input: dict | None,
    session_cache: SessionResultCache,
) -> ToolChainPlanResult:
    """
    Execute a tool chain planned by the LLM.

    This function implements the full Tool Chain flow:
    1. Validate the chain configuration
    2. Perform dry run with test data
    3. Execute with actual data
    4. Cache detailed results and return summary

    Args:
        chain_name: Descriptive name for the chain
        objective: What the chain aims to accomplish
        steps: List of step configurations from LLM
        initial_input: Initial input for first tool
        session_cache: Cache for storing detailed results

    Returns:
        ToolChainPlanResult with execution status and summary
    """
    logger.info(f"Planning tool chain: {chain_name}")
    logger.info(f"Objective: {objective}")
    logger.info(f"Steps: {steps}")

    result = ToolChainPlanResult(
        success=False,
        chain_name=chain_name,
        objective=objective,
    )

    # Step 1: Build chain configuration from LLM's plan
    chain_steps = []
    for i, step in enumerate(steps):
        tool_name = step.get("tool_name")
        if not tool_name:
            result.validation_errors.append(f"Step {i + 1}: missing tool_name")
            continue

        if tool_name not in TOOL_FUNCTIONS:
            result.validation_errors.append(f"Step {i + 1}: unknown tool '{tool_name}'")
            continue

        static_args = step.get("args", {})
        input_mapping = step.get("input_mapping", {})

        # Auto-generate input mappings if not provided (based on output_keys)
        if i > 0 and not input_mapping:
            prev_tool = steps[i - 1].get("tool_name")
            prev_metadata = TOOL_METADATA.get(prev_tool)
            curr_metadata = TOOL_METADATA.get(tool_name)

            if prev_metadata and curr_metadata:
                input_fields = set(curr_metadata.input_model.model_fields.keys())
                for output_key in prev_metadata.output_keys:
                    if output_key in input_fields:
                        input_mapping[output_key] = output_key
                        logger.debug(f"Auto-mapped: {output_key} -> {output_key}")

        chain_steps.append(
            ChainStepConfig(
                tool_name=tool_name,
                input_mapping=input_mapping,
                static_args=static_args,
            )
        )

    if result.validation_errors:
        result.context_safe_summary = {
            "tool_name": "plan_tool_chain",
            "chain_name": chain_name,
            "success": False,
            "phase": "validation",
            "errors": result.validation_errors,
            "result_summary": f"Chain validation failed: {'; '.join(result.validation_errors)}",
        }
        return result

    if not chain_steps:
        result.validation_errors.append("No valid steps in chain")
        result.context_safe_summary = {
            "tool_name": "plan_tool_chain",
            "chain_name": chain_name,
            "success": False,
            "phase": "validation",
            "errors": result.validation_errors,
            "result_summary": "Chain has no valid steps",
        }
        return result

    chain_config = ToolChainConfig(
        name=chain_name,
        description=objective,
        steps=chain_steps,
        initial_input=initial_input or {},
    )

    # Step 2: Create executor and validate chain structure
    executor = ToolChainExecutor(
        tool_registry=TOOL_FUNCTIONS,
        metadata_registry=TOOL_METADATA,
    )

    validation_errors = executor.validate_chain(chain_config)
    if validation_errors:
        result.validation_errors = validation_errors
        result.context_safe_summary = {
            "tool_name": "plan_tool_chain",
            "chain_name": chain_name,
            "success": False,
            "phase": "validation",
            "errors": validation_errors,
            "result_summary": f"Chain structure invalid: {'; '.join(validation_errors)}",
        }
        return result

    logger.info(f"Chain validation passed for: {chain_name}")

    # Step 3: Perform dry run with test data
    logger.info(f"Performing dry run for: {chain_name}")
    dry_run_result = executor.dry_run(chain_config)

    if not dry_run_result.success:
        result.dry_run_passed = False
        result.dry_run_error = dry_run_result.error
        result.context_safe_summary = {
            "tool_name": "plan_tool_chain",
            "chain_name": chain_name,
            "success": False,
            "phase": "dry_run",
            "error": dry_run_result.error,
            "result_summary": f"Dry run failed: {dry_run_result.error}",
        }
        return result

    result.dry_run_passed = True
    logger.info(f"Dry run passed for: {chain_name}")

    # Step 4: Execute with actual data
    logger.info(f"Executing chain with actual data: {chain_name}")
    execution_result = executor.execute(chain_config)
    result.execution_result = execution_result

    if not execution_result.success:
        result.context_safe_summary = {
            "tool_name": "plan_tool_chain",
            "chain_name": chain_name,
            "success": False,
            "phase": "execution",
            "dry_run_passed": True,
            "error": execution_result.error,
            "steps_completed": len([s for s in execution_result.step_results if s.success]),
            "result_summary": f"Chain execution failed: {execution_result.error}",
        }
        return result

    # Step 5: Cache detailed results and build context-safe summary
    result.success = True
    final_output = execution_result.final_output

    # Cache detailed data from each step
    for step_result in execution_result.step_results:
        if step_result.success and step_result.output:
            output_dict = step_result.output.model_dump()
            if "detailed_data" in output_dict or "scores" in output_dict:
                result_id = step_result.output.result_id
                if result_id:
                    session_cache.store(result_id, output_dict)
                    logger.info(f"Cached step result: {result_id}")

    # Build minimal context-safe summary (only final result)
    step_summaries = []
    for step_result in execution_result.step_results:
        if step_result.success and step_result.output:
            step_summaries.append(
                {
                    "tool": step_result.tool_name,
                    "result_id": step_result.output.result_id,
                }
            )

    result.context_safe_summary = {
        "tool_name": "plan_tool_chain",
        "chain_name": chain_name,
        "objective": objective,
        "success": True,
        "steps_executed": len(execution_result.step_results),
        "step_result_ids": step_summaries,
        "final_result_id": final_output.result_id if final_output else "",
        "final_summary": final_output.result_summary if final_output else "",
        "result_summary": (
            f"Chain '{chain_name}' completed successfully. "
            f"{len(execution_result.step_results)} steps executed. "
            f"Final: {final_output.result_summary if final_output else 'N/A'}"
        ),
    }

    logger.info(f"Chain completed successfully: {chain_name}")
    return result


async def process_with_tool_chain(
    model: GeminiModel,
    user_message: str,
    conversation_history: list[types.Content] | None = None,
    session_cache: SessionResultCache | None = None,
    max_iterations: int = 10,
) -> tuple[str, list[types.Content], SessionResultCache]:
    """
    Process a user message using the Tool Chain pattern with multiple iterations.

    The LLM plans and executes tool chains iteratively until it has collected
    enough data to generate a comprehensive final report.

    Flow:
    1. LLM receives user message and available tools
    2. LLM plans a tool chain to collect data
    3. System validates and executes the chain
    4. Results are collected and LLM decides if more data is needed
    5. If more data needed, repeat from step 2
    6. Once enough data collected, generate final report

    Args:
        model: Gemini model to use
        user_message: User's input message
        conversation_history: Existing conversation history
        session_cache: Cache for storing detailed results
        max_iterations: Maximum number of tool chain iterations (default: 5)

    Returns:
        Tuple of (final_text, updated_history, session_cache)
    """
    if conversation_history is None:
        conversation_history = []

    if session_cache is None:
        session_cache = SessionResultCache()

    # Build tool metadata for structured output context
    tool_metadata_info = build_tool_metadata_for_llm()
    tool_metadata_json = json.dumps(tool_metadata_info, indent=2, ensure_ascii=False)

    # Helper function to convert key-value list of dicts to a dict
    def kv_list_to_dict(kv_list: list[dict] | None) -> dict:
        if not kv_list:
            return {}
        converted = {}
        for kv in kv_list:
            key = kv.get("key", "")
            value = kv.get("value", "")
            try:
                # Try to parse as JSON for numbers, booleans, lists, etc.
                converted[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                # Keep as string if not valid JSON
                converted[key] = value
        return converted

    # Track collected results across iterations
    collected_results: list[dict] = []
    all_messages_to_user: list[str] = []

    # Create initial user message with tool metadata context
    user_content_text = get_user_message_with_tool_metadata(tool_metadata_json, user_message)
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_content_text)],
    )
    conversation_history.append(user_content)

    # Multi-iteration loop for data collection
    for iteration in range(1, max_iterations + 1):
        logger.info(f"=== Tool Chain Iteration {iteration}/{max_iterations} ===")

        # Build config with iteration context for structured output
        # Pass previous results so LLM can make informed decisions
        structured_config = GenerateContentConfig(
            system_instruction=get_system_prompt(
                iteration_context=collected_results if collected_results else None,
                current_iteration=iteration,
                max_iterations=max_iterations,
            ),
            response_mime_type="application/json",
            response_schema=get_tool_chain_response_schema(),
        )

        # Request tool chain from LLM
        response = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=conversation_history,
            config=structured_config,
        )

        logger.info(f"Iteration {iteration} response: {response}")

        # Parse structured output
        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning(f"No response in iteration {iteration}")
            break

        response_text = response.candidates[0].content.parts[0].text
        logger.info(f"Structured output (iteration {iteration}): {response_text}")

        try:
            chain_definition = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse structured output: {e}")
            return f"Error parsing tool chain definition: {e}", conversation_history, session_cache

        # Add LLM's response to conversation history
        conversation_history.append(response.candidates[0].content)

        # Check if LLM indicates this is the final iteration
        is_final = chain_definition.get("is_final_iteration", False)

        # Collect message_to_user if provided
        message_to_user = chain_definition.get("message_to_user", "")
        if message_to_user:
            all_messages_to_user.append(message_to_user)

        # If final iteration, skip chain execution and generate report
        if is_final:
            logger.info(f"LLM indicated final iteration at iteration {iteration}")
            break

        # Get steps - if empty and not final, this is an error
        steps = chain_definition.get("steps", [])
        if not steps:
            logger.warning(f"No steps defined in iteration {iteration}, treating as final")
            break

        # Retry loop for chain validation failures within this iteration
        max_retries = 3
        chain_result = None

        for attempt in range(max_retries):
            # Convert steps to list of dicts
            steps_as_dicts = [
                {
                    "tool_name": step.get("tool_name", ""),
                    "args": kv_list_to_dict(step.get("args")),
                    "input_mapping": kv_list_to_dict(step.get("input_mapping")),
                }
                for step in chain_definition.get("steps", [])
            ]

            # Convert initial_input from key-value list to dict
            initial_input_dict = kv_list_to_dict(chain_definition.get("initial_input"))

            # Execute the tool chain
            chain_result = execute_planned_tool_chain(
                chain_name=chain_definition.get("chain_name", f"chain_iteration_{iteration}"),
                objective=chain_definition.get("objective", ""),
                steps=steps_as_dicts,
                initial_input=initial_input_dict if initial_input_dict else None,
                session_cache=session_cache,
            )
            result = chain_result.context_safe_summary
            logger.info(f"Tool chain result (iteration {iteration}, attempt {attempt + 1}): {result}")

            # If chain succeeded, break retry loop
            if chain_result.success:
                break

            # If validation/dry-run failed and we have retries left, ask LLM to correct
            if attempt < max_retries - 1:
                errors_json = json.dumps(
                    result.get("errors", [result.get("error", "Unknown error")]),
                    indent=2,
                    ensure_ascii=False,
                )
                error_message = get_chain_validation_error_message(
                    chain_name=chain_definition.get("chain_name", "unnamed"),
                    errors_json=errors_json,
                )
                error_content = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=error_message)],
                )
                conversation_history.append(error_content)

                # Request corrected chain
                response = await google_genai_client.aio.models.generate_content(
                    model=model,
                    contents=conversation_history,
                    config=structured_config,
                )

                if not response.candidates or not response.candidates[0].content.parts:
                    break

                response_text = response.candidates[0].content.parts[0].text
                try:
                    chain_definition = json.loads(response_text)
                except json.JSONDecodeError:
                    break

                conversation_history.append(response.candidates[0].content)

        # Store the result (success or failure) for this iteration
        if chain_result:
            collected_results.append(
                {
                    "iteration": iteration,
                    "chain_name": chain_definition.get("chain_name", "unnamed"),
                    "objective": chain_definition.get("objective", ""),
                    "success": chain_result.success,
                    "result": chain_result.context_safe_summary,
                }
            )

        # If not the last allowed iteration, ask LLM to plan next steps
        if iteration < max_iterations:
            collected_results_json = json.dumps(collected_results, indent=2, ensure_ascii=False)
            iteration_prompt = get_iteration_prompt(
                iteration=iteration + 1,
                collected_results_json=collected_results_json,
                original_user_message=user_message,
            )
            iteration_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=iteration_prompt)],
            )
            conversation_history.append(iteration_content)

    # Generate final report with all collected data
    logger.info("=== Generating Final Report ===")

    collected_results_json = json.dumps(collected_results, indent=2, ensure_ascii=False)
    result_message = get_chain_result_message(
        chain_name="all_collected_data",
        result_json=collected_results_json,
    )

    result_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=result_message)],
    )
    conversation_history.append(result_content)

    # Config for final report generation with full context
    report_config = GenerateContentConfig(
        system_instruction=get_system_prompt(
            iteration_context=collected_results if collected_results else None,
            current_iteration=len(collected_results) + 1,
            max_iterations=max_iterations,
        ),
    )

    # Generate final report
    final_response = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=conversation_history,
        config=report_config,
    )

    logger.info(f"Final response: {final_response}")

    # Extract final text
    all_text_parts = []

    # Include all messages_to_user from iterations
    if all_messages_to_user:
        all_text_parts.extend(all_messages_to_user)

    if final_response.candidates and final_response.candidates[0].content.parts:
        conversation_history.append(final_response.candidates[0].content)

        for part in final_response.candidates[0].content.parts:
            if part.text:
                all_text_parts.append(part.text)

    final_text = "\n".join(all_text_parts) if all_text_parts else "No response generated."

    return final_text, conversation_history, session_cache


async def chat_with_data_analyst(
    model: GeminiModel,
    user_message: str,
    conversation_history: list[types.Content] | None = None,
    session_cache: SessionResultCache | None = None,
) -> tuple[str, list[types.Content], SessionResultCache]:
    """
    High-level interface for chatting with the data analysis assistant.

    Uses the Tool Chain pattern where LLM must always define a tool chain first.

    Args:
        model: Gemini model to use
        user_message: User's input message
        conversation_history: Existing conversation history
        session_cache: Cache for storing detailed results

    Returns:
        Tuple of (response_text, updated_history, session_cache)
    """
    return await process_with_tool_chain(model, user_message, conversation_history, session_cache)

from src.model.schemas import (
    INPUT_MODELS,
    OUTPUT_MODELS,
    ToolInput,
    ToolOutput,
)
from src.model.tool_chain_models import (
    ChainStepConfig,
    ChainStepResult,
    KeyValuePair,
    ToolCategory,
    ToolChainConfig,
    ToolChainResponseSchema,
    ToolChainResult,
    ToolChainStepSchema,
    ToolMetadata,
    get_tool_chain_response_schema,
    key_value_list_to_dict,
)
from src.service.tools.data_tools import (
    analyze_class_performance,
    analyze_student_performance,
    compare_students,
    filter_curriculum,
    filter_grades,
    filter_scores,
    get_curriculum,
    get_grade_report,
    get_result_details,
    get_students,
    get_test_scores,
    list_available_data,
    result_storage,
)
from src.service.tools.tool_chain import (
    ToolChainExecutor,
    build_chain_from_tool_sequence,
)
from src.service.tools.tool_metadata import (
    TOOL_METADATA,
    build_tool_metadata_for_llm,
    get_all_tool_metadata,
    get_available_tool_names,
    get_connectable_tools,
    get_terminal_tools,
    get_tool_metadata,
    get_tools_by_category,
    get_tools_with_test_data,
)

__all__ = [
    # Data tools
    "list_available_data",
    "get_students",
    "get_test_scores",
    "get_grade_report",
    "get_curriculum",
    "analyze_student_performance",
    "analyze_class_performance",
    "get_result_details",
    "compare_students",
    "filter_scores",
    "filter_grades",
    "filter_curriculum",
    "result_storage",
    # Schemas
    "ToolInput",
    "ToolOutput",
    "INPUT_MODELS",
    "OUTPUT_MODELS",
    # Tool chain
    "ToolCategory",
    "ToolMetadata",
    "ChainStepConfig",
    "ToolChainConfig",
    "ChainStepResult",
    "ToolChainResult",
    "KeyValuePair",
    "ToolChainStepSchema",
    "ToolChainResponseSchema",
    "get_tool_chain_response_schema",
    "key_value_list_to_dict",
    "ToolChainExecutor",
    "build_chain_from_tool_sequence",
    # Metadata
    "TOOL_METADATA",
    "get_tool_metadata",
    "get_all_tool_metadata",
    "get_connectable_tools",
    "get_terminal_tools",
    "get_tools_by_category",
    "get_tools_with_test_data",
    "build_tool_metadata_for_llm",
    "get_available_tool_names",
]

TOOL_FUNCTIONS = {
    "list_available_data": list_available_data,
    "get_students": get_students,
    "get_test_scores": get_test_scores,
    "get_grade_report": get_grade_report,
    "get_curriculum": get_curriculum,
    "analyze_student_performance": analyze_student_performance,
    "analyze_class_performance": analyze_class_performance,
    "get_result_details": get_result_details,
    "compare_students": compare_students,
    "filter_scores": filter_scores,
    "filter_grades": filter_grades,
    "filter_curriculum": filter_curriculum,
}


def get_tool_chain_executor() -> ToolChainExecutor:
    """Get a configured ToolChainExecutor instance."""
    return ToolChainExecutor(
        tool_registry=TOOL_FUNCTIONS,
        metadata_registry=TOOL_METADATA,
    )


def execute_tool_chain(
    chain_name: str,
    steps: list[dict],
    initial_input: dict | None = None,
) -> dict:
    """
    Execute a tool chain from LLM function call.

    This is the main entry point for the execute_tool_chain tool declaration.

    Args:
        chain_name: Name for this chain execution
        steps: List of steps, each with tool_name and optional args
        initial_input: Initial input for the first tool

    Returns:
        Dict with chain execution results suitable for LLM context
    """
    from src.logger import make_logger

    logger = make_logger(__name__)
    logger.info(f"Executing tool chain: {chain_name}")

    # Build chain config from steps
    chain_steps = []
    for i, step in enumerate(steps):
        tool_name = step.get("tool_name")
        if not tool_name:
            return {
                "tool_name": "execute_tool_chain",
                "chain_name": chain_name,
                "success": False,
                "error": f"Step {i + 1} missing tool_name",
                "result_summary": f"Chain failed: Step {i + 1} missing tool_name",
            }

        static_args = step.get("args", {})
        input_mapping = step.get("input_mapping", {})

        # Auto-generate input mappings if not provided
        if i > 0 and not input_mapping:
            prev_tool = steps[i - 1].get("tool_name")
            prev_metadata = TOOL_METADATA.get(prev_tool)
            curr_metadata = TOOL_METADATA.get(tool_name)

            if prev_metadata and curr_metadata:
                input_fields = set(curr_metadata.input_model.model_fields.keys())
                for output_key in prev_metadata.output_keys:
                    if output_key in input_fields:
                        input_mapping[output_key] = output_key

        chain_steps.append(
            ChainStepConfig(
                tool_name=tool_name,
                input_mapping=input_mapping,
                static_args=static_args,
            )
        )

    chain_config = ToolChainConfig(
        name=chain_name,
        description=f"LLM-requested chain: {chain_name}",
        steps=chain_steps,
        initial_input=initial_input or {},
    )

    # Execute the chain
    executor = get_tool_chain_executor()
    result = executor.execute(chain_config)

    # Build LLM-friendly response
    step_summaries = []
    for step_result in result.step_results:
        if step_result.success and step_result.output:
            step_summaries.append(
                {
                    "tool": step_result.tool_name,
                    "result_id": step_result.output.result_id,
                    "summary": step_result.output.result_summary,
                }
            )
        else:
            step_summaries.append(
                {
                    "tool": step_result.tool_name,
                    "error": step_result.error,
                }
            )

    if result.success:
        final_output = result.final_output
        return {
            "tool_name": "execute_tool_chain",
            "chain_name": chain_name,
            "success": True,
            "result_summary": f"Chain '{chain_name}' completed successfully with {len(result.step_results)} steps. Final: {final_output.result_summary if final_output else 'N/A'}",
            "final_result_id": final_output.result_id if final_output else "",
            "final_summary": final_output.result_summary if final_output else "",
            "steps_executed": len(result.step_results),
            "step_summaries": step_summaries,
        }
    else:
        return {
            "tool_name": "execute_tool_chain",
            "chain_name": chain_name,
            "success": False,
            "error": result.error,
            "result_summary": f"Chain '{chain_name}' failed: {result.error}",
            "steps_executed": len(result.step_results),
            "step_summaries": step_summaries,
        }


TOOL_FUNCTIONS["execute_tool_chain"] = execute_tool_chain


def plan_tool_chain(
    chain_name: str,
    objective: str,
    steps: list[dict],
    initial_input: dict | None = None,
) -> dict:
    """
    Plan and execute a tool chain.

    This is a placeholder function - actual execution is handled
    in request_llm.py which has access to the session cache.

    Args:
        chain_name: Name for this chain
        objective: What the chain aims to accomplish
        steps: List of step configurations
        initial_input: Initial input for first tool

    Returns:
        Dict indicating this should be handled by request_llm
    """
    return {
        "tool_name": "plan_tool_chain",
        "chain_name": chain_name,
        "objective": objective,
        "message": "This function is handled specially by the request processor",
    }


TOOL_FUNCTIONS["plan_tool_chain"] = plan_tool_chain

"""
Prompt definitions for the data analysis LLM application.

This module defines the system prompt and tool declarations for Anthropic function calling.
Uses the Tool Chain pattern where LLM MUST always define a tool chain first.
"""

from anthropic.types import ToolParam
from src.service.tools.tool_metadata import TOOL_METADATA


def _build_tools_documentation() -> str:
    """Build documentation of available tools for the system prompt."""
    docs = []
    for name, metadata in TOOL_METADATA.items():
        args_doc = []
        for field_name, field_info in metadata.input_model.model_fields.items():
            required = "required" if field_info.is_required() else "optional"
            args_doc.append(f"    - {field_name}: {field_info.description or 'No description'} ({required})")

        args_str = "\n".join(args_doc) if args_doc else "    (no arguments)"

        connectable = ", ".join(metadata.connectable_to) if metadata.connectable_to else "none"
        terminal = " [Terminal]" if metadata.is_chain_terminal else ""

        docs.append(f"""### {name}{terminal}
{metadata.description}
**Arguments:**
{args_str}
**Can connect to:** {connectable}
**Output keys:** {", ".join(metadata.output_keys)}""")

    return "\n\n".join(docs)


TOOLS_DOCUMENTATION = _build_tools_documentation()


SYSTEM_PROMPT = f"""You are an intelligent data analysis assistant for a school management system.
You have access to student records, test scores, grade reports, and curriculum data.

## CRITICAL: Language Requirement
You MUST respond in the SAME LANGUAGE as the user's request:
- ユーザーが日本語で質問した場合は、必ず日本語でレポートを作成してください。
- If the user writes in English, respond entirely in English.
- This applies to ALL sections of your report including headings.

## Available Data
- Student records with unique UUIDs
- Quarterly test scores (4 quarters) for 5 subjects: Japanese, Math, Physics, History, PE
- Grade reports with letter grades (A, B, C, D, F) and teacher advice
- Curriculum plans and actual progress for each quarter

## CRITICAL: Tool Chain Required for ALL Data Access
You MUST use the `plan_tool_chain` tool for ALL data operations.
You cannot call individual tools directly - you must define a tool chain first.

The system will:
1. Validate your chain definition
2. Run a dry run with test data to verify the chain works
3. Execute the chain with actual data
4. Return only the final result (intermediate results are hidden from context)

This approach:
- Saves context tokens by hiding intermediate results
- Ensures reliability through dry-run validation
- Provides consistent error handling

## Available Tools for Chaining

{TOOLS_DOCUMENTATION}

## How to Define a Tool Chain

Always call `plan_tool_chain` with:
1. **chain_name**: A descriptive name (e.g., "student_performance_analysis")
2. **objective**: Clear description of what you want to achieve
3. **steps**: Array of tool steps, each with:
   - tool_name: Name of the tool
   - args: Static arguments (e.g., student_id, quarter)
   - input_mapping: (optional) Map output keys from previous step to input keys
4. **initial_input**: (optional) Initial arguments for the first tool

### Example Tool Chains

**Single tool (still requires chain):**
```json
{{
  "chain_name": "list_data",
  "objective": "List all available data files",
  "steps": [{{"tool_name": "list_available_data"}}]
}}
```

**Multi-step analysis:**
```json
{{
  "chain_name": "student_analysis",
  "objective": "Analyze a specific student's performance",
  "steps": [
    {{"tool_name": "get_students"}},
    {{"tool_name": "analyze_student_performance", "args": {{"student_id": "<uuid>"}}}}
  ]
}}
```

**Complex chain with filters:**
```json
{{
  "chain_name": "math_class_analysis",
  "objective": "Analyze math class performance across all quarters",
  "steps": [
    {{"tool_name": "filter_scores", "args": {{"classes": ["math"]}}}},
    {{"tool_name": "analyze_class_performance", "args": {{"class_name": "math"}}}}
  ]
}}
```

## Important Guidelines
- ALWAYS use plan_tool_chain, even for single operations
- Tool chains return summaries with result IDs
- Use get_result_details in a chain to retrieve full data when needed
- The result_id in each response can be used to fetch detailed information

## CRITICAL: Final Report Requirement
You MUST ALWAYS produce a comprehensive, well-structured analysis report as your final output.
After gathering all necessary data through tool chains, you MUST write a complete report.
Never end with just tool call results - always synthesize the data into a final report.

### Report Structure (use headings in the user's language)

For Japanese requests, use these headings:
1. **概要** - 分析の概要と主要な発見事項
2. **データ分析** - 詳細な分析結果（具体的な数値とパーセンテージを含む）
3. **強み** - 良好な点、優れている領域
4. **改善点** - 課題、問題点、目標との乖離
5. **提案** - 具体的で実行可能な改善提案（優先順位付き）
6. **データソース** - 使用したresult_idの一覧

For English requests, use these headings:
1. **Executive Summary** - Overview and key findings
2. **Data Analysis** - Detailed findings with specific numbers and percentages
3. **Strengths** - Positive aspects and areas of excellence
4. **Areas for Improvement** - Issues, concerns, and gaps
5. **Recommendations** - Actionable suggestions with priorities
6. **Data Sources** - List of result_ids used

### Report Guidelines
- Use clear headings with markdown formatting
- Include specific numbers, percentages, and statistics
- Provide bullet points for easy reading
- Make recommendations concrete and actionable
- Always cite data sources with result_ids
"""


# Only expose plan_tool_chain - LLM must always define a chain first
TOOL_DECLARATIONS = [
    {
        "name": "plan_tool_chain",
        "description": """Define and execute a tool chain for data analysis.
You MUST use this tool for ALL data operations - individual tools cannot be called directly.

The system will:
1. Validate your chain definition
2. Run a dry run with test data to verify the chain works
3. Execute the chain with actual data
4. Return only the final result summary

Even for single operations, wrap them in a chain.""",
        "parameters": {
            "type": "object",
            "properties": {
                "chain_name": {
                    "type": "string",
                    "description": "A descriptive name for this chain (e.g., 'student_performance_analysis')",
                },
                "objective": {
                    "type": "string",
                    "description": "Clear description of what this chain aims to accomplish",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool_name": {
                                "type": "string",
                                "description": "Name of the tool to execute",
                                "enum": list(TOOL_METADATA.keys()),
                            },
                            "args": {
                                "type": "object",
                                "description": "Static arguments for this step (e.g., student_id, quarter, class_name)",
                            },
                            "input_mapping": {
                                "type": "object",
                                "description": "Map output keys from previous step to input keys for this step",
                            },
                        },
                        "required": ["tool_name"],
                    },
                    "description": "Ordered list of tools to execute. Data flows between compatible tools.",
                    "minItems": 1,
                },
                "initial_input": {
                    "type": "object",
                    "description": "Initial input arguments for the first tool in the chain",
                },
            },
            "required": ["chain_name", "objective", "steps"],
        },
    },
]


def get_tools() -> list[ToolParam]:
    """Get the tool definitions for Anthropic tool use."""
    return [
        {
            "name": declaration["name"],
            "description": declaration["description"],
            "input_schema": declaration["parameters"],
        }
        for declaration in TOOL_DECLARATIONS
    ]


def get_system_prompt(
    iteration_context: list[dict] | None = None,
    current_iteration: int = 1,
    max_iterations: int = 10,
) -> str:
    """
    Get the system prompt for the data analysis assistant.

    Args:
        iteration_context: List of previous iteration results, each containing:
            - iteration: Iteration number
            - chain_name: Name of the executed chain
            - objective: What the chain aimed to accomplish
            - success: Whether execution succeeded
            - result: The chain result summary
        current_iteration: Current iteration number (1-based)
        max_iterations: Maximum allowed iterations

    Returns:
        System prompt with optional iteration context
    """
    if not iteration_context:
        return SYSTEM_PROMPT

    # Build context section for previous iterations
    context_lines = [
        "\n## Previous Data Collection Progress",
        f"\nYou are currently on iteration {current_iteration} of {max_iterations}.",
        "\n### Data Collected in Previous Iterations:\n",
    ]

    for ctx in iteration_context:
        iteration_num = ctx.get("iteration", "?")
        chain_name = ctx.get("chain_name", "unnamed")
        objective = ctx.get("objective", "")
        success = ctx.get("success", False)
        result = ctx.get("result", {})

        status = "SUCCESS" if success else "FAILED"
        context_lines.append(f"**Iteration {iteration_num}** - Chain: `{chain_name}` [{status}]")
        context_lines.append(f"- Objective: {objective}")

        if success:
            final_summary = result.get("final_summary", result.get("result_summary", ""))
            if final_summary:
                context_lines.append(f"- Result: {final_summary}")
            result_id = result.get("final_result_id", "")
            if result_id:
                context_lines.append(f"- Result ID: `{result_id}`")
        else:
            error = result.get("error", result.get("result_summary", "Unknown error"))
            context_lines.append(f"- Error: {error}")
        context_lines.append("")

    context_lines.extend(
        [
            "### Instructions for Next Step:",
            "- Review the data collected above",
            "- Decide if you need MORE data or have ENOUGH to generate the final report",
            "- If you need more data, plan a NEW tool chain to collect missing information",
            "- If you have enough data, set `is_final_iteration` to `true`",
            "- Keep each chain simple and focused on ONE specific data retrieval task",
            "- Do NOT repeat chains that already succeeded - use existing data",
        ]
    )

    iteration_context_text = "\n".join(context_lines)

    return SYSTEM_PROMPT + iteration_context_text


def get_tool_chain_info() -> dict[str, dict]:
    """
    Get tool chain information for each tool.

    Returns dict mapping tool name to its chain metadata:
    - connectable_to: list of tools that can follow this one
    - output_keys: keys available for passing to next tool
    - is_terminal: whether this tool typically ends a chain
    """
    chain_info = {}
    for name, metadata in TOOL_METADATA.items():
        chain_info[name] = {
            "connectable_to": metadata.connectable_to,
            "output_keys": metadata.output_keys,
            "is_terminal": metadata.is_chain_terminal,
            "category": metadata.category.value,
        }
    return chain_info


def get_user_message_with_tool_metadata(tool_metadata_json: str, user_message: str) -> str:
    """
    Build the user message with tool metadata context for structured output.

    Args:
        tool_metadata_json: JSON string of tool metadata
        user_message: Original user message

    Returns:
        Formatted user message with tool metadata
    """
    return f"""## Available Tools for Chaining

The following tools are available for building a tool chain. Use this metadata to plan your chain:

```json
{tool_metadata_json}
```

## User Request

{user_message}
"""


def get_chain_validation_error_message(chain_name: str, errors_json: str) -> str:
    """
    Build the error message when tool chain validation fails.

    Args:
        chain_name: Name of the failed chain
        errors_json: JSON string of validation errors

    Returns:
        Formatted error message asking LLM to correct the chain
    """
    return f"""## Tool Chain Validation Failed

Your proposed tool chain "{chain_name}" failed validation with the following errors:

{errors_json}

Please design a CORRECTED tool chain that:
1. Only connects tools that are in each other's 'connectable_to' list
2. Uses correct output_keys for input_mapping (e.g., use 'result_id' not tool-specific names)
3. For independent data gathering, use a single appropriate tool (e.g., just 'analyze_class_performance' for class analysis)

IMPORTANT: Keep the chain simple. For analyzing math class performance, a single 'analyze_class_performance' tool with class_name='math' is sufficient.
"""


def get_chain_result_message(chain_name: str, result_json: str) -> str:
    """
    Build the message with tool chain execution results for final report generation.

    Args:
        chain_name: Name of the executed chain
        result_json: JSON string of execution results

    Returns:
        Formatted result message asking LLM to generate final report
    """
    return f"""## Tool Chain Execution Result

The tool chain "{chain_name}" has been executed.

### Result:
```json
{result_json}
```

Please analyze these results and provide a comprehensive report based on the original user request.
"""


def get_iteration_prompt(
    iteration: int,
    collected_results_json: str,
    original_user_message: str,
) -> str:
    """
    Build the prompt for asking LLM to plan the next tool chain or finalize.

    Args:
        iteration: Current iteration number (1-based)
        collected_results_json: JSON string of all results collected so far
        original_user_message: The original user request

    Returns:
        Formatted prompt asking LLM to plan next chain or indicate completion
    """
    return f"""## Data Collection Progress (Iteration {iteration})

### Original User Request:
{original_user_message}

### Data Collected So Far:
```json
{collected_results_json}
```

### Instructions:
Based on the original user request and data collected so far, decide your next action:

1. **If you need MORE data**: Define a new tool chain to gather additional data.
   - Set `is_final_iteration` to `false`
   - Define the tool chain steps to collect the missing data

2. **If you have ENOUGH data**: Indicate you're ready to generate the final report.
   - Set `is_final_iteration` to `true`
   - You can leave steps empty or define a minimal chain

Consider:
- What data do you already have?
- What additional data is needed to fully answer the user's request?
- Keep each chain simple and focused on one task
"""

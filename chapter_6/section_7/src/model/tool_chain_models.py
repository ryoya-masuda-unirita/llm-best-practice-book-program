"""
Tool Chain data models.

This module defines the data models for Tool Chain configuration and execution:
- ToolCategory: Categories for organizing tools
- ToolMetadata: Metadata for a single tool
- ChainStepConfig: Configuration for a single step in a chain
- ToolChainConfig: Configuration for an entire chain
- ChainStepResult: Result from a single step
- ToolChainResult: Result from executing an entire chain
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.model.schemas import (
    ToolInput,
    ToolOutput,
)


class ToolCategory(StrEnum):
    """Categories for organizing tools."""

    LOADER = "loader"  # Tools that load raw data
    ANALYZER = "analyzer"  # Tools that analyze data
    FILTER = "filter"  # Tools that filter data
    AGGREGATOR = "aggregator"  # Tools that aggregate results
    RETRIEVER = "retriever"  # Tools that retrieve stored results


@dataclass
class ToolMetadata:
    """
    Metadata for a single tool including I/O schemas and chain information.

    Attributes:
        name: Unique tool name
        description: Human-readable description
        category: Tool category for organization
        input_model: Pydantic model for input validation
        output_model: Pydantic model for output structure
        output_keys: Keys in output that can be passed to connected tools
        connectable_to: List of tool names this tool can connect to
        is_chain_terminal: Whether this tool typically ends a chain
        test_input: Mini test data for dry run validation
    """

    name: str
    description: str
    category: ToolCategory
    input_model: type[ToolInput]
    output_model: type[ToolOutput]
    output_keys: list[str] = field(default_factory=list)
    connectable_to: list[str] = field(default_factory=list)
    is_chain_terminal: bool = False
    test_input: dict[str, Any] | None = None


class ChainStepConfig(BaseModel):
    """Configuration for a single step in a tool chain."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., description="Name of the tool to execute")
    input_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from previous output keys to this tool's input keys",
    )
    static_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Static arguments to pass to the tool",
    )


class ToolChainConfig(BaseModel):
    """Configuration for an entire tool chain."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Unique name for this chain")
    description: str = Field(default="", description="Description of what this chain does")
    steps: list[ChainStepConfig] = Field(..., min_length=1, description="Ordered list of steps in the chain")
    initial_input: dict[str, Any] = Field(default_factory=dict, description="Initial input for the first step")


class ChainStepResult(BaseModel):
    """Result from a single step in the chain."""

    model_config = ConfigDict(extra="ignore")

    step_index: int = Field(..., description="Index of this step in the chain")
    tool_name: str = Field(..., description="Name of the tool executed")
    success: bool = Field(..., description="Whether the step succeeded")
    output: ToolOutput | None = Field(default=None, description="Tool output if successful")
    error: str | None = Field(default=None, description="Error message if failed")
    input_used: dict[str, Any] = Field(default_factory=dict, description="Input passed to the tool")


class ToolChainResult(BaseModel):
    """Result from executing an entire tool chain."""

    model_config = ConfigDict(extra="ignore")

    chain_name: str = Field(..., description="Name of the chain that was executed")
    success: bool = Field(..., description="Whether the entire chain succeeded")
    step_results: list[ChainStepResult] = Field(default_factory=list, description="Results from each step")
    final_output: ToolOutput | None = Field(default=None, description="Output from the last successful step")
    error: str | None = Field(default=None, description="Error message if chain failed")
    is_dry_run: bool = Field(default=False, description="Whether this was a dry run")


class KeyValuePair(BaseModel):
    """A key-value pair for structured output (Gemini doesn't support additionalProperties)."""

    key: str = Field(..., description="The key/parameter name")
    value: str = Field(..., description="The value (as string, will be parsed appropriately)")


class ToolChainStepSchema(BaseModel):
    """Schema for a single step in the tool chain (for structured output)."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    args: list[KeyValuePair] = Field(
        default_factory=list,
        description="Static arguments for this step as key-value pairs (e.g., {key: 'student_id', value: 'uuid'}, {key: 'quarter', value: '1'})",
    )
    input_mapping: list[KeyValuePair] = Field(
        default_factory=list,
        description="Map output keys from previous step to input keys for this step as key-value pairs",
    )


class ToolChainResponseSchema(BaseModel):
    """
    Structured output schema for LLM to define a tool chain.

    This schema is used for structured output generation where the LLM
    returns a JSON object defining the tool chain to execute.
    """

    chain_name: str = Field(
        ...,
        description="A descriptive name for this chain (e.g., 'student_performance_analysis')",
    )
    objective: str = Field(
        ...,
        description="Clear description of what this chain aims to accomplish",
    )
    steps: list[ToolChainStepSchema] = Field(
        ...,
        min_length=1,
        description="Ordered list of tools to execute. Data flows between compatible tools.",
    )
    initial_input: list[KeyValuePair] = Field(
        default_factory=list,
        description="Initial input arguments for the first tool in the chain as key-value pairs",
    )
    message_to_user: str = Field(
        default="",
        description="Message to display to the user explaining what the chain will do",
    )


def get_tool_chain_response_schema() -> dict[str, Any]:
    """
    Get the JSON schema for ToolChainResponseSchema in Gemini-compatible format.

    Gemini API doesn't support 'additionalProperties' field, so we manually
    construct the schema without it.
    """
    return {
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
                "description": "Ordered list of tools to execute. Data flows between compatible tools. Can be empty if is_final_iteration is true.",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool to execute",
                        },
                        "args": {
                            "type": "array",
                            "description": "Static arguments for this step as key-value pairs",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string", "description": "The parameter name"},
                                    "value": {"type": "string", "description": "The value as string"},
                                },
                                "required": ["key", "value"],
                            },
                        },
                        "input_mapping": {
                            "type": "array",
                            "description": "Map output keys from previous step to input keys",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string", "description": "The input key name"},
                                    "value": {"type": "string", "description": "The output key to map from"},
                                },
                                "required": ["key", "value"],
                            },
                        },
                    },
                    "required": ["tool_name"],
                },
            },
            "initial_input": {
                "type": "array",
                "description": "Initial input arguments for the first tool as key-value pairs",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "The parameter name"},
                        "value": {"type": "string", "description": "The value as string"},
                    },
                    "required": ["key", "value"],
                },
            },
            "message_to_user": {
                "type": "string",
                "description": "Message to display to the user explaining what the chain will do",
            },
            "is_final_iteration": {
                "type": "boolean",
                "description": "Set to true when you have collected enough data and are ready to generate the final report. Set to false if you need to collect more data with another chain.",
            },
        },
        "required": ["chain_name", "objective", "steps", "is_final_iteration"],
    }


def key_value_list_to_dict(kv_list: list[KeyValuePair]) -> dict[str, Any]:
    """
    Convert a list of KeyValuePair to a dictionary.

    Attempts to parse values as JSON (for numbers, booleans, lists, etc.),
    falling back to string if parsing fails.
    """
    import json

    result = {}
    for kv in kv_list:
        try:
            # Try to parse as JSON for numbers, booleans, lists, etc.
            result[kv.key] = json.loads(kv.value)
        except (json.JSONDecodeError, ValueError):
            # Keep as string if not valid JSON
            result[kv.key] = kv.value
    return result

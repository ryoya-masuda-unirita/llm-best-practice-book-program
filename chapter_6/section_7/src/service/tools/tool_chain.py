"""
Tool Chain executor for chaining multiple tool calls.

This module implements the Tool Chain pattern from CLAUDE.md:
- Execute chains of tools with data passing between steps
- Support dry run validation with mini test data
- Validate chain configurations

Data models are defined in src.model.tool_chain_models.
"""

from typing import Any, Callable

from src.logger import make_logger
from src.model.schemas import ToolOutput
from src.model.tool_chain_models import (
    ChainStepConfig,
    ChainStepResult,
    ToolChainConfig,
    ToolChainResult,
    ToolMetadata,
)

logger = make_logger(__name__)


class ToolChainExecutor:
    """
    Executor for running tool chains with data passing between steps.

    Implements the bucket relay pattern where output from one tool
    becomes input for the next tool in the chain.
    """

    def __init__(
        self,
        tool_registry: dict[str, Callable],
        metadata_registry: dict[str, ToolMetadata],
    ):
        """
        Initialize the executor.

        Args:
            tool_registry: Mapping of tool names to callable functions
            metadata_registry: Mapping of tool names to their metadata
        """
        self.tool_registry = tool_registry
        self.metadata_registry = metadata_registry

    def _resolve_input(
        self,
        step: ChainStepConfig,
        previous_output: ToolOutput | None,
        initial_input: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve input for a step by combining:
        1. Static args from step config
        2. Mapped values from previous output
        3. Initial input values (for first step or unmapped keys)
        """
        resolved = {}

        # Start with static args
        resolved.update(step.static_args)

        # Add initial input (may be overwritten by mappings)
        resolved.update(initial_input)

        # Apply input mappings from previous output
        if previous_output and step.input_mapping:
            output_dict = previous_output.model_dump()
            for target_key, source_key in step.input_mapping.items():
                if source_key in output_dict:
                    resolved[target_key] = output_dict[source_key]
                else:
                    logger.warning(f"Input mapping failed: '{source_key}' not found in previous output")

        return resolved

    def _execute_step(
        self,
        step: ChainStepConfig,
        step_index: int,
        resolved_input: dict[str, Any],
    ) -> ChainStepResult:
        """Execute a single step in the chain."""
        tool_name = step.tool_name

        if tool_name not in self.tool_registry:
            return ChainStepResult(
                step_index=step_index,
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
                input_used=resolved_input,
            )

        metadata = self.metadata_registry.get(tool_name)
        if not metadata:
            return ChainStepResult(
                step_index=step_index,
                tool_name=tool_name,
                success=False,
                error=f"No metadata found for tool: {tool_name}",
                input_used=resolved_input,
            )

        # Validate input against schema
        try:
            input_model = metadata.input_model
            validated_input = input_model(**resolved_input)
        except Exception as e:
            return ChainStepResult(
                step_index=step_index,
                tool_name=tool_name,
                success=False,
                error=f"Input validation failed: {e}",
                input_used=resolved_input,
            )

        # Execute the tool
        try:
            tool_func = self.tool_registry[tool_name]
            result_dict = tool_func(**validated_input.model_dump(exclude_none=True))

            # Wrap result in output model
            output_model = metadata.output_model
            output = output_model(**result_dict)

            return ChainStepResult(
                step_index=step_index,
                tool_name=tool_name,
                success=True,
                output=output,
                input_used=resolved_input,
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return ChainStepResult(
                step_index=step_index,
                tool_name=tool_name,
                success=False,
                error=str(e),
                input_used=resolved_input,
            )

    def execute(
        self,
        chain_config: ToolChainConfig,
    ) -> ToolChainResult:
        """
        Execute a tool chain, passing data between steps.

        Args:
            chain_config: Configuration defining the chain steps

        Returns:
            ToolChainResult with all step results and final output
        """
        logger.info(f"Executing tool chain: {chain_config.name}")

        step_results: list[ChainStepResult] = []
        previous_output: ToolOutput | None = None

        for i, step in enumerate(chain_config.steps):
            logger.info(f"Executing step {i + 1}/{len(chain_config.steps)}: {step.tool_name}")

            # Resolve input for this step
            resolved_input = self._resolve_input(
                step=step,
                previous_output=previous_output,
                initial_input=chain_config.initial_input,
            )

            # Execute the step
            step_result = self._execute_step(
                step=step,
                step_index=i,
                resolved_input=resolved_input,
            )
            step_results.append(step_result)

            # Check for failure
            if not step_result.success:
                logger.error(f"Chain failed at step {i + 1}: {step_result.error}")
                return ToolChainResult(
                    chain_name=chain_config.name,
                    success=False,
                    step_results=step_results,
                    final_output=None,
                    error=f"Chain failed at step {i + 1} ({step.tool_name}): {step_result.error}",
                )

            previous_output = step_result.output

        logger.info(f"Tool chain completed successfully: {chain_config.name}")
        return ToolChainResult(
            chain_name=chain_config.name,
            success=True,
            step_results=step_results,
            final_output=previous_output,
        )

    def dry_run(
        self,
        chain_config: ToolChainConfig,
    ) -> ToolChainResult:
        """
        Perform a dry run of the chain using mini test data.

        This validates:
        1. All tools exist in the registry
        2. Input/output schemas are compatible
        3. Input mappings are valid
        4. Tools can execute with test data

        Args:
            chain_config: Configuration defining the chain steps

        Returns:
            ToolChainResult with is_dry_run=True
        """
        logger.info(f"Performing dry run of tool chain: {chain_config.name}")

        # Create test chain config using mini test data
        test_steps = []
        for step in chain_config.steps:
            metadata = self.metadata_registry.get(step.tool_name)
            if metadata and metadata.test_input:
                test_step = ChainStepConfig(
                    tool_name=step.tool_name,
                    input_mapping={},  # Use test data directly
                    static_args=metadata.test_input,
                )
            else:
                test_step = step
            test_steps.append(test_step)

        test_config = ToolChainConfig(
            name=f"{chain_config.name}_dry_run",
            description=f"Dry run of {chain_config.name}",
            steps=test_steps,
            initial_input={},
        )

        # Execute with test data
        result = self.execute(test_config)
        result.is_dry_run = True
        result.chain_name = chain_config.name

        if result.success:
            logger.info(f"Dry run passed for chain: {chain_config.name}")
        else:
            logger.warning(f"Dry run failed for chain: {chain_config.name} - {result.error}")

        return result

    def validate_chain(
        self,
        chain_config: ToolChainConfig,
    ) -> list[str]:
        """
        Validate a chain configuration without executing.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for i, step in enumerate(chain_config.steps):
            # Check tool exists
            if step.tool_name not in self.tool_registry:
                errors.append(f"Step {i + 1}: Unknown tool '{step.tool_name}'")
                continue

            # Check metadata exists
            metadata = self.metadata_registry.get(step.tool_name)
            if not metadata:
                errors.append(f"Step {i + 1}: No metadata for tool '{step.tool_name}'")
                continue

            # Check input mapping validity (for non-first steps)
            if i > 0 and step.input_mapping:
                prev_step = chain_config.steps[i - 1]
                prev_metadata = self.metadata_registry.get(prev_step.tool_name)
                if prev_metadata:
                    for target_key, source_key in step.input_mapping.items():
                        if source_key not in prev_metadata.output_keys:
                            errors.append(
                                f"Step {i + 1}: Input mapping '{source_key}' not in "
                                f"previous tool's output keys: {prev_metadata.output_keys}"
                            )

            # Check connectable_to (if defined)
            if i > 0:
                prev_step = chain_config.steps[i - 1]
                prev_metadata = self.metadata_registry.get(prev_step.tool_name)
                if prev_metadata and prev_metadata.connectable_to:
                    if step.tool_name not in prev_metadata.connectable_to:
                        errors.append(
                            f"Step {i + 1}: Tool '{step.tool_name}' is not in "
                            f"connectable_to list of '{prev_step.tool_name}'"
                        )

        return errors


def build_chain_from_tool_sequence(
    name: str,
    tool_names: list[str],
    initial_input: dict[str, Any],
    metadata_registry: dict[str, ToolMetadata],
    description: str = "",
) -> ToolChainConfig:
    """
    Build a chain configuration from a sequence of tool names.

    Automatically creates input mappings based on output_keys and input model fields.

    Args:
        name: Name for the chain
        tool_names: Ordered list of tool names
        initial_input: Input for the first tool
        metadata_registry: Registry of tool metadata
        description: Optional description

    Returns:
        ToolChainConfig ready for execution
    """
    steps = []

    for i, tool_name in enumerate(tool_names):
        metadata = metadata_registry.get(tool_name)
        if not metadata:
            raise ValueError(f"No metadata found for tool: {tool_name}")

        input_mapping = {}

        # Auto-map from previous output keys to current input fields
        if i > 0:
            prev_metadata = metadata_registry.get(tool_names[i - 1])
            if prev_metadata:
                # Get input field names for current tool
                input_fields = set(metadata.input_model.model_fields.keys())

                # Map matching output keys to input fields
                for output_key in prev_metadata.output_keys:
                    if output_key in input_fields:
                        input_mapping[output_key] = output_key

        steps.append(
            ChainStepConfig(
                tool_name=tool_name,
                input_mapping=input_mapping,
                static_args={},
            )
        )

    return ToolChainConfig(
        name=name,
        description=description,
        steps=steps,
        initial_input=initial_input,
    )

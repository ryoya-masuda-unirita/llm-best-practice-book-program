"""Base Agent implementation with Strategy pattern."""

from typing import NoReturn

from src.agent.core.base import Action, ActionType, AgentExecutionError, Strategy, ToolResult
from src.agent.core.controller import ExecutionController, ExecutionRequest
from src.agent.core.memory import Memory
from src.agent.core.states import (
    ActingState,
    AgentContext,
    AgentStatus,
    CompletedState,
    ErrorState,
    IdleState,
    ThinkingState,
)
from src.agent.core.toolbox import ToolBox
from src.logger import make_logger

logger = make_logger(__name__)


def _create_default_controller() -> ExecutionController:
    """Create a minimal controller. Use extensions for full functionality."""
    return ExecutionController()


class BaseAgent:
    """Base agent that combines Brain (Strategy), ToolBox, and Memory."""

    def __init__(
        self,
        strategy: Strategy,
        toolbox: ToolBox,
        memory: Memory | None = None,
        controller: ExecutionController | None = None,
    ):
        self.strategy = strategy
        self.toolbox = toolbox
        self._memory = memory
        self.controller = controller or _create_default_controller()
        self.agent_context = AgentContext()

    @property
    def memory(self) -> Memory:
        if self._memory is None:
            raise RuntimeError("Memory not initialized. Provide a Memory instance to the agent.")
        return self._memory

    @memory.setter
    def memory(self, value: Memory) -> None:
        self._memory = value

    def execute(self, goal: str) -> str:
        self._validate_memory()
        self.agent_context.transition_to(ThinkingState())

        try:
            final_answer = self._run_execution_loop(goal)
            return self._process_result(final_answer)
        except AgentExecutionError:
            raise
        except Exception as e:
            self._handle_unexpected_error(e)
        finally:
            self.agent_context.transition_to(IdleState())

    def _validate_memory(self) -> None:
        if self._memory is None:
            raise RuntimeError("Memory not initialized. Provide a Memory instance to the agent.")

    def _run_execution_loop(self, goal: str) -> str | None:
        final_answer: str | None = None
        while not self._is_task_complete(goal):
            result = self._execute_single_step(goal)
            if isinstance(result, str):
                final_answer = result
            if self.agent_context.is_terminal():
                break
        return final_answer

    def _execute_single_step(self, goal: str) -> ToolResult | str:
        context = self.memory.get_context()
        action = self.strategy.think(goal, context, self.toolbox.get_all_tools())

        self._validate_action(action, context)
        self.memory.add_action(action)
        result = self._execute_action(action)

        if action.type != ActionType.FINAL_ANSWER:
            self.memory.add_observation(result)
            self.strategy.update_context(context, action, result)

        return result

    def _validate_action(self, action: Action, context: dict[str, object]) -> None:
        exec_response = self.controller.check_execution(ExecutionRequest(action=action, context=context))
        if not exec_response.allowed:
            error_msg = f"Action blocked: {exec_response.reason}"
            self.agent_context.transition_to(ErrorState(error_msg))
            raise AgentExecutionError(error_msg, reason=exec_response.reason)

    def _process_result(self, final_answer: str | None) -> str:
        if self.agent_context.get_status() == AgentStatus.COMPLETED and final_answer:
            return final_answer
        if self.agent_context.get_status() == AgentStatus.ERROR:
            raise AgentExecutionError("Task execution terminated with error")
        raise AgentExecutionError("Task execution terminated without completion")

    def _handle_unexpected_error(self, e: Exception) -> NoReturn:
        error_msg = f"Agent error: {str(e)}"
        self.agent_context.transition_to(ErrorState(error_msg))
        raise AgentExecutionError(error_msg) from e

    def _execute_action(self, action: Action) -> ToolResult | str:
        if action.type == ActionType.TOOL_CALL:
            return self._execute_tool_call(action)
        elif action.type == ActionType.FINAL_ANSWER:
            self.agent_context.transition_to(CompletedState())
            return action.answer or ""
        else:  # THINK
            return action.thought or ""

    def _execute_tool_call(self, action: Action) -> ToolResult:
        if self.agent_context.get_status() != AgentStatus.ACTING:
            self.agent_context.transition_to(ActingState())

        tool = self.toolbox.get_tool(action.tool_name or "")
        if not tool:
            if self.agent_context.get_status() == AgentStatus.ACTING:
                self.agent_context.transition_to(ThinkingState())
            return ToolResult(success=False, data=None, error=f"Tool '{action.tool_name}' not found")

        if not tool.validate_params(action.params):
            if self.agent_context.get_status() == AgentStatus.ACTING:
                self.agent_context.transition_to(ThinkingState())
            return ToolResult(success=False, data=None, error=f"Invalid parameters for tool '{action.tool_name}'")

        result = tool.execute(action.params)

        if self.agent_context.get_status() == AgentStatus.ACTING:
            self.agent_context.transition_to(ThinkingState())

        return result

    def _is_task_complete(self, goal: str) -> bool:
        return self.agent_context.is_terminal() or not self.agent_context.can_act()

    def get_execution_trace(self) -> dict[str, object]:
        return {
            "context": self.memory.get_context() if self._memory else {},
            "state_history": self.agent_context.get_state_history(),
            "events": self.agent_context.get_events(),
            "current_state": self.agent_context.get_status().value,
        }

    def reset(self) -> None:
        if self._memory:
            self.memory.clear()
        self.agent_context.reset()
        self.controller.reset_all()

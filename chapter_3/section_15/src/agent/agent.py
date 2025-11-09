"""Base Agent implementation with Strategy pattern."""

from typing import Any

from src.agent.base import Action, ActionType, Memory, Strategy
from src.agent.controller import ExecutionController, ExecutionRequest, create_default_controller
from src.agent.memory import ConversationalMemory
from src.agent.states import (
    ActingState,
    AgentContext,
    AgentStatus,
    CompletedState,
    ErrorState,
    IdleState,
    ThinkingState,
)
from src.agent.toolbox import ToolBox


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
        self.memory = memory or ConversationalMemory()
        self.controller = controller or create_default_controller()
        self.agent_context = AgentContext()

    def execute(self, goal: str) -> str:
        """Execute the agent to achieve a goal."""
        self.agent_context.transition_to(ThinkingState())

        try:
            while not self._is_task_complete(goal):
                context = self.memory.get_context()
                action = self.strategy.think(goal, context, self.toolbox.get_all_tools())

                # Check if action is allowed
                exec_response = self.controller.check_execution(ExecutionRequest(action=action, context=context))
                if not exec_response.allowed:
                    error_msg = f"Action blocked: {exec_response.reason}"
                    self.agent_context.transition_to(ErrorState(error_msg))
                    return error_msg

                # Record and execute action
                self.memory.add_action(action)
                result = self._execute_action(action)

                if action.type != ActionType.FINAL_ANSWER:
                    self.memory.add_observation(result)
                    self.strategy.update_context(context, action, result)

                if self.agent_context.is_terminal():
                    break

            return "Task completed" if not self.agent_context.is_terminal() else "Task execution terminated"

        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            self.agent_context.transition_to(ErrorState(error_msg))
            return error_msg
        finally:
            self.agent_context.transition_to(IdleState())

    def _execute_action(self, action: Action) -> Any:
        """Execute an action based on its type."""
        if action.type == ActionType.TOOL_CALL:
            return self._execute_tool_call(action)
        elif action.type == ActionType.FINAL_ANSWER:
            self.agent_context.transition_to(CompletedState())
            return str(action.answer)
        else:  # THINK
            return action.thought

    def _execute_tool_call(self, action: Action) -> Any:
        """Execute a tool call action."""
        if self.agent_context.get_status() != AgentStatus.ACTING:
            self.agent_context.transition_to(ActingState())

        tool = self.toolbox.get_tool(action.tool_name or "")
        if not tool:
            if self.agent_context.get_status() == AgentStatus.ACTING:
                self.agent_context.transition_to(ThinkingState())
            return {"error": f"Tool '{action.tool_name}' not found"}

        if not tool.validate_params(action.params):
            if self.agent_context.get_status() == AgentStatus.ACTING:
                self.agent_context.transition_to(ThinkingState())
            return {"error": f"Invalid parameters for tool '{action.tool_name}'"}

        result = tool.execute(action.params)

        if self.agent_context.get_status() == AgentStatus.ACTING:
            self.agent_context.transition_to(ThinkingState())

        return result

    def _is_task_complete(self, goal: str) -> bool:
        """Check if task is complete."""
        return self.agent_context.is_terminal() or not self.agent_context.can_act()

    def get_execution_trace(self) -> dict[str, Any]:
        """Get detailed execution trace."""
        return {
            "context": self.memory.get_context(),
            "state_history": self.agent_context.get_state_history(),
            "events": self.agent_context.get_events(),
            "current_state": self.agent_context.get_status().value,
        }

    def reset(self) -> None:
        """Reset the agent for a new task."""
        self.memory.clear()
        self.agent_context.reset()
        self.controller.reset_all()


class ConfigurableAgent(BaseAgent):
    """Agent with additional configuration options."""

    def __init__(
        self,
        strategy: Strategy,
        toolbox: ToolBox,
        memory: Memory | None = None,
        controller: ExecutionController | None = None,
        enable_logging: bool = True,
        max_iterations: int = 50,
    ):
        super().__init__(strategy, toolbox, memory, controller)
        self.enable_logging = enable_logging
        self.max_iterations = max_iterations
        self.current_iteration = 0

    def execute(self, goal: str) -> str:
        """Execute with iteration counting and logging."""
        self.current_iteration = 0
        result = super().execute(goal)
        if self.enable_logging:
            self._log_execution()
        return result

    def _is_task_complete(self, goal: str) -> bool:
        """Check if task complete with iteration limit."""
        self.current_iteration += 1
        if self.current_iteration >= self.max_iterations:
            self.agent_context.add_event(f"Maximum iterations ({self.max_iterations}) reached")
            return True
        return super()._is_task_complete(goal)

    def _log_execution(self) -> None:
        """Log execution details."""
        trace = self.get_execution_trace()
        print("\n=== Agent Execution Trace ===")
        print(f"Iterations: {self.current_iteration}")
        print(f"Final State: {trace['current_state']}\n")
        print("State History:")
        for state in trace["state_history"]:
            print(f"  {state['from_state']} -> {state['to_state']} at {state['timestamp']}")
        print("\nEvents:")
        for event in trace["events"]:
            print(f"  [{event['state']}] {event['message']}")


class MultiStrategyAgent(BaseAgent):
    """Agent that can switch between multiple strategies dynamically."""

    def __init__(
        self,
        strategies: dict[str, Strategy],
        default_strategy: str,
        toolbox: ToolBox,
        memory: Memory | None = None,
        controller: ExecutionController | None = None,
    ):
        if default_strategy not in strategies:
            raise ValueError(f"Default strategy '{default_strategy}' not found in strategies")

        super().__init__(strategies[default_strategy], toolbox, memory, controller)
        self.strategies = strategies
        self.current_strategy_name = default_strategy

    def switch_strategy(self, strategy_name: str) -> bool:
        """Switch to a different thinking strategy."""
        if strategy_name not in self.strategies:
            return False
        self.strategy = self.strategies[strategy_name]
        self.current_strategy_name = strategy_name
        self.agent_context.add_event(f"Switched to strategy: {strategy_name}")
        return True

    def get_current_strategy(self) -> str:
        """Get name of current strategy."""
        return self.current_strategy_name

"""State pattern for agent execution states."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    """Possible agent statuses."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


class AgentState(ABC):
    """Abstract base class for agent states (State pattern)."""

    @abstractmethod
    def get_status(self) -> AgentStatus:
        """Get the status for this state."""
        pass

    def handle(self, agent: "AgentContext") -> None:
        """Handle this state."""
        agent.add_event(f"Agent is {self.get_status().value}")

    def can_transition_to(self, next_state: "AgentState") -> bool:
        """Check if transition to next state is allowed."""
        return True  # Default: allow all transitions


# Concrete states
class IdleState(AgentState):
    def get_status(self) -> AgentStatus:
        return AgentStatus.IDLE

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, (ThinkingState, ErrorState))


class ThinkingState(AgentState):
    def get_status(self) -> AgentStatus:
        return AgentStatus.THINKING

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, (ActingState, CompletedState, ErrorState, PausedState))


class ActingState(AgentState):
    def get_status(self) -> AgentStatus:
        return AgentStatus.ACTING

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, (WaitingState, ThinkingState, ErrorState))


class WaitingState(AgentState):
    def get_status(self) -> AgentStatus:
        return AgentStatus.WAITING

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, (ThinkingState, ErrorState))


class CompletedState(AgentState):
    def get_status(self) -> AgentStatus:
        return AgentStatus.COMPLETED

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, IdleState)


class ErrorState(AgentState):
    def __init__(self, error_message: str | None = None):
        self.error_message = error_message

    def get_status(self) -> AgentStatus:
        return AgentStatus.ERROR

    def handle(self, agent: "AgentContext") -> None:
        msg = f"Agent error: {self.error_message}" if self.error_message else "Agent error occurred"
        agent.add_event(msg)

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, IdleState)


class PausedState(AgentState):
    def get_status(self) -> AgentStatus:
        return AgentStatus.PAUSED

    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state, (ThinkingState, IdleState))


class AgentContext:
    """Context that maintains the current state of an agent (State pattern)."""

    def __init__(self):
        self._state: AgentState = IdleState()
        self._state_history: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []

    @property
    def state(self) -> AgentState:
        return self._state

    def transition_to(self, new_state: AgentState) -> bool:
        """Transition to a new state."""
        if not self._state.can_transition_to(new_state):
            self.add_event(
                f"Invalid state transition: {self._state.get_status().value} -> {new_state.get_status().value}"
            )
            return False

        old_state = self._state
        self._state = new_state
        self._state_history.append(
            {
                "timestamp": datetime.now(),
                "from_state": old_state.get_status().value,
                "to_state": new_state.get_status().value,
            }
        )
        self._state.handle(self)
        return True

    def get_status(self) -> AgentStatus:
        return self._state.get_status()

    def add_event(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        self._events.append(
            {
                "timestamp": datetime.now(),
                "state": self._state.get_status().value,
                "message": message,
                "metadata": metadata or {},
            }
        )

    def get_state_history(self) -> list[dict[str, Any]]:
        return self._state_history.copy()

    def get_events(self) -> list[dict[str, Any]]:
        return self._events.copy()

    def is_terminal(self) -> bool:
        return self.get_status() in (AgentStatus.COMPLETED, AgentStatus.ERROR)

    def can_act(self) -> bool:
        return self.get_status() not in (AgentStatus.ERROR, AgentStatus.COMPLETED, AgentStatus.PAUSED)

    def reset(self) -> None:
        self._state = IdleState()
        self._state_history.clear()
        self._events.clear()

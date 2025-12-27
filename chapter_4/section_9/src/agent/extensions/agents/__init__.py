"""Specialized agent implementations.

This module provides extended agent variants with additional functionality.
"""

from src.agent.extensions.agents.configurable import ConfigurableAgent
from src.agent.extensions.agents.multi_strategy import MultiStrategyAgent

__all__ = [
    "ConfigurableAgent",
    "MultiStrategyAgent",
]

"""
Hierarchical AI Agent Layer Package.

This package implements the 4-layer hierarchical AI agent architecture:

1. Strategy Layer (戦略・プランニング層):
   - Interprets user goals and defines high-level learning roadmaps
   - Creates blueprints for lower layers without involving implementation details

2. Tactics Layer (戦術・マネジメント層):
   - Transforms strategy into actionable sub-tasks (weekly/daily plans)
   - Manages task assignment and progress aggregation

3. Execution Layer (実行層):
   - Performs concrete tasks (content generation, quiz creation)
   - Operates external tools and generates learning materials

4. Reflection Layer (自己評価・省察層):
   - Monitors execution outputs and evaluates quality
   - Requests plan corrections or retries when alignment with goals is off
"""

from src.layer.base import BaseAgent
from src.layer.execution import ContentAgent, ExecutionCoordinator, QuizAgent
from src.layer.reflection import ReflectionAgent
from src.layer.strategy import StrategyAgent
from src.layer.tactics import TacticsAgent

__all__ = [
    "BaseAgent",
    "StrategyAgent",
    "TacticsAgent",
    "ContentAgent",
    "QuizAgent",
    "ExecutionCoordinator",
    "ReflectionAgent",
]

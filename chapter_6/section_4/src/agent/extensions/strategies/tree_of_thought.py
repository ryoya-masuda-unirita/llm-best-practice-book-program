"""Tree of Thought strategy implementation."""

from dataclasses import dataclass, field

from src.agent.core.base import Action, ActionType, Tool
from src.agent.extensions.strategies.base_strategy import BaseStrategy


@dataclass
class ThoughtNode:
    """A node in the thought tree."""

    thought: str
    score: float = 0.0
    children: list["ThoughtNode"] = field(default_factory=list)


@dataclass
class ThoughtTreeLevel:
    """A level in the thought tree."""

    depth: int
    nodes: list[ThoughtNode] = field(default_factory=list)


class TreeOfThoughtStrategy(BaseStrategy):
    """Explores multiple reasoning paths using a thought tree structure."""

    def __init__(
        self,
        model: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        max_iterations: int = 10,
        branch_factor: int = 3,
    ):
        super().__init__("tree_of_thought", model, max_iterations)
        self.branch_factor = branch_factor
        self.tree_levels: list[ThoughtTreeLevel] = []

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        if self._iteration >= self.max_iterations:
            return Action(type=ActionType.FINAL_ANSWER, answer="Maximum iterations reached")

        alternatives = self._generate_alternatives(goal, available_tools)
        best = max(alternatives, key=lambda n: n.score) if alternatives else None

        if best:
            action = self._parse_action(best.thought, available_tools)
            if action.type == ActionType.THINK:
                action.thought = f"[ToT Score: {best.score:.2f}] {best.thought}"
            return action

        return Action(type=ActionType.THINK, thought="No viable alternatives found")

    def _generate_alternatives(self, goal: str, available_tools: list[Tool]) -> list[ThoughtNode]:
        tool_descriptions = "\n".join(f"- {t.name}: {t.description}" for t in available_tools)
        prompt = f"""Goal: {goal}

Available Tools:
{tool_descriptions}

Generate {self.branch_factor} different approaches to solve this goal.
For each approach, provide a brief description.
Format: Approach N: <description>
"""
        response = self._call_llm(prompt)
        nodes = []
        for line in response.split("\n"):
            line = line.strip()
            if line and ("approach" in line.lower() or ":" in line):
                node = ThoughtNode(thought=line)
                node.score = self._evaluate(node, goal)
                nodes.append(node)

        level = ThoughtTreeLevel(depth=len(self.tree_levels), nodes=nodes)
        self.tree_levels.append(level)
        return nodes

    def _evaluate(self, node: ThoughtNode, goal: str) -> float:
        prompt = f"""Rate how promising this approach is for the goal (0.0 to 1.0):
Goal: {goal}
Approach: {node.thought}

Respond with just a number between 0.0 and 1.0."""
        response = self._call_llm(prompt)
        try:
            return float(response.strip())
        except ValueError:
            return 0.5

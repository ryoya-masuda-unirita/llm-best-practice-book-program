"""Tree-of-Thought strategy: Explores multiple reasoning paths."""

from dataclasses import dataclass, field

from src.agent.core.base import Action, ActionType, Tool
from src.agent.extensions.strategies.base_strategy import BaseStrategy
from src.client.llm_client import GeminiModel
from src.logger import make_logger

logger = make_logger(__name__)


@dataclass
class ThoughtNode:
    """A node in the thought tree for Tree-of-Thought strategy."""

    thought: str
    score: float


@dataclass
class ThoughtTreeLevel:
    """A level in the thought tree."""

    depth: int
    alternatives: list[ThoughtNode] = field(default_factory=list)


class TreeOfThoughtStrategy(BaseStrategy):
    """Tree-of-Thought strategy: Explores multiple reasoning paths."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH, max_depth: int = 3, branch_factor: int = 3):
        super().__init__("Tree-of-Thought", model, max_depth)
        self.branch_factor = branch_factor
        self.thought_tree: list[ThoughtTreeLevel] = []

    def think(self, goal: str, context: dict[str, object], available_tools: list[Tool]) -> Action:
        if self.iteration >= self.max_iterations:
            best_path = " -> ".join(
                [
                    max(node.alternatives, key=lambda x: x.score).thought
                    for node in self.thought_tree
                    if node.alternatives
                ]
            )
            return Action(type=ActionType.FINAL_ANSWER, answer=f"Best solution: {best_path}")

        alternatives = self._generate_alternatives(goal)
        evaluated = [ThoughtNode(thought=alt, score=self._evaluate(alt, goal)) for alt in alternatives]
        self.thought_tree.append(ThoughtTreeLevel(depth=self.iteration, alternatives=evaluated))

        best = max(evaluated, key=lambda x: x.score)
        self.iteration += 1
        return Action(type=ActionType.THINK, thought=f"Exploring: {best.thought} (score: {best.score})")

    def _generate_alternatives(self, goal: str) -> list[str]:
        prompt = f"Generate {self.branch_factor} different approaches to solve: {goal}\n\nProvide {self.branch_factor} distinct thoughts, one per line:"
        try:
            lines = [x.strip() for x in self._call_llm(prompt).split("\n") if x.strip()]
            return lines[: self.branch_factor]
        except Exception as e:
            logger.error(e)
            return [f"Alternative approach {i + 1}" for i in range(self.branch_factor)]

    def _evaluate(self, thought: str, goal: str) -> float:
        try:
            prompt = f"Rate this approach for solving the goal (0-10):\nGoal: {goal}\nApproach: {thought}\n\nProvide only a number 0-10:"
            return float(self._call_llm(prompt).strip())
        except Exception as e:
            logger.error(e)
            return 5.0

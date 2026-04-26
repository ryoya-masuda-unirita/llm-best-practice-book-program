"""Enhanced ToolBox with categorization support."""

from src.agent.core.base import Tool
from src.agent.core.toolbox import ToolBox


class CategorizableToolBox(ToolBox):
    """ToolBox with category support for organizing tools."""

    def __init__(self, name: str = "CategorizableToolBox", description: str = "Categorized tool container"):
        super().__init__(name, description)
        self._categories: dict[str, ToolBox] = {}

    def add_category(self, category_name: str) -> None:
        if category_name not in self._categories:
            self._categories[category_name] = ToolBox(category_name, f"Tools in {category_name}")
            self.add(self._categories[category_name])

    def add_to_category(self, category_name: str, tool: Tool) -> None:
        if category_name not in self._categories:
            self.add_category(category_name)
        self._categories[category_name].add(tool)

    def get_category(self, category_name: str) -> ToolBox | None:
        return self._categories.get(category_name)

    def get_tool(self, tool_name: str) -> Tool | None:
        tool = super().get_tool(tool_name)
        if tool:
            return tool
        for category in self._categories.values():
            tool = category.get_tool(tool_name)
            if tool:
                return tool
        return None

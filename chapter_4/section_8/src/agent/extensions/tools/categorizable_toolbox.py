"""Enhanced ToolBox with categorization support."""

from src.agent.core.base import Tool
from src.agent.core.toolbox import ToolBox


class CategorizableToolBox(ToolBox):
    """Enhanced ToolBox with categorization support."""

    def __init__(self, name: str = "ToolBox", description: str = "Categorizable tool container"):
        super().__init__(name, description)
        self._categories: dict[str, ToolBox] = {}

    def add_category(self, category_name: str, description: str = "") -> ToolBox:
        """Add a tool category."""
        if category_name not in self._categories:
            category_box = ToolBox(category_name, description or f"{category_name} tools")
            self._categories[category_name] = category_box
            self.add(category_box)
        return self._categories[category_name]

    def add_to_category(self, category_name: str, tool: Tool) -> None:
        """Add a tool to a specific category."""
        self.add_category(category_name).add(tool)

    def get_category(self, category_name: str) -> ToolBox | None:
        """Get a category by name."""
        return self._categories.get(category_name)

    def get_tool(self, tool_name: str) -> Tool | None:
        """Get a tool by name, searching in categories too."""
        if tool := super().get_tool(tool_name):
            return tool
        for category in self._categories.values():
            if tool := category.get_tool(tool_name):
                return tool
        return None

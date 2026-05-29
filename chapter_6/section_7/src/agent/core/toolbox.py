"""ToolBox implementation with Composite pattern.

This module provides the core tool container that manages a collection
of tools. Specific tool implementations should be placed in the extensions layer.
"""

from src.agent.core.base import Tool, ToolParams, ToolResult


class ToolBox(Tool):
    """Composite: Container for multiple tools (Composite pattern).

    This is a core infrastructure component that provides tool management.
    It can contain individual tools or nested ToolBox instances.
    """

    def __init__(self, name: str = "ToolBox", description: str = "Container for tools"):
        super().__init__(name, description)
        self._tools: dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def remove(self, tool_name: str) -> bool:
        return self._tools.pop(tool_name, None) is not None

    def get_tool(self, tool_name: str) -> Tool | None:
        return self._tools.get(tool_name)

    def get_all_tools(self) -> list[Tool]:
        result: list[Tool] = []
        for tool in self._tools.values():
            result.extend(tool.get_all_tools() if isinstance(tool, ToolBox) else [tool])
        return result

    def execute(self, params: ToolParams) -> ToolResult:
        tool_name = params.get("tool_name")
        if not isinstance(tool_name, str) or (tool := self.get_tool(tool_name)) is None:
            return ToolResult(success=False, data=None, error=f"Tool '{tool_name}' not found")
        return tool.execute({k: v for k, v in params.items() if k != "tool_name"})

    def validate_params(self, params: ToolParams) -> bool:
        tool_name = params.get("tool_name")
        if not isinstance(tool_name, str):
            return False
        tool = self.get_tool(tool_name)
        return tool.validate_params({k: v for k, v in params.items() if k != "tool_name"}) if tool else False

    def get_schema(self) -> dict[str, str | dict]:
        return {
            "name": self.name,
            "description": self.description,
            "tools": {tool.name: tool.get_schema() for tool in self._tools.values()},
        }

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools

"""ToolBox implementation with Composite pattern."""

from src.agent.base import Tool, ToolParams, ToolResult


class ToolBox(Tool):
    """Composite: Container for multiple tools (Composite pattern)."""

    def __init__(self, name: str = "ToolBox", description: str = "Container for tools"):
        super().__init__(name, description)
        self._tools: dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        """Add a tool to the toolbox."""
        self._tools[tool.name] = tool

    def remove(self, tool_name: str) -> bool:
        """Remove a tool from the toolbox."""
        return self._tools.pop(tool_name, None) is not None

    def get_tool(self, tool_name: str) -> Tool | None:
        """Get a tool by name, searching recursively in nested toolboxes."""
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            if not isinstance(tool, ToolBox):  # Don't return ToolBoxes as tools
                return tool

        for tool in self._tools.values():
            if isinstance(tool, ToolBox):
                found = tool.get_tool(tool_name)
                if found is not None:
                    return found

        return None

    def get_all_tools(self) -> list[Tool]:
        """Get all tools recursively."""
        result: list[Tool] = []
        for tool in self._tools.values():
            result.extend(tool.get_all_tools() if isinstance(tool, ToolBox) else [tool])
        return result

    def execute(self, params: ToolParams) -> ToolResult:
        """Execute a tool from the toolbox."""
        tool_name = params.get("tool_name")
        if not isinstance(tool_name, str) or (tool := self.get_tool(tool_name)) is None:
            return ToolResult(success=False, data=None, error=f"Tool '{tool_name}' not found")
        return tool.execute({k: v for k, v in params.items() if k != "tool_name"})

    def validate_params(self, params: ToolParams) -> bool:
        """Validate parameters for toolbox execution."""
        tool_name = params.get("tool_name")
        if not isinstance(tool_name, str):
            return False
        tool = self.get_tool(tool_name)
        return tool.validate_params({k: v for k, v in params.items() if k != "tool_name"}) if tool else False

    def get_schema(self) -> dict[str, str | dict]:
        """Get schema for all tools in the toolbox."""
        return {
            "name": self.name,
            "description": self.description,
            "tools": {tool.name: tool.get_schema() for tool in self._tools.values()},
        }

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools


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


class CalculatorTool(Tool):
    """Example: Simple calculator tool."""

    def __init__(self):
        super().__init__("calculator", "Performs basic arithmetic operations")

    def execute(self, params: ToolParams) -> ToolResult:
        try:
            op = params.get("operation")
            operands = params.get("operands")
            if not isinstance(op, str) or not isinstance(operands, list):
                return ToolResult(success=False, data=None, error="operation and operands required")

            nums: list[int | float] = [n for n in operands if isinstance(n, (int, float))]
            if not nums:
                return ToolResult(success=False, data=None, error="No valid numeric operands")

            result: int | float | None = {
                "add": lambda: sum(nums),
                "subtract": lambda: nums[0] - sum(nums[1:]),
                "multiply": lambda: eval("*".join(map(str, nums))),
                "divide": lambda: nums[0] / nums[1] if len(nums) == 2 and nums[1] != 0 else None,
            }.get(op, lambda: None)()

            return ToolResult(
                success=result is not None,
                data=result,
                error=None if result is not None else "Invalid operation or division by zero",
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def validate_params(self, params: ToolParams) -> bool:
        op = params.get("operation")
        operands = params.get("operands")
        return (
            isinstance(op, str)
            and op in ["add", "subtract", "multiply", "divide"]
            and isinstance(operands, list)
            and len(operands) > 0
            and all(isinstance(x, (int, float)) for x in operands)
        )


class WebSearchTool(Tool):
    """Example: Mock web search tool."""

    def __init__(self):
        super().__init__("web_search", "Searches the web for information")

    def execute(self, params: ToolParams) -> ToolResult:
        query = params.get("query")
        if not isinstance(query, str):
            return ToolResult(success=False, data=None, error="query is required")
        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": [
                    {"title": f"Result 1 for {query}", "snippet": "Mock result 1"},
                    {"title": f"Result 2 for {query}", "snippet": "Mock result 2"},
                ],
            },
            metadata={"search_time_ms": 150},
        )

    def validate_params(self, params: ToolParams) -> bool:
        return isinstance(params.get("query"), str)


class BrainstormTool(Tool):
    """Creative writing tool: Generates ideas for a given topic."""

    def __init__(self):
        super().__init__("brainstorm", "Generates creative ideas for a given topic or theme")

    def execute(self, params: ToolParams) -> ToolResult:
        topic = params.get("topic")
        if not isinstance(topic, str):
            return ToolResult(success=False, data=None, error="topic is required")
        count = params.get("count", 3)
        if not isinstance(count, int):
            count = 3
        ideas = [f"Idea {i + 1} for '{topic}': A creative concept exploring {topic}" for i in range(count)]
        return ToolResult(
            success=True,
            data={"topic": topic, "ideas": ideas},
        )

    def validate_params(self, params: ToolParams) -> bool:
        return isinstance(params.get("topic"), str)


class WriteDraftTool(Tool):
    """Creative writing tool: Writes a draft based on a prompt."""

    def __init__(self):
        super().__init__("write_draft", "Writes a creative draft based on a prompt and style")

    def execute(self, params: ToolParams) -> ToolResult:
        prompt = params.get("prompt")
        style = params.get("style", "narrative")
        if not isinstance(prompt, str):
            return ToolResult(success=False, data=None, error="prompt is required")
        draft = f"[Draft in {style} style]\n\n{prompt}\n\nThis is a creative draft exploring the theme..."
        return ToolResult(
            success=True,
            data={"prompt": prompt, "style": style, "draft": draft},
        )

    def validate_params(self, params: ToolParams) -> bool:
        return isinstance(params.get("prompt"), str)


class EditTextTool(Tool):
    """Creative writing tool: Edits and improves text."""

    def __init__(self):
        super().__init__("edit_text", "Edits and improves text based on specified criteria")

    def execute(self, params: ToolParams) -> ToolResult:
        text = params.get("text")
        edit_type = params.get("edit_type", "polish")
        if not isinstance(text, str):
            return ToolResult(success=False, data=None, error="text is required")
        edited = f"[Edited ({edit_type})]: {text}"
        return ToolResult(
            success=True,
            data={"original": text, "edit_type": edit_type, "edited": edited},
        )

    def validate_params(self, params: ToolParams) -> bool:
        return isinstance(params.get("text"), str)


class GenerateTitleTool(Tool):
    """Creative writing tool: Generates titles for content."""

    def __init__(self):
        super().__init__("generate_title", "Generates creative titles for content")

    def execute(self, params: ToolParams) -> ToolResult:
        content = params.get("content")
        genre = params.get("genre", "general")
        if not isinstance(content, str):
            return ToolResult(success=False, data=None, error="content is required")
        titles = [
            f"Title 1: The Art of {genre.title()}",
            f"Title 2: A {genre.title()} Journey",
            f"Title 3: Beyond {genre.title()}",
        ]
        return ToolResult(
            success=True,
            data={"content_preview": content[:50], "genre": genre, "titles": titles},
        )

    def validate_params(self, params: ToolParams) -> bool:
        return isinstance(params.get("content"), str)

"""Mock web search tool."""

from src.agent.core.base import Tool, ToolParams, ToolResult


class WebSearchTool(Tool):
    MOCK_DATA = {
        "eiffel tower": "The Eiffel Tower is 330 meters tall, located in Paris, France.",
        "tokyo population": "Tokyo has a population of approximately 14 million people.",
        "earth moon distance": "The average distance from Earth to the Moon is about 384,400 km.",
        "speed of light": "The speed of light in vacuum is approximately 299,792,458 meters per second.",
        "water boiling point": "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
    }

    def __init__(self):
        super().__init__("web_search", "Search the web for information")

    def execute(self, params: ToolParams) -> ToolResult:
        query = str(params.get("query", "")).lower()

        for key, value in self.MOCK_DATA.items():
            if key in query:
                return ToolResult(success=True, data={"query": query, "answer": value})

        return ToolResult(
            success=True,
            data={"query": query, "answer": f"No specific results found for: {query}"},
        )

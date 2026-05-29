"""Mock web search tool implementation."""

from src.agent.core.base import Tool, ToolParams, ToolResult


class WebSearchTool(Tool):
    """Example: Mock web search tool."""

    # Mock knowledge base for realistic responses
    MOCK_KNOWLEDGE: dict[str, str] = {
        "eiffel tower": "The Eiffel Tower is a 330-meter tall iron lattice tower in Paris, France. Built in 1889 for the World's Fair, it was designed by Gustave Eiffel. It attracts nearly 7 million visitors annually and offers stunning views of Paris from its observation decks.",
        "population tokyo": "Tokyo has a population of approximately 14 million people.",
        "distance earth moon": "The distance from Earth to the Moon is about 384,400 kilometers.",
        "speed of light": "The speed of light is approximately 299,792 kilometers per second.",
        "boiling point water": "Water boils at 100 degrees Celsius at sea level.",
    }

    def __init__(self):
        super().__init__(
            "web_search",
            "Searches the web for factual information. "
            'Parameters: query (string). Example: {"query": "eiffel tower height"}',
        )

    def execute(self, params: ToolParams) -> ToolResult:
        query = params.get("query")
        if not isinstance(query, str):
            return ToolResult(success=False, data=None, error="query is required")

        query_lower = query.lower()
        for key, answer in self.MOCK_KNOWLEDGE.items():
            if key in query_lower or all(word in query_lower for word in key.split()):
                return ToolResult(
                    success=True,
                    data={"query": query, "answer": answer},
                    metadata={"search_time_ms": 150},
                )

        return ToolResult(
            success=True,
            data={"query": query, "answer": "No relevant information found."},
            metadata={"search_time_ms": 150},
        )

    def validate_params(self, params: ToolParams) -> bool:
        return isinstance(params.get("query"), str)

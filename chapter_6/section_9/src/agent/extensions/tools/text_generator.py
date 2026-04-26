"""Text generation tool using LLM."""

from src.agent.core.base import Tool, ToolParams, ToolResult
from src.client.llm_client import google_genai_client


class TextGeneratorTool(Tool):
    def __init__(self):
        super().__init__("text_generator", "Generate creative text content")

    def execute(self, params: ToolParams) -> ToolResult:
        topic = params.get("topic", "general")
        style = params.get("style", "formal")

        valid_styles = ["formal", "casual", "poetic", "humorous"]
        if style not in valid_styles:
            return ToolResult(success=False, data=None, error=f"Invalid style. Choose from: {valid_styles}")

        prompt = f"Write a short {style} paragraph about {topic}."

        try:
            response = google_genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return ToolResult(
                success=True,
                data={"content": response.text, "style": style, "topic": topic},
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

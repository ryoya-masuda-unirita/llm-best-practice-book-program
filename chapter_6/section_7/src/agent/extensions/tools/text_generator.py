"""Text generation tool for creative writing tasks."""

from src.agent.core.base import Tool, ToolParams, ToolResult
from src.client.llm_client import AnthropicModel, anthropic_client


class TextGeneratorTool(Tool):
    """Tool for generating creative text content."""

    def __init__(self, model: AnthropicModel = AnthropicModel.CLAUDE_HAIKU_4_5):
        super().__init__(
            "text_generator",
            "Generates creative text content. "
            "Parameters: task (string describing what to write), "
            "style (optional: 'formal', 'casual', 'poetic', 'humorous'). "
            'Example: {"task": "write a haiku about rain", "style": "poetic"}',
        )
        self.model = model

    def execute(self, params: ToolParams) -> ToolResult:
        task = params.get("task")
        if not isinstance(task, str):
            return ToolResult(success=False, data=None, error="task parameter is required")

        style = params.get("style", "casual")
        prompt = f"You are a creative writer. Style: {style}. Task: {task}\n\nProvide only the creative content, no explanations."

        try:
            response = anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return ToolResult(
                success=True,
                data={"content": response.content[0].text, "style": style},
                metadata={"task": task},
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def validate_params(self, params: ToolParams) -> bool:
        task = params.get("task")
        style = params.get("style")
        if not isinstance(task, str) or not task.strip():
            return False
        if style is not None and style not in ["formal", "casual", "poetic", "humorous"]:
            return False
        return True

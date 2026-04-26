"""Simple calculator tool."""

from src.agent.core.base import Tool, ToolParams, ToolResult


class CalculatorTool(Tool):
    def __init__(self):
        super().__init__("calculator", "Perform basic arithmetic operations")

    def execute(self, params: ToolParams) -> ToolResult:
        operation = params.get("operation", "")
        a = params.get("a")
        b = params.get("b")

        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return ToolResult(success=False, data=None, error="Operands must be numeric")

        operations = {
            "add": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else None,
        }

        if operation not in operations:
            return ToolResult(success=False, data=None, error=f"Unknown operation: {operation}")
        if operations[operation] is None:
            return ToolResult(success=False, data=None, error="Division by zero")

        return ToolResult(success=True, data=operations[operation])

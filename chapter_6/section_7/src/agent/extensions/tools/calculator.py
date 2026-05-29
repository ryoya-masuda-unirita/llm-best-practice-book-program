"""Simple calculator tool implementation."""

from src.agent.core.base import Tool, ToolParams, ToolResult


class CalculatorTool(Tool):
    """Example: Simple calculator tool."""

    def __init__(self):
        super().__init__(
            "calculator",
            "Performs basic arithmetic operations. "
            "Parameters: operation (string: 'add', 'subtract', 'multiply', or 'divide'), "
            'operands (list of numbers). Example: {"operation": "add", "operands": [15, 27]}',
        )

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

"""Result formatting functions for tool responses."""

from datetime import datetime

from src.model import ToolResultStatus


def generate_result_id(tool_name: str, context: str = "") -> str:
    """Generate a human-readable result ID with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if context:
        return f"{tool_name}_{context}_{timestamp}"
    return f"{tool_name}_{timestamp}"


def build_error_response(tool_name: str, message: str) -> dict:
    """Build a standardized error response dict."""
    return {
        "tool_name": tool_name,
        "result_id": "",
        "result_summary": f"Error: {message}",
        "status": ToolResultStatus.ERROR.value,
    }


def build_success_response(
    tool_name: str,
    result_id: str,
    summary: str,
    **extra_fields,
) -> dict:
    """Build a standardized success response dict."""
    response = {
        "tool_name": tool_name,
        "result_id": result_id,
        "result_summary": summary,
        "status": ToolResultStatus.SUCCESS.value,
    }
    response.update(extra_fields)
    return response


def format_filter_context(
    classes: list[str] | None = None,
    student_ids: list[str] | None = None,
    quarters: list[int] | None = None,
    all_classes_count: int = 5,
    all_quarters_count: int = 4,
) -> str:
    """Build a context string for result ID from filter parameters."""
    parts = []

    if classes and len(classes) < all_classes_count:
        parts.append("_".join(classes))

    if student_ids:
        parts.append(f"{len(student_ids)}students")

    if quarters and len(quarters) < all_quarters_count:
        parts.append(f"q{''.join(map(str, quarters))}")

    return "_".join(parts) if parts else "all"


def format_grade_distribution(grade_counts: dict[str, int]) -> str:
    """Format grade distribution as 'A:5, B:10, C:3'."""
    return ", ".join(f"{k}:{v}" for k, v in grade_counts.items() if v > 0)


def format_comparison_summary(comparison: dict, subjects: list[str]) -> str:
    """Format student comparison as 'math: S1 wins; physics: tie'."""
    parts = []
    for subject in subjects:
        winner = comparison[subject]["winner"]
        if winner == "student1":
            parts.append(f"{subject}: S1 wins")
        elif winner == "student2":
            parts.append(f"{subject}: S2 wins")
        else:
            parts.append(f"{subject}: tie")
    return "; ".join(parts)


def format_statistics_summary(stats: dict[str, dict]) -> str:
    """Format statistics dict for summary display."""
    subject_means = []
    for subject, stat in stats.items():
        if "mean" in stat:
            subject_means.append(f"{subject}: {stat['mean']}")
    return ", ".join(subject_means)


def truncate_id(id_str: str, length: int = 8) -> str:
    """Truncate an ID string for display, appending '...' if needed."""
    if len(id_str) <= length:
        return id_str
    return f"{id_str[:length]}..."

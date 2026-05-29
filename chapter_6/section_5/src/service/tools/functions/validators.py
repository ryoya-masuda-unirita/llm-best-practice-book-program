"""Input validation functions for data analysis tools."""

from dataclasses import dataclass

VALID_CLASSES = ["japanese", "math", "physics", "history", "pe"]
VALID_QUARTERS = [1, 2, 3, 4]


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    value: any = None
    error_message: str = ""


def validate_quarter(quarter: int) -> ValidationResult:
    """Validate a quarter number (must be 1-4)."""
    if quarter in VALID_QUARTERS:
        return ValidationResult(is_valid=True, value=quarter)
    return ValidationResult(
        is_valid=False,
        error_message=f"Invalid quarter {quarter}. Must be 1-4.",
    )


def validate_quarters(quarters: list[int] | None) -> ValidationResult:
    """Validate quarter list; None defaults to all quarters."""
    if quarters is None:
        return ValidationResult(is_valid=True, value=list(VALID_QUARTERS))

    invalid = [q for q in quarters if q not in VALID_QUARTERS]
    if invalid:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid quarter(s): {invalid}. Must be 1-4.",
        )
    return ValidationResult(is_valid=True, value=quarters)


def validate_class_name(class_name: str) -> ValidationResult:
    """Validate a class name; returns normalized lowercase value."""
    normalized = class_name.lower()
    if normalized in VALID_CLASSES:
        return ValidationResult(is_valid=True, value=normalized)
    return ValidationResult(
        is_valid=False,
        error_message=f"Invalid class '{class_name}'. Must be one of: {', '.join(VALID_CLASSES)}",
    )


def validate_classes(classes: list[str] | None) -> ValidationResult:
    """Validate class name list; None defaults to all classes."""
    if classes is None:
        return ValidationResult(is_valid=True, value=list(VALID_CLASSES))

    normalized = [c.lower() for c in classes]
    invalid = [c for c in normalized if c not in VALID_CLASSES]
    if invalid:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid class(es): {', '.join(invalid)}. Valid: {', '.join(VALID_CLASSES)}",
        )
    return ValidationResult(is_valid=True, value=normalized)


def validate_student_id(student_id: str, available_ids: list[str]) -> ValidationResult:
    """Validate a student ID against available IDs."""
    if student_id in available_ids:
        return ValidationResult(is_valid=True, value=student_id)
    return ValidationResult(
        is_valid=False,
        error_message=f"Student {student_id} not found in records.",
    )


def validate_student_ids(
    student_ids: list[str] | None,
    available_ids: list[str],
) -> ValidationResult:
    """Validate student ID list; None defaults to all students."""
    if student_ids is None:
        return ValidationResult(is_valid=True, value=None)

    invalid = [sid for sid in student_ids if sid not in available_ids]
    if invalid:
        return ValidationResult(
            is_valid=False,
            error_message=f"Student(s) not found: {', '.join(s[:8] + '...' for s in invalid)}",
        )
    return ValidationResult(is_valid=True, value=student_ids)


def validate_result_id(result_id: str, available_ids: list[str]) -> ValidationResult:
    """Validate a result ID against stored results."""
    if result_id in available_ids:
        return ValidationResult(is_valid=True, value=result_id)
    return ValidationResult(
        is_valid=False,
        error_message=f"Result ID '{result_id}' not found. Available IDs: {', '.join(available_ids)}",
    )

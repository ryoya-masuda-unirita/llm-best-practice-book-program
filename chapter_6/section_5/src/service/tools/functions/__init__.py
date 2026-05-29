"""
Reusable functions for data analysis tools.

This module provides small, testable functions that are composed
by the tool functions in data_tools.py.
"""

from src.service.tools.functions.analyzers import (
    ClassPerformance,
    GradeDistribution,
    ScoreAnalysis,
    StudentPerformance,
    SubjectStats,
    analyze_class_scores,
    analyze_scores,
    analyze_student_scores,
    calculate_curriculum_completion,
    calculate_grade_distribution,
    calculate_overall_mean,
    calculate_subject_stats,
    compare_two_students,
)
from src.service.tools.functions.formatters import (
    build_error_response,
    build_success_response,
    format_comparison_summary,
    format_filter_context,
    format_grade_distribution,
    format_statistics_summary,
    generate_result_id,
    truncate_id,
)
from src.service.tools.functions.loaders import (
    get_data_directory,
    list_json_files,
    load_all_quarterly_curriculum,
    load_all_quarterly_grades,
    load_all_quarterly_scores,
    load_curriculum,
    load_grade_report,
    load_json_file,
    load_students,
    load_test_scores,
    quarter_to_ordinal,
)
from src.service.tools.functions.validators import (
    VALID_CLASSES,
    VALID_QUARTERS,
    ValidationResult,
    validate_class_name,
    validate_classes,
    validate_quarter,
    validate_quarters,
    validate_result_id,
    validate_student_id,
    validate_student_ids,
)

__all__ = [
    # Loaders
    "get_data_directory",
    "list_json_files",
    "load_json_file",
    "load_students",
    "load_test_scores",
    "load_grade_report",
    "load_curriculum",
    "load_all_quarterly_scores",
    "load_all_quarterly_grades",
    "load_all_quarterly_curriculum",
    "quarter_to_ordinal",
    # Validators
    "VALID_CLASSES",
    "VALID_QUARTERS",
    "ValidationResult",
    "validate_quarter",
    "validate_quarters",
    "validate_class_name",
    "validate_classes",
    "validate_student_id",
    "validate_student_ids",
    "validate_result_id",
    # Analyzers
    "SubjectStats",
    "ScoreAnalysis",
    "GradeDistribution",
    "StudentPerformance",
    "ClassPerformance",
    "calculate_subject_stats",
    "calculate_overall_mean",
    "analyze_scores",
    "calculate_grade_distribution",
    "analyze_student_scores",
    "analyze_class_scores",
    "compare_two_students",
    "calculate_curriculum_completion",
    # Formatters
    "generate_result_id",
    "build_error_response",
    "build_success_response",
    "format_filter_context",
    "format_grade_distribution",
    "format_comparison_summary",
    "format_statistics_summary",
    "truncate_id",
]

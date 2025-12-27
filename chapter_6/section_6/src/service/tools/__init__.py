from src.service.tools.data_tools import (
    analyze_class_performance,
    analyze_student_performance,
    compare_students,
    filter_curriculum,
    filter_grades,
    filter_scores,
    get_curriculum,
    get_grade_report,
    get_result_details,
    get_students,
    get_test_scores,
    list_available_data,
    result_storage,
)

__all__ = [
    "list_available_data",
    "get_students",
    "get_test_scores",
    "get_grade_report",
    "get_curriculum",
    "analyze_student_performance",
    "analyze_class_performance",
    "get_result_details",
    "compare_students",
    "filter_scores",
    "filter_grades",
    "filter_curriculum",
    "result_storage",
]

# Tool function registry for easy access
TOOL_FUNCTIONS = {
    "list_available_data": list_available_data,
    "get_students": get_students,
    "get_test_scores": get_test_scores,
    "get_grade_report": get_grade_report,
    "get_curriculum": get_curriculum,
    "analyze_student_performance": analyze_student_performance,
    "analyze_class_performance": analyze_class_performance,
    "get_result_details": get_result_details,
    "compare_students": compare_students,
    "filter_scores": filter_scores,
    "filter_grades": filter_grades,
    "filter_curriculum": filter_curriculum,
}

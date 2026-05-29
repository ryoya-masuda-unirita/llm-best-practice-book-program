"""
Tool metadata registry with test data for dry run validation.

This module defines metadata for all tools including:
- Input/output schemas
- Connectable tools for chaining
- Mini test data for dry run validation
"""

from src.model.schemas import (
    AnalyzeClassPerformanceInput,
    AnalyzeClassPerformanceOutput,
    AnalyzeStudentPerformanceInput,
    AnalyzeStudentPerformanceOutput,
    CompareStudentsInput,
    CompareStudentsOutput,
    FilterCurriculumInput,
    FilterCurriculumOutput,
    FilterGradesInput,
    FilterGradesOutput,
    FilterScoresInput,
    FilterScoresOutput,
    GetCurriculumInput,
    GetCurriculumOutput,
    GetGradeReportInput,
    GetGradeReportOutput,
    GetResultDetailsInput,
    GetResultDetailsOutput,
    GetStudentsInput,
    GetStudentsOutput,
    GetTestScoresInput,
    GetTestScoresOutput,
    ListAvailableDataInput,
    ListAvailableDataOutput,
)
from src.model.tool_chain_models import ToolCategory, ToolMetadata

TEST_STUDENT_ID_1 = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
TEST_STUDENT_ID_2 = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"

TOOL_METADATA: dict[str, ToolMetadata] = {
    "list_available_data": ToolMetadata(
        name="list_available_data",
        description="List all available data files in the data directory",
        category=ToolCategory.LOADER,
        input_model=ListAvailableDataInput,
        output_model=ListAvailableDataOutput,
        output_keys=["file_count", "file_categories", "files"],
        connectable_to=[
            "get_students",
            "get_test_scores",
            "get_grade_report",
            "get_curriculum",
        ],
        is_chain_terminal=False,
        test_input={},
    ),
    "get_students": ToolMetadata(
        name="get_students",
        description="Get the list of all students in the system",
        category=ToolCategory.LOADER,
        input_model=GetStudentsInput,
        output_model=GetStudentsOutput,
        output_keys=["student_count", "student_ids"],
        connectable_to=[
            "analyze_student_performance",
            "compare_students",
            "filter_scores",
            "filter_grades",
        ],
        is_chain_terminal=False,
        test_input={},
    ),
    "get_test_scores": ToolMetadata(
        name="get_test_scores",
        description="Get test scores for a specific quarter",
        category=ToolCategory.LOADER,
        input_model=GetTestScoresInput,
        output_model=GetTestScoresOutput,
        output_keys=[
            "quarter",
            "student_count",
            "subjects",
            "subject_stats",
            "overall_average",
            "scores",
        ],
        connectable_to=[
            "filter_scores",
            "analyze_student_performance",
            "analyze_class_performance",
        ],
        is_chain_terminal=False,
        test_input={"quarter": 1},
    ),
    "get_grade_report": ToolMetadata(
        name="get_grade_report",
        description="Get grade reports for a specific quarter",
        category=ToolCategory.LOADER,
        input_model=GetGradeReportInput,
        output_model=GetGradeReportOutput,
        output_keys=["quarter", "student_count", "grade_distribution", "reports"],
        connectable_to=[
            "filter_grades",
            "analyze_student_performance",
        ],
        is_chain_terminal=False,
        test_input={"quarter": 1},
    ),
    "get_curriculum": ToolMetadata(
        name="get_curriculum",
        description="Get curriculum information for a specific quarter",
        category=ToolCategory.LOADER,
        input_model=GetCurriculumInput,
        output_model=GetCurriculumOutput,
        output_keys=["quarter", "subjects", "average_completion", "curriculum_data"],
        connectable_to=[
            "filter_curriculum",
            "analyze_class_performance",
        ],
        is_chain_terminal=False,
        test_input={"quarter": 1},
    ),
    "analyze_student_performance": ToolMetadata(
        name="analyze_student_performance",
        description="Comprehensive analysis of a student's performance across all quarters",
        category=ToolCategory.ANALYZER,
        input_model=AnalyzeStudentPerformanceInput,
        output_model=AnalyzeStudentPerformanceOutput,
        output_keys=[
            "student_id",
            "quarters_analyzed",
            "overall_average",
            "subject_averages",
            "strongest_subject",
            "weakest_subject",
            "trends",
        ],
        connectable_to=[
            "compare_students",
            "get_result_details",
        ],
        is_chain_terminal=True,
        test_input={"student_id": TEST_STUDENT_ID_1},
    ),
    "analyze_class_performance": ToolMetadata(
        name="analyze_class_performance",
        description="Comprehensive analysis of a class's performance across all students and quarters",
        category=ToolCategory.ANALYZER,
        input_model=AnalyzeClassPerformanceInput,
        output_model=AnalyzeClassPerformanceOutput,
        output_keys=[
            "class_name",
            "quarters_analyzed",
            "class_average",
            "top_performer_id",
            "top_performer_avg",
            "curriculum_completion_avg",
        ],
        connectable_to=[
            "get_result_details",
        ],
        is_chain_terminal=True,
        test_input={"class_name": "math"},
    ),
    "get_result_details": ToolMetadata(
        name="get_result_details",
        description="Retrieve detailed data for a previously computed result",
        category=ToolCategory.RETRIEVER,
        input_model=GetResultDetailsInput,
        output_model=GetResultDetailsOutput,
        output_keys=["original_result_id", "data_type", "detailed_data"],
        connectable_to=[],
        is_chain_terminal=True,
        test_input=None,  # Cannot test without valid result_id
    ),
    "compare_students": ToolMetadata(
        name="compare_students",
        description="Compare performance between two students across all quarters",
        category=ToolCategory.ANALYZER,
        input_model=CompareStudentsInput,
        output_model=CompareStudentsOutput,
        output_keys=[
            "student1_id",
            "student2_id",
            "comparison",
            "overall_averages",
        ],
        connectable_to=[
            "get_result_details",
        ],
        is_chain_terminal=True,
        test_input={
            "student_id_1": TEST_STUDENT_ID_1,
            "student_id_2": TEST_STUDENT_ID_2,
        },
    ),
    "filter_scores": ToolMetadata(
        name="filter_scores",
        description="Filter and retrieve test scores with flexible filtering",
        category=ToolCategory.FILTER,
        input_model=FilterScoresInput,
        output_model=FilterScoresOutput,
        output_keys=[
            "record_count",
            "unique_students",
            "unique_quarters",
            "overall_average",
            "subject_stats",
            "scores",
        ],
        connectable_to=[
            "analyze_student_performance",
            "analyze_class_performance",
            "get_result_details",
        ],
        is_chain_terminal=False,
        test_input={
            "classes": ["math", "physics"],
            "quarters": [1],
        },
    ),
    "filter_grades": ToolMetadata(
        name="filter_grades",
        description="Filter and retrieve grade reports with flexible filtering",
        category=ToolCategory.FILTER,
        input_model=FilterGradesInput,
        output_model=FilterGradesOutput,
        output_keys=[
            "record_count",
            "unique_students",
            "unique_quarters",
            "overall_distribution",
            "class_distribution",
            "grades",
        ],
        connectable_to=[
            "analyze_student_performance",
            "get_result_details",
        ],
        is_chain_terminal=False,
        test_input={
            "classes": ["math"],
            "quarters": [1],
        },
    ),
    "filter_curriculum": ToolMetadata(
        name="filter_curriculum",
        description="Filter and retrieve curriculum data with flexible filtering",
        category=ToolCategory.FILTER,
        input_model=FilterCurriculumInput,
        output_model=FilterCurriculumOutput,
        output_keys=[
            "record_count",
            "average_completion",
            "class_completion",
            "curriculum",
        ],
        connectable_to=[
            "analyze_class_performance",
            "get_result_details",
        ],
        is_chain_terminal=False,
        test_input={
            "classes": ["math"],
            "quarters": [1],
        },
    ),
}


def get_tool_metadata(tool_name: str) -> ToolMetadata | None:
    """Get metadata for a specific tool."""
    return TOOL_METADATA.get(tool_name)


def get_all_tool_metadata() -> dict[str, ToolMetadata]:
    """Get all tool metadata."""
    return TOOL_METADATA.copy()


def get_connectable_tools(tool_name: str) -> list[str]:
    """Get list of tools that can be connected after the given tool."""
    metadata = get_tool_metadata(tool_name)
    if metadata:
        return metadata.connectable_to.copy()
    return []


def get_tools_by_category(category: ToolCategory) -> list[ToolMetadata]:
    """Get all tools in a specific category."""
    return [m for m in TOOL_METADATA.values() if m.category == category]


def get_terminal_tools() -> list[str]:
    """Get list of tools that typically end a chain."""
    return [name for name, m in TOOL_METADATA.items() if m.is_chain_terminal]


def get_tools_with_test_data() -> list[str]:
    """Get list of tools that have test data for dry run."""
    return [name for name, m in TOOL_METADATA.items() if m.test_input is not None]


def build_tool_metadata_for_llm() -> list[dict]:
    """
    Build tool metadata information for LLM context.

    This function creates a serializable representation of all tool metadata
    that can be passed to the LLM as context for structured output generation.
    The LLM uses this information to decide which tools to include in a chain
    and how to connect them.

    Returns:
        List of dicts containing tool metadata with:
        - name: Tool name
        - description: What the tool does
        - category: Tool category (loader, analyzer, filter, etc.)
        - input_schema: Dict of input field names with their descriptions and requirements
        - output_keys: List of output keys available for chaining
        - connectable_to: List of tools that can follow this one
        - is_chain_terminal: Whether this tool typically ends a chain
    """
    tools_info = []

    for name, metadata in TOOL_METADATA.items():
        # Build input schema from Pydantic model
        input_schema = {}
        for field_name, field_info in metadata.input_model.model_fields.items():
            input_schema[field_name] = {
                "description": field_info.description or "No description",
                "required": field_info.is_required(),
                "type": str(field_info.annotation) if field_info.annotation else "any",
            }

        tools_info.append(
            {
                "name": name,
                "description": metadata.description,
                "category": metadata.category.value,
                "input_schema": input_schema,
                "output_keys": metadata.output_keys,
                "connectable_to": metadata.connectable_to,
                "is_chain_terminal": metadata.is_chain_terminal,
            }
        )

    return tools_info


def get_available_tool_names() -> list[str]:
    """Get list of all available tool names."""
    return list(TOOL_METADATA.keys())

"""
Pydantic models for tool input/output schemas.

This module defines strongly-typed input and output models for all tool functions,
enabling Tool Chain execution with type-safe data passing between tools.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClassName(StrEnum):
    """Valid class names for the school system."""

    JAPANESE = "japanese"
    MATH = "math"
    PHYSICS = "physics"
    HISTORY = "history"
    PE = "pe"

    @classmethod
    def all(cls) -> list[str]:
        return [c.value for c in cls]


class Quarter(StrEnum):
    """Valid quarters for the school year."""

    Q1 = "1"
    Q2 = "2"
    Q3 = "3"
    Q4 = "4"

    @classmethod
    def all(cls) -> list[int]:
        return [1, 2, 3, 4]


class GradeLetter(StrEnum):
    """Valid letter grades."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ToolInput(BaseModel):
    """Base class for tool input models."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        frozen=True,
    )


class ToolOutput(BaseModel):
    """Base class for tool output models."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
    )

    tool_name: str = Field(..., description="Name of the tool that produced this output")
    result_id: str = Field(default="", description="Unique ID to reference the result")
    result_summary: str = Field(default="", description="Human-readable summary")
    success: bool = Field(default=True, description="Whether the tool execution succeeded")
    error_message: str | None = Field(default=None, description="Error message if failed")


class ListAvailableDataInput(ToolInput):
    """Input for list_available_data tool (no parameters)."""

    pass


class GetStudentsInput(ToolInput):
    """Input for get_students tool (no parameters)."""

    pass


class GetTestScoresInput(ToolInput):
    """Input for get_test_scores tool."""

    quarter: int = Field(..., ge=1, le=4, description="Quarter number (1-4)")


class GetGradeReportInput(ToolInput):
    """Input for get_grade_report tool."""

    quarter: int = Field(..., ge=1, le=4, description="Quarter number (1-4)")


class GetCurriculumInput(ToolInput):
    """Input for get_curriculum tool."""

    quarter: int = Field(..., ge=1, le=4, description="Quarter number (1-4)")


class AnalyzeStudentPerformanceInput(ToolInput):
    """Input for analyze_student_performance tool."""

    student_id: str = Field(..., description="UUID of the student to analyze")


class AnalyzeClassPerformanceInput(ToolInput):
    """Input for analyze_class_performance tool."""

    class_name: str = Field(..., description="Name of the class to analyze")


class GetResultDetailsInput(ToolInput):
    """Input for get_result_details tool."""

    result_id: str = Field(..., description="The result ID from a previous tool call")


class CompareStudentsInput(ToolInput):
    """Input for compare_students tool."""

    student_id_1: str = Field(..., description="UUID of the first student")
    student_id_2: str = Field(..., description="UUID of the second student")


class FilterScoresInput(ToolInput):
    """Input for filter_scores tool."""

    classes: list[str] | None = Field(default=None, description="List of class names to include")
    student_ids: list[str] | None = Field(default=None, description="List of student UUIDs to include")
    quarters: list[int] | None = Field(default=None, description="List of quarter numbers (1-4)")


class FilterGradesInput(ToolInput):
    """Input for filter_grades tool."""

    classes: list[str] | None = Field(default=None, description="List of class names to include")
    student_ids: list[str] | None = Field(default=None, description="List of student UUIDs to include")
    quarters: list[int] | None = Field(default=None, description="List of quarter numbers (1-4)")


class FilterCurriculumInput(ToolInput):
    """Input for filter_curriculum tool."""

    classes: list[str] | None = Field(default=None, description="List of class names to include")
    quarters: list[int] | None = Field(default=None, description="List of quarter numbers (1-4)")


class SubjectStatsOutput(BaseModel):
    """Statistics for a single subject."""

    mean: float = Field(..., description="Average score")
    min: int = Field(..., description="Minimum score")
    max: int = Field(..., description="Maximum score")
    std: float = Field(default=0.0, description="Standard deviation")


class ListAvailableDataOutput(ToolOutput):
    """Output for list_available_data tool."""

    file_count: int = Field(..., description="Number of files found")
    file_categories: list[str] = Field(default_factory=list, description="Categories of data")
    files: list[str] = Field(default_factory=list, description="List of file names")


class GetStudentsOutput(ToolOutput):
    """Output for get_students tool."""

    student_count: int = Field(..., description="Number of students")
    student_ids: list[str] = Field(default_factory=list, description="List of student UUIDs")


class GetTestScoresOutput(ToolOutput):
    """Output for get_test_scores tool."""

    quarter: int = Field(..., description="Quarter number")
    student_count: int = Field(..., description="Number of students")
    subjects: list[str] = Field(default_factory=list, description="Subject names")
    subject_stats: dict[str, SubjectStatsOutput] = Field(default_factory=dict, description="Statistics per subject")
    overall_average: float = Field(default=0.0, description="Overall average score")
    scores: list[dict[str, Any]] = Field(default_factory=list, description="Raw score data")


class GetGradeReportOutput(ToolOutput):
    """Output for get_grade_report tool."""

    quarter: int = Field(..., description="Quarter number")
    student_count: int = Field(..., description="Number of students")
    grade_distribution: dict[str, int] = Field(default_factory=dict, description="Count per grade letter")
    reports: list[dict[str, Any]] = Field(default_factory=list, description="Raw report data")


class GetCurriculumOutput(ToolOutput):
    """Output for get_curriculum tool."""

    quarter: int = Field(..., description="Quarter number")
    subjects: list[str] = Field(default_factory=list, description="Subject names")
    average_completion: float = Field(default=0.0, description="Average completion rate")
    curriculum_data: dict[str, Any] = Field(default_factory=dict, description="Full curriculum data")


class StudentTrendOutput(BaseModel):
    """Trend data for a student's subject."""

    subject: str = Field(..., description="Subject name")
    first_quarter_score: int = Field(..., description="Score in first quarter")
    last_quarter_score: int = Field(..., description="Score in last quarter")
    change: int = Field(..., description="Change from first to last quarter")


class AnalyzeStudentPerformanceOutput(ToolOutput):
    """Output for analyze_student_performance tool."""

    student_id: str = Field(..., description="Student UUID")
    quarters_analyzed: list[int] = Field(default_factory=list, description="Quarters analyzed")
    overall_average: float = Field(..., description="Overall average score")
    subject_averages: dict[str, float] = Field(default_factory=dict, description="Average per subject")
    strongest_subject: str = Field(..., description="Subject with highest average")
    weakest_subject: str = Field(..., description="Subject with lowest average")
    trends: dict[str, int] = Field(default_factory=dict, description="Score change per subject")
    quarterly_scores: list[dict[str, Any]] = Field(default_factory=list, description="Scores by quarter")
    quarterly_grades: list[dict[str, Any]] = Field(default_factory=list, description="Grades by quarter")
    teacher_advice: list[dict[str, Any]] = Field(default_factory=list, description="Teacher advice by quarter")


class AnalyzeClassPerformanceOutput(ToolOutput):
    """Output for analyze_class_performance tool."""

    class_name: str = Field(..., description="Class name analyzed")
    quarters_analyzed: list[int] = Field(default_factory=list, description="Quarters analyzed")
    class_average: float = Field(..., description="Class average score")
    top_performer_id: str = Field(..., description="UUID of top performer")
    top_performer_avg: float = Field(..., description="Top performer's average")
    curriculum_completion_avg: float = Field(..., description="Average curriculum completion")
    student_averages: list[dict[str, Any]] = Field(default_factory=list, description="Averages per student")
    quarterly_averages: list[dict[str, Any]] = Field(default_factory=list, description="Averages per quarter")


class GetResultDetailsOutput(ToolOutput):
    """Output for get_result_details tool."""

    original_result_id: str = Field(..., description="The queried result ID")
    data_type: str = Field(..., description="Type of data retrieved")
    detailed_data: Any = Field(default=None, description="The full detailed data")


class CompareStudentsOutput(ToolOutput):
    """Output for compare_students tool."""

    student1_id: str = Field(..., description="First student UUID")
    student2_id: str = Field(..., description="Second student UUID")
    comparison: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Subject-by-subject comparison")
    overall_averages: dict[str, float] = Field(default_factory=dict, description="Overall averages for both students")
    student1_scores: list[dict[str, Any]] = Field(default_factory=list, description="First student's scores")
    student2_scores: list[dict[str, Any]] = Field(default_factory=list, description="Second student's scores")


class FilterScoresOutput(ToolOutput):
    """Output for filter_scores tool."""

    record_count: int = Field(..., description="Number of records matching filter")
    unique_students: int = Field(..., description="Number of unique students")
    unique_quarters: int = Field(..., description="Number of unique quarters")
    overall_average: float = Field(..., description="Overall average of filtered scores")
    filters_applied: dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")
    subject_stats: dict[str, SubjectStatsOutput] = Field(default_factory=dict, description="Statistics per subject")
    scores: list[dict[str, Any]] = Field(default_factory=list, description="Filtered score data")


class FilterGradesOutput(ToolOutput):
    """Output for filter_grades tool."""

    record_count: int = Field(..., description="Number of records matching filter")
    unique_students: int = Field(..., description="Number of unique students")
    unique_quarters: int = Field(..., description="Number of unique quarters")
    filters_applied: dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")
    overall_distribution: dict[str, int] = Field(default_factory=dict, description="Overall grade distribution")
    class_distribution: dict[str, dict[str, int]] = Field(
        default_factory=dict, description="Grade distribution per class"
    )
    grades: list[dict[str, Any]] = Field(default_factory=list, description="Filtered grade data")
    teacher_advice: list[dict[str, Any]] = Field(default_factory=list, description="Teacher advice data")


class FilterCurriculumOutput(ToolOutput):
    """Output for filter_curriculum tool."""

    record_count: int = Field(..., description="Number of records matching filter")
    average_completion: float = Field(..., description="Average completion rate")
    filters_applied: dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")
    class_completion: dict[str, float] = Field(default_factory=dict, description="Completion rate per class")
    curriculum: list[dict[str, Any]] = Field(default_factory=list, description="Filtered curriculum data")


INPUT_MODELS: dict[str, type[ToolInput]] = {
    "list_available_data": ListAvailableDataInput,
    "get_students": GetStudentsInput,
    "get_test_scores": GetTestScoresInput,
    "get_grade_report": GetGradeReportInput,
    "get_curriculum": GetCurriculumInput,
    "analyze_student_performance": AnalyzeStudentPerformanceInput,
    "analyze_class_performance": AnalyzeClassPerformanceInput,
    "get_result_details": GetResultDetailsInput,
    "compare_students": CompareStudentsInput,
    "filter_scores": FilterScoresInput,
    "filter_grades": FilterGradesInput,
    "filter_curriculum": FilterCurriculumInput,
}

OUTPUT_MODELS: dict[str, type[ToolOutput]] = {
    "list_available_data": ListAvailableDataOutput,
    "get_students": GetStudentsOutput,
    "get_test_scores": GetTestScoresOutput,
    "get_grade_report": GetGradeReportOutput,
    "get_curriculum": GetCurriculumOutput,
    "analyze_student_performance": AnalyzeStudentPerformanceOutput,
    "analyze_class_performance": AnalyzeClassPerformanceOutput,
    "get_result_details": GetResultDetailsOutput,
    "compare_students": CompareStudentsOutput,
    "filter_scores": FilterScoresOutput,
    "filter_grades": FilterGradesOutput,
    "filter_curriculum": FilterCurriculumOutput,
}

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolResultStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class ToolResult(BaseModel):
    """Base model for tool call results following the ID reference pattern."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    tool_name: str = Field(..., description="Name of the tool that was called")
    result_id: str = Field(..., description="Unique ID to reference the full result data")
    result_summary: str = Field(..., description="Human-readable summary of the result")
    status: ToolResultStatus = Field(default=ToolResultStatus.SUCCESS, description="Status of the tool execution")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of the result creation")

    def to_llm_response(self) -> dict:
        """Convert to a minimal response for LLM context."""
        return {
            "tool_name": self.tool_name,
            "result_id": self.result_id,
            "result_summary": self.result_summary,
            "status": self.status.value,
        }


class DataListResult(ToolResult):
    """Result for listing available data files."""

    file_count: int = Field(..., description="Number of files found")
    file_categories: list[str] = Field(default_factory=list, description="Categories of data available")


class StudentListResult(ToolResult):
    """Result for student list query."""

    student_count: int = Field(..., description="Number of students")
    student_ids: list[str] = Field(default_factory=list, description="List of student IDs")


class TestScoreResult(ToolResult):
    """Result for test score queries."""

    quarter: int = Field(..., description="Quarter number (1-4)")
    student_count: int = Field(..., description="Number of students with scores")
    subjects: list[str] = Field(default_factory=list, description="Subjects included")


class GradeReportResult(ToolResult):
    """Result for grade report queries."""

    quarter: int = Field(..., description="Quarter number (1-4)")
    student_count: int = Field(..., description="Number of students in report")


class CurriculumResult(ToolResult):
    """Result for curriculum queries."""

    quarter: int = Field(..., description="Quarter number (1-4)")
    subjects: list[str] = Field(default_factory=list, description="Subjects included")


class StudentAnalysisResult(ToolResult):
    """Result for comprehensive student performance analysis."""

    student_id: str = Field(..., description="Student ID analyzed")
    quarters_analyzed: list[int] = Field(default_factory=list, description="Quarters included in analysis")
    overall_average: float = Field(..., description="Overall average score across all subjects and quarters")
    strongest_subject: str = Field(..., description="Subject with highest average")
    weakest_subject: str = Field(..., description="Subject with lowest average")


class ClassAnalysisResult(ToolResult):
    """Result for class-wide performance analysis."""

    class_name: str = Field(..., description="Name of the class analyzed")
    quarters_analyzed: list[int] = Field(default_factory=list, description="Quarters included in analysis")
    class_average: float = Field(..., description="Class average score")
    top_performer_id: str = Field(..., description="Student ID of top performer")
    curriculum_completion_avg: float = Field(..., description="Average curriculum completion rate")


class DetailedDataResult(ToolResult):
    """Result for retrieving detailed data by result ID."""

    original_result_id: str = Field(..., description="The result ID that was queried")
    data_type: str = Field(..., description="Type of data retrieved")


class ResultStorage(BaseModel):
    """Storage for tool results with ID reference pattern."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    results: dict[str, Any] = Field(default_factory=dict, description="Stored results by ID")
    metadata: dict[str, ToolResult] = Field(default_factory=dict, description="Metadata for each result")

    def store(self, result_id: str, data: Any, metadata: ToolResult) -> None:
        """Store data with its metadata."""
        self.results[result_id] = data
        self.metadata[result_id] = metadata

    def get(self, result_id: str) -> tuple[Any, ToolResult] | None:
        """Retrieve data and metadata by result ID."""
        if result_id in self.results:
            return self.results[result_id], self.metadata[result_id]
        return None

    def exists(self, result_id: str) -> bool:
        """Check if a result ID exists."""
        return result_id in self.results

    def list_ids(self) -> list[str]:
        """List all stored result IDs."""
        return list(self.results.keys())

    def clear(self) -> None:
        """Clear all stored results."""
        self.results.clear()
        self.metadata.clear()

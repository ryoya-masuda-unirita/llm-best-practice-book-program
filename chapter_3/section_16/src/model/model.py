from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class SampledSentences(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    sentences: list[str] = Field(..., description="List of representative sentences sampled from the document.")
    document_type: str = Field(..., description="Identified type of the document (e.g., contract, report, manual).")
    key_sections: list[str] = Field(..., description="Identified key section names or headers in the document.")


class GeneratedScript(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    script: str = Field(..., description="The generated Python script code.")
    explanation: str = Field(..., description="Brief explanation of what the script does.")


class DocumentSection(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    title: str = Field(..., description="Title or heading of the section.")
    level: int = Field(..., description="Heading level (1 for top-level, 2 for subsection, etc.).")
    content: str = Field(default="", description="Content of the section.")
    subsections: list["DocumentSection"] = Field(default_factory=list, description="Nested subsections.")


class DocumentStructure(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    title: str = Field(..., description="Title of the document.")
    document_type: str = Field(..., description="Type of the document.")
    sections: list[DocumentSection] = Field(default_factory=list, description="List of top-level sections.")
    metadata: dict = Field(default_factory=dict, description="Additional metadata extracted.")

    def save_as_json(self, file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)


class ScriptExecutionResult(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    success: bool = Field(..., description="Whether the script executed successfully.")
    output: str = Field(default="", description="Standard output from the script.")
    error: str = Field(default="", description="Error message if execution failed.")
    result: dict | None = Field(default=None, description="Parsed JSON result if available.")


class ValidationResult(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    reasoning: str = Field(..., description="Detailed reasoning for the score.")
    score: int = Field(..., description="Validation score from 1 to 5.", ge=1, le=5)
    fix_proposal: str | None = Field(
        default=None,
        description="Proposal to fix issues if score is below 3.",
    )


@dataclass
class ExtractionResult:
    success: bool
    document_structure: DocumentStructure | None
    raw_result: dict | None
    final_script: str
    sampled_info: SampledSentences
    script_explanation: str
    error: str | None = None
    validation_result: ValidationResult | None = None

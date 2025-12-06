"""
Pydantic models for the Contract Risk Compliance Pipeline.

This module defines all data models used across the pipeline AI agent system
for contract risk evaluation.

Pipeline Stages:
    1. Input Stage: Read contract document
    2. Extraction Stage: Extract content by chapter and section
    3. Risk Scoring Stage: Evaluate risk for each section
    4. Report Generation Stage: Generate comprehensive compliance report
"""

from enum import StrEnum
from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

# =============================================================================
# Base Model Configuration
# =============================================================================


class FrozenModel(BaseModel):
    """
    Base model with common configuration for all contract pipeline models.

    Configuration:
    - validate_assignment: Validates data on attribute assignment
    - frozen: Makes instances immutable after creation
    - extra: Ignores extra fields not defined in the model
    """

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )


# =============================================================================
# Enums for Contract Risk Compliance Pipeline
# =============================================================================


class RiskLevel(StrEnum):
    """Risk level classification for contract clauses."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(StrEnum):
    """Categories of contract risks."""

    INTELLECTUAL_PROPERTY = "intellectual_property"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    PAYMENT = "payment"
    COMPLIANCE = "compliance"
    WARRANTY = "warranty"
    INDEMNIFICATION = "indemnification"
    DISPUTE_RESOLUTION = "dispute_resolution"
    OTHER = "other"


class ComplianceStatus(StrEnum):
    """Overall compliance status of a contract."""

    COMPLIANT = "compliant"
    NEEDS_REVIEW = "needs_review"
    NON_COMPLIANT = "non_compliant"


# =============================================================================
# Input Stage Models
# =============================================================================


class ContractInput(FrozenModel):
    """Input contract document information."""

    contract_id: str = Field(..., description="Unique identifier for the contract")
    file_path: str = Field(..., description="Path to the contract document")
    raw_content: str = Field(..., description="Raw text content of the contract")


# =============================================================================
# Extraction Stage Models
# =============================================================================


class ContractSection(FrozenModel):
    """A section within a chapter of the contract."""

    section_id: str = Field(..., description="Unique identifier for the section")
    section_number: str = Field(..., description="Section number (e.g., '第1条')")
    title: str = Field(..., description="Title of the section")
    content: str = Field(..., description="Full text content of the section")
    chapter_id: str = Field(..., description="Parent chapter identifier")


class ContractChapter(FrozenModel):
    """A chapter in the contract document."""

    chapter_id: str = Field(..., description="Unique identifier for the chapter")
    chapter_number: str = Field(..., description="Chapter number (e.g., '第1章')")
    title: str = Field(..., description="Title of the chapter")
    sections: list[ContractSection] = Field(default_factory=list, description="Sections within this chapter")


class ContractStructure(FrozenModel):
    """Extracted structure of the contract document."""

    contract_id: str = Field(..., description="Unique identifier for the contract")
    title: str = Field(..., description="Title of the contract")
    parties: list[str] = Field(..., description="Parties involved in the contract")
    effective_date: str = Field(default="", description="Effective date of the contract")
    chapters: list[ContractChapter] = Field(..., description="Chapters in the contract")
    total_sections: int = Field(..., description="Total number of sections extracted")


class ExtractionOutput(FrozenModel):
    """Output from the Extraction Stage."""

    structure: ContractStructure = Field(..., description="Extracted contract structure")
    extraction_notes: str = Field(default="", description="Notes about the extraction process")


# =============================================================================
# Risk Scoring Stage Models
# =============================================================================


class RiskFinding(FrozenModel):
    """A specific risk finding within a section."""

    finding_id: str = Field(..., description="Unique identifier for the finding")
    description: str = Field(..., description="Description of the risk")
    risk_level: RiskLevel = Field(..., description="Severity level of the risk")
    risk_category: RiskCategory = Field(..., description="Category of the risk")
    affected_clause: str = Field(..., description="The specific clause text affected")
    recommendation: str = Field(..., description="Recommendation to mitigate the risk")


class SectionRiskAssessment(FrozenModel):
    """Risk assessment for a specific section."""

    section_id: str = Field(..., description="Identifier of the assessed section")
    section_title: str = Field(..., description="Title of the section")
    overall_risk_level: RiskLevel = Field(..., description="Overall risk level for this section")
    findings: list[RiskFinding] = Field(default_factory=list, description="List of risk findings in this section")
    is_compliant: bool = Field(..., description="Whether the section is compliant")
    notes: str = Field(default="", description="Additional notes about the assessment")


class RiskScoringOutput(FrozenModel):
    """Output from the Risk Scoring Stage."""

    contract_id: str = Field(..., description="Contract identifier")
    assessed_sections: list[SectionRiskAssessment] = Field(..., description="Risk assessments for each section")
    high_risk_count: int = Field(..., description="Number of high/critical risk findings")
    total_findings: int = Field(..., description="Total number of risk findings")


# =============================================================================
# Report Generation Stage Models
# =============================================================================


class ExecutiveSummary(FrozenModel):
    """Executive summary of the contract risk assessment."""

    overall_status: ComplianceStatus = Field(..., description="Overall compliance status")
    overall_risk_score: int = Field(..., description="Overall risk score (0-100, higher is riskier)")
    key_concerns: list[str] = Field(..., description="Key concerns identified")
    immediate_actions: list[str] = Field(..., description="Immediate actions recommended")
    summary_text: str = Field(..., description="Brief summary text")


class RiskBreakdown(FrozenModel):
    """Breakdown of risks by category."""

    category: RiskCategory = Field(..., description="Risk category")
    count: int = Field(..., description="Number of findings in this category")
    severity_distribution: dict[str, int] = Field(..., description="Distribution by severity level")
    key_issues: list[str] = Field(..., description="Key issues in this category")


class ComplianceReport(FrozenModel):
    """Complete compliance report for a contract."""

    report_id: str = Field(..., description="Unique identifier for the report")
    contract_id: str = Field(..., description="Contract identifier")
    contract_title: str = Field(..., description="Title of the contract")
    generated_at: str = Field(..., description="Timestamp when report was generated")
    executive_summary: ExecutiveSummary = Field(..., description="Executive summary")
    risk_breakdown: list[RiskBreakdown] = Field(..., description="Risk breakdown by category")
    section_assessments: list[SectionRiskAssessment] = Field(..., description="Detailed section assessments")
    recommendations: list[str] = Field(..., description="Overall recommendations for the contract")
    conclusion: str = Field(..., description="Conclusion and next steps")

    def to_markdown(self) -> str:
        """Convert the compliance report to markdown format."""
        lines = [
            "# 契約書リスクコンプライアンスレポート",
            "",
            f"**契約書**: {self.contract_title}",
            f"**レポートID**: {self.report_id}",
            f"**生成日時**: {self.generated_at}",
            "",
            "---",
            "",
            "## エグゼクティブサマリー",
            "",
            "### 総合評価",
            f"- **コンプライアンス状態**: {self._status_to_japanese(self.executive_summary.overall_status)}",
            f"- **リスクスコア**: {self.executive_summary.overall_risk_score}/100",
            "",
            f"{self.executive_summary.summary_text}",
            "",
        ]

        if self.executive_summary.key_concerns:
            lines.extend(
                [
                    "### 主要な懸念事項",
                ]
            )
            for concern in self.executive_summary.key_concerns:
                lines.append(f"- {concern}")
            lines.append("")

        if self.executive_summary.immediate_actions:
            lines.extend(
                [
                    "### 即時対応が必要な事項",
                ]
            )
            for action in self.executive_summary.immediate_actions:
                lines.append(f"- ⚠️ {action}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## リスク分析",
                "",
            ]
        )

        for breakdown in self.risk_breakdown:
            if breakdown.count > 0:
                lines.extend(
                    [
                        f"### {self._category_to_japanese(breakdown.category)}",
                        f"- **検出件数**: {breakdown.count}件",
                    ]
                )
                if breakdown.key_issues:
                    lines.append("- **主な問題点**:")
                    for issue in breakdown.key_issues:
                        lines.append(f"  - {issue}")
                lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## セクション別評価詳細",
                "",
            ]
        )

        for assessment in self.section_assessments:
            status_icon = "✅" if assessment.is_compliant else "⚠️"
            lines.extend(
                [
                    f"### {status_icon} {assessment.section_title}",
                    f"- **リスクレベル**: {self._risk_level_to_japanese(assessment.overall_risk_level)}",
                    f"- **コンプライアンス**: {'適合' if assessment.is_compliant else '要確認'}",
                ]
            )

            if assessment.findings:
                lines.append("")
                lines.append("**検出されたリスク:**")
                for finding in assessment.findings:
                    lines.extend(
                        [
                            "",
                            f"- **{finding.description}**",
                            f"  - カテゴリ: {self._category_to_japanese(finding.risk_category)}",
                            f"  - レベル: {self._risk_level_to_japanese(finding.risk_level)}",
                            f"  - 推奨対応: {finding.recommendation}",
                        ]
                    )

            if assessment.notes:
                lines.extend(
                    [
                        "",
                        f"**備考**: {assessment.notes}",
                    ]
                )
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## 総合的な推奨事項",
                "",
            ]
        )
        for i, rec in enumerate(self.recommendations, 1):
            lines.append(f"{i}. {rec}")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 結論",
                "",
                self.conclusion,
                "",
            ]
        )

        return "\n".join(lines)

    def _status_to_japanese(self, status: ComplianceStatus) -> str:
        """Convert compliance status to Japanese."""
        mapping = {
            ComplianceStatus.COMPLIANT: "✅ 適合",
            ComplianceStatus.NEEDS_REVIEW: "⚠️ 要確認",
            ComplianceStatus.NON_COMPLIANT: "❌ 不適合",
        }
        return mapping.get(status, str(status))

    def _risk_level_to_japanese(self, level: RiskLevel) -> str:
        """Convert risk level to Japanese."""
        mapping = {
            RiskLevel.LOW: "🟢 低",
            RiskLevel.MEDIUM: "🟡 中",
            RiskLevel.HIGH: "🟠 高",
            RiskLevel.CRITICAL: "🔴 重大",
        }
        return mapping.get(level, str(level))

    def _category_to_japanese(self, category: RiskCategory) -> str:
        """Convert risk category to Japanese."""
        mapping = {
            RiskCategory.INTELLECTUAL_PROPERTY: "知的財産権",
            RiskCategory.LIABILITY: "責任・賠償",
            RiskCategory.CONFIDENTIALITY: "秘密保持",
            RiskCategory.TERMINATION: "契約解除",
            RiskCategory.PAYMENT: "支払条件",
            RiskCategory.COMPLIANCE: "法令遵守",
            RiskCategory.WARRANTY: "保証",
            RiskCategory.INDEMNIFICATION: "補償",
            RiskCategory.DISPUTE_RESOLUTION: "紛争解決",
            RiskCategory.OTHER: "その他",
        }
        return mapping.get(category, str(category))


# =============================================================================
# Pipeline State Model
# =============================================================================


class ContractPipelineState(TypedDict):
    """State for the contract risk compliance pipeline."""

    # Input
    contract_input: ContractInput

    # Extraction stage output
    extraction_output: ExtractionOutput | None

    # Risk scoring stage output
    risk_scoring_output: RiskScoringOutput | None

    # Report generation stage output
    compliance_report: ComplianceReport | None

    # Current pipeline stage
    current_stage: str

    # Sections pending risk assessment
    pending_sections: list[ContractSection]
    current_section_index: int

    # Messages for agent communication
    messages: Annotated[Sequence[BaseMessage], add_messages]

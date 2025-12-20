import operator
from typing import Annotated, Literal, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class ContractClause(BaseModel):
    """Represents a single clause from a contract."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )

    clause_number: str = Field(..., description="Clause number (e.g., '第1条')")
    title: str = Field(..., description="Title of the clause")
    content: str = Field(..., description="Full text content of the clause")


class ClauseCategory(BaseModel):
    """Category classification for a clause."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )

    clause_number: str = Field(..., description="Clause number")
    category: str = Field(
        ...,
        description="Category type: 守秘義務, 責任制限, 準拠法, 損害賠償, 再委託, 知的財産, 契約解除, その他",
    )
    reason: str = Field(..., description="Reason for classification")


class RiskAssessment(BaseModel):
    """Risk assessment for a clause."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )

    clause_number: str = Field(..., description="Clause number")
    risk_level: str = Field(..., description="Risk level: 高, 中, 低")
    risk_score: int = Field(..., ge=1, le=10, description="Risk score from 1 to 10")
    risk_factors: list[str] = Field(..., description="List of risk factors identified")
    explanation: str = Field(..., description="Detailed explanation of risk assessment")


class ClauseDiff(BaseModel):
    """Difference between contract clause and standard template."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )

    clause_number: str = Field(..., description="Clause number")
    diff_type: str = Field(..., description="Type of difference: 追加, 削除, 修正, 一致")
    original_text: str = Field(..., description="Text from the contract being reviewed")
    standard_text: str = Field(..., description="Text from the standard template")
    summary: str = Field(..., description="Summary of the difference")


class AmendmentProposal(BaseModel):
    """Proposed amendment for a high-risk clause."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
    )

    clause_number: str = Field(..., description="Clause number")
    original_text: str = Field(..., description="Original problematic text")
    proposed_text: str = Field(..., description="Proposed amended text")
    rationale: str = Field(..., description="Rationale for the proposed change")
    negotiation_points: list[str] = Field(..., description="Key negotiation points to discuss with counterparty")


class DocumentParserResponse(BaseModel):
    """Response model for document parser agent."""

    model_config = ConfigDict(extra="ignore")

    clauses: list[ContractClause] = Field(..., description="List of parsed contract clauses")


class ClauseClassifierResponse(BaseModel):
    """Response model for clause classifier agent."""

    model_config = ConfigDict(extra="ignore")

    categories: list[ClauseCategory] = Field(..., description="List of clause category classifications")


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment agent."""

    model_config = ConfigDict(extra="ignore")

    risk_assessments: list[RiskAssessment] = Field(..., description="List of risk assessments for each clause")


class DiffCheckerResponse(BaseModel):
    """Response model for diff checker agent."""

    model_config = ConfigDict(extra="ignore")

    diffs: list[ClauseDiff] = Field(..., description="List of differences between contract and template")


class AmendmentProposerResponse(BaseModel):
    """Response model for amendment proposer agent."""

    model_config = ConfigDict(extra="ignore")

    amendments: list[AmendmentProposal] = Field(..., description="List of proposed amendments for high-risk clauses")


class ReportGeneratorResponse(BaseModel):
    """Response model for report generator agent."""

    model_config = ConfigDict(extra="ignore")

    overall_risk_level: str = Field(..., description="Overall risk level: 高, 中, 低")
    overall_risk_score: float = Field(..., ge=1.0, le=10.0, description="Overall risk score from 1.0 to 10.0")
    executive_summary: str = Field(..., description="Executive summary for non-legal stakeholders")
    key_issues: list[str] = Field(..., description="List of key issues identified")
    recommended_actions: list[str] = Field(..., description="List of recommended actions")


# =============================================================================
# Orchestrator Models
# =============================================================================

WorkerType = Literal[
    "document_parser",
    "clause_classifier",
    "risk_assessment",
    "diff_checker",
    "amendment_proposer",
    "report_generator",
]


class TaskAssignment(BaseModel):
    """Task assignment from orchestrator to worker."""

    model_config = ConfigDict(extra="ignore")

    worker: WorkerType = Field(..., description="Worker agent to assign the task to")
    task_description: str = Field(..., description="Description of the task for the worker")
    priority: int = Field(default=1, ge=1, le=10, description="Task priority (1=highest)")
    depends_on: list[WorkerType] = Field(
        default_factory=list,
        description="List of workers that must complete before this task",
    )


class OrchestratorPlan(BaseModel):
    """Orchestrator's plan for contract review."""

    model_config = ConfigDict(extra="ignore")

    tasks: list[TaskAssignment] = Field(..., description="List of task assignments")
    strategy: str = Field(..., description="Overall strategy for the review")
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Specific areas to focus on during review",
    )


class OrchestratorResponse(BaseModel):
    """Response model for orchestrator agent."""

    model_config = ConfigDict(extra="ignore")

    plan: OrchestratorPlan = Field(..., description="The review plan")
    reasoning: str = Field(..., description="Reasoning behind the plan")


class ContractReviewReport(BaseModel):
    """Final contract review report."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        extra="ignore",
    )

    overall_risk_level: str = Field(..., description="Overall risk level: 高, 中, 低")
    overall_risk_score: float = Field(..., ge=1.0, le=10.0, description="Overall risk score from 1.0 to 10.0")
    executive_summary: str = Field(..., description="Executive summary for non-legal stakeholders")
    key_issues: list[str] = Field(..., description="List of key issues identified")
    recommended_actions: list[str] = Field(..., description="List of recommended actions")
    clauses: list[ContractClause] = Field(default_factory=list)
    categories: list[ClauseCategory] = Field(default_factory=list)
    risk_assessments: list[RiskAssessment] = Field(default_factory=list)
    diffs: list[ClauseDiff] = Field(default_factory=list)
    amendments: list[AmendmentProposal] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert the report to markdown format."""
        md_parts = []

        md_parts.append("# 契約書レビューレポート\n")

        md_parts.append("## エグゼクティブサマリー\n")
        md_parts.append(f"**総合リスクレベル**: {self.overall_risk_level}\n")
        md_parts.append(f"**総合リスクスコア**: {self.overall_risk_score:.1f} / 10.0\n")
        md_parts.append(f"\n{self.executive_summary}\n")

        md_parts.append("\n## 主要な論点\n")
        for i, issue in enumerate(self.key_issues, 1):
            md_parts.append(f"{i}. {issue}\n")

        md_parts.append("\n## 推奨アクション\n")
        for i, action in enumerate(self.recommended_actions, 1):
            md_parts.append(f"{i}. {action}\n")

        if self.risk_assessments:
            md_parts.append("\n## リスク評価詳細\n")
            high_risk = [r for r in self.risk_assessments if r.risk_level == "高"]
            if high_risk:
                md_parts.append("\n### 高リスク条項\n")
                for risk in high_risk:
                    md_parts.append(f"\n#### {risk.clause_number}\n")
                    md_parts.append(f"- **リスクスコア**: {risk.risk_score}/10\n")
                    md_parts.append("- **リスク要因**:\n")
                    for factor in risk.risk_factors:
                        md_parts.append(f"  - {factor}\n")
                    md_parts.append(f"- **詳細説明**: {risk.explanation}\n")

        if self.diffs:
            significant_diffs = [d for d in self.diffs if d.diff_type != "一致"]
            if significant_diffs:
                md_parts.append("\n## 標準契約との差分\n")
                for diff in significant_diffs:
                    md_parts.append(f"\n### {diff.clause_number} ({diff.diff_type})\n")
                    md_parts.append(f"**概要**: {diff.summary}\n")
                    if diff.original_text:
                        md_parts.append(f"\n**レビュー対象契約**:\n> {diff.original_text[:200]}...\n")
                    if diff.standard_text:
                        md_parts.append(f"\n**自社標準**:\n> {diff.standard_text[:200]}...\n")

        if self.amendments:
            md_parts.append("\n## 修正提案\n")
            for amend in self.amendments:
                md_parts.append(f"\n### {amend.clause_number}\n")
                md_parts.append(f"**現行文言**:\n> {amend.original_text}\n")
                md_parts.append(f"\n**修正案**:\n> {amend.proposed_text}\n")
                md_parts.append(f"\n**修正理由**: {amend.rationale}\n")
                if amend.negotiation_points:
                    md_parts.append("\n**交渉ポイント**:\n")
                    for point in amend.negotiation_points:
                        md_parts.append(f"- {point}\n")

        return "".join(md_parts)


def reduce_list(left: list | None, right: list | None) -> list:
    """Reducer for concurrent list updates. Prefers non-empty right (newer) value."""
    if left is None:
        left = []
    if right is None:
        right = []
    if right:
        return right
    return left


class AgentState(TypedDict):
    """State for the multi-agent contract review system."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    contract_text: str
    standard_template: str
    parsed_clauses: Annotated[list[dict], reduce_list]
    clause_categories: Annotated[list[dict], reduce_list]
    risk_assessments: Annotated[list[dict], reduce_list]
    diffs: Annotated[list[dict], reduce_list]
    amendments: Annotated[list[dict], reduce_list]
    final_report: str | None
    orchestrator_plan: OrchestratorPlan | None
    completed_tasks: Annotated[list[str], operator.add]
    current_phase: str


class WorkerState(TypedDict):
    """State for individual worker agents in orchestrator pattern."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    contract_text: str
    standard_template: str
    parsed_clauses: list[dict]
    clause_categories: list[dict]
    risk_assessments: list[dict]
    diffs: list[dict]
    amendments: list[dict]
    worker_type: str
    task_description: str
    completed_tasks: Annotated[list[str], operator.add]

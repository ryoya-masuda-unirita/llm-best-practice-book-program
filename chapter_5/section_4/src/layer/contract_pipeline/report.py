"""
Report Generation Stage Module.

The Report Generation Stage is the final stage in the contract risk compliance pipeline,
responsible for:
- Aggregating risk assessments from all sections
- Generating executive summary
- Creating comprehensive compliance report
"""

from datetime import datetime
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.model import (
    ComplianceReport,
    ContractPipelineState,
    ExecutiveSummary,
    ReportResponse,
    RiskBreakdown,
)
from src.prompt.prompt import (
    make_report_system_prompt,
    make_report_user_prompt,
)


class ReportAgent(BaseAgent):
    """
    Report Generation Stage Agent (レポート生成ステージエージェント).

    Aggregates all risk assessments and generates a comprehensive
    compliance report with executive summary and recommendations.
    """

    def __init__(self):
        super().__init__(layer_name="PIPELINE", agent_name="ReportAgent")

    def _format_section_assessments(self, state: ContractPipelineState) -> str:
        """Format section assessments for the prompt."""
        risk_output = state["risk_scoring_output"]
        if risk_output is None:
            return "評価結果なし"

        lines = []
        for assessment in risk_output.assessed_sections:
            lines.append(f"\n### {assessment.section_title}")
            lines.append(f"- リスクレベル: {assessment.overall_risk_level}")
            lines.append(f"- コンプライアンス: {'適合' if assessment.is_compliant else '要確認'}")
            lines.append(f"- 発見件数: {len(assessment.findings)}件")

            if assessment.findings:
                lines.append("- 主な発見事項:")
                for finding in assessment.findings[:3]:
                    lines.append(f"  - [{finding.risk_level}] {finding.description}")

        return "\n".join(lines)

    def _convert_response_to_report(self, response: ReportResponse, state: ContractPipelineState) -> ComplianceReport:
        """Convert LLM response to domain report model."""
        extraction = state["extraction_output"]
        risk_output = state["risk_scoring_output"]

        if extraction is None or risk_output is None:
            raise ValueError("Report requires extraction and risk scoring outputs")

        executive_summary = ExecutiveSummary(
            overall_status=response.executive_summary.overall_status,
            overall_risk_score=min(100, max(0, response.executive_summary.overall_risk_score)),
            key_concerns=response.executive_summary.key_concerns,
            immediate_actions=response.executive_summary.immediate_actions,
            summary_text=response.executive_summary.summary_text,
        )

        risk_breakdown = [
            RiskBreakdown(
                category=rb.category,
                count=rb.count,
                severity_distribution=rb.severity_distribution.model_dump(),
                key_issues=rb.key_issues,
            )
            for rb in response.risk_breakdown
        ]

        return ComplianceReport(
            report_id=f"report_{uuid4().hex[:8]}",
            contract_id=extraction.structure.contract_id,
            contract_title=extraction.structure.title,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            executive_summary=executive_summary,
            risk_breakdown=risk_breakdown,
            section_assessments=risk_output.assessed_sections,
            recommendations=response.recommendations,
            conclusion=response.conclusion,
        )

    def execute(self, state: ContractPipelineState, config: RunnableConfig) -> dict:
        """Execute the report generation stage."""
        self._log_layer_start("Report Generation")

        extraction = state["extraction_output"]
        risk_output = state["risk_scoring_output"]

        if extraction is None or risk_output is None:
            raise ValueError("Report generation requires extraction and risk outputs")

        structure = extraction.structure
        self.logger.info(f"Generating report for: {structure.title}")

        user_prompt = make_report_user_prompt(
            contract_title=structure.title,
            parties=structure.parties,
            total_sections=structure.total_sections,
            high_risk_count=risk_output.high_risk_count,
            total_findings=risk_output.total_findings,
            section_assessments=self._format_section_assessments(state),
        )

        response = self._invoke_structured(
            config,
            make_report_system_prompt(),
            user_prompt,
            ReportResponse,
        )

        report = self._convert_response_to_report(response, state)
        self.logger.info(f"Report generated: {report.report_id} - Status: {report.executive_summary.overall_status}")

        return {
            "compliance_report": report,
            "current_stage": "complete",
        }


def report_stage_node(state: ContractPipelineState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Report Generation Stage."""
    return ReportAgent().execute(state, config)

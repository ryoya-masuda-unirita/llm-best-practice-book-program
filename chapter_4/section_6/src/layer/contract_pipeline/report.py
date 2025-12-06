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
from src.model.contract_pipeline_model import (
    ComplianceReport,
    ComplianceStatus,
    ContractPipelineState,
    ExecutiveSummary,
    RiskBreakdown,
    RiskCategory,
)
from src.prompt.contract_pipeline_prompt import (
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
                for finding in assessment.findings[:3]:  # Limit to first 3
                    lines.append(f"  - [{finding.risk_level}] {finding.description}")

        return "\n".join(lines)

    def _parse_executive_summary(self, data: dict) -> ExecutiveSummary:
        """Parse executive summary from JSON data."""
        return ExecutiveSummary(
            overall_status=self._safe_enum_parse(
                ComplianceStatus,
                data.get("overall_status", "needs_review"),
                ComplianceStatus.NEEDS_REVIEW,
            ),
            overall_risk_score=min(100, max(0, data.get("overall_risk_score", 50))),
            key_concerns=data.get("key_concerns", []),
            immediate_actions=data.get("immediate_actions", []),
            summary_text=data.get("summary_text", ""),
        )

    def _parse_risk_breakdown(self, data: dict) -> RiskBreakdown:
        """Parse risk breakdown from JSON data."""
        severity_dist = data.get("severity_distribution", {})
        return RiskBreakdown(
            category=self._safe_enum_parse(RiskCategory, data.get("category", "other"), RiskCategory.OTHER),
            count=data.get("count", 0),
            severity_distribution={
                "low": severity_dist.get("low", 0),
                "medium": severity_dist.get("medium", 0),
                "high": severity_dist.get("high", 0),
                "critical": severity_dist.get("critical", 0),
            },
            key_issues=data.get("key_issues", []),
        )

    def _parse_report_result(self, result: dict, state: ContractPipelineState) -> ComplianceReport:
        """Parse the complete report from JSON result."""
        extraction = state["extraction_output"]
        risk_output = state["risk_scoring_output"]

        if extraction is None or risk_output is None:
            raise ValueError("Report requires extraction and risk scoring outputs")

        # Parse executive summary
        exec_summary_data = result.get("executive_summary", {})
        executive_summary = self._parse_executive_summary(exec_summary_data)

        # Parse risk breakdown
        risk_breakdown = [self._parse_risk_breakdown(rb) for rb in result.get("risk_breakdown", [])]

        return ComplianceReport(
            report_id=f"report_{uuid4().hex[:8]}",
            contract_id=extraction.structure.contract_id,
            contract_title=extraction.structure.title,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            executive_summary=executive_summary,
            risk_breakdown=risk_breakdown,
            section_assessments=risk_output.assessed_sections,
            recommendations=result.get("recommendations", []),
            conclusion=result.get("conclusion", ""),
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

        try:
            result = self._invoke_and_parse(config, make_report_system_prompt(), user_prompt)
            report = self._parse_report_result(result, state)

            self.logger.info(
                f"Report generated: {report.report_id} - Status: {report.executive_summary.overall_status}"
            )

            return {
                "compliance_report": report,
                "current_stage": "complete",
            }

        except (KeyError, ValueError) as e:
            self._handle_parse_error(e)
            raise ValueError(f"Report generation failed: {e}")


def report_stage_node(state: ContractPipelineState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Report Generation Stage."""
    return ReportAgent().execute(state, config)

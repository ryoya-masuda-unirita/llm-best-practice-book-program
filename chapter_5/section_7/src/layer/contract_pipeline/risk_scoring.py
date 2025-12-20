"""
Risk Scoring Stage Module.

The Risk Scoring Stage is the second stage in the contract risk compliance pipeline,
responsible for:
- Evaluating risk for each contract section
- Identifying risk findings with severity levels
- Providing recommendations for risk mitigation
"""

from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.contract_pipeline_model import (
    ContractPipelineState,
    ContractSection,
    RiskCategory,
    RiskFinding,
    RiskLevel,
    RiskScoringOutput,
    SectionRiskAssessment,
)
from src.prompt.contract_pipeline_prompt import (
    make_risk_scoring_system_prompt,
    make_risk_scoring_user_prompt,
)


class RiskScoringAgent(BaseAgent):
    """
    Risk Scoring Stage Agent (リスク評価ステージエージェント).

    Evaluates risk for each contract section and provides findings
    with severity levels and recommendations.
    """

    def __init__(self):
        super().__init__(layer_name="PIPELINE", agent_name="RiskScoringAgent")

    def _parse_risk_finding(self, data: dict, index: int) -> RiskFinding:
        """Parse a risk finding from JSON data."""
        return RiskFinding(
            finding_id=data.get("finding_id", f"find_{uuid4().hex[:6]}"),
            description=data.get("description", ""),
            risk_level=self._safe_enum_parse(RiskLevel, data.get("risk_level", "low"), RiskLevel.LOW),
            risk_category=self._safe_enum_parse(RiskCategory, data.get("risk_category", "other"), RiskCategory.OTHER),
            affected_clause=data.get("affected_clause", ""),
            recommendation=data.get("recommendation", ""),
        )

    def _parse_section_assessment(self, result: dict, section: ContractSection) -> SectionRiskAssessment:
        """Parse section risk assessment from JSON result."""
        findings = [self._parse_risk_finding(f, i) for i, f in enumerate(result.get("findings", []))]

        return SectionRiskAssessment(
            section_id=result.get("section_id", section.section_id),
            section_title=result.get("section_title", f"{section.section_number} {section.title}"),
            overall_risk_level=self._safe_enum_parse(RiskLevel, result.get("overall_risk_level", "low"), RiskLevel.LOW),
            findings=findings,
            is_compliant=result.get("is_compliant", True),
            notes=result.get("notes", ""),
        )

    def _assess_section(
        self,
        section: ContractSection,
        parties: list[str],
        config: RunnableConfig,
    ) -> SectionRiskAssessment:
        """Assess risk for a single section."""
        self.logger.info(f"Assessing section: {section.section_number} {section.title}")

        user_prompt = make_risk_scoring_user_prompt(
            section_id=section.section_id,
            section_number=section.section_number,
            section_title=section.title,
            section_content=section.content,
            parties=parties,
        )

        result = self._invoke_and_parse(config, make_risk_scoring_system_prompt(), user_prompt)
        return self._parse_section_assessment(result, section)

    def execute(self, state: ContractPipelineState, config: RunnableConfig) -> dict:
        """Execute the risk scoring stage for all pending sections."""
        self._log_layer_start("Risk Scoring")

        extraction = state["extraction_output"]
        if extraction is None:
            raise ValueError("Risk scoring requires extraction output")

        pending_sections = state["pending_sections"]
        parties = extraction.structure.parties

        self.logger.info(f"Assessing {len(pending_sections)} sections...")

        # Assess all sections
        assessments: list[SectionRiskAssessment] = []
        for section in pending_sections:
            try:
                assessment = self._assess_section(section, parties, config)
                assessments.append(assessment)
                self.logger.info(f"Completed: {section.section_number} - Risk: {assessment.overall_risk_level}")
            except Exception as e:
                self.logger.error(f"Failed to assess {section.section_id}: {e}")
                # Create a default assessment for failed sections
                assessments.append(
                    SectionRiskAssessment(
                        section_id=section.section_id,
                        section_title=f"{section.section_number} {section.title}",
                        overall_risk_level=RiskLevel.MEDIUM,
                        findings=[],
                        is_compliant=True,
                        notes=f"評価中にエラーが発生しました: {str(e)}",
                    )
                )

        # Count high risk findings
        high_risk_count = sum(
            1 for a in assessments for f in a.findings if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )
        total_findings = sum(len(a.findings) for a in assessments)

        risk_output = RiskScoringOutput(
            contract_id=extraction.structure.contract_id,
            assessed_sections=assessments,
            high_risk_count=high_risk_count,
            total_findings=total_findings,
        )

        self.logger.info(f"Risk scoring complete: {total_findings} findings, {high_risk_count} high/critical")

        return {
            "risk_scoring_output": risk_output,
            "current_stage": "report",
        }


def risk_scoring_stage_node(state: ContractPipelineState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Risk Scoring Stage."""
    return RiskScoringAgent().execute(state, config)

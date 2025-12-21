"""
Risk Scoring Stage Module.

The Risk Scoring Stage is the second stage in the contract risk compliance pipeline,
responsible for:
- Evaluating risk for each contract section
- Identifying risk findings with severity levels
- Providing recommendations for risk mitigation
"""

import asyncio
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.model import (
    ContractPipelineState,
    ContractSection,
    RiskFinding,
    RiskLevel,
    RiskScoringOutput,
    RiskScoringResponse,
    SectionRiskAssessment,
)
from src.prompt.prompt import (
    make_risk_scoring_system_prompt,
    make_risk_scoring_user_prompt,
)

CONCURRENCY_LIMIT = 20


class RiskScoringAgent(BaseAgent):
    """
    Risk Scoring Stage Agent (リスク評価ステージエージェント).

    Evaluates risk for each contract section and provides findings
    with severity levels and recommendations.
    """

    def __init__(self):
        super().__init__(layer_name="PIPELINE", agent_name="RiskScoringAgent")

    def _convert_response_to_assessment(
        self, response: RiskScoringResponse, section: ContractSection
    ) -> SectionRiskAssessment:
        """Convert LLM response to domain assessment model."""
        findings = [
            RiskFinding(
                finding_id=f.finding_id or f"find_{uuid4().hex[:6]}",
                description=f.description,
                risk_level=f.risk_level,
                risk_category=f.risk_category,
                affected_clause=f.affected_clause,
                recommendation=f.recommendation,
            )
            for f in response.findings
        ]

        return SectionRiskAssessment(
            section_id=response.section_id or section.section_id,
            section_title=response.section_title or f"{section.section_number} {section.title}",
            overall_risk_level=response.overall_risk_level,
            findings=findings,
            is_compliant=response.is_compliant,
            notes=response.notes,
        )

    async def _assess_section_async(
        self,
        section: ContractSection,
        parties: list[str],
        config: RunnableConfig,
        semaphore: asyncio.Semaphore,
    ) -> SectionRiskAssessment:
        """Assess risk for a single section asynchronously."""
        async with semaphore:
            self.logger.info(f"Assessing section: {section.section_number} {section.title}")

            user_prompt = make_risk_scoring_user_prompt(
                section_id=section.section_id,
                section_number=section.section_number,
                section_title=section.title,
                section_content=section.content,
                parties=parties,
            )

            response = await self._ainvoke_structured(
                config,
                make_risk_scoring_system_prompt(),
                user_prompt,
                RiskScoringResponse,
            )
            assessment = self._convert_response_to_assessment(response, section)
            self.logger.info(f"Completed: {section.section_number} - Risk: {assessment.overall_risk_level}")
            return assessment

    def execute(self, state: ContractPipelineState, config: RunnableConfig) -> dict:
        pass

    async def execute_async(self, state: ContractPipelineState, config: RunnableConfig) -> dict:
        """Execute the risk scoring stage asynchronously."""
        self._log_layer_start("Risk Scoring")

        extraction = state["extraction_output"]
        if extraction is None:
            raise ValueError("Risk scoring requires extraction output")

        pending_sections = state["pending_sections"]
        parties = extraction.structure.parties

        self.logger.info(f"Assessing {len(pending_sections)} sections concurrently (limit: {CONCURRENCY_LIMIT})...")

        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        tasks = [self._assess_section_async(section, parties, config, semaphore) for section in pending_sections]

        assessments = await asyncio.gather(*tasks)

        high_risk_count = sum(
            1 for a in assessments for f in a.findings if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )
        total_findings = sum(len(a.findings) for a in assessments)

        risk_output = RiskScoringOutput(
            contract_id=extraction.structure.contract_id,
            assessed_sections=list(assessments),
            high_risk_count=high_risk_count,
            total_findings=total_findings,
        )

        self.logger.info(f"Risk scoring complete: {total_findings} findings, {high_risk_count} high/critical")

        return {
            "risk_scoring_output": risk_output,
            "current_stage": "report",
        }


async def risk_scoring_stage_node(state: ContractPipelineState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Risk Scoring Stage (async)."""
    return await RiskScoringAgent().execute_async(state, config)

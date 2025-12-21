"""
Contract Risk Compliance Pipeline Service.

This module implements a pipeline AI agent system for evaluating
contract risk compliance using LangGraph.

Pipeline Architecture:
    ┌─────────────────┐
    │  Input Stage    │  (Read contract file)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Extraction Stage│  (Parse structure: chapters, sections)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Risk Scoring    │  (Evaluate each section)
    │     Stage       │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Report Stage    │  (Generate compliance report)
    └────────┬────────┘
             │
             ▼
           [END]

"""

from pathlib import Path
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from src.client.llm_client import OpenAIModel
from src.layer.contract_pipeline import (
    extraction_stage_node,
    report_stage_node,
    risk_scoring_stage_node,
)
from src.logger import make_logger
from src.model.model import (
    ComplianceReport,
    ContractInput,
    ContractPipelineState,
)

logger = make_logger(__name__)


def create_contract_pipeline_graph() -> StateGraph:
    """Create the contract risk compliance pipeline graph."""
    logger.info("Creating contract compliance pipeline graph...")

    graph = StateGraph(ContractPipelineState)

    graph.add_node("extraction", extraction_stage_node)
    graph.add_node("risk_scoring", risk_scoring_stage_node)
    graph.add_node("report", report_stage_node)

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "risk_scoring")
    graph.add_edge("risk_scoring", "report")
    graph.add_edge("report", END)

    logger.info("Contract pipeline graph created successfully")
    return graph.compile()


def _read_contract_file(file_path: str) -> str:
    """Read contract content from file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {file_path}")

    logger.info(f"Reading contract file: {file_path}")
    return path.read_text(encoding="utf-8")


def _create_initial_state(file_path: str) -> ContractPipelineState:
    """Create initial state for the contract pipeline."""
    raw_content = _read_contract_file(file_path)

    contract_input = ContractInput(
        contract_id=f"contract_{uuid4().hex[:8]}",
        file_path=file_path,
        raw_content=raw_content,
    )

    return {
        "contract_input": contract_input,
        "extraction_output": None,
        "risk_scoring_output": None,
        "compliance_report": None,
        "current_stage": "extraction",
        "pending_sections": [],
        "current_section_index": 0,
        "messages": [],
    }


def _extract_report_from_state(final_state: dict) -> ComplianceReport | None:
    """Extract the compliance report from final graph state."""
    return final_state.get("compliance_report")


async def run_contract_compliance_pipeline(
    contract_file_path: str,
    model: str = OpenAIModel.GPT_4O,
) -> ComplianceReport | None:
    """Run the contract risk compliance pipeline."""
    logger.info("=" * 80)
    logger.info("CONTRACT RISK COMPLIANCE PIPELINE")
    logger.info("Pipeline: Input -> Extraction -> Risk Scoring -> Report")
    logger.info("=" * 80)
    logger.info(f"Contract file: {contract_file_path}")
    logger.info(f"Model: {model}")

    graph = create_contract_pipeline_graph()
    config = RunnableConfig(configurable={"model": model})

    initial_state = _create_initial_state(contract_file_path)
    logger.info(f"Contract ID: {initial_state['contract_input'].contract_id}")

    final_state = await graph.ainvoke(initial_state, config)
    report = _extract_report_from_state(final_state)

    if report:
        logger.info("=" * 80)
        logger.info("COMPLIANCE REPORT GENERATED SUCCESSFULLY")
        logger.info(f"Report ID: {report.report_id}")
        logger.info(f"Overall Status: {report.executive_summary.overall_status}")
        logger.info(f"Risk Score: {report.executive_summary.overall_risk_score}/100")
        logger.info("=" * 80)

    return report

"""
Pipeline AI Agent Layer Package.

This package implements the pipeline AI agent architecture for contract
risk compliance evaluation:

1. Extraction Stage (抽出ステージ):
   - Parses contract text into structured data
   - Extracts chapters, sections, and party information

2. Risk Scoring Stage (リスク評価ステージ):
   - Evaluates each section for legal and commercial risks
   - Provides findings with severity levels and recommendations

3. Report Generation Stage (レポート生成ステージ):
   - Aggregates all risk assessments
   - Generates comprehensive compliance report with executive summary
"""

from src.layer.base import BaseAgent
from src.layer.contract_pipeline import (
    extraction_stage_node,
    report_stage_node,
    risk_scoring_stage_node,
)

__all__ = [
    "BaseAgent",
    "extraction_stage_node",
    "risk_scoring_stage_node",
    "report_stage_node",
]

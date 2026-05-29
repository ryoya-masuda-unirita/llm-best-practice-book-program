"""Pytest configuration and shared fixtures."""

import pytest
from src.client.llm_client import LLMProvider
from src.model.llm_pipeline_model import AnalysisEvaluation, DocumentAnalysis, PipelineState


@pytest.fixture
def sample_document_content() -> str:
    """Sample Japanese markdown document for testing."""
    return """# テストドキュメント

## 概要

これはLLM出力の構造化に関するテストドキュメントです。

## 詳細

構造化出力を使用することで、LLMの応答を予測可能な形式で受け取ることができます。
"""


@pytest.fixture
def sample_analysis() -> DocumentAnalysis:
    """Sample document analysis result."""
    return DocumentAnalysis(
        theme="This document explains structured output for LLMs",
        value="It provides guidance on receiving LLM responses in predictable formats",
        improvement_requests=[
            "Add more code examples",
            "Include performance metrics",
            "Provide troubleshooting guide",
        ],
    )


@pytest.fixture
def sample_evaluation_good() -> AnalysisEvaluation:
    """Sample evaluation with good grade (4)."""
    return AnalysisEvaluation(
        grade=4,
        reasoning="The analysis captures the main theme well and provides clear value statement. "
        "Improvement requests are specific and actionable. Minor room for improvement in depth.",
        specific_improvements=[],
    )


@pytest.fixture
def sample_evaluation_poor() -> AnalysisEvaluation:
    """Sample evaluation with poor grade (2)."""
    return AnalysisEvaluation(
        grade=2,
        reasoning="The analysis is too generic and lacks depth. "
        "The theme is vague and value statement doesn't clearly articulate benefits. "
        "Improvement requests are not specific enough.",
        specific_improvements=[
            "Provide more specific theme that captures the main technical concept",
            "Elaborate on concrete benefits and use cases",
            "Make improvement requests more actionable with specific examples",
        ],
    )


@pytest.fixture
def base_pipeline_state(sample_document_content: str) -> PipelineState:
    """Base pipeline state for testing."""
    return {
        "document_path": "/path/to/test.md",
        "document_content": sample_document_content,
        "analysis_result": None,
        "evaluation_result": None,
        "retry_count": 0,
        "error": None,
        "llm_provider": LLMProvider.GEMINI,  # type: ignore
        "model": "gemini-2.5-flash",  # type: ignore
    }


@pytest.fixture
def pipeline_state_with_analysis(
    base_pipeline_state: PipelineState, sample_analysis: DocumentAnalysis
) -> PipelineState:
    """Pipeline state with analysis result."""
    return {
        **base_pipeline_state,
        "analysis_result": sample_analysis,
    }


@pytest.fixture
def pipeline_state_with_evaluation(
    pipeline_state_with_analysis: PipelineState, sample_evaluation_poor: AnalysisEvaluation
) -> PipelineState:
    """Pipeline state with analysis and poor evaluation."""
    return {
        **pipeline_state_with_analysis,
        "evaluation_result": sample_evaluation_poor,
    }

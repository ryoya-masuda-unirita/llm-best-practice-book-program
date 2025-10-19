"""Unit tests for LLM pipeline service nodes and routing functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.client.llm_client import LLMProvider
from src.model.llm_pipeline_model import AnalysisEvaluation, DocumentAnalysis, PipelineState
from src.service.llm_pipeline_service import (
    MAX_RETRIES,
    analyze_document_gemini_node,
    analyze_document_openai_node,
    judge_analysis_gemini_node,
    judge_analysis_openai_node,
    read_document_node,
    route_after_judge,
    route_to_judge,
    route_to_llm_provider,
)


class TestReadDocumentNode:
    """Tests for read_document_node."""

    @pytest.mark.asyncio
    async def test_read_document_success(
        self, tmp_path, base_pipeline_state: PipelineState, sample_document_content: str
    ):
        """Test successfully reading a document."""
        # Create a temporary file
        doc_file = tmp_path / "test.md"
        doc_file.write_text(sample_document_content, encoding="utf-8")

        # Update state with the file path
        state = {**base_pipeline_state, "document_path": str(doc_file)}

        # Execute
        result = await read_document_node(state)

        # Assert
        assert result["error"] is None
        assert result["document_content"] == sample_document_content
        assert len(result["document_content"]) > 0

    @pytest.mark.asyncio
    async def test_read_document_file_not_found(self, base_pipeline_state: PipelineState):
        """Test reading a non-existent file."""
        # Update state with non-existent file
        state = {**base_pipeline_state, "document_path": "/nonexistent/file.md"}

        # Execute
        result = await read_document_node(state)

        # Assert
        assert result["error"] is not None
        assert "Failed to read document" in result["error"]
        assert result["document_content"] == ""


class TestAnalyzeDocumentOpenAINode:
    """Tests for analyze_document_openai_node."""

    @pytest.mark.asyncio
    async def test_analyze_first_attempt(self, base_pipeline_state: PipelineState, sample_analysis: DocumentAnalysis):
        """Test first analysis attempt with OpenAI."""
        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = sample_analysis

        with patch("src.service.llm_pipeline_service.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

            # Execute
            state = {**base_pipeline_state, "llm_provider": LLMProvider.OPENAI, "model": "gpt-4o"}
            result = await analyze_document_openai_node(state)

            # Assert
            assert result["error"] is None
            assert result["analysis_result"] == sample_analysis
            mock_client.beta.chat.completions.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_with_retry_feedback(
        self,
        base_pipeline_state: PipelineState,
        sample_analysis: DocumentAnalysis,
        sample_evaluation_poor: AnalysisEvaluation,
    ):
        """Test analysis retry with judge feedback."""
        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = sample_analysis

        with patch("src.service.llm_pipeline_service.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

            # Execute with retry state
            state = {
                **base_pipeline_state,
                "llm_provider": LLMProvider.OPENAI,
                "model": "gpt-4o",
                "retry_count": 1,
                "evaluation_result": sample_evaluation_poor,
            }
            result = await analyze_document_openai_node(state)

            # Assert
            assert result["error"] is None
            assert result["analysis_result"] == sample_analysis

            # Check that feedback was added to prompt
            call_args = mock_client.beta.chat.completions.parse.call_args
            messages = call_args.kwargs["messages"]
            assert any("grade of 2/5" in str(msg) for msg in messages)

    @pytest.mark.asyncio
    async def test_analyze_api_error(self, base_pipeline_state: PipelineState):
        """Test handling API errors."""
        with patch("src.service.llm_pipeline_service.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API Error"))

            # Execute
            state = {**base_pipeline_state, "llm_provider": LLMProvider.OPENAI}
            result = await analyze_document_openai_node(state)

            # Assert
            assert result["error"] is not None
            assert "Failed to analyze document with OpenAI" in result["error"]
            assert result["analysis_result"] is None


class TestAnalyzeDocumentGeminiNode:
    """Tests for analyze_document_gemini_node."""

    @pytest.mark.asyncio
    async def test_analyze_first_attempt(self, base_pipeline_state: PipelineState, sample_analysis: DocumentAnalysis):
        """Test first analysis attempt with Gemini."""
        # Mock Gemini client
        mock_response = MagicMock()
        mock_response.parsed = sample_analysis

        with patch("src.service.llm_pipeline_service.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            # Execute
            state = {**base_pipeline_state, "llm_provider": LLMProvider.GEMINI}
            result = await analyze_document_gemini_node(state)

            # Assert
            assert result["error"] is None
            assert result["analysis_result"] == sample_analysis
            mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_api_error(self, base_pipeline_state: PipelineState):
        """Test handling API errors."""
        with patch("src.service.llm_pipeline_service.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))

            # Execute
            result = await analyze_document_gemini_node(base_pipeline_state)

            # Assert
            assert result["error"] is not None
            assert "Failed to analyze document with Gemini" in result["error"]
            assert result["analysis_result"] is None


class TestJudgeAnalysisOpenAINode:
    """Tests for judge_analysis_openai_node."""

    @pytest.mark.asyncio
    async def test_judge_analysis(
        self,
        pipeline_state_with_analysis: PipelineState,
        sample_evaluation_good: AnalysisEvaluation,
    ):
        """Test judging analysis with OpenAI."""
        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = sample_evaluation_good

        with patch("src.service.llm_pipeline_service.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

            # Execute
            state = {**pipeline_state_with_analysis, "llm_provider": LLMProvider.OPENAI}
            result = await judge_analysis_openai_node(state)

            # Assert
            assert result["error"] is None
            assert result["evaluation_result"] == sample_evaluation_good
            assert result["evaluation_result"].grade == 4
            mock_client.beta.chat.completions.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_judge_without_analysis(self, base_pipeline_state: PipelineState):
        """Test judge node when no analysis result exists."""
        # Execute
        result = await judge_analysis_openai_node(base_pipeline_state)

        # Assert - should return state unchanged
        assert result["evaluation_result"] is None

    @pytest.mark.asyncio
    async def test_judge_api_error(self, pipeline_state_with_analysis: PipelineState):
        """Test handling API errors."""
        with patch("src.service.llm_pipeline_service.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API Error"))

            # Execute
            state = {**pipeline_state_with_analysis, "llm_provider": LLMProvider.OPENAI}
            result = await judge_analysis_openai_node(state)

            # Assert
            assert result["error"] is not None
            assert "Failed to evaluate analysis with OpenAI" in result["error"]


class TestJudgeAnalysisGeminiNode:
    """Tests for judge_analysis_gemini_node."""

    @pytest.mark.asyncio
    async def test_judge_analysis(
        self,
        pipeline_state_with_analysis: PipelineState,
        sample_evaluation_good: AnalysisEvaluation,
    ):
        """Test judging analysis with Gemini."""
        # Mock Gemini client
        mock_response = MagicMock()
        mock_response.parsed = sample_evaluation_good

        with patch("src.service.llm_pipeline_service.google_genai_client") as mock_client:
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            # Execute
            result = await judge_analysis_gemini_node(pipeline_state_with_analysis)

            # Assert
            assert result["error"] is None
            assert result["evaluation_result"] == sample_evaluation_good
            mock_client.aio.models.generate_content.assert_called_once()


class TestRouteToLLMProvider:
    """Tests for route_to_llm_provider routing function."""

    def test_route_to_openai(self, base_pipeline_state: PipelineState):
        """Test routing to OpenAI provider."""
        state = {**base_pipeline_state, "llm_provider": LLMProvider.OPENAI}
        result = route_to_llm_provider(state)
        assert result == "analyze_openai"

    def test_route_to_gemini(self, base_pipeline_state: PipelineState):
        """Test routing to Gemini provider."""
        state = {**base_pipeline_state, "llm_provider": LLMProvider.GEMINI}
        result = route_to_llm_provider(state)
        assert result == "analyze_gemini"

    def test_route_with_error(self, base_pipeline_state: PipelineState):
        """Test routing when error exists."""
        state = {**base_pipeline_state, "error": "Some error"}
        result = route_to_llm_provider(state)
        assert result == "end"


class TestRouteToJudge:
    """Tests for route_to_judge routing function."""

    def test_route_to_openai_judge(self, pipeline_state_with_analysis: PipelineState):
        """Test routing to OpenAI judge."""
        state = {**pipeline_state_with_analysis, "llm_provider": LLMProvider.OPENAI}
        result = route_to_judge(state)
        assert result == "judge_openai"

    def test_route_to_gemini_judge(self, pipeline_state_with_analysis: PipelineState):
        """Test routing to Gemini judge."""
        state = {**pipeline_state_with_analysis, "llm_provider": LLMProvider.GEMINI}
        result = route_to_judge(state)
        assert result == "judge_gemini"

    def test_route_with_error(self, pipeline_state_with_analysis: PipelineState):
        """Test routing when error exists."""
        state = {**pipeline_state_with_analysis, "error": "Some error"}
        result = route_to_judge(state)
        assert result == "end"

    def test_route_without_analysis(self, base_pipeline_state: PipelineState):
        """Test routing when no analysis result exists."""
        result = route_to_judge(base_pipeline_state)
        assert result == "end"


class TestRouteAfterJudge:
    """Tests for route_after_judge routing function."""

    def test_accept_good_analysis(
        self,
        pipeline_state_with_analysis: PipelineState,
        sample_evaluation_good: AnalysisEvaluation,
    ):
        """Test accepting analysis with good grade (4+)."""
        state = {**pipeline_state_with_analysis, "evaluation_result": sample_evaluation_good}
        result = route_after_judge(state)
        assert result == "end"

    def test_retry_poor_analysis_openai(
        self,
        pipeline_state_with_analysis: PipelineState,
        sample_evaluation_poor: AnalysisEvaluation,
    ):
        """Test retrying analysis with poor grade (OpenAI)."""
        state = {
            **pipeline_state_with_analysis,
            "llm_provider": LLMProvider.OPENAI,
            "evaluation_result": sample_evaluation_poor,
            "retry_count": 0,
        }
        result = route_after_judge(state)
        assert result == "analyze_openai"
        assert state["retry_count"] == 1

    def test_retry_poor_analysis_gemini(
        self,
        pipeline_state_with_analysis: PipelineState,
        sample_evaluation_poor: AnalysisEvaluation,
    ):
        """Test retrying analysis with poor grade (Gemini)."""
        state = {
            **pipeline_state_with_analysis,
            "llm_provider": LLMProvider.GEMINI,
            "evaluation_result": sample_evaluation_poor,
            "retry_count": 0,
        }
        result = route_after_judge(state)
        assert result == "analyze_gemini"
        assert state["retry_count"] == 1

    def test_max_retries_reached(
        self,
        pipeline_state_with_analysis: PipelineState,
        sample_evaluation_poor: AnalysisEvaluation,
    ):
        """Test accepting analysis when max retries reached."""
        state = {
            **pipeline_state_with_analysis,
            "evaluation_result": sample_evaluation_poor,
            "retry_count": MAX_RETRIES,
        }
        result = route_after_judge(state)
        assert result == "end"

    def test_route_with_error(self, pipeline_state_with_evaluation: PipelineState):
        """Test routing when error exists."""
        state = {**pipeline_state_with_evaluation, "error": "Some error"}
        result = route_after_judge(state)
        assert result == "end"

    def test_route_without_evaluation(self, pipeline_state_with_analysis: PipelineState):
        """Test routing when no evaluation result exists."""
        result = route_after_judge(pipeline_state_with_analysis)
        assert result == "end"


class TestEvaluationModel:
    """Tests for AnalysisEvaluation model methods."""

    def test_is_acceptable_grade_4(self, sample_evaluation_good: AnalysisEvaluation):
        """Test is_acceptable returns True for grade 4."""
        assert sample_evaluation_good.is_acceptable() is True

    def test_is_acceptable_grade_5(self):
        """Test is_acceptable returns True for grade 5."""
        eval_5 = AnalysisEvaluation(
            grade=5,
            reasoning="Excellent analysis",
            specific_improvements=[],
        )
        assert eval_5.is_acceptable() is True

    def test_not_acceptable_grade_3(self):
        """Test is_acceptable returns False for grade 3."""
        eval_3 = AnalysisEvaluation(
            grade=3,
            reasoning="Acceptable but needs improvement",
            specific_improvements=["Improve depth"],
        )
        assert eval_3.is_acceptable() is False

    def test_not_acceptable_grade_2(self, sample_evaluation_poor: AnalysisEvaluation):
        """Test is_acceptable returns False for grade 2."""
        assert sample_evaluation_poor.is_acceptable() is False

"""Tests for Pydantic models used in the pipeline."""

import json

import pytest
from pydantic import ValidationError
from src.model.llm_pipeline_model import AnalysisEvaluation, DocumentAnalysis


class TestDocumentAnalysis:
    """Tests for DocumentAnalysis model."""

    def test_create_valid_analysis(self):
        """Test creating a valid DocumentAnalysis."""
        analysis = DocumentAnalysis(
            theme="Test theme",
            value="Test value",
            improvement_requests=["Improvement 1", "Improvement 2", "Improvement 3"],
        )

        assert analysis.theme == "Test theme"
        assert analysis.value == "Test value"
        assert len(analysis.improvement_requests) == 3

    def test_minimum_improvement_requests(self):
        """Test that minimum 3 improvement requests are required."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentAnalysis(
                theme="Test theme",
                value="Test value",
                improvement_requests=["Only one", "Only two"],
            )

        # Check that the error is about list length
        errors = exc_info.value.errors()
        assert any("at least 3 items" in str(error).lower() for error in errors)

    def test_maximum_improvement_requests(self):
        """Test that maximum 5 improvement requests are allowed."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentAnalysis(
                theme="Test theme",
                value="Test value",
                improvement_requests=["1", "2", "3", "4", "5", "6"],  # 6 items, should fail
            )

        # Check that the error is about list length
        errors = exc_info.value.errors()
        assert any("at most 5 items" in str(error).lower() for error in errors)

    def test_to_markdown(self, sample_analysis: DocumentAnalysis):
        """Test markdown conversion."""
        markdown = sample_analysis.to_markdown()

        assert "# Document Analysis Result" in markdown
        assert "## Theme" in markdown
        assert "## Value" in markdown
        assert "## Improvement Requests" in markdown
        assert sample_analysis.theme in markdown
        assert sample_analysis.value in markdown
        assert all(req in markdown for req in sample_analysis.improvement_requests)

    def test_save_as_json(self, tmp_path, sample_analysis: DocumentAnalysis):
        """Test saving analysis as JSON."""
        output_file = tmp_path / "analysis.json"
        sample_analysis.save_as_json(str(output_file))

        # Verify file was created
        assert output_file.exists()

        # Load and verify content
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["theme"] == sample_analysis.theme
        assert data["value"] == sample_analysis.value
        assert data["improvement_requests"] == sample_analysis.improvement_requests

    def test_save_as_markdown(self, tmp_path, sample_analysis: DocumentAnalysis):
        """Test saving analysis as Markdown."""
        output_file = tmp_path / "analysis.md"
        sample_analysis.save_as_markdown(str(output_file))

        # Verify file was created
        assert output_file.exists()

        # Load and verify content
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# Document Analysis Result" in content
        assert sample_analysis.theme in content
        assert sample_analysis.value in content

    def test_model_is_frozen(self, sample_analysis: DocumentAnalysis):
        """Test that the model is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_analysis.theme = "New theme"


class TestAnalysisEvaluation:
    """Tests for AnalysisEvaluation model."""

    def test_create_valid_evaluation_grade_5(self):
        """Test creating evaluation with grade 5."""
        evaluation = AnalysisEvaluation(
            grade=5,
            reasoning="Excellent analysis with comprehensive insights",
            specific_improvements=[],
        )

        assert evaluation.grade == 5
        assert evaluation.is_acceptable() is True

    def test_create_valid_evaluation_grade_4(self):
        """Test creating evaluation with grade 4."""
        evaluation = AnalysisEvaluation(
            grade=4,
            reasoning="Good analysis with minor improvements needed",
            specific_improvements=[],
        )

        assert evaluation.grade == 4
        assert evaluation.is_acceptable() is True

    def test_create_evaluation_grade_3(self):
        """Test creating evaluation with grade 3."""
        evaluation = AnalysisEvaluation(
            grade=3,
            reasoning="Acceptable but needs improvement",
            specific_improvements=["Add more depth", "Improve clarity"],
        )

        assert evaluation.grade == 3
        assert evaluation.is_acceptable() is False

    def test_create_evaluation_grade_2(self):
        """Test creating evaluation with grade 2."""
        evaluation = AnalysisEvaluation(
            grade=2,
            reasoning="Poor analysis",
            specific_improvements=["Rewrite theme", "Add value", "Better improvements"],
        )

        assert evaluation.grade == 2
        assert evaluation.is_acceptable() is False

    def test_create_evaluation_grade_1(self):
        """Test creating evaluation with grade 1."""
        evaluation = AnalysisEvaluation(
            grade=1,
            reasoning="Very poor analysis",
            specific_improvements=["Complete rewrite needed"],
        )

        assert evaluation.grade == 1
        assert evaluation.is_acceptable() is False

    def test_invalid_grade_0(self):
        """Test that grade 0 is invalid."""
        with pytest.raises(ValidationError):
            AnalysisEvaluation(
                grade=0,  # Invalid
                reasoning="Test",
                specific_improvements=[],
            )

    def test_invalid_grade_6(self):
        """Test that grade 6 is invalid."""
        with pytest.raises(ValidationError):
            AnalysisEvaluation(
                grade=6,  # Invalid
                reasoning="Test",
                specific_improvements=[],
            )

    def test_specific_improvements_optional(self):
        """Test that specific_improvements field is optional."""
        evaluation = AnalysisEvaluation(
            grade=5,
            reasoning="Perfect analysis",
        )

        assert evaluation.specific_improvements == []

    def test_model_is_frozen(self, sample_evaluation_good: AnalysisEvaluation):
        """Test that the model is immutable (frozen)."""
        with pytest.raises(ValidationError):
            sample_evaluation_good.grade = 3

    def test_is_acceptable_boundary_grade_4(self):
        """Test is_acceptable at boundary (grade 4)."""
        evaluation = AnalysisEvaluation(
            grade=4,
            reasoning="Good enough",
            specific_improvements=[],
        )

        assert evaluation.is_acceptable() is True

    def test_is_acceptable_boundary_grade_3(self):
        """Test is_acceptable at boundary (grade 3)."""
        evaluation = AnalysisEvaluation(
            grade=3,
            reasoning="Not good enough",
            specific_improvements=["Needs work"],
        )

        assert evaluation.is_acceptable() is False


class TestModelSerialization:
    """Tests for model serialization and deserialization."""

    def test_document_analysis_serialization(self, sample_analysis: DocumentAnalysis):
        """Test DocumentAnalysis can be serialized and deserialized."""
        # Serialize
        data = sample_analysis.model_dump()

        # Deserialize
        reconstructed = DocumentAnalysis(**data)

        # Verify
        assert reconstructed.theme == sample_analysis.theme
        assert reconstructed.value == sample_analysis.value
        assert reconstructed.improvement_requests == sample_analysis.improvement_requests

    def test_document_analysis_json_serialization(self, sample_analysis: DocumentAnalysis):
        """Test DocumentAnalysis JSON serialization."""
        # Serialize to JSON string
        json_str = sample_analysis.model_dump_json()

        # Deserialize
        reconstructed = DocumentAnalysis.model_validate_json(json_str)

        # Verify
        assert reconstructed == sample_analysis

    def test_evaluation_serialization(self, sample_evaluation_good: AnalysisEvaluation):
        """Test AnalysisEvaluation can be serialized and deserialized."""
        # Serialize
        data = sample_evaluation_good.model_dump()

        # Deserialize
        reconstructed = AnalysisEvaluation(**data)

        # Verify
        assert reconstructed.grade == sample_evaluation_good.grade
        assert reconstructed.reasoning == sample_evaluation_good.reasoning
        assert reconstructed.specific_improvements == sample_evaluation_good.specific_improvements

    def test_evaluation_json_serialization(self, sample_evaluation_poor: AnalysisEvaluation):
        """Test AnalysisEvaluation JSON serialization."""
        # Serialize to JSON string
        json_str = sample_evaluation_poor.model_dump_json()

        # Deserialize
        reconstructed = AnalysisEvaluation.model_validate_json(json_str)

        # Verify
        assert reconstructed.grade == sample_evaluation_poor.grade
        assert reconstructed.reasoning == sample_evaluation_poor.reasoning
        assert reconstructed.specific_improvements == sample_evaluation_poor.specific_improvements

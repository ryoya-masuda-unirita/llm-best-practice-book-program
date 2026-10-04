import json

from src.model.llm_pipeline_model import AnalysisEvaluation, DocumentAnalysis


def make_document_analysis_prompt(document_content: str) -> list[dict[str, str]]:
    """Create a prompt for document analysis."""
    schema_fields = {}
    for field_name, field_info in DocumentAnalysis.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an excellent document analyst.
You will read technical documents written in Japanese markdown format and analyze them from the following perspectives:

1. **Theme**: Briefly summarize the main theme of the document in 1-2 sentences
2. **Value**: Explain the value and importance this document provides to readers in 2-3 sentences
3. **Improvement Requests**: List 3-5 specific improvement requests to enhance the quality of the document

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- All fields must be included
- Improvement requests must be between 3 and 5 items
- Do not include explanations or additional text outside the JSON structure
- Analysis should be objective and constructive
- **IMPORTANT: All responses must be in Japanese (日本語で回答してください)**
"""

    user_prompt = f"""Please analyze the following markdown document:

{document_content}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def make_document_analysis_system_instruction(document_content: str) -> tuple[str, str]:
    """Create system instruction and user prompt for document analysis (for Anthropic)."""
    schema_fields = {}
    for field_name, field_info in DocumentAnalysis.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an excellent document analyst.
You will read technical documents written in Japanese markdown format and analyze them from the following perspectives:

1. **Theme**: Briefly summarize the main theme of the document in 1-2 sentences
2. **Value**: Explain the value and importance this document provides to readers in 2-3 sentences
3. **Improvement Requests**: List 3-5 specific improvement requests to enhance the quality of the document

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- All fields must be included
- Improvement requests must be between 3 and 5 items
- Do not include explanations or additional text outside the JSON structure
- Analysis should be objective and constructive
- **IMPORTANT: All responses must be in Japanese (日本語で回答してください)**
"""

    user_content = f"""Please analyze the following markdown document:

{document_content}
"""

    return system_instruction, user_content


def make_judge_prompt(document_content: str, analysis_result: DocumentAnalysis) -> list[dict[str, str]]:
    """Create a prompt for evaluating the document analysis (LLM-as-a-judge)."""
    schema_fields = {}
    for field_name, field_info in AnalysisEvaluation.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an expert evaluator of document analysis quality.
Your task is to evaluate how well the provided analysis captures the essence, value, and improvement opportunities of the original document.

Evaluation Criteria:
1. **Theme Accuracy (20%)**: Does the theme accurately and concisely capture the main topic?
2. **Value Assessment (30%)**: Does the value statement clearly articulate the document's importance and benefits?
3. **Improvement Quality (30%)**: Are the improvement requests specific, actionable, and relevant?
4. **Completeness (10%)**: Does the analysis cover all key aspects of the document?
5. **Clarity (10%)**: Is the analysis clear, well-written, and easy to understand?

Grading Scale:
- **5 (Excellent)**: Outstanding analysis that deeply understands the document and provides highly valuable insights
- **4 (Good)**: Solid analysis with minor areas for improvement
- **3 (Acceptable)**: Adequate analysis but missing some important aspects or lacking depth
- **2 (Poor)**: Significant issues with accuracy, completeness, or quality
- **1 (Very Poor)**: Fails to capture the document's essence or provides unhelpful analysis

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Grade must be an integer between 1 and 5
- Reasoning must be 3-5 sentences explaining the grade
- If grade is below 4, include 3-5 specific improvements in the specific_improvements array
- Be objective and constructive in your evaluation
- **IMPORTANT: All responses must be in Japanese (日本語で回答してください)**
"""

    analysis_json = json.dumps(analysis_result.model_dump(), indent=2, ensure_ascii=False)

    user_prompt = f"""Please evaluate this document analysis.

**Original Document:**
{document_content}

**Analysis to Evaluate:**
{analysis_json}

Provide your evaluation following the specified JSON structure.
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def make_judge_system_instruction(document_content: str, analysis_result: DocumentAnalysis) -> tuple[str, str]:
    """Create system instruction and user prompt for evaluating the analysis (for Anthropic)."""
    schema_fields = {}
    for field_name, field_info in AnalysisEvaluation.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an expert evaluator of document analysis quality.
Your task is to evaluate how well the provided analysis captures the essence, value, and improvement opportunities of the original document.

Evaluation Criteria:
1. **Theme Accuracy (20%)**: Does the theme accurately and concisely capture the main topic?
2. **Value Assessment (30%)**: Does the value statement clearly articulate the document's importance and benefits?
3. **Improvement Quality (30%)**: Are the improvement requests specific, actionable, and relevant?
4. **Completeness (10%)**: Does the analysis cover all key aspects of the document?
5. **Clarity (10%)**: Is the analysis clear, well-written, and easy to understand?

Grading Scale:
- **5 (Excellent)**: Outstanding analysis that deeply understands the document and provides highly valuable insights
- **4 (Good)**: Solid analysis with minor areas for improvement
- **3 (Acceptable)**: Adequate analysis but missing some important aspects or lacking depth
- **2 (Poor)**: Significant issues with accuracy, completeness, or quality
- **1 (Very Poor)**: Fails to capture the document's essence or provides unhelpful analysis

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Grade must be an integer between 1 and 5
- Reasoning must be 3-5 sentences explaining the grade
- If grade is below 4, include 3-5 specific improvements in the specific_improvements array
- Be objective and constructive in your evaluation
- **IMPORTANT: All responses must be in Japanese (日本語で回答してください)**
"""

    analysis_json = json.dumps(analysis_result.model_dump(), indent=2, ensure_ascii=False)

    user_content = f"""Please evaluate this document analysis.

**Original Document:**
{document_content}

**Analysis to Evaluate:**
{analysis_json}

Provide your evaluation following the specified JSON structure.
"""

    return system_instruction, user_content

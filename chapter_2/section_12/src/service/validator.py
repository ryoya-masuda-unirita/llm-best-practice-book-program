import json

from src.client.llm_client import (
    AnthropicModel,
    anthropic_client,
)
from src.logger import make_logger
from src.model.model import ExtractionResult, ValidationResult
from src.prompt.prompt import make_validation_prompt

logger = make_logger(__name__)


async def validate_extraction_result(
    model: AnthropicModel,
    extraction_result: ExtractionResult,
    document_content: str,
) -> ValidationResult:
    if extraction_result.raw_result is not None:
        result_for_validation = extraction_result.raw_result
    elif extraction_result.document_structure is not None:
        result_for_validation = extraction_result.document_structure.model_dump()
    else:
        return ValidationResult(
            score=1,
            reasoning="No extraction result available to validate.",
            fix_proposal="Re-run the extraction process to generate valid output.",
        )

    prompt = make_validation_prompt(
        document_content=document_content,
        extraction_result=json.dumps(result_for_validation, ensure_ascii=False, indent=2),
        script_explanation=extraction_result.script_explanation,
    )

    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=2048,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=ValidationResult,
    )

    validation_result = result.parsed_output

    logger.info(f"Validation score: {validation_result.score}/5")
    logger.info(f"Reasoning: {validation_result.reasoning}")
    if validation_result.fix_proposal:
        logger.warning(f"Fix proposal: {validation_result.fix_proposal}")

    return validation_result

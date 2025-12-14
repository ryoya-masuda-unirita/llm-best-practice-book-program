import json
import os
from pathlib import Path
from uuid import uuid4

from src.client.llm_client import AnthropicModel
from src.logger import make_logger
from src.model.model import DocumentStructure, ExtractionResult, ScriptExecutionResult
from src.service.request_llm import (
    correct_script,
    correct_script_from_validation,
    generate_extraction_script,
    sample_document,
)
from src.service.script_executor import execute_script
from src.service.validator import validate_extraction_result

logger = make_logger(__name__)

DEFAULT_MAX_CORRECTION_ATTEMPTS = 3
DEFAULT_MAX_VALIDATION_ATTEMPTS = 3
VALIDATION_THRESHOLD = 3


async def extract_document_structure(
    model: AnthropicModel,
    document_content: str,
    max_correction_attempts: int = DEFAULT_MAX_CORRECTION_ATTEMPTS,
    max_validation_attempts: int = DEFAULT_MAX_VALIDATION_ATTEMPTS,
) -> ExtractionResult:
    logger.info("Step 1: Sampling document sentences...")
    sampled_info = await sample_document(model=model, document_content=document_content)
    logger.info(f"Document type identified: {sampled_info.document_type}")
    logger.info(f"Key sections found: {sampled_info.key_sections}")

    logger.info("Step 2: Generating extraction script...")
    generated_script = await generate_extraction_script(
        model=model,
        document_content=document_content,
        sampled_info=sampled_info.model_dump(),
    )
    logger.info(f"Script explanation: {generated_script.explanation}")

    current_script = generated_script.script
    current_explanation = generated_script.explanation
    validation_result = None

    for validation_attempt in range(max_validation_attempts + 1):
        execution_result = await _execute_script_with_retry(
            model=model,
            script=current_script,
            document_content=document_content,
            max_attempts=max_correction_attempts,
        )

        if not execution_result.success or not execution_result.result:
            return ExtractionResult(
                success=False,
                document_structure=None,
                raw_result=None,
                final_script=current_script,
                sampled_info=sampled_info,
                script_explanation=current_explanation,
                error=execution_result.error,
                validation_result=validation_result,
            )

        document_structure = _parse_document_structure(execution_result.result)

        temp_result = ExtractionResult(
            success=True,
            document_structure=document_structure,
            raw_result=execution_result.result,
            final_script=current_script,
            sampled_info=sampled_info,
            script_explanation=current_explanation,
        )

        logger.info(
            f"Step 4: Validating extraction result (attempt {validation_attempt + 1}/{max_validation_attempts + 1})..."
        )
        validation_result = await validate_extraction_result(
            model=model,
            extraction_result=temp_result,
            document_content=document_content,
        )

        if validation_result.score > VALIDATION_THRESHOLD:
            logger.info(f"Validation passed with score {validation_result.score}/5")
            return ExtractionResult(
                success=True,
                document_structure=document_structure,
                raw_result=execution_result.result,
                final_script=current_script,
                sampled_info=sampled_info,
                script_explanation=current_explanation,
                validation_result=validation_result,
            )

        if validation_attempt < max_validation_attempts:
            logger.warning(f"Validation score {validation_result.score}/5 is below threshold {VALIDATION_THRESHOLD}")
            fix_proposal = validation_result.fix_proposal or validation_result.reasoning
            logger.info("Attempting to correct script based on validation feedback...")
            corrected_script = await correct_script_from_validation(
                model=model,
                original_script=current_script,
                validation_reasoning=validation_result.reasoning,
                fix_proposal=fix_proposal,
                document_content=document_content,
            )
            current_script = corrected_script.script
            current_explanation = corrected_script.explanation
            logger.info(f"Script corrected: {current_explanation}")
        else:
            logger.warning(
                f"Validation failed after {max_validation_attempts + 1} attempts with final score {validation_result.score}/5"
            )

    return ExtractionResult(
        success=True,
        document_structure=document_structure,
        raw_result=execution_result.result,
        final_script=current_script,
        sampled_info=sampled_info,
        script_explanation=current_explanation,
        validation_result=validation_result,
    )


async def _execute_script_with_retry(
    model: AnthropicModel,
    script: str,
    document_content: str,
    max_attempts: int = DEFAULT_MAX_CORRECTION_ATTEMPTS,
) -> ScriptExecutionResult:
    current_script = script

    for attempt in range(max_attempts + 1):
        logger.info(f"Step 3: Executing script (attempt {attempt + 1}/{max_attempts + 1})...")
        execution_result = execute_script(current_script, document_content)

        if execution_result.success:
            logger.info("Script executed successfully!")
            return execution_result

        if attempt < max_attempts:
            logger.warning(f"Script execution failed: {execution_result.error}")
            logger.info("Attempting to correct script...")
            corrected_script = await correct_script(
                model=model,
                original_script=current_script,
                error_message=execution_result.error,
                document_content=document_content,
            )
            current_script = corrected_script.script
            logger.info(f"Script correction: {corrected_script.explanation}")
        else:
            logger.error(f"Script execution failed after {max_attempts + 1} attempts")

    return execution_result


def _parse_document_structure(result: dict) -> DocumentStructure | None:
    try:
        return DocumentStructure(**result)
    except Exception as e:
        logger.warning(f"Failed to parse as DocumentStructure, will save raw result: {e}")
        return None


def save_extraction_results(
    extraction_result: ExtractionResult,
    input_file: str,
    output_directory: str,
    model: str,
) -> dict[str, str]:
    os.makedirs(output_directory, exist_ok=True)

    run_id = uuid4().hex[:8]
    input_filename = Path(input_file).stem
    output_files = {}

    structure_file = os.path.join(output_directory, f"{input_filename}_{run_id}_structure.json")
    if extraction_result.document_structure:
        extraction_result.document_structure.save_as_json(structure_file)
    else:
        with open(structure_file, "w", encoding="utf-8") as f:
            json.dump(extraction_result.raw_result, f, indent=4, ensure_ascii=False)
    logger.info(f"Document structure saved to: {structure_file}")
    output_files["structure"] = structure_file

    script_file = os.path.join(output_directory, f"{input_filename}_{run_id}_script.py")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(extraction_result.final_script)
    logger.info(f"Generated script saved to: {script_file}")
    output_files["script"] = script_file

    metadata_file = os.path.join(output_directory, f"{input_filename}_{run_id}_metadata.json")
    metadata = {
        "model": model,
        "input_file": input_file,
        "document_type": extraction_result.sampled_info.document_type,
        "key_sections": extraction_result.sampled_info.key_sections,
        "sampled_sentences": extraction_result.sampled_info.sentences,
        "script_explanation": extraction_result.script_explanation,
    }
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)
    logger.info(f"Metadata saved to: {metadata_file}")
    output_files["metadata"] = metadata_file

    return output_files

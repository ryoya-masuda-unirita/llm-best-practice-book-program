from src.client.llm_client import (
    AnthropicModel,
    anthropic_client,
)
from src.logger import make_logger
from src.model.model import GeneratedScript, SampledSentences
from src.prompt.prompt import (
    make_error_correction_prompt,
    make_sampling_prompt,
    make_script_generation_prompt,
)

logger = make_logger(__name__)


async def sample_document(model: AnthropicModel, document_content: str) -> SampledSentences:
    """Sample representative sentences from a document using LLM."""
    prompt = make_sampling_prompt(document_content)
    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=2048,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=SampledSentences,
    )
    logger.info(f"Sampled document info: {result.parsed_output}")
    return result.parsed_output


async def generate_extraction_script(
    model: AnthropicModel,
    document_content: str,
    sampled_info: dict,
) -> GeneratedScript:
    """Generate a Python script to extract document structure."""
    prompt = make_script_generation_prompt(document_content, sampled_info)
    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=GeneratedScript,
    )
    logger.info(f"Generated script explanation: {result.parsed_output.explanation}")
    return result.parsed_output


async def correct_script(
    model: AnthropicModel,
    original_script: str,
    error_message: str,
    document_content: str,
) -> GeneratedScript:
    """Correct a failed script using LLM."""
    prompt = make_error_correction_prompt(original_script, error_message, document_content)
    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=GeneratedScript,
    )
    logger.info(f"Corrected script explanation: {result.parsed_output.explanation}")
    return result.parsed_output

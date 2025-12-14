from google.genai.types import File, GenerateContentConfig

from src.client.llm_client import (
    GeminiModel,
    google_genai_client,
)
from src.logger import make_logger
from src.model.model import Diagram, DiagramType, Invoice, Slide
from src.prompt.prompt import make_diagram_identification_prompt, make_invoice_prompt, make_slide_prompt

logger = make_logger(__name__)


async def request_identify_diagram_type(model: GeminiModel, gemini_path: File) -> Diagram:
    system_prompt, user_prompt = make_diagram_identification_prompt()

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=[gemini_path, user_prompt],
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=Diagram,
        ),
    )
    logger.info(result)
    return result.parsed


async def extract_from_image(model: GeminiModel, gemini_path: File, diagram_type: DiagramType) -> Invoice | Slide:
    system_prompt, user_prompt = make_invoice_prompt() if diagram_type == DiagramType.INVOICE else make_slide_prompt()
    response_schema = Invoice if diagram_type == DiagramType.INVOICE else Slide

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=[gemini_path, user_prompt],
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    logger.info(result)
    return result.parsed


async def request_gemini(model: str, gemini_path: File) -> Invoice | Slide:
    logger.info(f"Processing image with model: {model}")

    diagram = await request_identify_diagram_type(model=model, gemini_path=gemini_path)
    logger.info(f"Identified diagram type: {diagram.diagram_type}")

    result = await extract_from_image(model=model, gemini_path=gemini_path, diagram_type=diagram.diagram_type)
    logger.info(f"Extracted data: {result}")

    return result

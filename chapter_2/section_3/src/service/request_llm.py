import base64
import mimetypes

from anthropic.types import ImageBlockParam
from src.client.llm_client import (
    AnthropicModel,
    anthropic_client,
)
from src.logger import make_logger
from src.model.model import Diagram, DiagramType, Invoice, Slide
from src.prompt.prompt import make_diagram_identification_prompt, make_invoice_prompt, make_slide_prompt

logger = make_logger(__name__)


def load_image(image_path: str) -> ImageBlockParam:
    """Read an image file and convert it into a base64 image block for Claude."""
    media_type = mimetypes.guess_type(image_path)[0] or "image/png"
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


async def request_identify_diagram_type(model: AnthropicModel, image: ImageBlockParam) -> Diagram:
    system_prompt, user_prompt = make_diagram_identification_prompt()

    result = await anthropic_client.messages.parse(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": [image, {"type": "text", "text": user_prompt}]}],
        output_format=Diagram,
    )
    logger.info(result)
    return result.parsed_output


async def extract_from_image(
    model: AnthropicModel, image: ImageBlockParam, diagram_type: DiagramType
) -> Invoice | Slide:
    system_prompt, user_prompt = make_invoice_prompt() if diagram_type == DiagramType.INVOICE else make_slide_prompt()
    response_schema = Invoice if diagram_type == DiagramType.INVOICE else Slide

    result = await anthropic_client.messages.parse(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": [image, {"type": "text", "text": user_prompt}]}],
        output_format=response_schema,
    )
    logger.info(result)
    return result.parsed_output


async def request_anthropic(model: str, image: ImageBlockParam) -> Invoice | Slide:
    logger.info(f"Processing image with model: {model}")

    diagram = await request_identify_diagram_type(model=model, image=image)
    logger.info(f"Identified diagram type: {diagram.diagram_type}")

    result = await extract_from_image(model=model, image=image, diagram_type=diagram.diagram_type)
    logger.info(f"Extracted data: {result}")

    return result

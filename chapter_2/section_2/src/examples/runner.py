from typing import Optional

from openai import OpenAI
from src.auto_structured_output import StructureExtractor
from src.client.llm_client import OpenAIModel
from src.logger import make_logger

logger = make_logger(__name__)


def run(
    llm_client: OpenAI,
    model: OpenAIModel,
    prompt: str,
    file_name: Optional[str] = None,
) -> None:
    extractor = StructureExtractor(llm_client=llm_client, model=model)
    T_Model = extractor.extract_structure([prompt])

    logger.info(f"Generated model: {T_Model.__name__}")
    logger.info(f"Fields: {T_Model.model_json_schema()}")

    response = llm_client.responses.parse(
        model=model,
        input=[{"role": "user", "content": prompt}],
        text_format=T_Model,
    )

    data = response.output_parsed
    if data is None:
        raise ValueError("Parsed data is None")
    data_dict = data.model_dump()
    logger.info("\nGenerated data:")
    logger.info(data_dict)

    if file_name:
        extractor.save_extracted_json(T_Model, file_name)

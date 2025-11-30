"""Dependency injection container for LLM services."""

from src.client.llm_client import anthropic_client
from src.service.interfaces import ITextClassificationService, ITextGenerationService
from src.service.text_classification_service import TextClassificationService
from src.service.text_generation_service import TextGenerationService


class ServiceContainer:
    """Container for managing LLM service instances."""

    def __init__(self):
        self._text_generation_service = TextGenerationService(client=anthropic_client)
        self._text_classification_service = TextClassificationService(client=anthropic_client)

    def get_text_generation_service(self) -> ITextGenerationService:
        return self._text_generation_service

    def get_text_classification_service(self) -> ITextClassificationService:
        return self._text_classification_service


service_container = ServiceContainer()

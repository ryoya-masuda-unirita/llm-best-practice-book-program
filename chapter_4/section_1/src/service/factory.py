"""Factory pattern for LLM service creation.

This module implements the Factory pattern to create appropriate LLM service
instances based on configuration, enabling flexible dependency injection.
"""

from src.config import config
from src.logger import make_logger
from src.service.execution import ExecutionLLMService
from src.service.interface import ILLMService
from src.service.storage import CachedLLMService

logger = make_logger(__name__)

_service_instance: ILLMService | None = None


class LLMServiceFactory:
    """Factory class for creating LLM service instances."""

    @staticmethod
    def create_service() -> ILLMService:
        """Create an LLM service instance based on configuration."""
        execution_service = ExecutionLLMService()

        if config.cache_enabled:
            logger.info(f"Creating CachedLLMService with {config.cache_backend} backend (TTL: {config.cache_ttl}s)")
            return CachedLLMService(execution_service)

        logger.info("Creating ExecutionLLMService without caching")
        return execution_service

    @staticmethod
    def create_execution_service() -> ExecutionLLMService:
        """Create a direct execution service without caching."""
        return ExecutionLLMService()

    @staticmethod
    def create_cached_service(execution_service: ILLMService | None = None) -> CachedLLMService:
        """Create a cached service with explicit execution service."""
        if execution_service is None:
            execution_service = ExecutionLLMService()
        return CachedLLMService(execution_service)


def get_llm_service() -> ILLMService:
    """Get or create the singleton LLM service instance."""
    global _service_instance

    if _service_instance is None:
        _service_instance = LLMServiceFactory.create_service()
        logger.info("LLM service singleton initialized")

    return _service_instance


def reset_llm_service() -> None:
    """Reset the singleton service instance (useful for testing)."""
    global _service_instance
    _service_instance = None
    logger.info("LLM service singleton reset")

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


class LLMServiceFactory:
    """
    Factory class for creating LLM service instances.

    This factory implements dependency injection, allowing the application
    to switch between different implementations (cached vs. direct execution)
    based on configuration without changing application code.
    """

    @staticmethod
    def create_service() -> ILLMService:
        """
        Create an LLM service instance based on configuration.

        The factory creates the appropriate service implementation:
        - If caching is enabled: Returns CachedLLMService wrapping ExecutionLLMService
        - If caching is disabled: Returns ExecutionLLMService directly

        This follows the Bridge pattern where the abstraction (ILLMService) is
        decoupled from its implementation.

        Returns:
            ILLMService: The configured LLM service instance
        """
        # Always create the execution service (core LLM functionality)
        execution_service = ExecutionLLMService()

        # Wrap with caching layer if enabled
        if config.cache_enabled:
            logger.info(f"Creating CachedLLMService with {config.cache_backend} backend (TTL: {config.cache_ttl}s)")
            return CachedLLMService(execution_service)
        else:
            logger.info("Creating ExecutionLLMService without caching")
            return execution_service

    @staticmethod
    def create_execution_service() -> ExecutionLLMService:
        """
        Create a direct execution service without caching.

        This is useful for scenarios where caching should be bypassed,
        such as testing or specific API endpoints that require fresh data.

        Returns:
            ExecutionLLMService: Direct execution service
        """
        logger.info("Creating ExecutionLLMService (direct, no cache)")
        return ExecutionLLMService()

    @staticmethod
    def create_cached_service(execution_service: ILLMService = None) -> CachedLLMService:
        """
        Create a cached service with explicit execution service.

        This allows for custom composition of services, useful for testing
        or when you want to explicitly control the service chain.

        Args:
            execution_service: Optional execution service to wrap. If not provided,
                             creates a new ExecutionLLMService

        Returns:
            CachedLLMService: Cached service wrapping the execution service
        """
        if execution_service is None:
            execution_service = ExecutionLLMService()

        logger.info(f"Creating CachedLLMService with {config.cache_backend} backend")
        return CachedLLMService(execution_service)


# Singleton instance for application-wide use
_service_instance: ILLMService = None


def get_llm_service() -> ILLMService:
    """
    Get or create the singleton LLM service instance.

    This function implements the Singleton pattern to ensure only one
    service instance is created and reused throughout the application lifecycle.

    Returns:
        ILLMService: The singleton LLM service instance
    """
    global _service_instance

    if _service_instance is None:
        _service_instance = LLMServiceFactory.create_service()
        logger.info("LLM service singleton initialized")

    return _service_instance


def reset_llm_service():
    """
    Reset the singleton service instance.

    This is primarily useful for testing scenarios where you need to
    recreate the service with different configurations.
    """
    global _service_instance
    _service_instance = None
    logger.info("LLM service singleton reset")

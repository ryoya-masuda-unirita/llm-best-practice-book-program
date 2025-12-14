"""Service layer for LLM operations."""


# Avoid circular imports by using lazy imports
def __getattr__(name):
    if name == "CacheManager":
        from src.service.cache_manager import CacheManager

        return CacheManager
    elif name == "FallbackCoordinator":
        from src.service.fallback_coordinator import FallbackCoordinator

        return FallbackCoordinator
    elif name == "FallbackStrategy":
        from src.service.fallback_coordinator import FallbackStrategy

        return FallbackStrategy
    elif name == "TemplateResponseGenerator":
        from src.service.template_response import TemplateResponseGenerator

        return TemplateResponseGenerator
    elif name == "template_generator":
        from src.service.template_response import template_generator

        return template_generator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CacheManager",
    "FallbackCoordinator",
    "FallbackStrategy",
    "TemplateResponseGenerator",
    "template_generator",
]

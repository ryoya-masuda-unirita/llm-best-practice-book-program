# Note: Imports are deferred to avoid circular dependencies
# Import directly from submodules as needed:
#   from src.service.request_llm import request_openai
#   from src.service.template_engine import TemplateEngine
#   from src.service.prompt_service import PromptManagementService

__all__ = [
    "request_openai",
    "TemplateEngine",
    "PromptManagementService",
    "PromptStorage",
    "PromptAnalyzer",
    "PromptCatalog",
    "PromptAnalytics",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "request_openai":
        from src.service.request_llm import request_openai

        return request_openai
    elif name == "TemplateEngine":
        from src.service.template_engine import TemplateEngine

        return TemplateEngine
    elif name == "PromptManagementService":
        from src.service.prompt_service import PromptManagementService

        return PromptManagementService
    elif name == "PromptStorage":
        from src.service.prompt_storage import PromptStorage

        return PromptStorage
    elif name == "PromptAnalyzer":
        from src.service.prompt_analyzer import PromptAnalyzer

        return PromptAnalyzer
    elif name == "PromptCatalog":
        from src.service.prompt_catalog import PromptCatalog

        return PromptCatalog
    elif name == "PromptAnalytics":
        from src.service.prompt_analytics import PromptAnalytics

        return PromptAnalytics
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Note: Imports are deferred to avoid circular dependencies
# Import directly from submodules as needed:
#   from src.service.request_llm import request_openai
#   from src.service.template_engine import TemplateEngine

__all__ = ["request_openai", "TemplateEngine"]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "request_openai":
        from src.service.request_llm import request_openai

        return request_openai
    elif name == "TemplateEngine":
        from src.service.template_engine import TemplateEngine

        return TemplateEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

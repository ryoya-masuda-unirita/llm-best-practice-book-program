__all__ = ["request_openai", "TemplateEngine"]


def __getattr__(name):
    if name == "request_openai":
        from src.service.request_llm import request_openai

        return request_openai
    elif name == "TemplateEngine":
        from src.service.template_engine import TemplateEngine

        return TemplateEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

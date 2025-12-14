"""
Example implementations demonstrating Dependency Injection in LLM workflows.

This module provides practical examples showing how to use DI patterns
to build flexible, testable, and maintainable LLM pipelines.
"""

from typing import Optional

from pydantic import BaseModel

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.logger import make_logger
from src.workflow import (
    DIContainer,
    GeminiLLMClient,
    ILLMClient,
    IPromptBuilder,
    IResponseParser,
    MessageListPromptBuilder,
    MockLLMClient,
    OpenAILLMClient,
    StructuredResponseParser,
    TemplatePromptBuilder,
    TextResponseParser,
    WorkflowBuilder,
    WorkflowEngine,
)
from src.workflow.base import ExecutionContext

logger = make_logger(__name__)


def create_llm_client(llm_provider: LLMProvider) -> ILLMClient:
    """Create an LLM client based on the provider."""
    if llm_provider == LLMProvider.OPENAI:
        return OpenAILLMClient(model=OpenAIModel.GPT_4O_MINI)
    elif llm_provider == LLMProvider.GEMINI:
        return GeminiLLMClient(model=GeminiModel.GEMINI_2_5_FLASH)
    else:
        raise ValueError(f"Unknown LLM provider: {llm_provider}")


async def example_1_manual_di(llm_provider: Optional[LLMProvider] = None):
    """
    Example 1: Manual dependency injection without a container.

    This demonstrates the basic concept of injecting dependencies
    directly into nodes.
    """
    logger.info("=" * 60)
    logger.info("Example 1: Manual Dependency Injection")
    logger.info("=" * 60)

    prompt_builder = TemplatePromptBuilder(template="Translate '{text}' to {target_language}")
    if llm_provider is None:
        llm_client: ILLMClient = MockLLMClient(mock_response="Bonjour le monde")
    else:
        llm_client = create_llm_client(llm_provider)
    response_parser = TextResponseParser()

    workflow = (
        WorkflowBuilder("translation-workflow", "Translation Example")
        .add_start_node(initial_data={"text": "Hello world", "target_language": "French"})
        .add_prompt_node(
            "translate",
            name="Translate Text",
            injected_prompt_builder=prompt_builder,
            injected_llm_client=llm_client,
            injected_response_parser=response_parser,
        )
        .add_end_node()
        .add_edge("start", "translate")
        .add_edge("translate", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    logger.info(f"Translation result: {result['outputs']['translate']}")

    return result


async def example_2_di_container_singleton(llm_provider: Optional[LLMProvider] = None):
    """
    Example 2: Using DI container with singleton services.

    Demonstrates how to register and resolve services from a container,
    with singleton lifetime for shared LLM clients.
    """
    logger.info("=" * 60)
    logger.info("Example 2: DI Container with Singleton Services")
    logger.info("=" * 60)

    container = DIContainer()

    if llm_provider is None:
        container.register_singleton(ILLMClient, lambda: MockLLMClient(mock_response="Analyzed content"))
    else:
        container.register_singleton(ILLMClient, lambda: create_llm_client(llm_provider))
    container.register_singleton(IResponseParser, TextResponseParser)
    container.register_transient(IPromptBuilder, lambda: TemplatePromptBuilder(template="Analyze: {content}"))

    llm_client = container.resolve(ILLMClient)
    response_parser = container.resolve(IResponseParser)
    prompt_builder = container.resolve(IPromptBuilder)

    workflow = (
        WorkflowBuilder("analysis-workflow", "Content Analysis")
        .add_start_node(initial_data={"content": "This is a sample document for analysis."})
        .add_prompt_node(
            "analyze",
            name="Analyze Content",
            injected_prompt_builder=prompt_builder,
            injected_llm_client=llm_client,
            injected_response_parser=response_parser,
        )
        .add_end_node()
        .add_edge("start", "analyze")
        .add_edge("analyze", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=False, di_container=container)
    result = await engine.execute(workflow)

    logger.info(f"Analysis result: {result['outputs']['analyze']}")

    return result


async def example_3_swapping_providers(llm_provider: Optional[LLMProvider] = None):
    """
    Example 3: Easy A/B testing by swapping LLM providers.

    Demonstrates how DI enables switching between different LLM providers
    without changing workflow code.
    """
    logger.info("=" * 60)
    logger.info("Example 3: Swapping LLM Providers for A/B Testing")
    logger.info("=" * 60)

    prompt_builder = TemplatePromptBuilder(template="Summarize: {article}")

    if llm_provider is None:
        providers: list[tuple[str, ILLMClient]] = [
            ("Mock Provider A", MockLLMClient(mock_response="Summary from provider A")),
            ("Mock Provider B", MockLLMClient(mock_response="Summary from provider B")),
        ]
    else:
        # Use real provider
        providers = [(f"{llm_provider.value}", create_llm_client(llm_provider))]

    results = []
    for provider_name, llm_client in providers:
        logger.info(f"\nTesting with: {provider_name}")

        workflow = (
            WorkflowBuilder(f"summarization-{provider_name}", "Summarization Workflow")
            .add_start_node(initial_data={"article": "Long article text goes here..."})
            .add_prompt_node(
                "summarize",
                name="Summarize Article",
                injected_prompt_builder=prompt_builder,
                injected_llm_client=llm_client,
                injected_response_parser=TextResponseParser(),
            )
            .add_end_node()
            .add_edge("start", "summarize")
            .add_edge("summarize", "end")
            .build()
        )

        engine = WorkflowEngine(enable_checkpointing=False)
        result = await engine.execute(workflow)

        logger.info(f"  Result: {result['outputs']['summarize']}")
        results.append(result)

    return results[0]


async def example_4_multi_stage_pipeline(llm_provider: Optional[LLMProvider] = None):
    """
    Example 4: Multi-stage pipeline with different injected components.

    Shows a complex workflow where different stages use different
    prompt builders and parsers.
    """
    logger.info("=" * 60)
    logger.info("Example 4: Multi-Stage Pipeline with DI")
    logger.info("=" * 60)

    extract_builder = TemplatePromptBuilder(template="Extract key points from: {document}")
    if llm_provider is None:
        extract_client: ILLMClient = MockLLMClient(mock_response="Key points: A, B, C")
    else:
        extract_client = create_llm_client(llm_provider)
    extract_parser = TextResponseParser()

    summary_builder = MessageListPromptBuilder(system_message="You are a summarization expert.")
    if llm_provider is None:
        summary_client: ILLMClient = MockLLMClient(mock_response="Professional summary of key points")
    else:
        summary_client = create_llm_client(llm_provider)
    summary_parser = TextResponseParser()

    def format_output(context: ExecutionContext) -> str:
        key_points = context.get_variable("extract_output", "")
        summary = context.get_variable("summarize_output", "")
        return f"## Key Points\n{key_points}\n\n## Summary\n{summary}"

    workflow = (
        WorkflowBuilder("multi-stage-workflow", "Document Processing Pipeline")
        .add_start_node(initial_data={"document": "Long technical document...", "prompt": "temp"})
        .add_prompt_node(
            "extract",
            name="Extract Key Points",
            injected_prompt_builder=extract_builder,
            injected_llm_client=extract_client,
            injected_response_parser=extract_parser,
        )
        .add_prompt_node(
            "summarize",
            name="Generate Summary",
            injected_prompt_builder=summary_builder,
            injected_llm_client=summary_client,
            injected_response_parser=summary_parser,
        )
        .add_python_script_node("format", name="Format Output", script_func=format_output)
        .add_end_node()
        .add_edge("start", "extract")
        .add_edge("extract", "summarize")
        .add_edge("summarize", "format")
        .add_edge("format", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    logger.info("\nFinal formatted output:")
    logger.info(result["outputs"]["format"])

    return result


class Character(BaseModel):
    """Example structured output model."""

    name: str
    age: int
    occupation: str


async def example_5_structured_output(llm_provider: Optional[LLMProvider] = None):
    """
    Example 5: Using structured output with custom parsers.

    Demonstrates how to work with typed responses using Pydantic models.
    """
    logger.info("=" * 60)
    logger.info("Example 5: Structured Output with DI")
    logger.info("=" * 60)

    prompt_builder = TemplatePromptBuilder(template="Create a character named {name}")

    if llm_provider is None:

        class MockStructuredClient(MockLLMClient):
            async def generate(self, prompt, context, **kwargs):
                response = await super().generate(prompt, context, **kwargs)
                response["parsed"] = Character(name="Alice", age=30, occupation="Engineer")
                return response

        llm_client: ILLMClient = MockStructuredClient()
    elif llm_provider == LLMProvider.OPENAI:
        llm_client = OpenAILLMClient(model=OpenAIModel.GPT_4O_MINI, response_format=Character)
    elif llm_provider == LLMProvider.GEMINI:
        llm_client = GeminiLLMClient(model=GeminiModel.GEMINI_2_5_FLASH, response_schema=Character)
    else:
        raise ValueError(f"Unknown LLM provider: {llm_provider}")

    response_parser = StructuredResponseParser()

    workflow = (
        WorkflowBuilder("character-generation", "Character Generator")
        .add_start_node(initial_data={"name": "Alice", "prompt": "temp"})
        .add_prompt_node(
            "generate",
            name="Generate Character",
            injected_prompt_builder=prompt_builder,
            injected_llm_client=llm_client,
            injected_response_parser=response_parser,
        )
        .add_end_node()
        .add_edge("start", "generate")
        .add_edge("generate", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    character = result["outputs"]["generate"]
    logger.info(f"Generated character: {character}")
    logger.info(f"Type: {type(character)}")

    return result


async def example_6_testing_pattern(llm_provider: Optional[LLMProvider] = None):
    """
    Example 6: Testing pattern showing mock vs real clients.

    Demonstrates how DI makes testing easy by allowing mock substitution.
    """
    logger.info("=" * 60)
    logger.info("Example 6: Testing Pattern with Mock and Real Clients")
    logger.info("=" * 60)

    async def run_sentiment_analysis(llm_client: ILLMClient, test_mode: bool = False):
        """Shared workflow logic that works with any ILLMClient."""
        mode = "TEST" if test_mode else "PRODUCTION"
        logger.info(f"\nRunning in {mode} mode")

        workflow = (
            WorkflowBuilder(f"sentiment-{mode.lower()}", "Sentiment Analysis")
            .add_start_node(initial_data={"review": "This product is amazing!", "prompt": "temp"})
            .add_prompt_node(
                "analyze",
                name="Analyze Sentiment",
                prompt_template="Analyze sentiment: {review}",
                injected_llm_client=llm_client,
                injected_response_parser=TextResponseParser(),
            )
            .add_end_node()
            .add_edge("start", "analyze")
            .add_edge("analyze", "end")
            .build()
        )

        engine = WorkflowEngine(enable_checkpointing=False)
        result = await engine.execute(workflow)
        return result

    mock_client = MockLLMClient(mock_response="Positive sentiment (confidence: 0.95)")
    test_result = await run_sentiment_analysis(mock_client, test_mode=True)
    logger.info(f"Test result: {test_result['outputs']['analyze']}")

    if llm_provider is not None:
        real_client = create_llm_client(llm_provider)
        prod_result = await run_sentiment_analysis(real_client, test_mode=False)
        logger.info(f"Production result: {prod_result['outputs']['analyze']}")

    logger.info("\nSame workflow code works with both mock and real clients!")

    return test_result

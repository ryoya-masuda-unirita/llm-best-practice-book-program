"""
Example implementations demonstrating Dependency Injection in LLM workflows.

This module provides practical examples showing how to use DI patterns
to build flexible, testable, and maintainable LLM pipelines.
"""

from pydantic import BaseModel

from src.logger import make_logger
from src.workflow import (
    DIContainer,
    ILLMClient,
    IPromptBuilder,
    IResponseParser,
    MessageListPromptBuilder,
    MockLLMClient,
    StructuredResponseParser,
    TemplatePromptBuilder,
    TextResponseParser,
    WorkflowBuilder,
    WorkflowEngine,
)

logger = make_logger(__name__)


# ============================================================================
# Example 1: Basic DI with Manual Injection
# ============================================================================


async def example_1_manual_di():
    """
    Example 1: Manual dependency injection without a container.

    This demonstrates the basic concept of injecting dependencies
    directly into nodes.
    """
    logger.info("=" * 60)
    logger.info("Example 1: Manual Dependency Injection")
    logger.info("=" * 60)

    # Create dependencies manually
    prompt_builder = TemplatePromptBuilder(template="Translate '{text}' to {target_language}")
    llm_client = MockLLMClient(mock_response="Bonjour le monde")
    response_parser = TextResponseParser()

    # Build workflow with injected dependencies
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

    # Execute
    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    logger.info(f"Translation result: {result['outputs']['translate']}")
    logger.info(f"Mock client was called {llm_client.call_count} time(s)")

    return result


# ============================================================================
# Example 2: DI Container with Singleton Services
# ============================================================================


async def example_2_di_container_singleton():
    """
    Example 2: Using DI container with singleton services.

    Demonstrates how to register and resolve services from a container,
    with singleton lifetime for shared LLM clients.
    """
    logger.info("=" * 60)
    logger.info("Example 2: DI Container with Singleton Services")
    logger.info("=" * 60)

    # Create and configure DI container
    container = DIContainer()

    # Register services as singletons (one instance shared)
    container.register_singleton(ILLMClient, lambda: MockLLMClient(mock_response="Analyzed content"))
    container.register_singleton(IResponseParser, TextResponseParser)

    # Register prompt builder as transient (new instance each time)
    container.register_transient(IPromptBuilder, lambda: TemplatePromptBuilder(template="Analyze: {content}"))

    # Resolve services from container
    llm_client = container.resolve(ILLMClient)
    response_parser = container.resolve(IResponseParser)
    prompt_builder = container.resolve(IPromptBuilder)

    # Build workflow
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

    # Execute with DI-enabled engine
    engine = WorkflowEngine(enable_checkpointing=False, di_container=container)
    result = await engine.execute(workflow)

    logger.info(f"Analysis result: {result['outputs']['analyze']}")

    return result


# ============================================================================
# Example 3: Swapping LLM Providers (A/B Testing)
# ============================================================================


async def example_3_swapping_providers():
    """
    Example 3: Easy A/B testing by swapping LLM providers.

    Demonstrates how DI enables switching between different LLM providers
    without changing workflow code.
    """
    logger.info("=" * 60)
    logger.info("Example 3: Swapping LLM Providers for A/B Testing")
    logger.info("=" * 60)

    # Shared prompt builder
    prompt_builder = TemplatePromptBuilder(template="Summarize: {article}")

    # Test with different providers
    providers = [
        ("Mock Provider A", MockLLMClient(mock_response="Summary from provider A")),
        ("Mock Provider B", MockLLMClient(mock_response="Summary from provider B")),
    ]

    initial_data = {"article": "Long article text goes here..."}

    results = []
    for provider_name, llm_client in providers:
        logger.info(f"\nTesting with: {provider_name}")

        workflow = (
            WorkflowBuilder(f"summarization-{provider_name}", "Summarization Workflow")
            .add_start_node(initial_data=initial_data)
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

    return results[0]  # Return first result for compatibility


# ============================================================================
# Example 4: Multi-Stage Pipeline with Different Components
# ============================================================================


async def example_4_multi_stage_pipeline():
    """
    Example 4: Multi-stage pipeline with different injected components.

    Shows a complex workflow where different stages use different
    prompt builders and parsers.
    """
    logger.info("=" * 60)
    logger.info("Example 4: Multi-Stage Pipeline with DI")
    logger.info("=" * 60)

    # Stage 1: Extract information (simple template)
    extract_builder = TemplatePromptBuilder(template="Extract key points from: {document}")
    extract_client = MockLLMClient(mock_response="Key points: A, B, C")
    extract_parser = TextResponseParser()

    # Stage 2: Generate summary (message-based)
    summary_builder = MessageListPromptBuilder(system_message="You are a summarization expert.")
    summary_client = MockLLMClient(mock_response="Professional summary of key points")
    summary_parser = TextResponseParser()

    # Stage 3: Format output
    def format_output(context):
        key_points = context.get_variable("extract_output", "")
        summary = context.get_variable("summarize_output", "")
        return f"## Key Points\n{key_points}\n\n## Summary\n{summary}"

    # Build multi-stage workflow
    workflow = (
        WorkflowBuilder("multi-stage-workflow", "Document Processing Pipeline")
        .add_start_node(initial_data={"document": "Long technical document...", "prompt": "temp"})
        # Stage 1: Extract
        .add_prompt_node(
            "extract",
            name="Extract Key Points",
            injected_prompt_builder=extract_builder,
            injected_llm_client=extract_client,
            injected_response_parser=extract_parser,
        )
        # Stage 2: Summarize
        .add_prompt_node(
            "summarize",
            name="Generate Summary",
            injected_prompt_builder=summary_builder,
            injected_llm_client=summary_client,
            injected_response_parser=summary_parser,
        )
        # Stage 3: Format
        .add_python_script_node("format", name="Format Output", script_func=format_output)
        .add_end_node()
        # Connect stages
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


# ============================================================================
# Example 5: Structured Output with Custom Parser
# ============================================================================


class Character(BaseModel):
    """Example structured output model."""

    name: str
    age: int
    occupation: str


async def example_5_structured_output():
    """
    Example 5: Using structured output with custom parsers.

    Demonstrates how to work with typed responses using Pydantic models.
    """
    logger.info("=" * 60)
    logger.info("Example 5: Structured Output with DI")
    logger.info("=" * 60)

    # Note: In real usage, you'd use OpenAILLMClient or GeminiLLMClient
    # with response_format parameter for actual structured output
    prompt_builder = TemplatePromptBuilder(template="Create a character named {name}")

    # Mock client that returns structured-like response
    class MockStructuredClient(MockLLMClient):
        async def generate(self, prompt, context, **kwargs):
            response = await super().generate(prompt, context, **kwargs)
            # Simulate parsed response
            response["parsed"] = Character(name="Alice", age=30, occupation="Engineer")
            return response

    llm_client = MockStructuredClient()
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


# ============================================================================
# Example 6: Testing with Mock vs Real Clients
# ============================================================================


async def example_6_testing_pattern():
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

    # Test mode: Use mock client (no API costs, fast)
    mock_client = MockLLMClient(mock_response="Positive sentiment (confidence: 0.95)")
    test_result = await run_sentiment_analysis(mock_client, test_mode=True)
    logger.info(f"Test result: {test_result['outputs']['analyze']}")

    # Production mode: Would use real client
    # Uncomment to test with real API:
    # real_client = OpenAILLMClient(model=OpenAIModel.GPT_4O_MINI)
    # prod_result = await run_sentiment_analysis(real_client, test_mode=False)
    # logger.info(f"Production result: {prod_result}")

    logger.info("\nSame workflow code works with both mock and real clients!")

    return test_result

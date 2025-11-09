"""
Example workflows using REAL LLM APIs (OpenAI and Gemini).

These examples demonstrate how to integrate actual LLM services with the workflow engine.
Unlike examples.py which uses mock executors, these make real API calls.

IMPORTANT: Set your API keys in .envrc before running:
    export OPENAI_API_KEY="your-key-here"
    export GEMINI_API_KEY="your-key-here"
"""

from src.client.llm_client import GeminiModel, OpenAIModel
from src.logger import make_logger
from src.workflow.base import ExecutionContext
from src.workflow.builder import WorkflowBuilder
from src.workflow.engine import WorkflowEngine
from src.workflow.llm_executors import (
    create_gemini_executor,
    create_openai_executor,
)

logger = make_logger(__name__)


async def example_gemini_simple():
    """
    Example: Simple workflow with Gemini API.

    This example uses the direct Gemini client executor for text completion.
    """
    logger.info("=" * 60)
    logger.info("Example: Gemini Simple Text Completion")
    logger.info("=" * 60)

    # Create Gemini executor
    gemini_executor = create_gemini_executor(
        model=GeminiModel.GEMINI_2_5_FLASH, system_instruction="You are a helpful assistant."
    )

    # Build workflow
    builder = WorkflowBuilder("gemini_simple", "Gemini Text Completion")

    workflow = (
        builder.add_start_node("start", initial_data={"topic": "artificial intelligence"})
        .add_prompt_node(
            "generate",
            name="Generate Content",
            prompt_template="Write a brief explanation of {topic} in 2-3 sentences.",
            llm_executor=gemini_executor,
        )
        .add_python_script_node(
            "display", name="Display Result", script_func=lambda ctx: ctx.get_node_output("generate")
        )
        .add_end_node("end")
        .add_edge("start", "generate")
        .add_edge("generate", "display")
        .add_edge("display", "end")
        .build()
    )

    # Execute
    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    logger.info("\n✓ Workflow completed")
    logger.info(f"Response: {result['outputs']['generate']['content']}")

    return result


async def example_openai_simple():
    """
    Example: Simple workflow with OpenAI API.

    This example uses the direct OpenAI client executor for text completion.
    """
    logger.info("=" * 60)
    logger.info("Example: OpenAI Simple Text Completion")
    logger.info("=" * 60)

    # Create OpenAI executor
    openai_executor = create_openai_executor(model=OpenAIModel.GPT_4O_MINI)

    # Build workflow
    builder = WorkflowBuilder("openai_simple", "OpenAI Text Completion")

    workflow = (
        builder.add_start_node("start", initial_data={"language": "Python", "task": "fibonacci sequence"})
        .add_prompt_node(
            "generate",
            name="Generate Code",
            prompt_template="Write a {language} function to calculate {task}. Include brief comments.",
            llm_executor=openai_executor,
        )
        .add_python_script_node(
            "display", name="Display Result", script_func=lambda ctx: ctx.get_node_output("generate")
        )
        .add_end_node("end")
        .add_edge("start", "generate")
        .add_edge("generate", "display")
        .add_edge("display", "end")
        .build()
    )

    # Execute
    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    logger.info("\n✓ Workflow completed")
    logger.info(f"Response: {result['outputs']['generate']['content']}")

    return result


async def example_multi_provider():
    """
    Example: Workflow using multiple LLM providers.

    This example demonstrates using both OpenAI and Gemini in the same workflow.
    Note: Uses sequential execution to compare responses from both providers.
    """
    logger.info("=" * 60)
    logger.info("Example: Multi-Provider Workflow")
    logger.info("=" * 60)

    # Create executors for both providers
    openai_executor = create_openai_executor(model=OpenAIModel.GPT_4O_MINI)
    gemini_executor = create_gemini_executor(model=GeminiModel.GEMINI_2_5_FLASH)

    # Build workflow with sequential execution (OpenAI → Gemini → Compare)
    builder = WorkflowBuilder("multi_provider", "Multi-Provider Comparison")

    workflow = (
        builder.add_start_node("start", initial_data={"question": "What is machine learning?"})
        .add_prompt_node(
            "openai_response",
            name="OpenAI Response",
            prompt_template="Answer this question briefly: {question}",
            llm_executor=openai_executor,
        )
        .add_prompt_node(
            "gemini_response",
            name="Gemini Response",
            prompt_template="Answer this question briefly: {question}",
            llm_executor=gemini_executor,
        )
        .add_python_script_node(
            "compare",
            name="Compare Responses",
            script_func=lambda ctx: {
                "openai": ctx.get_node_output("openai_response")["content"],
                "gemini": ctx.get_node_output("gemini_response")["content"],
            },
        )
        .add_end_node("end")
        # Sequential execution: start → openai → gemini → compare → end
        .add_edge("start", "openai_response")
        .add_edge("openai_response", "gemini_response")
        .add_edge("gemini_response", "compare")
        .add_edge("compare", "end")
        .build()
    )

    # Execute
    engine = WorkflowEngine(enable_checkpointing=False)
    result = await engine.execute(workflow)

    logger.info("\n✓ Workflow completed")
    logger.info(f"OpenAI: {result['outputs']['compare']['openai']}...")
    logger.info(f"Gemini: {result['outputs']['compare']['gemini']}...")

    return result


async def example_conditional_workflow():
    """
    Example 2: Workflow with conditional branching (IfElse)
    START -> Script (check condition) -> IfElse -> [Path A | Path B] -> END
    """
    logger.info("=" * 60)
    logger.info("Example 2: Conditional Workflow with IfElse")
    logger.info("=" * 60)

    builder = WorkflowBuilder("conditional_workflow", "Conditional Processing")

    # Define condition function
    def check_character_age(ctx: ExecutionContext) -> bool:
        age = ctx.get_variable("character_age", 0)
        return age >= 18

    workflow = (
        builder.add_start_node("start", "Start", initial_data={"character_age": 25})
        .add_if_else_node("age_check", "Check Age", condition=check_character_age)
        .add_python_script_node(
            "adult_processing",
            "Process Adult Character",
            script_func=lambda ctx: {"category": "adult", "age": ctx.get_variable("character_age")},
        )
        .add_python_script_node(
            "minor_processing",
            "Process Minor Character",
            script_func=lambda ctx: {"category": "minor", "age": ctx.get_variable("character_age")},
        )
        .add_end_node("end", "End")
        .add_edge("start", "age_check")
        .set_if_else_branches("age_check", "adult_processing", "minor_processing")
        .add_edge("adult_processing", "end")
        .add_edge("minor_processing", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=True)
    result = await engine.execute(workflow)

    logger.info(f"Workflow result: {result['status']}")
    logger.info(f"Final outputs: {result['outputs']}")

    return result


async def example_loop_workflow():
    """
    Example 3: Workflow with loop iteration
    START -> Loop (iterate collection) -> Display Results -> END

    Note: LoopNode executes internally without creating graph cycles.
    The loop body logic is contained within the LoopNode's execute method.
    """
    logger.info("=" * 60)
    logger.info("Example 3: Loop Workflow")
    logger.info("=" * 60)

    builder = WorkflowBuilder("loop_workflow", "Batch Processing")

    # Simple workflow: start -> loop -> display -> end
    # The loop node handles iteration internally
    workflow = (
        builder.add_start_node("start", "Start", initial_data={"items": ["item1", "item2", "item3"]})
        .add_loop_node("process_loop", "Process Items", collection_key="items", max_iterations=10)
        .add_python_script_node(
            "display_results",
            "Display Loop Results",
            script_func=lambda ctx: {
                "total_iterations": ctx.get_node_output("process_loop").get("iterations", 0),
                "items_processed": ctx.get_variable("items", []),
            },
        )
        .add_end_node("end", "End")
        .add_edge("start", "process_loop")
        .add_edge("process_loop", "display_results")
        .add_edge("display_results", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=True)
    result = await engine.execute(workflow)

    logger.info(f"Workflow result: {result['status']}")
    logger.info(f"Loop iterations: {result['outputs'].get('process_loop', {}).get('iterations', 0)}")

    return result


async def example_checkpoint_recovery():
    """
    Example 5: Demonstrates checkpoint and recovery
    Shows how to resume a workflow from a checkpoint
    """
    logger.info("=" * 60)
    logger.info("Example 5: Checkpoint and Recovery")
    logger.info("=" * 60)

    builder = WorkflowBuilder("checkpoint_workflow", "Checkpoint Demo")

    workflow = (
        builder.add_start_node("start", "Start", initial_data={"counter": 0})
        .add_python_script_node(
            "step1",
            "Step 1",
            script_func=lambda ctx: {"step": 1, "counter": ctx.get_variable("counter", 0) + 1},
        )
        .add_python_script_node(
            "step2", "Step 2", script_func=lambda ctx: {"step": 2, "counter": ctx.get_variable("counter", 0) + 1}
        )
        .add_python_script_node(
            "step3", "Step 3", script_func=lambda ctx: {"step": 3, "counter": ctx.get_variable("counter", 0) + 1}
        )
        .add_end_node("end", "End")
        .add_edge("start", "step1")
        .add_edge("step1", "step2")
        .add_edge("step2", "step3")
        .add_edge("step3", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=True, checkpoint_interval=1)
    result = await engine.execute(workflow)

    logger.info(f"Initial execution completed: {result['status']}")

    # List checkpoints
    checkpoints = engine.list_checkpoints(workflow.workflow_id)
    logger.info(f"Checkpoints available: {len(checkpoints)}")

    for checkpoint in checkpoints:
        logger.info(f"  - Checkpoint: {checkpoint['checkpoint_id']} at {checkpoint['timestamp']}")

    return result


async def example_complex_content_pipeline():
    """
    Complex Example 1: Multi-Stage Content Generation and Analysis Pipeline (12 nodes)

    This workflow demonstrates:
    - Multiple LLM calls with different providers
    - Conditional branching based on content quality
    - Data transformation and aggregation
    - Error handling and validation

    Flow:
    START -> Generate Topics (Gemini) -> Validate Topics ->
    Loop(Topics) -> Generate Content (OpenAI) -> Analyze Quality (Gemini) ->
    IfElse(Quality Check) -> [Refine Content (OpenAI) | Accept Content] ->
    Aggregate Results -> Generate Summary (Gemini) -> END
    """
    logger.info("=" * 60)
    logger.info("Complex Example 1: Content Generation Pipeline")
    logger.info("=" * 60)

    # Create executors for different providers
    gemini_executor = create_gemini_executor(
        model=GeminiModel.GEMINI_2_5_FLASH, system_instruction="You are a creative content generator."
    )
    openai_executor = create_openai_executor(model=OpenAIModel.GPT_4O_MINI)

    builder = WorkflowBuilder("content_pipeline", "Multi-Stage Content Pipeline")

    # Quality check condition
    def check_quality(ctx: ExecutionContext) -> bool:
        """Check if content quality score is above threshold."""
        quality_score = ctx.get_variable("quality_score", 0)
        return quality_score >= 7

    workflow = (
        builder
        # 1. START: Initialize with content requirements
        .add_start_node(
            "start", initial_data={"domain": "artificial intelligence", "num_topics": 3, "quality_threshold": 7}
        )
        # 2. Generate topic ideas using Gemini
        .add_prompt_node(
            "generate_topics",
            name="Generate Topic Ideas",
            prompt_template="Generate {num_topics} engaging blog post topics about {domain}. Return as a comma-separated list.",
            llm_executor=gemini_executor,
        )
        # 3. Parse and validate topics
        .add_python_script_node(
            "parse_topics",
            name="Parse Topics",
            script_func=lambda ctx: {
                "topics": [
                    t.strip()
                    for t in ctx.get_node_output("generate_topics")["content"].split(",")[
                        : ctx.get_variable("num_topics", 3)
                    ]
                ],
                "topics_count": len(ctx.get_node_output("generate_topics")["content"].split(",")),
            },
        )
        # 4. Select first topic for detailed processing
        .add_python_script_node(
            "select_topic",
            name="Select Topic",
            script_func=lambda ctx: (
                ctx.set_variable("selected_topic", ctx.get_node_output("parse_topics")["topics"][0]),
                {
                    "selected_topic": ctx.get_node_output("parse_topics")["topics"][0],
                    "remaining_topics": ctx.get_node_output("parse_topics")["topics"][1:],
                },
            )[1],
        )
        # 5. Generate detailed content using OpenAI
        .add_prompt_node(
            "generate_content",
            name="Generate Content",
            prompt_template="Write a detailed 3-paragraph blog post about: {selected_topic}",
            llm_executor=openai_executor,
        )
        # 5b. Store content in context for later nodes
        .add_python_script_node(
            "store_content",
            name="Store Content",
            script_func=lambda ctx: (
                ctx.set_variable("content", ctx.get_node_output("generate_content")["content"]),
                {"stored": True},
            )[1],
        )
        # 6. Analyze content quality using Gemini
        .add_prompt_node(
            "analyze_quality",
            name="Analyze Quality",
            prompt_template="Rate the following content on a scale of 1-10 for clarity, engagement, and accuracy. Return only the number:\n\n{content}",
            llm_executor=gemini_executor,
        )
        # 7. Extract quality score
        .add_python_script_node(
            "extract_quality_score",
            name="Extract Quality Score",
            script_func=lambda ctx: {
                "quality_score": int(
                    "".join(filter(str.isdigit, ctx.get_node_output("analyze_quality")["content"][:2])) or "5"
                )
            },
        )
        # 8. Store quality score in context
        .add_python_script_node(
            "store_quality",
            name="Store Quality Score",
            script_func=lambda ctx: ctx.set_variable(
                "quality_score", ctx.get_node_output("extract_quality_score")["quality_score"]
            )
            or {"stored": True},
        )
        # 9. Quality check decision
        .add_if_else_node("quality_check", name="Quality Check", condition=check_quality)
        # 10a. Refine content if quality is low (using OpenAI)
        .add_prompt_node(
            "refine_content",
            name="Refine Content",
            prompt_template="Improve this content to make it more engaging and clear:\n\n{content}",
            llm_executor=openai_executor,
        )
        # 10b. Accept content if quality is high
        .add_python_script_node(
            "accept_content",
            name="Accept Content",
            script_func=lambda ctx: {
                "final_content": ctx.get_node_output("generate_content")["content"],
                "status": "accepted",
                "quality_score": ctx.get_variable("quality_score"),
            },
        )
        # 11. Merge results from both branches
        .add_python_script_node(
            "merge_results",
            name="Merge Results",
            script_func=lambda ctx: (
                lambda merged_content: (
                    ctx.set_variable("content", merged_content),
                    {
                        "content": merged_content,
                        "was_refined": "refine_content" in ctx.node_outputs,
                        "quality_score": ctx.get_variable("quality_score"),
                    },
                )[1]
            )(
                ctx.get_node_output("refine_content", {}).get("content")
                or ctx.get_node_output("accept_content", {}).get("final_content")
            ),
        )
        # 12. Generate executive summary using Gemini
        .add_prompt_node(
            "generate_summary",
            name="Generate Summary",
            prompt_template="Create a 2-sentence executive summary of this content:\n\n{content}",
            llm_executor=gemini_executor,
        )
        # 13. END
        .add_end_node("end")
        # Build the graph edges
        .add_edge("start", "generate_topics")
        .add_edge("generate_topics", "parse_topics")
        .add_edge("parse_topics", "select_topic")
        .add_edge("select_topic", "generate_content")
        .add_edge("generate_content", "store_content")
        .add_edge("store_content", "analyze_quality")
        .add_edge("analyze_quality", "extract_quality_score")
        .add_edge("extract_quality_score", "store_quality")
        .add_edge("store_quality", "quality_check")
        # Conditional branches
        .set_if_else_branches("quality_check", "accept_content", "refine_content")
        # Merge paths
        .add_edge("accept_content", "merge_results")
        .add_edge("refine_content", "merge_results")
        .add_edge("merge_results", "generate_summary")
        .add_edge("generate_summary", "end")
        .build()
    )

    # Execute with checkpointing
    engine = WorkflowEngine(enable_checkpointing=True, checkpoint_interval=3)
    result = await engine.execute(workflow)

    logger.info("\n✓ Complex Content Pipeline Completed")
    logger.info(f"  Nodes executed: {result['nodes_executed']}")
    logger.info(f"  Quality score: {result['variables'].get('quality_score', 'N/A')}")
    logger.info(f"  Content was refined: {result['outputs']['merge_results']['was_refined']}")
    logger.info(f"\n  Summary: {result['outputs']['generate_summary']['content']}...")

    return result


async def example_complex_research_workflow():
    """
    Complex Example 2: Automated Research and Report Generation Workflow (14 nodes)

    This workflow demonstrates:
    - Parallel concept exploration with multiple LLM calls
    - Data aggregation and synthesis
    - Multi-stage validation and refinement
    - Checkpoint-based recovery

    Flow:
    START -> Define Research Questions (Gemini) -> Split Questions ->
    Research Q1 (OpenAI) -> Research Q2 (Gemini) -> Research Q3 (OpenAI) ->
    Aggregate Findings -> Validate Completeness (Gemini) ->
    IfElse(Is Complete?) -> [Generate Report | Add More Research] ->
    Format Report -> Review Report (Gemini) -> Finalize -> END
    """
    logger.info("=" * 60)
    logger.info("Complex Example 2: Research and Report Generation")
    logger.info("=" * 60)

    # Create executors
    gemini_executor = create_gemini_executor(
        model=GeminiModel.GEMINI_2_5_FLASH, system_instruction="You are a thorough research assistant."
    )
    openai_executor = create_openai_executor(model=OpenAIModel.GPT_4O_MINI)

    builder = WorkflowBuilder("research_workflow", "Research and Report Generation")

    # Completeness check
    def check_completeness(ctx: ExecutionContext) -> bool:
        """Check if research findings are complete."""
        completeness = ctx.get_variable("completeness_score", 0)
        return completeness >= 8

    workflow = (
        builder
        # 1. START: Initialize research parameters
        .add_start_node(
            "start",
            initial_data={
                "research_topic": "impact of large language models on software development",
                "depth": "comprehensive",
            },
        )
        # 2. Define research questions using Gemini
        .add_prompt_node(
            "define_questions",
            name="Define Research Questions",
            prompt_template="Generate 3 specific research questions about: {research_topic}. Format as numbered list.",
            llm_executor=gemini_executor,
        )
        # 3. Parse questions
        .add_python_script_node(
            "parse_questions",
            name="Parse Questions",
            script_func=lambda ctx: {
                "questions": [
                    q.strip()
                    for q in ctx.get_node_output("define_questions")["content"].split("\n")
                    if q.strip() and any(c.isdigit() for c in q[:3])
                ][:3]
            },
        )
        # 4. Research Question 1 (OpenAI)
        .add_python_script_node(
            "prep_q1",
            name="Prepare Q1",
            script_func=lambda ctx: (
                ctx.set_variable("question", ctx.get_node_output("parse_questions")["questions"][0]),
                {"question": ctx.get_node_output("parse_questions")["questions"][0]},
            )[1],
        )
        .add_prompt_node(
            "research_q1",
            name="Research Q1",
            prompt_template="Provide a detailed answer to: {question}",
            llm_executor=openai_executor,
        )
        # 5. Research Question 2 (Gemini)
        .add_python_script_node(
            "prep_q2",
            name="Prepare Q2",
            script_func=lambda ctx: (
                lambda q: (
                    ctx.set_variable("question", q),
                    {"question": q},
                )[1]
            )(
                ctx.get_node_output("parse_questions")["questions"][1]
                if len(ctx.get_node_output("parse_questions")["questions"]) > 1
                else "No second question available"
            ),
        )
        .add_prompt_node(
            "research_q2",
            name="Research Q2",
            prompt_template="Provide a detailed answer to: {question}",
            llm_executor=gemini_executor,
        )
        # 6. Research Question 3 (OpenAI)
        .add_python_script_node(
            "prep_q3",
            name="Prepare Q3",
            script_func=lambda ctx: (
                lambda q: (
                    ctx.set_variable("question", q),
                    {"question": q},
                )[1]
            )(
                ctx.get_node_output("parse_questions")["questions"][2]
                if len(ctx.get_node_output("parse_questions")["questions"]) > 2
                else "No third question available"
            ),
        )
        .add_prompt_node(
            "research_q3",
            name="Research Q3",
            prompt_template="Provide a detailed answer to: {question}",
            llm_executor=openai_executor,
        )
        # 7. Aggregate all findings
        .add_python_script_node(
            "aggregate_findings",
            name="Aggregate Findings",
            script_func=lambda ctx: (
                lambda findings_list: (
                    ctx.set_variable(
                        "findings", "\n\n".join(f"Finding {i + 1}: {f}" for i, f in enumerate(findings_list))
                    ),
                    {
                        "findings": findings_list,
                        "questions": ctx.get_node_output("parse_questions")["questions"],
                    },
                )[1]
            )(
                [
                    ctx.get_node_output("research_q1")["content"],
                    ctx.get_node_output("research_q2")["content"],
                    ctx.get_node_output("research_q3")["content"],
                ]
            ),
        )
        # 8. Validate completeness using Gemini
        .add_prompt_node(
            "validate_completeness",
            name="Validate Completeness",
            prompt_template="Rate the completeness of these research findings (1-10). Return only the number:\n\nTopic: {research_topic}\n\nFindings:\n{findings}",
            llm_executor=gemini_executor,
        )
        # 9. Extract completeness score
        .add_python_script_node(
            "extract_completeness",
            name="Extract Completeness",
            script_func=lambda ctx: {
                "completeness_score": int(
                    "".join(filter(str.isdigit, ctx.get_node_output("validate_completeness")["content"][:2])) or "7"
                )
            },
        )
        # 10. Store completeness score
        .add_python_script_node(
            "store_completeness",
            name="Store Completeness",
            script_func=lambda ctx: ctx.set_variable(
                "completeness_score", ctx.get_node_output("extract_completeness")["completeness_score"]
            )
            or {"stored": True},
        )
        # 11. Completeness check
        .add_if_else_node("completeness_check", name="Completeness Check", condition=check_completeness)
        # 12a. Generate report if complete (Gemini)
        .add_prompt_node(
            "generate_report",
            name="Generate Report",
            prompt_template="Create a comprehensive research report on '{research_topic}' using these findings:\n\n{findings}\n\nInclude: Executive Summary, Key Findings, and Conclusion.",
            llm_executor=gemini_executor,
        )
        # 12b. Add supplementary research if incomplete
        .add_prompt_node(
            "add_research",
            name="Add Supplementary Research",
            prompt_template="Provide additional context on: {research_topic}",
            llm_executor=openai_executor,
        )
        # 13. Merge paths
        .add_python_script_node(
            "merge_report",
            name="Merge Report",
            script_func=lambda ctx: (
                lambda report_content: (
                    ctx.set_variable("report", report_content),
                    {
                        "report": report_content,
                        "is_complete": ctx.get_variable("completeness_score", 0) >= 8,
                    },
                )[1]
            )(
                ctx.get_node_output("generate_report", {}).get("content")
                or ctx.get_node_output("add_research", {}).get("content")
            ),
        )
        # 14. Final review using Gemini
        .add_prompt_node(
            "final_review",
            name="Final Review",
            prompt_template="Provide a brief quality assessment of this report:\n\n{report}",
            llm_executor=gemini_executor,
        )
        # 15. END
        .add_end_node("end")
        # Build the graph - Sequential execution to avoid DAG cycles
        .add_edge("start", "define_questions")
        .add_edge("define_questions", "parse_questions")
        # Sequential research path
        .add_edge("parse_questions", "prep_q1")
        .add_edge("prep_q1", "research_q1")
        .add_edge("research_q1", "prep_q2")
        .add_edge("prep_q2", "research_q2")
        .add_edge("research_q2", "prep_q3")
        .add_edge("prep_q3", "research_q3")
        .add_edge("research_q3", "aggregate_findings")
        .add_edge("aggregate_findings", "validate_completeness")
        .add_edge("validate_completeness", "extract_completeness")
        .add_edge("extract_completeness", "store_completeness")
        .add_edge("store_completeness", "completeness_check")
        # Conditional branches
        .set_if_else_branches("completeness_check", "generate_report", "add_research")
        # Merge and finalize
        .add_edge("generate_report", "merge_report")
        .add_edge("add_research", "merge_report")
        .add_edge("merge_report", "final_review")
        .add_edge("final_review", "end")
        .build()
    )

    # Execute with checkpointing for long-running workflow
    engine = WorkflowEngine(enable_checkpointing=True, checkpoint_interval=2)
    result = await engine.execute(workflow)

    logger.info("\n✓ Complex Research Workflow Completed")
    logger.info(f"  Nodes executed: {result['nodes_executed']}")
    logger.info(f"  Completeness score: {result['variables'].get('completeness_score', 'N/A')}")
    logger.info(f"  Research was complete: {result['outputs']['merge_report']['is_complete']}")
    logger.info(f"\n  Final review: {result['outputs']['final_review']['content']}...")

    return result

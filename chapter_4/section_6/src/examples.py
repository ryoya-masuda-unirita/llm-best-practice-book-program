"""Example workflows demonstrating the orchestration engine with Gemini API."""

from src.client import GeminiModel, create_executor
from src.logger import make_logger
from src.workflow import ExecutionContext, WorkflowBuilder, WorkflowEngine

logger = make_logger(__name__)


def parse_topics(ctx: ExecutionContext) -> dict:
    """Parse comma-separated topics from LLM output."""
    content = ctx.get_node_output("generate_topics")["content"]
    topics = [t.strip() for t in content.split(",")][:3]
    return {"topics": topics, "count": len(topics)}


def select_first_topic(ctx: ExecutionContext) -> dict:
    """Select the first topic from parsed topics."""
    topics = ctx.get_node_output("parse_topics")["topics"]
    ctx.set_variable("selected_topic", topics[0])
    return {"selected_topic": topics[0], "remaining": topics[1:]}


def store_content(ctx: ExecutionContext) -> dict:
    """Store generated content in context."""
    content = ctx.get_node_output("generate_content")["content"]
    ctx.set_variable("content", content)
    return {"stored": True}


def extract_score(ctx: ExecutionContext, node_id: str) -> dict:
    """Extract numeric score from LLM output."""
    content = ctx.get_node_output(node_id)["content"]
    digits = "".join(c for c in content[:2] if c.isdigit())
    return {"score": int(digits) if digits else 5}


def check_quality(ctx: ExecutionContext) -> bool:
    """Check if quality score meets threshold."""
    return ctx.get_variable("quality_score", 0) >= 7


def check_completeness(ctx: ExecutionContext) -> bool:
    """Check if research completeness score meets threshold."""
    return ctx.get_variable("completeness_score", 0) >= 8


def merge_content(ctx: ExecutionContext) -> dict:
    """Merge refined or accepted content."""
    refined = ctx.get_node_output("refine_content", {}).get("content")
    accepted = ctx.get_node_output("accept_content", {}).get("final_content")
    content = refined or accepted
    ctx.set_variable("content", content)
    return {"content": content, "was_refined": refined is not None}


def parse_questions(ctx: ExecutionContext) -> dict:
    """Parse numbered questions from LLM output."""
    content = ctx.get_node_output("define_questions")["content"]
    questions = [q.strip() for q in content.split("\n") if q.strip() and any(c.isdigit() for c in q[:3])][:3]
    return {"questions": questions}


def prepare_question(ctx: ExecutionContext, index: int) -> dict:
    """Prepare a specific question for research."""
    questions = ctx.get_node_output("parse_questions")["questions"]
    question = questions[index] if len(questions) > index else f"Question {index + 1} not available"
    ctx.set_variable("question", question)
    return {"question": question}


def aggregate_findings(ctx: ExecutionContext) -> dict:
    """Aggregate research findings from all questions."""
    findings = [
        ctx.get_node_output("research_q1")["content"],
        ctx.get_node_output("research_q2")["content"],
        ctx.get_node_output("research_q3")["content"],
    ]
    ctx.set_variable("findings", "\n\n".join(f"Finding {i + 1}: {f}" for i, f in enumerate(findings)))
    return {"findings": findings, "questions": ctx.get_node_output("parse_questions")["questions"]}


def merge_report(ctx: ExecutionContext) -> dict:
    """Merge report content from either branch."""
    report = ctx.get_node_output("generate_report", {}).get("content")
    if not report:
        report = ctx.get_node_output("add_research", {}).get("content")
    ctx.set_variable("report", report)
    return {"report": report, "is_complete": ctx.get_variable("completeness_score", 0) >= 8}


async def example_gemini_simple():
    """Simple text completion workflow."""
    logger.info("=" * 60)
    logger.info("Example: Gemini Simple")
    logger.info("=" * 60)

    executor = create_executor(model=GeminiModel.GEMINI_2_5_FLASH, system_instruction="You are a helpful assistant.")

    workflow = (
        WorkflowBuilder("gemini_simple", "Simple Completion")
        .add_start_node("start", initial_data={"topic": "artificial intelligence"})
        .add_prompt_node(
            "generate", "Generate", prompt_template="Explain {topic} in 2-3 sentences.", llm_executor=executor
        )
        .add_script_node("display", "Display", func=lambda ctx: ctx.get_node_output("generate"))
        .add_end_node("end")
        .add_edge("start", "generate")
        .add_edge("generate", "display")
        .add_edge("display", "end")
        .build()
    )

    result = await WorkflowEngine(enable_checkpointing=False).execute(workflow)
    logger.info(f"Response: {result['outputs']['generate']['content']}")
    return result


async def example_conditional_workflow():
    """Workflow with conditional branching."""
    logger.info("=" * 60)
    logger.info("Example: Conditional Workflow")
    logger.info("=" * 60)

    def check_age(ctx: ExecutionContext) -> bool:
        return ctx.get_variable("character_age", 0) >= 18

    workflow = (
        WorkflowBuilder("conditional", "Conditional Processing")
        .add_start_node("start", initial_data={"character_age": 25})
        .add_if_else_node("age_check", "Check Age", condition=check_age)
        .add_script_node(
            "adult", "Adult Path", func=lambda ctx: {"category": "adult", "age": ctx.get_variable("character_age")}
        )
        .add_script_node(
            "minor", "Minor Path", func=lambda ctx: {"category": "minor", "age": ctx.get_variable("character_age")}
        )
        .add_end_node("end")
        .add_edge("start", "age_check")
        .set_if_else_branches("age_check", "adult", "minor")
        .add_edge("adult", "end")
        .add_edge("minor", "end")
        .build()
    )

    result = await WorkflowEngine().execute(workflow)
    logger.info(f"Result: {result['outputs']}")
    return result


async def example_loop_workflow():
    """Workflow with loop iteration."""
    logger.info("=" * 60)
    logger.info("Example: Loop Workflow")
    logger.info("=" * 60)

    workflow = (
        WorkflowBuilder("loop", "Batch Processing")
        .add_start_node("start", initial_data={"items": ["a", "b", "c"]})
        .add_loop_node("loop", "Process Items", collection_key="items", max_iterations=10)
        .add_script_node(
            "display", "Display", func=lambda ctx: {"iterations": ctx.get_node_output("loop").get("iterations", 0)}
        )
        .add_end_node("end")
        .add_edge("start", "loop")
        .add_edge("loop", "display")
        .add_edge("display", "end")
        .build()
    )

    result = await WorkflowEngine().execute(workflow)
    logger.info(f"Iterations: {result['outputs']['loop']['iterations']}")
    return result


async def example_checkpoint_recovery():
    """Workflow demonstrating checkpoint/recovery."""
    logger.info("=" * 60)
    logger.info("Example: Checkpoint Recovery")
    logger.info("=" * 60)

    workflow = (
        WorkflowBuilder("checkpoint", "Checkpoint Demo")
        .add_start_node("start", initial_data={"counter": 0})
        .add_script_node("step1", "Step 1", func=lambda ctx: {"step": 1, "counter": ctx.get_variable("counter", 0) + 1})
        .add_script_node("step2", "Step 2", func=lambda ctx: {"step": 2, "counter": ctx.get_variable("counter", 0) + 1})
        .add_script_node("step3", "Step 3", func=lambda ctx: {"step": 3, "counter": ctx.get_variable("counter", 0) + 1})
        .add_end_node("end")
        .add_edge("start", "step1")
        .add_edge("step1", "step2")
        .add_edge("step2", "step3")
        .add_edge("step3", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=True, checkpoint_interval=1)
    result = await engine.execute(workflow)

    checkpoints = engine.list_checkpoints(workflow.workflow_id)
    logger.info(f"Checkpoints created: {len(checkpoints)}")
    return result


async def example_complex_content_pipeline():
    """Multi-stage content generation pipeline (12 nodes)."""
    logger.info("=" * 60)
    logger.info("Example: Content Pipeline")
    logger.info("=" * 60)

    executor = create_executor(
        model=GeminiModel.GEMINI_2_5_FLASH, system_instruction="You are a creative content generator."
    )

    workflow = (
        WorkflowBuilder("content_pipeline", "Content Pipeline")
        .add_start_node("start", initial_data={"domain": "artificial intelligence", "num_topics": 3})
        .add_prompt_node(
            "generate_topics",
            "Generate Topics",
            prompt_template="Generate {num_topics} blog topics about {domain}. Return as comma-separated list.",
            llm_executor=executor,
        )
        .add_script_node("parse_topics", "Parse Topics", func=parse_topics)
        .add_script_node("select_topic", "Select Topic", func=select_first_topic)
        .add_prompt_node(
            "generate_content",
            "Generate Content",
            prompt_template="Write a 3-paragraph blog post about: {selected_topic}",
            llm_executor=executor,
        )
        .add_script_node("store_content", "Store Content", func=store_content)
        .add_prompt_node(
            "analyze_quality",
            "Analyze Quality",
            prompt_template="Rate this content 1-10. Return only the number:\n\n{content}",
            llm_executor=executor,
        )
        .add_script_node(
            "extract_score",
            "Extract Score",
            func=lambda ctx: (
                ctx.set_variable("quality_score", extract_score(ctx, "analyze_quality")["score"]),
                {"score": ctx.get_variable("quality_score")},
            )[1],
        )
        .add_if_else_node("quality_check", "Quality Check", condition=check_quality)
        .add_prompt_node(
            "refine_content",
            "Refine Content",
            prompt_template="Improve this content:\n\n{content}",
            llm_executor=executor,
        )
        .add_script_node(
            "accept_content",
            "Accept Content",
            func=lambda ctx: {"final_content": ctx.get_variable("content"), "status": "accepted"},
        )
        .add_script_node("merge_results", "Merge Results", func=merge_content)
        .add_prompt_node(
            "generate_summary",
            "Generate Summary",
            prompt_template="Summarize in 2 sentences:\n\n{content}",
            llm_executor=executor,
        )
        .add_end_node("end")
        .add_edge("start", "generate_topics")
        .add_edge("generate_topics", "parse_topics")
        .add_edge("parse_topics", "select_topic")
        .add_edge("select_topic", "generate_content")
        .add_edge("generate_content", "store_content")
        .add_edge("store_content", "analyze_quality")
        .add_edge("analyze_quality", "extract_score")
        .add_edge("extract_score", "quality_check")
        .set_if_else_branches("quality_check", "accept_content", "refine_content")
        .add_edge("accept_content", "merge_results")
        .add_edge("refine_content", "merge_results")
        .add_edge("merge_results", "generate_summary")
        .add_edge("generate_summary", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=True, checkpoint_interval=3)
    result = await engine.execute(workflow)

    logger.info(f"Nodes executed: {result['nodes_executed']}")
    logger.info(f"Quality score: {result['variables'].get('quality_score')}")
    logger.info(f"Summary: {result['outputs']['generate_summary']['content'][:200]}...")
    return result


async def example_complex_research_workflow():
    """Automated research and report generation (14 nodes)."""
    logger.info("=" * 60)
    logger.info("Example: Research Workflow")
    logger.info("=" * 60)

    executor = create_executor(
        model=GeminiModel.GEMINI_2_5_FLASH, system_instruction="You are a thorough research assistant."
    )

    workflow = (
        WorkflowBuilder("research", "Research Workflow")
        .add_start_node("start", initial_data={"research_topic": "impact of LLMs on software development"})
        .add_prompt_node(
            "define_questions",
            "Define Questions",
            prompt_template="Generate 3 research questions about: {research_topic}. Format as numbered list.",
            llm_executor=executor,
        )
        .add_script_node("parse_questions", "Parse Questions", func=parse_questions)
        .add_script_node("prep_q1", "Prep Q1", func=lambda ctx: prepare_question(ctx, 0))
        .add_prompt_node("research_q1", "Research Q1", prompt_template="Answer: {question}", llm_executor=executor)
        .add_script_node("prep_q2", "Prep Q2", func=lambda ctx: prepare_question(ctx, 1))
        .add_prompt_node("research_q2", "Research Q2", prompt_template="Answer: {question}", llm_executor=executor)
        .add_script_node("prep_q3", "Prep Q3", func=lambda ctx: prepare_question(ctx, 2))
        .add_prompt_node("research_q3", "Research Q3", prompt_template="Answer: {question}", llm_executor=executor)
        .add_script_node("aggregate", "Aggregate", func=aggregate_findings)
        .add_prompt_node(
            "validate",
            "Validate",
            prompt_template="Rate completeness 1-10. Return only the number:\n\n{findings}",
            llm_executor=executor,
        )
        .add_script_node(
            "extract_completeness",
            "Extract",
            func=lambda ctx: (
                ctx.set_variable("completeness_score", extract_score(ctx, "validate")["score"]),
                {"score": ctx.get_variable("completeness_score")},
            )[1],
        )
        .add_if_else_node("completeness_check", "Check Completeness", condition=check_completeness)
        .add_prompt_node(
            "generate_report",
            "Generate Report",
            prompt_template="Create a research report on '{research_topic}':\n\n{findings}",
            llm_executor=executor,
        )
        .add_prompt_node(
            "add_research",
            "Add Research",
            prompt_template="Provide additional context on: {research_topic}",
            llm_executor=executor,
        )
        .add_script_node("merge_report", "Merge Report", func=merge_report)
        .add_prompt_node(
            "final_review", "Final Review", prompt_template="Quality assessment:\n\n{report}", llm_executor=executor
        )
        .add_end_node("end")
        .add_edge("start", "define_questions")
        .add_edge("define_questions", "parse_questions")
        .add_edge("parse_questions", "prep_q1")
        .add_edge("prep_q1", "research_q1")
        .add_edge("research_q1", "prep_q2")
        .add_edge("prep_q2", "research_q2")
        .add_edge("research_q2", "prep_q3")
        .add_edge("prep_q3", "research_q3")
        .add_edge("research_q3", "aggregate")
        .add_edge("aggregate", "validate")
        .add_edge("validate", "extract_completeness")
        .add_edge("extract_completeness", "completeness_check")
        .set_if_else_branches("completeness_check", "generate_report", "add_research")
        .add_edge("generate_report", "merge_report")
        .add_edge("add_research", "merge_report")
        .add_edge("merge_report", "final_review")
        .add_edge("final_review", "end")
        .build()
    )

    engine = WorkflowEngine(enable_checkpointing=True, checkpoint_interval=2)
    result = await engine.execute(workflow)

    logger.info(f"Nodes executed: {result['nodes_executed']}")
    logger.info(f"Completeness: {result['variables'].get('completeness_score')}")
    logger.info(f"Review: {result['outputs']['final_review']['content'][:200]}...")
    return result

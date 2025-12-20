"""Multi-agent contract review service using LangGraph and Google Gemini.

This module implements a multi-agent system using the orchestrator-worker pattern
with LangGraph subgraphs. An orchestrator agent plans the workflow and dispatches
tasks to specialized worker subgraphs using the Send API.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send
from src.client.llm_client import GeminiModel
from src.config import config as global_config
from src.logger import make_logger
from src.model.multi_agent_model import (
    AgentState,
    AmendmentProposal,
    AmendmentProposerResponse,
    ClauseCategory,
    ClauseClassifierResponse,
    ClauseDiff,
    ContractClause,
    ContractReviewReport,
    DiffCheckerResponse,
    DocumentParserResponse,
    OrchestratorPlan,
    OrchestratorResponse,
    ReportGeneratorResponse,
    RiskAssessment,
    RiskAssessmentResponse,
    WorkerState,
)
from src.prompt.multi_agent_prompt import (
    AMENDMENT_PROPOSER_SYSTEM_PROMPT,
    CLAUSE_CLASSIFIER_SYSTEM_PROMPT,
    DIFF_CHECKER_SYSTEM_PROMPT,
    DOCUMENT_PARSER_SYSTEM_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
    REPORT_GENERATOR_SYSTEM_PROMPT,
    RISK_ASSESSMENT_SYSTEM_PROMPT,
    make_amendment_proposer_prompt,
    make_clause_classifier_prompt,
    make_diff_checker_prompt,
    make_document_parser_prompt,
    make_orchestrator_prompt,
    make_report_generator_prompt,
    make_risk_assessment_prompt,
)

logger = make_logger(__name__)


# =============================================================================
# Agent Node Functions
# =============================================================================


def document_parser_node(state: AgentState, config: RunnableConfig) -> dict:
    """Parse the contract document into structured clauses."""
    logger.info("Document Parser Agent: Starting document parsing...")

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(DocumentParserResponse)

    messages = [
        SystemMessage(content=DOCUMENT_PARSER_SYSTEM_PROMPT),
        HumanMessage(content=make_document_parser_prompt(state["contract_text"])),
    ]

    try:
        response: DocumentParserResponse = model.invoke(messages)
        logger.info("Document Parser Agent: Received response from LLM")
        clauses = [clause.model_dump() for clause in response.clauses]
        logger.info(f"Document Parser Agent: Parsed {len(clauses)} clauses")
        return {"parsed_clauses": clauses}
    except Exception as e:
        logger.error(f"Document Parser Agent: Failed to parse response: {e}")
        return {"parsed_clauses": []}


def clause_classifier_node(state: AgentState, config: RunnableConfig) -> dict:
    """Classify each clause into categories."""
    logger.info("Clause Classifier Agent: Starting classification...")

    if not state["parsed_clauses"]:
        logger.warning("Clause Classifier Agent: No clauses to classify")
        return {"clause_categories": []}

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(ClauseClassifierResponse)

    messages = [
        SystemMessage(content=CLAUSE_CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=make_clause_classifier_prompt(state["parsed_clauses"])),
    ]

    try:
        response: ClauseClassifierResponse = model.invoke(messages)
        logger.info("Clause Classifier Agent: Received response from LLM")
        categories = [category.model_dump() for category in response.categories]
        logger.info(f"Clause Classifier Agent: Classified {len(categories)} clauses")
        return {"clause_categories": categories}
    except Exception as e:
        logger.error(f"Clause Classifier Agent: Failed to parse response: {e}")
        return {"clause_categories": []}


def risk_assessment_node(state: AgentState, config: RunnableConfig) -> dict:
    """Assess risk for each clause."""
    logger.info("Risk Assessment Agent: Starting risk assessment...")

    if not state["parsed_clauses"]:
        logger.warning("Risk Assessment Agent: No clauses to assess")
        return {"risk_assessments": []}

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(RiskAssessmentResponse)

    messages = [
        SystemMessage(content=RISK_ASSESSMENT_SYSTEM_PROMPT),
        HumanMessage(content=make_risk_assessment_prompt(state["parsed_clauses"], state["clause_categories"])),
    ]

    try:
        response: RiskAssessmentResponse = model.invoke(messages)
        logger.info("Risk Assessment Agent: Received response from LLM")
        assessments = [assessment.model_dump() for assessment in response.risk_assessments]
        logger.info(f"Risk Assessment Agent: Assessed {len(assessments)} clauses")
        return {"risk_assessments": assessments}
    except Exception as e:
        logger.error(f"Risk Assessment Agent: Failed to parse response: {e}")
        return {"risk_assessments": []}


def diff_checker_node(state: AgentState, config: RunnableConfig) -> dict:
    """Check differences between contract and standard template."""
    logger.info("Diff Checker Agent: Starting diff check...")

    if not state["parsed_clauses"]:
        logger.warning("Diff Checker Agent: No clauses to compare")
        return {"diffs": []}

    if not state["standard_template"]:
        logger.warning("Diff Checker Agent: No standard template provided")
        return {"diffs": []}

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(DiffCheckerResponse)

    messages = [
        SystemMessage(content=DIFF_CHECKER_SYSTEM_PROMPT),
        HumanMessage(content=make_diff_checker_prompt(state["parsed_clauses"], state["standard_template"])),
    ]

    try:
        response: DiffCheckerResponse = model.invoke(messages)
        logger.info("Diff Checker Agent: Received response from LLM")
        diffs = [diff.model_dump() for diff in response.diffs]
        logger.info(f"Diff Checker Agent: Found {len(diffs)} diff entries")
        return {"diffs": diffs}
    except Exception as e:
        logger.error(f"Diff Checker Agent: Failed to parse response: {e}")
        return {"diffs": []}


def amendment_proposer_node(state: AgentState, config: RunnableConfig) -> dict:
    """Propose amendments for high-risk clauses."""
    logger.info("Amendment Proposer Agent: Starting amendment proposals...")

    if not state["risk_assessments"]:
        logger.warning("Amendment Proposer Agent: No risk assessments available")
        return {"amendments": []}

    high_risk = [r for r in state["risk_assessments"] if r.get("risk_level") == "高"]
    if not high_risk:
        logger.info("Amendment Proposer Agent: No high-risk clauses found")
        return {"amendments": []}

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.3,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(AmendmentProposerResponse)

    messages = [
        SystemMessage(content=AMENDMENT_PROPOSER_SYSTEM_PROMPT),
        HumanMessage(content=make_amendment_proposer_prompt(state["parsed_clauses"], state["risk_assessments"])),
    ]

    try:
        response: AmendmentProposerResponse = model.invoke(messages)
        logger.info("Amendment Proposer Agent: Received response from LLM")
        amendments = [amendment.model_dump() for amendment in response.amendments]
        logger.info(f"Amendment Proposer Agent: Proposed {len(amendments)} amendments")
        return {"amendments": amendments}
    except Exception as e:
        logger.error(f"Amendment Proposer Agent: Failed to parse response: {e}")
        return {"amendments": []}


def report_generator_node(state: AgentState, config: RunnableConfig) -> dict:
    """Generate the final review report."""
    logger.info("Report Generator Agent: Starting report generation...")

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.3,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(ReportGeneratorResponse)

    messages = [
        SystemMessage(content=REPORT_GENERATOR_SYSTEM_PROMPT),
        HumanMessage(
            content=make_report_generator_prompt(
                state["parsed_clauses"],
                state["clause_categories"],
                state["risk_assessments"],
                state["diffs"],
                state["amendments"],
            )
        ),
    ]

    try:
        response: ReportGeneratorResponse = model.invoke(messages)
        logger.info("Report Generator Agent: Received response from LLM")

        clauses = [ContractClause(**c) for c in state["parsed_clauses"] if c]
        categories = [ClauseCategory(**c) for c in state["clause_categories"] if c]
        risk_assessments = [RiskAssessment(**r) for r in state["risk_assessments"] if r]
        diffs = [ClauseDiff(**d) for d in state["diffs"] if d]
        amendments = [AmendmentProposal(**a) for a in state["amendments"] if a]

        report = ContractReviewReport(
            overall_risk_level=response.overall_risk_level,
            overall_risk_score=response.overall_risk_score,
            executive_summary=response.executive_summary,
            key_issues=response.key_issues,
            recommended_actions=response.recommended_actions,
            clauses=clauses,
            categories=categories,
            risk_assessments=risk_assessments,
            diffs=diffs,
            amendments=amendments,
        )

        logger.info("Report Generator Agent: Report generated successfully")
        return {"final_report": report.to_markdown()}

    except Exception as e:
        logger.error(f"Report Generator Agent: Failed to generate report: {e}")
        return {"final_report": None}


# =============================================================================
# Orchestrator Node Functions
# =============================================================================


def orchestrator_node(state: AgentState, config: RunnableConfig) -> dict:
    """Orchestrator agent that plans the contract review workflow."""
    logger.info("Orchestrator Agent: Planning contract review workflow...")

    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_PRO)
    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        api_key=global_config.gemini_api_key,
    )
    model = base_model.with_structured_output(OrchestratorResponse)

    messages = [
        SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        HumanMessage(
            content=make_orchestrator_prompt(
                state["contract_text"],
                state["standard_template"],
            )
        ),
    ]

    try:
        response: OrchestratorResponse = model.invoke(messages)
        logger.info("Orchestrator Agent: Received plan from LLM")
        logger.info(f"Orchestrator Agent: Strategy - {response.plan.strategy}")
        logger.info(f"Orchestrator Agent: Focus areas - {response.plan.focus_areas}")
        logger.info(f"Orchestrator Agent: Planned {len(response.plan.tasks)} tasks")

        return {
            "orchestrator_plan": response.plan,
            "current_phase": "planning_complete",
        }
    except Exception as e:
        logger.error(f"Orchestrator Agent: Failed to create plan: {e}")
        # Return a default plan if orchestrator fails
        default_plan = OrchestratorPlan(
            tasks=[],
            strategy="Default sequential review",
            focus_areas=["All clauses"],
        )
        return {
            "orchestrator_plan": default_plan,
            "current_phase": "planning_failed",
        }


def dispatch_to_document_parser(state: AgentState) -> list[Send]:
    """Dispatch task to document parser worker."""
    logger.info("Dispatching to Document Parser...")
    return [
        Send(
            "document_parser_worker",
            {
                "messages": state["messages"],
                "contract_text": state["contract_text"],
                "standard_template": state["standard_template"],
                "parsed_clauses": state["parsed_clauses"],
                "clause_categories": state["clause_categories"],
                "risk_assessments": state["risk_assessments"],
                "diffs": state["diffs"],
                "amendments": state["amendments"],
                "worker_type": "document_parser",
                "task_description": "Parse contract into clauses",
                "completed_tasks": [],
            },
        )
    ]


def dispatch_to_parallel_analyzers(state: AgentState) -> list[Send]:
    """Dispatch tasks to parallel analyzer workers (classifier, risk, diff)."""
    logger.info("Dispatching to parallel analyzers...")

    base_state = {
        "messages": state["messages"],
        "contract_text": state["contract_text"],
        "standard_template": state["standard_template"],
        "parsed_clauses": state["parsed_clauses"],
        "clause_categories": state["clause_categories"],
        "risk_assessments": state["risk_assessments"],
        "diffs": state["diffs"],
        "amendments": state["amendments"],
        "completed_tasks": [],
    }

    return [
        Send(
            "clause_classifier_worker",
            {
                **base_state,
                "worker_type": "clause_classifier",
                "task_description": "Classify clauses into categories",
            },
        ),
        Send(
            "risk_assessment_worker",
            {
                **base_state,
                "worker_type": "risk_assessment",
                "task_description": "Assess risk for each clause",
            },
        ),
        Send(
            "diff_checker_worker",
            {
                **base_state,
                "worker_type": "diff_checker",
                "task_description": "Check differences with standard template",
            },
        ),
    ]


def collector_node(state: AgentState, config: RunnableConfig) -> dict:
    """Aggregate results from parallel analyzers before passing to next stage."""
    logger.info("Collector: Aggregating results from parallel analyzers...")
    logger.info(f"Collector: Clause categories count: {len(state.get('clause_categories', []))}")
    logger.info(f"Collector: Risk assessments count: {len(state.get('risk_assessments', []))}")
    logger.info(f"Collector: Diffs count: {len(state.get('diffs', []))}")

    return {
        "current_phase": "analysis_complete",
        "completed_tasks": ["collector"],
    }


def synthesizer_node(state: AgentState, config: RunnableConfig) -> dict:
    """Combine all worker outputs into final report."""
    logger.info("Synthesizer: Combining worker outputs into final report...")
    return report_generator_node(state, config)


# =============================================================================
# Worker Node Functions
# =============================================================================


def document_parser_worker(state: WorkerState, config: RunnableConfig) -> dict:
    """Worker wrapper for document parser."""
    logger.info(f"Document Parser Worker: {state['task_description']}")
    result = document_parser_node(state, config)  # type: ignore[arg-type]
    return {
        **result,
        "completed_tasks": ["document_parser"],
    }


def clause_classifier_worker(state: WorkerState, config: RunnableConfig) -> dict:
    """Worker wrapper for clause classifier."""
    logger.info(f"Clause Classifier Worker: {state['task_description']}")
    result = clause_classifier_node(state, config)  # type: ignore[arg-type]
    return {
        **result,
        "completed_tasks": ["clause_classifier"],
    }


def risk_assessment_worker(state: WorkerState, config: RunnableConfig) -> dict:
    """Worker wrapper for risk assessment."""
    logger.info(f"Risk Assessment Worker: {state['task_description']}")
    result = risk_assessment_node(state, config)  # type: ignore[arg-type]
    return {
        **result,
        "completed_tasks": ["risk_assessment"],
    }


def diff_checker_worker(state: WorkerState, config: RunnableConfig) -> dict:
    """Worker wrapper for diff checker."""
    logger.info(f"Diff Checker Worker: {state['task_description']}")
    result = diff_checker_node(state, config)  # type: ignore[arg-type]
    return {
        **result,
        "completed_tasks": ["diff_checker"],
    }


def amendment_proposer_worker(state: AgentState, config: RunnableConfig) -> dict:
    """Worker wrapper for amendment proposer."""
    logger.info("Amendment Proposer Worker: Propose amendments for high-risk clauses")
    result = amendment_proposer_node(state, config)
    return {
        **result,
        "completed_tasks": ["amendment_proposer"],
    }


# =============================================================================
# Subgraph Construction
# =============================================================================


def create_document_parser_subgraph() -> CompiledStateGraph:
    """Create the document parser agent subgraph."""
    logger.info("Creating document parser subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("parse", document_parser_node)
    graph.add_edge(START, "parse")
    graph.add_edge("parse", END)
    return graph.compile()


def create_clause_classifier_subgraph() -> CompiledStateGraph:
    """Create the clause classifier agent subgraph."""
    logger.info("Creating clause classifier subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("classify", clause_classifier_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", END)
    return graph.compile()


def create_risk_assessment_subgraph() -> CompiledStateGraph:
    """Create the risk assessment agent subgraph."""
    logger.info("Creating risk assessment subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("assess", risk_assessment_node)
    graph.add_edge(START, "assess")
    graph.add_edge("assess", END)
    return graph.compile()


def create_diff_checker_subgraph() -> CompiledStateGraph:
    """Create the diff checker agent subgraph."""
    logger.info("Creating diff checker subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("check_diff", diff_checker_node)
    graph.add_edge(START, "check_diff")
    graph.add_edge("check_diff", END)
    return graph.compile()


def create_amendment_proposer_subgraph() -> CompiledStateGraph:
    """Create the amendment proposer agent subgraph."""
    logger.info("Creating amendment proposer subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("propose", amendment_proposer_node)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", END)
    return graph.compile()


def create_report_generator_subgraph() -> CompiledStateGraph:
    """Create the report generator agent subgraph."""
    logger.info("Creating report generator subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("generate", report_generator_node)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", END)
    return graph.compile()


# =============================================================================
# Parent Graph Construction (Simple Subgraph Pattern)
# =============================================================================


def create_simple_subgraph_review_graph() -> CompiledStateGraph:
    """Create a simple multi-agent contract review graph using subgraphs."""
    logger.info("Creating simple subgraph-based contract review graph...")

    document_parser_subgraph = create_document_parser_subgraph()
    clause_classifier_subgraph = create_clause_classifier_subgraph()
    risk_assessment_subgraph = create_risk_assessment_subgraph()
    diff_checker_subgraph = create_diff_checker_subgraph()
    amendment_proposer_subgraph = create_amendment_proposer_subgraph()
    report_generator_subgraph = create_report_generator_subgraph()

    parent_graph = StateGraph(AgentState)
    parent_graph.add_node("document_parser", document_parser_subgraph)
    parent_graph.add_node("clause_classifier", clause_classifier_subgraph)
    parent_graph.add_node("risk_assessment", risk_assessment_subgraph)
    parent_graph.add_node("diff_checker", diff_checker_subgraph)
    parent_graph.add_node("amendment_proposer", amendment_proposer_subgraph)
    parent_graph.add_node("report_generator", report_generator_subgraph)

    parent_graph.add_edge(START, "document_parser")
    parent_graph.add_edge("document_parser", "clause_classifier")
    parent_graph.add_edge("clause_classifier", "risk_assessment")
    parent_graph.add_edge("risk_assessment", "diff_checker")
    parent_graph.add_edge("diff_checker", "amendment_proposer")
    parent_graph.add_edge("amendment_proposer", "report_generator")
    parent_graph.add_edge("report_generator", END)

    logger.info("Simple subgraph review graph created successfully")
    return parent_graph.compile()


# =============================================================================
# Orchestrator-Worker Graph Construction
# =============================================================================


def create_contract_review_graph() -> CompiledStateGraph:
    """Create the orchestrator-worker contract review graph.

    Pipeline: Orchestrator -> Document Parser -> [Parallel Analyzers] -> Collector
           -> Amendment Proposer -> Synthesizer
    """
    logger.info("Creating orchestrator-worker contract review graph...")

    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("document_parser_worker", document_parser_worker)
    graph.add_node("clause_classifier_worker", clause_classifier_worker)
    graph.add_node("risk_assessment_worker", risk_assessment_worker)
    graph.add_node("diff_checker_worker", diff_checker_worker)
    graph.add_node("amendment_proposer_worker", amendment_proposer_worker)
    graph.add_node("collector", collector_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        dispatch_to_document_parser,
        ["document_parser_worker"],
    )
    graph.add_conditional_edges(
        "document_parser_worker",
        dispatch_to_parallel_analyzers,
        ["clause_classifier_worker", "risk_assessment_worker", "diff_checker_worker"],
    )
    graph.add_edge("clause_classifier_worker", "collector")
    graph.add_edge("risk_assessment_worker", "collector")
    graph.add_edge("diff_checker_worker", "collector")
    graph.add_edge("collector", "amendment_proposer_worker")
    graph.add_edge("amendment_proposer_worker", "synthesizer")
    graph.add_edge("synthesizer", END)

    logger.info("Orchestrator-worker graph created successfully")
    return graph.compile()


# =============================================================================
# Main Entry Point
# =============================================================================


async def run_contract_review(
    contract_text: str,
    standard_template: str,
    model: str = GeminiModel.GEMINI_2_5_PRO,
) -> str | None:
    """Run the contract review multi-agent system."""
    logger.info("Starting contract review multi-agent system")
    logger.info(f"Using model: {model}")

    initial_state: AgentState = {
        "messages": [],
        "contract_text": contract_text,
        "standard_template": standard_template,
        "parsed_clauses": [],
        "clause_categories": [],
        "risk_assessments": [],
        "diffs": [],
        "amendments": [],
        "final_report": None,
        "orchestrator_plan": None,
        "completed_tasks": [],
        "current_phase": "initializing",
    }

    graph = create_contract_review_graph()
    config = RunnableConfig(configurable={"model": model})

    try:
        final_state = await graph.ainvoke(initial_state, config)

        report = final_state.get("final_report")
        if report:
            logger.info("Contract review completed successfully")
            return report
        else:
            logger.warning("Contract review completed but no report was generated")
            return None

    except Exception as e:
        logger.error(f"Contract review failed: {str(e)}")
        raise

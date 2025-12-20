"""Multi-agent contract review service using LangGraph and Google Gemini.

This module implements a multi-agent system using LangGraph subgraphs.
Each agent is implemented as a separate subgraph, which are then composed
into a parent graph for the complete contract review pipeline.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
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
    ReportGeneratorResponse,
    RiskAssessment,
    RiskAssessmentResponse,
)
from src.prompt.multi_agent_prompt import (
    AMENDMENT_PROPOSER_SYSTEM_PROMPT,
    CLAUSE_CLASSIFIER_SYSTEM_PROMPT,
    DIFF_CHECKER_SYSTEM_PROMPT,
    DOCUMENT_PARSER_SYSTEM_PROMPT,
    REPORT_GENERATOR_SYSTEM_PROMPT,
    RISK_ASSESSMENT_SYSTEM_PROMPT,
    make_amendment_proposer_prompt,
    make_clause_classifier_prompt,
    make_diff_checker_prompt,
    make_document_parser_prompt,
    make_report_generator_prompt,
    make_risk_assessment_prompt,
)

logger = make_logger(__name__)


# =============================================================================
# Agent Node Functions
# =============================================================================


def document_parser_node(state: AgentState, config: RunnableConfig) -> dict:
    """Parse the contract document into structured clauses.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with parsed clauses
    """
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
    """Classify each clause into categories.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with clause categories
    """
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
    """Assess risk for each clause.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with risk assessments
    """
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
    """Check differences between contract and standard template.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with diffs
    """
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
    """Propose amendments for high-risk clauses.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with amendments
    """
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
    """Generate the final review report.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with final report
    """
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
# Subgraph Construction
# =============================================================================


def create_document_parser_subgraph() -> CompiledStateGraph:
    """Create the document parser agent subgraph.

    Returns:
        Compiled subgraph for document parsing
    """
    logger.info("Creating document parser subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("parse", document_parser_node)
    graph.add_edge(START, "parse")
    graph.add_edge("parse", END)
    return graph.compile()


def create_clause_classifier_subgraph() -> CompiledStateGraph:
    """Create the clause classifier agent subgraph.

    Returns:
        Compiled subgraph for clause classification
    """
    logger.info("Creating clause classifier subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("classify", clause_classifier_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", END)
    return graph.compile()


def create_risk_assessment_subgraph() -> CompiledStateGraph:
    """Create the risk assessment agent subgraph.

    Returns:
        Compiled subgraph for risk assessment
    """
    logger.info("Creating risk assessment subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("assess", risk_assessment_node)
    graph.add_edge(START, "assess")
    graph.add_edge("assess", END)
    return graph.compile()


def create_diff_checker_subgraph() -> CompiledStateGraph:
    """Create the diff checker agent subgraph.

    Returns:
        Compiled subgraph for diff checking
    """
    logger.info("Creating diff checker subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("check_diff", diff_checker_node)
    graph.add_edge(START, "check_diff")
    graph.add_edge("check_diff", END)
    return graph.compile()


def create_amendment_proposer_subgraph() -> CompiledStateGraph:
    """Create the amendment proposer agent subgraph.

    Returns:
        Compiled subgraph for amendment proposals
    """
    logger.info("Creating amendment proposer subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("propose", amendment_proposer_node)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", END)
    return graph.compile()


def create_report_generator_subgraph() -> CompiledStateGraph:
    """Create the report generator agent subgraph.

    Returns:
        Compiled subgraph for report generation
    """
    logger.info("Creating report generator subgraph...")
    graph = StateGraph(AgentState)
    graph.add_node("generate", report_generator_node)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", END)
    return graph.compile()


# =============================================================================
# Parent Graph Construction
# =============================================================================


def create_contract_review_graph() -> CompiledStateGraph:
    """Create the multi-agent contract review graph using subgraphs.

    The graph implements the following pipeline using subgraphs:
    1. Document Parser -> 2. Clause Classifier -> 3. Risk Assessment
                                                -> 4. Diff Checker
    5. Amendment Proposer -> 6. Report Generator

    Each agent is implemented as a separate subgraph, allowing for:
    - Better modularity and separation of concerns
    - Independent testing of each agent
    - Potential for parallel execution where applicable
    - Easier maintenance and extension

    Returns:
        Compiled StateGraph for contract review
    """
    logger.info("Creating contract review multi-agent graph with subgraphs...")

    # Create subgraphs for each agent
    document_parser_subgraph = create_document_parser_subgraph()
    clause_classifier_subgraph = create_clause_classifier_subgraph()
    risk_assessment_subgraph = create_risk_assessment_subgraph()
    diff_checker_subgraph = create_diff_checker_subgraph()
    amendment_proposer_subgraph = create_amendment_proposer_subgraph()
    report_generator_subgraph = create_report_generator_subgraph()

    # Create parent graph and add subgraphs as nodes
    parent_graph = StateGraph(AgentState)

    parent_graph.add_node("document_parser", document_parser_subgraph)
    parent_graph.add_node("clause_classifier", clause_classifier_subgraph)
    parent_graph.add_node("risk_assessment", risk_assessment_subgraph)
    parent_graph.add_node("diff_checker", diff_checker_subgraph)
    parent_graph.add_node("amendment_proposer", amendment_proposer_subgraph)
    parent_graph.add_node("report_generator", report_generator_subgraph)

    # Define the pipeline flow
    parent_graph.add_edge(START, "document_parser")
    parent_graph.add_edge("document_parser", "clause_classifier")
    parent_graph.add_edge("clause_classifier", "risk_assessment")
    parent_graph.add_edge("risk_assessment", "diff_checker")
    parent_graph.add_edge("diff_checker", "amendment_proposer")
    parent_graph.add_edge("amendment_proposer", "report_generator")
    parent_graph.add_edge("report_generator", END)

    logger.info("Contract review graph with subgraphs created successfully")
    return parent_graph.compile()


# =============================================================================
# Main Entry Point
# =============================================================================


async def run_contract_review(
    contract_text: str,
    standard_template: str,
    model: str = GeminiModel.GEMINI_2_5_PRO,
) -> str | None:
    """Run the contract review multi-agent system.

    Args:
        contract_text: The contract document text to review
        standard_template: The standard template to compare against
        model: The Google Gemini model to use

    Returns:
        The contract review report in markdown format, or None if failed
    """
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

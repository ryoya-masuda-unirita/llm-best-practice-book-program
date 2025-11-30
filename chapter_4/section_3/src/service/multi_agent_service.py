"""Multi-agent contract review service using LangGraph and Anthropic."""

import json
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from src.client.llm_client import AnthropicModel
from src.logger import make_logger
from src.model.multi_agent_model import (
    AgentState,
    AmendmentProposal,
    ClauseCategory,
    ClauseDiff,
    ContractClause,
    ContractReviewReport,
    RiskAssessment,
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


def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from LLM response text.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed JSON as dictionary
    """
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text

    return json.loads(json_str)


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

    model_name = config.get("configurable", {}).get("model", AnthropicModel.CLAUDE_SONNET_4_5)
    model = ChatAnthropic(model=model_name, temperature=0)

    messages = [
        SystemMessage(content=DOCUMENT_PARSER_SYSTEM_PROMPT),
        HumanMessage(content=make_document_parser_prompt(state["contract_text"])),
    ]

    response = model.invoke(messages)
    logger.info("Document Parser Agent: Received response from LLM")

    try:
        result = extract_json_from_response(response.content)
        clauses = result.get("clauses", [])
        logger.info(f"Document Parser Agent: Parsed {len(clauses)} clauses")
        return {"parsed_clauses": clauses}
    except (json.JSONDecodeError, KeyError) as e:
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

    model_name = config.get("configurable", {}).get("model", AnthropicModel.CLAUDE_SONNET_4_5)
    model = ChatAnthropic(model=model_name, temperature=0)

    messages = [
        SystemMessage(content=CLAUSE_CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=make_clause_classifier_prompt(state["parsed_clauses"])),
    ]

    response = model.invoke(messages)
    logger.info("Clause Classifier Agent: Received response from LLM")

    try:
        result = extract_json_from_response(response.content)
        categories = result.get("categories", [])
        logger.info(f"Clause Classifier Agent: Classified {len(categories)} clauses")
        return {"clause_categories": categories}
    except (json.JSONDecodeError, KeyError) as e:
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

    model_name = config.get("configurable", {}).get("model", AnthropicModel.CLAUDE_SONNET_4_5)
    model = ChatAnthropic(model=model_name, temperature=0)

    messages = [
        SystemMessage(content=RISK_ASSESSMENT_SYSTEM_PROMPT),
        HumanMessage(
            content=make_risk_assessment_prompt(
                state["parsed_clauses"], state["clause_categories"]
            )
        ),
    ]

    response = model.invoke(messages)
    logger.info("Risk Assessment Agent: Received response from LLM")

    try:
        result = extract_json_from_response(response.content)
        assessments = result.get("risk_assessments", [])
        logger.info(f"Risk Assessment Agent: Assessed {len(assessments)} clauses")
        return {"risk_assessments": assessments}
    except (json.JSONDecodeError, KeyError) as e:
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

    model_name = config.get("configurable", {}).get("model", AnthropicModel.CLAUDE_SONNET_4_5)
    model = ChatAnthropic(model=model_name, temperature=0)

    messages = [
        SystemMessage(content=DIFF_CHECKER_SYSTEM_PROMPT),
        HumanMessage(
            content=make_diff_checker_prompt(
                state["parsed_clauses"], state["standard_template"]
            )
        ),
    ]

    response = model.invoke(messages)
    logger.info("Diff Checker Agent: Received response from LLM")

    try:
        result = extract_json_from_response(response.content)
        diffs = result.get("diffs", [])
        logger.info(f"Diff Checker Agent: Found {len(diffs)} diff entries")
        return {"diffs": diffs}
    except (json.JSONDecodeError, KeyError) as e:
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

    model_name = config.get("configurable", {}).get("model", AnthropicModel.CLAUDE_SONNET_4_5)
    model = ChatAnthropic(model=model_name, temperature=0.3)

    messages = [
        SystemMessage(content=AMENDMENT_PROPOSER_SYSTEM_PROMPT),
        HumanMessage(
            content=make_amendment_proposer_prompt(
                state["parsed_clauses"], state["risk_assessments"]
            )
        ),
    ]

    response = model.invoke(messages)
    logger.info("Amendment Proposer Agent: Received response from LLM")

    try:
        result = extract_json_from_response(response.content)
        amendments = result.get("amendments", [])
        logger.info(f"Amendment Proposer Agent: Proposed {len(amendments)} amendments")
        return {"amendments": amendments}
    except (json.JSONDecodeError, KeyError) as e:
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

    model_name = config.get("configurable", {}).get("model", AnthropicModel.CLAUDE_SONNET_4_5)
    model = ChatAnthropic(model=model_name, temperature=0.3)

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

    response = model.invoke(messages)
    logger.info("Report Generator Agent: Received response from LLM")

    try:
        result = extract_json_from_response(response.content)

        clauses = [
            ContractClause(**c) for c in state["parsed_clauses"] if c
        ]
        categories = [
            ClauseCategory(**c) for c in state["clause_categories"] if c
        ]
        risk_assessments = [
            RiskAssessment(**r) for r in state["risk_assessments"] if r
        ]
        diffs = [ClauseDiff(**d) for d in state["diffs"] if d]
        amendments = [AmendmentProposal(**a) for a in state["amendments"] if a]

        report = ContractReviewReport(
            overall_risk_level=result.get("overall_risk_level", "中"),
            overall_risk_score=float(result.get("overall_risk_score", 5.0)),
            executive_summary=result.get("executive_summary", ""),
            key_issues=result.get("key_issues", []),
            recommended_actions=result.get("recommended_actions", []),
            clauses=clauses,
            categories=categories,
            risk_assessments=risk_assessments,
            diffs=diffs,
            amendments=amendments,
        )

        logger.info("Report Generator Agent: Report generated successfully")
        return {"final_report": report.to_markdown()}

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Report Generator Agent: Failed to generate report: {e}")
        return {"final_report": None}


# =============================================================================
# Graph Construction
# =============================================================================


def create_contract_review_graph() -> StateGraph:
    """Create the multi-agent contract review graph.

    The graph implements the following pipeline:
    1. Document Parser -> 2. Clause Classifier -> 3. Risk Assessment
                                                -> 4. Diff Checker
    5. Amendment Proposer -> 6. Report Generator

    Returns:
        Compiled StateGraph for contract review
    """
    logger.info("Creating contract review multi-agent graph...")

    graph = StateGraph(AgentState)

    graph.add_node("document_parser", document_parser_node)
    graph.add_node("clause_classifier", clause_classifier_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("diff_checker", diff_checker_node)
    graph.add_node("amendment_proposer", amendment_proposer_node)
    graph.add_node("report_generator", report_generator_node)

    graph.set_entry_point("document_parser")

    graph.add_edge("document_parser", "clause_classifier")
    graph.add_edge("clause_classifier", "risk_assessment")
    graph.add_edge("risk_assessment", "diff_checker")
    graph.add_edge("diff_checker", "amendment_proposer")
    graph.add_edge("amendment_proposer", "report_generator")
    graph.add_edge("report_generator", END)

    logger.info("Contract review graph created successfully")
    return graph.compile()


# =============================================================================
# Main Entry Point
# =============================================================================


async def run_contract_review(
    contract_text: str,
    standard_template: str,
    model: str = AnthropicModel.CLAUDE_SONNET_4_5,
) -> str | None:
    """Run the contract review multi-agent system.

    Args:
        contract_text: The contract document text to review
        standard_template: The standard template to compare against
        model: The Anthropic model to use

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

from typing import Literal

from google.genai.types import GenerateContentConfig
from langgraph.graph import END, START, StateGraph

from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.llm_pipeline_model import AnalysisEvaluation, DocumentAnalysis, PipelineState
from src.prompt.llm_pipeline_prompt import (
    make_document_analysis_prompt,
    make_document_analysis_system_instruction,
    make_judge_prompt,
    make_judge_system_instruction,
)

logger = make_logger(__name__)

# Maximum number of retries for improving analysis
MAX_RETRIES = 2


async def read_document_node(state: PipelineState) -> PipelineState:
    """Read the markdown document from the file path."""
    logger.info(f"Reading document from: {state['document_path']}")

    try:
        with open(state["document_path"], "r", encoding="utf-8") as f:
            document_content = f.read()

        logger.info(f"Successfully read document ({len(document_content)} characters)")

        return {
            **state,
            "document_content": document_content,
            "error": None,
        }
    except Exception as e:
        error_msg = f"Failed to read document: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "document_content": "",
            "error": error_msg,
        }


async def analyze_document_openai_node(state: PipelineState) -> PipelineState:
    """Analyze the document using OpenAI API."""
    retry_count = state.get("retry_count", 0)
    logger.info(f"Analyzing document with OpenAI (attempt {retry_count + 1})")

    try:
        model = state.get("model", OpenAIModel.GPT_4O)
        prompt = make_document_analysis_prompt(state["document_content"])

        evaluation_result = state.get("evaluation_result")
        if evaluation_result and retry_count > 0:
            feedback_msg = f"""
前回の分析は {evaluation_result.grade}/5 の評価を受けました。

評価フィードバック:
{evaluation_result.reasoning}

改善が必要な具体的な点:
{chr(10).join(f"- {imp}" for imp in evaluation_result.specific_improvements)}

このフィードバックに基づいて分析を改善してください。
"""
            prompt.append({"role": "user", "content": feedback_msg})
            logger.info("Added judge feedback to prompt for retry")

        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=DocumentAnalysis,
        )

        analysis_result = result.output_parsed
        logger.info("Successfully analyzed document with OpenAI")

        return {
            **state,
            "analysis_result": analysis_result,
            "error": None,
        }
    except Exception as e:
        error_msg = f"Failed to analyze document with OpenAI: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "analysis_result": None,
            "error": error_msg,
        }


async def analyze_document_gemini_node(state: PipelineState) -> PipelineState:
    """Analyze the document using Google Gemini API."""
    retry_count = state.get("retry_count", 0)
    logger.info(f"Analyzing document with Gemini (attempt {retry_count + 1})")

    try:
        model = state.get("model", GeminiModel.GEMINI_2_5_FLASH)
        system_instruction, user_content = make_document_analysis_system_instruction(state["document_content"])

        evaluation_result = state.get("evaluation_result")
        if evaluation_result and retry_count > 0:
            feedback_msg = f"""
前回の分析は {evaluation_result.grade}/5 の評価を受けました。

評価フィードバック:
{evaluation_result.reasoning}

改善が必要な具体的な点:
{chr(10).join(f"- {imp}" for imp in evaluation_result.specific_improvements)}

このフィードバックに基づいて分析を改善してください。
"""
            user_content += "\n\n" + feedback_msg
            logger.info("Added judge feedback to prompt for retry")

        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=user_content,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=DocumentAnalysis,
            ),
        )

        analysis_result = result.parsed
        logger.info("Successfully analyzed document with Gemini")

        return {
            **state,
            "analysis_result": analysis_result,
            "error": None,
        }
    except Exception as e:
        error_msg = f"Failed to analyze document with Gemini: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "analysis_result": None,
            "error": error_msg,
        }


async def judge_analysis_openai_node(state: PipelineState) -> PipelineState:
    """Evaluate the analysis using OpenAI API (LLM-as-a-judge)."""
    logger.info("Evaluating analysis with OpenAI judge")

    try:
        if not state.get("analysis_result"):
            logger.warning("No analysis result to evaluate")
            return state

        model = state.get("model", OpenAIModel.GPT_4O)
        prompt = make_judge_prompt(state["document_content"], state["analysis_result"])

        result = await openai_client.responses.parse(
            model=model,
            input=prompt,
            text_format=AnalysisEvaluation,
        )

        evaluation_result = result.output_parsed
        logger.info(f"Evaluation complete: Grade {evaluation_result.grade}/5")
        logger.info(f"Reasoning: {evaluation_result.reasoning}")

        return {
            **state,
            "evaluation_result": evaluation_result,
            "error": None,
        }
    except Exception as e:
        error_msg = f"Failed to evaluate analysis with OpenAI: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "evaluation_result": None,
            "error": error_msg,
        }


async def judge_analysis_gemini_node(state: PipelineState) -> PipelineState:
    """Evaluate the analysis using Google Gemini API (LLM-as-a-judge)."""
    logger.info("Evaluating analysis with Gemini judge")

    try:
        if not state.get("analysis_result"):
            logger.warning("No analysis result to evaluate")
            return state

        model = state.get("model", GeminiModel.GEMINI_2_5_FLASH)
        system_instruction, user_content = make_judge_system_instruction(
            state["document_content"], state["analysis_result"]
        )

        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=user_content,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=AnalysisEvaluation,
            ),
        )

        evaluation_result = result.parsed
        logger.info(f"Evaluation complete: Grade {evaluation_result.grade}/5")
        logger.info(f"Reasoning: {evaluation_result.reasoning}")

        return {
            **state,
            "evaluation_result": evaluation_result,
            "error": None,
        }
    except Exception as e:
        error_msg = f"Failed to evaluate analysis with Gemini: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "evaluation_result": None,
            "error": error_msg,
        }


def route_to_llm_provider(state: PipelineState) -> Literal["analyze_openai", "analyze_gemini", "end"]:
    """Route to the appropriate LLM provider based on state."""
    if state.get("error"):
        logger.error(f"Error detected, ending pipeline: {state['error']}")
        return "end"

    llm_provider = state.get("llm_provider", LLMProvider.OPENAI)

    if llm_provider == LLMProvider.OPENAI:
        logger.info("Routing to OpenAI")
        return "analyze_openai"
    elif llm_provider == LLMProvider.GEMINI:
        logger.info("Routing to Gemini")
        return "analyze_gemini"
    else:
        logger.error(f"Unknown LLM provider: {llm_provider}")
        return "end"


def route_to_judge(state: PipelineState) -> Literal["judge_openai", "judge_gemini", "end"]:
    """Route to the appropriate LLM judge based on state."""
    if state.get("error"):
        logger.error(f"Error detected, ending pipeline: {state['error']}")
        return "end"

    if not state.get("analysis_result"):
        logger.error("No analysis result to judge, ending pipeline")
        return "end"

    llm_provider = state.get("llm_provider", LLMProvider.OPENAI)

    if llm_provider == LLMProvider.OPENAI:
        logger.info("Routing to OpenAI judge")
        return "judge_openai"
    elif llm_provider == LLMProvider.GEMINI:
        logger.info("Routing to Gemini judge")
        return "judge_gemini"
    else:
        logger.error(f"Unknown LLM provider: {llm_provider}")
        return "end"


def route_after_judge(state: PipelineState) -> Literal["analyze_openai", "analyze_gemini", "end"]:
    """Decide whether to retry analysis or end pipeline based on evaluation."""
    if state.get("error"):
        logger.error(f"Error detected, ending pipeline: {state['error']}")
        return "end"

    evaluation_result = state.get("evaluation_result")
    if not evaluation_result:
        logger.warning("No evaluation result, ending pipeline")
        return "end"

    retry_count = state.get("retry_count", 0)

    if evaluation_result.is_acceptable():
        logger.info(f"Analysis accepted with grade {evaluation_result.grade}/5")
        return "end"

    if retry_count >= MAX_RETRIES:
        logger.warning(
            f"Max retries ({MAX_RETRIES}) reached. Accepting analysis with grade {evaluation_result.grade}/5"
        )
        return "end"

    logger.info(
        f"Analysis grade {evaluation_result.grade}/5 is below threshold. "
        f"Retrying (attempt {retry_count + 2}/{MAX_RETRIES + 1})"
    )

    state["retry_count"] = retry_count + 1

    llm_provider = state.get("llm_provider", LLMProvider.OPENAI)
    if llm_provider == LLMProvider.OPENAI:
        return "analyze_openai"
    elif llm_provider == LLMProvider.GEMINI:
        return "analyze_gemini"
    else:
        return "end"


def create_document_analysis_graph() -> StateGraph:
    """Create the document analysis LangGraph pipeline with LLM-as-a-judge."""
    graph = StateGraph(PipelineState)

    graph.add_node("read_document", read_document_node)
    graph.add_node("analyze_openai", analyze_document_openai_node)
    graph.add_node("analyze_gemini", analyze_document_gemini_node)
    graph.add_node("judge_openai", judge_analysis_openai_node)
    graph.add_node("judge_gemini", judge_analysis_gemini_node)

    graph.add_edge(START, "read_document")

    graph.add_conditional_edges(
        "read_document",
        route_to_llm_provider,
        {
            "analyze_openai": "analyze_openai",
            "analyze_gemini": "analyze_gemini",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "analyze_openai",
        route_to_judge,
        {
            "judge_openai": "judge_openai",
            "judge_gemini": "judge_gemini",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "analyze_gemini",
        route_to_judge,
        {
            "judge_openai": "judge_openai",
            "judge_gemini": "judge_gemini",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "judge_openai",
        route_after_judge,
        {
            "analyze_openai": "analyze_openai",
            "analyze_gemini": "analyze_gemini",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "judge_gemini",
        route_after_judge,
        {
            "analyze_openai": "analyze_openai",
            "analyze_gemini": "analyze_gemini",
            "end": END,
        },
    )

    return graph.compile()


async def run_document_analysis_pipeline(
    document_path: str,
    llm_provider: LLMProvider,
    model: str,
) -> DocumentAnalysis | None:
    """Run the document analysis pipeline."""
    logger.info(f"Starting document analysis pipeline for: {document_path}")
    logger.info(f"LLM Provider: {llm_provider}, Model: {model}")

    initial_state: PipelineState = {
        "document_path": document_path,
        "document_content": "",
        "analysis_result": None,
        "evaluation_result": None,
        "retry_count": 0,
        "error": None,
        "llm_provider": llm_provider,  # type: ignore
        "model": model,  # type: ignore
    }

    graph = create_document_analysis_graph()
    final_state = await graph.ainvoke(initial_state)

    if final_state.get("error"):
        logger.error(f"Pipeline failed: {final_state['error']}")
        return None

    analysis_result = final_state.get("analysis_result")
    evaluation_result = final_state.get("evaluation_result")
    retry_count = final_state.get("retry_count", 0)

    if analysis_result:
        logger.info("Pipeline completed successfully")
        logger.info(f"Total analysis attempts: {retry_count + 1}")

        if evaluation_result:
            logger.info(f"Final evaluation grade: {evaluation_result.grade}/5")
            logger.info(f"Evaluation reasoning: {evaluation_result.reasoning}")
            if evaluation_result.specific_improvements:
                logger.info(f"Improvement suggestions: {', '.join(evaluation_result.specific_improvements)}")
    else:
        logger.warning("Pipeline completed but no analysis result was generated")

    return analysis_result

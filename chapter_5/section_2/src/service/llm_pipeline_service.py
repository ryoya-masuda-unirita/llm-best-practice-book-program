import json
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from src.client.llm_client import GeminiModel
from src.logger import make_logger
from src.model.llm_pipeline_model import (
    CHARACTER_TEMPLATES,
    STYLE_GUIDES,
    THEME_ELEMENTS,
    TONE_ELEMENTS,
    AgentState,
)
from src.prompt.llm_pipeline_prompt import (
    CHARACTER_RELATIONSHIP_TIPS,
    PROSE_GENERAL_SUGGESTIONS,
    THEME_WRITING_TIPS_DEFAULT,
    THEME_WRITING_TIPS_MATCHED,
    make_novel_writer_system_prompt,
    make_pacing_tips,
    make_user_request_prompt,
)

logger = make_logger(__name__)

# Maximum number of agent iterations to prevent infinite loops
MAX_ITERATIONS = 15


# =============================================================================
# Tool Definitions for the Deep Think Novel Agent
# =============================================================================


@tool
def analyze_theme(theme: str) -> str:
    """
    Deeply analyze a theme to extract literary elements, symbolism, and emotional undertones.

    Args:
        theme: The theme or concept to analyze (e.g., "loneliness", "redemption", "forbidden love")

    Returns:
        JSON string containing theme analysis with literary elements
    """
    logger.info(f"Tool: analyze_theme called with theme='{theme}'")

    # Find matching theme or provide general analysis
    theme_lower = theme.lower()
    matched_theme = None
    for key in THEME_ELEMENTS:
        if key in theme_lower or theme_lower in key:
            matched_theme = key
            break

    if matched_theme:
        result = {
            "theme": theme,
            "analysis": THEME_ELEMENTS[matched_theme],
            "writing_tips": THEME_WRITING_TIPS_MATCHED,
        }
    else:
        result = {
            "theme": theme,
            "analysis": {
                "emotional_core": f"The essence of {theme} and its human significance",
                "symbols": ["Objects that represent the theme", "Natural phenomena", "Everyday items with meaning"],
                "metaphors": ["Comparisons that illuminate the theme"],
                "conflicts": ["Internal struggles", "External challenges"],
                "settings": ["Places that enhance the theme's impact"],
                "archetypes": ["Characters who embody aspects of the theme"],
            },
            "writing_tips": THEME_WRITING_TIPS_DEFAULT,
        }

    return json.dumps(result, ensure_ascii=False)


@tool
def generate_characters(story_context: str, num_characters: int = 3) -> str:
    """
    Generate character profiles based on the story's needs.

    Args:
        story_context: Brief description of the story's theme and setting
        num_characters: Number of characters to generate (default 3)

    Returns:
        JSON string containing character profiles
    """
    logger.info(f"Tool: generate_characters called with context='{story_context}', num={num_characters}")

    characters = []
    for i in range(min(num_characters, len(CHARACTER_TEMPLATES))):
        template = CHARACTER_TEMPLATES[i]
        characters.append(
            {
                "role": template["role"],
                "suggested_traits": template["traits"],
                "development_framework": template["template"],
                "note": f"Adapt this {template['role']} to fit: {story_context[:100]}...",
            }
        )

    result = {
        "story_context": story_context,
        "characters": characters,
        "relationship_dynamics": CHARACTER_RELATIONSHIP_TIPS,
    }

    return json.dumps(result, ensure_ascii=False)


@tool
def create_plot_structure(premise: str, tone: str = "dramatic") -> str:
    """
    Create a structured plot outline with rising action, climax, and resolution.

    Args:
        premise: The basic premise or concept of the story
        tone: The desired tone (dramatic, hopeful, bittersweet, dark, uplifting)

    Returns:
        JSON string containing plot structure
    """
    logger.info(f"Tool: create_plot_structure called with premise='{premise}', tone='{tone}'")

    tone_guide = TONE_ELEMENTS.get(tone, TONE_ELEMENTS["dramatic"])

    result = {
        "premise": premise,
        "tone": tone,
        "structure": {
            "act_1_setup": {
                "hook": "First line/paragraph that grabs attention",
                "world": "Establish setting and normal world",
                "character": "Introduce protagonist and their want/need",
                "inciting_incident": "Event that disrupts equilibrium",
                "guidance": tone_guide["opening"],
            },
            "act_2_confrontation": {
                "rising_action_1": "First major obstacle or complication",
                "rising_action_2": "Stakes increase, relationships tested",
                "midpoint": "A revelation or shift in direction",
                "rising_action_3": "Darkest moment before climax",
                "guidance": tone_guide["escalation"],
            },
            "act_3_resolution": {
                "climax": "The decisive moment of confrontation",
                "climax_guidance": tone_guide["climax"],
                "falling_action": "Immediate aftermath of climax",
                "resolution": "New equilibrium established",
                "resolution_guidance": tone_guide["resolution"],
                "final_image": "Last impression that resonates",
            },
        },
        "pacing_tips": make_pacing_tips(tone, tone_guide["climax"]),
    }

    return json.dumps(result, ensure_ascii=False)


@tool
def refine_prose(text: str, style: str = "literary") -> str:
    """
    Refine and polish prose for better readability and impact.

    Args:
        text: The text to refine
        style: Desired style (literary, minimalist, lyrical, contemporary)

    Returns:
        JSON string containing prose refinement suggestions
    """
    logger.info(f"Tool: refine_prose called with style='{style}'")

    guide = STYLE_GUIDES.get(style, STYLE_GUIDES["literary"])

    # Analyze the provided text
    word_count = len(text.split())
    sentences = text.count(".") + text.count("!") + text.count("?")
    avg_sentence_length = word_count / max(sentences, 1)

    result = {
        "original_text_preview": text[:200] + "..." if len(text) > 200 else text,
        "analysis": {
            "word_count": word_count,
            "sentence_count": sentences,
            "avg_sentence_length": round(avg_sentence_length, 1),
        },
        "style_guide": guide,
        "general_suggestions": PROSE_GENERAL_SUGGESTIONS,
    }

    return json.dumps(result, ensure_ascii=False)


# =============================================================================
# Deep Think ReAct Agent Implementation
# =============================================================================

# Define available tools
tools = [analyze_theme, generate_characters, create_plot_structure, refine_prose]
tools_by_name = {tool.name: tool for tool in tools}


def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """
    Call the Gemini model with deep thinking enabled.

    This is the "Thought" and "Action" part of the ReAct loop.
    The model uses extended thinking to reason deeply before deciding on actions.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with model response
    """
    logger.info("Agent: Calling Gemini model with deep thinking...")

    # Get model from config or use default
    model_name = config.get("configurable", {}).get("model", GeminiModel.GEMINI_2_5_FLASH)

    # Initialize Gemini model with thinking enabled
    # thinking_budget: number of tokens for reasoning (0-24576)
    model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=1.0,  # Required for thinking mode
        thinking_budget=10000,
        include_thoughts=True,
    )
    model_with_tools = model.bind_tools(tools)

    # Build messages
    system_message = SystemMessage(content=make_novel_writer_system_prompt())
    messages = [system_message] + list(state["messages"])

    # Call the model
    response = model_with_tools.invoke(messages, config)
    logger.info(f"Agent: Model response received (has_tool_calls={bool(response.tool_calls)})")

    # Update thinking depth counter
    new_depth = state.get("thinking_depth", 0) + 1

    return {"messages": [response], "thinking_depth": new_depth}


def tool_node(state: AgentState) -> dict:
    """
    Execute the tools called by the model.

    This is the "Observation" part of the ReAct loop.
    The tool results are added to the message history for the model to observe.

    Args:
        state: Current agent state

    Returns:
        Updated state with tool results
    """
    logger.info("Agent: Executing tool calls...")

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {"messages": []}

    outputs = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        logger.info(f"Agent: Executing tool '{tool_name}' with args: {tool_args}")

        if tool_name in tools_by_name:
            tool_result = tools_by_name[tool_name].invoke(tool_args)
            logger.info(f"Agent: Tool '{tool_name}' returned result")
        else:
            logger.warning(f"Agent: Unknown tool '{tool_name}'")
            tool_result = f"Error: Unknown tool '{tool_name}'"

        outputs.append(
            ToolMessage(
                content=tool_result,
                name=tool_name,
                tool_call_id=tool_call["id"],
            )
        )

    return {"messages": outputs}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Determine whether to continue the ReAct loop or end.

    If the last message has tool calls, continue to execute tools.
    Otherwise, end the loop (the model has provided the final novel).

    Args:
        state: Current agent state

    Returns:
        "tools" to continue or "end" to finish
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check iteration count to prevent infinite loops
    tool_message_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    if tool_message_count >= MAX_ITERATIONS:
        logger.warning(f"Agent: Max iterations ({MAX_ITERATIONS}) reached, ending loop")
        return "end"

    # If the last message has tool calls, continue to tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.info("Agent: Tool calls detected, continuing to tool execution")
        return "tools"

    logger.info("Agent: No tool calls, ending loop with final novel")
    return "end"


def extract_final_novel(state: AgentState) -> dict:
    """
    Extract the final novel from the agent's response.

    When include_thoughts=True, message.content is a list containing both
    thinking content and the actual response.

    Args:
        state: Current agent state

    Returns:
        Updated state with final novel
    """
    messages = state["messages"]

    # Find the last AI message without tool calls (the final novel)
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            content = message.content
            # Handle case where content is a list (when include_thoughts=True)
            if isinstance(content, list):
                # Extract only the text parts, skip thinking parts
                text_parts = []
                for part in content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                return {"final_novel": "\n".join(text_parts)}
            return {"final_novel": content}

    return {"final_novel": None}


def create_novel_writer_graph() -> StateGraph:
    """
    Create the Deep Think ReAct agent graph for novel generation.

    The graph follows the ReAct pattern with deep thinking:
    1. Agent (Deep Think + Action): LLM reasons deeply and decides on actions
    2. Tools (Observation): Execute tools and observe results
    3. Loop back to Agent until the novel is complete

    Returns:
        Compiled StateGraph for the novel writer agent
    """
    logger.info("Creating deep think novel writer agent graph...")

    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", extract_final_novel)

    # Set entry point
    graph.set_entry_point("agent")

    # Add conditional edges from agent
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": "finalize",
        },
    )

    # Tools always go back to agent
    graph.add_edge("tools", "agent")

    # Finalize goes to END
    graph.add_edge("finalize", END)

    logger.info("Novel writer graph created successfully")
    return graph.compile()


async def run_novel_writer(
    user_request: str,
    model: str = GeminiModel.GEMINI_2_5_FLASH,
) -> str | None:
    """
    Run the deep think novel writer agent with a user's request.

    Args:
        user_request: The user's novel request (e.g., "Write a story about finding hope in darkness")
        model: The Gemini model to use

    Returns:
        The generated novel or None if failed
    """
    logger.info(f"Starting novel writer for request: {user_request}")
    logger.info(f"Using model: {model}")

    # Create initial state
    initial_state: AgentState = {
        "messages": [("user", make_user_request_prompt(user_request))],
        "user_request": user_request,
        "theme": None,
        "outline": None,
        "draft": None,
        "final_novel": None,
        "thinking_depth": 0,
    }

    # Create and run the graph
    graph = create_novel_writer_graph()
    config = RunnableConfig(configurable={"model": model})

    try:
        final_state = await graph.ainvoke(initial_state, config)

        novel = final_state.get("final_novel")
        thinking_depth = final_state.get("thinking_depth", 0)
        if novel:
            logger.info(f"Novel writer completed successfully (thinking_depth={thinking_depth})")
            return novel
        else:
            logger.warning("Novel writer completed but no novel was generated")
            return None

    except Exception as e:
        logger.error(f"Novel writer failed: {str(e)}")
        raise

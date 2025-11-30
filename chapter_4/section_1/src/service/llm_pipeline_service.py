import json
from datetime import datetime
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.client.llm_client import OpenAIModel
from src.logger import make_logger
from src.model.llm_pipeline_model import (
    BASE_COOKING_TIMES,
    DEFAULT_COOKING_TIMES,
    DEFAULT_NUTRITION,
    MAX_ITERATIONS,
    MONTH_TO_SEASON,
    NUTRITION_DATABASE,
    RECIPES_DATABASE,
    SEASON_TO_JAPANESE,
    SEASONAL_INGREDIENTS,
    SKILL_LEVEL_MULTIPLIERS,
    AgentState,
    DinnerRecommendation,
)
from src.prompt.llm_pipeline_prompt import (
    make_dinner_advisor_system_prompt,
    make_user_request_prompt,
)

logger = make_logger(__name__)


# =============================================================================
# Tool Definitions for the ReAct Agent
# =============================================================================


@tool
def search_recipes(query: str, cuisine_type: str | None = None) -> str:
    """
    Search for recipes based on keywords and optional cuisine type.

    Args:
        query: Search keywords (e.g., "chicken", "pasta", "quick dinner")
        cuisine_type: Optional cuisine type (e.g., "Japanese", "Italian", "Chinese")

    Returns:
        JSON string containing matching recipes
    """
    logger.info(f"Tool: search_recipes called with query='{query}', cuisine_type='{cuisine_type}'")

    query_lower = query.lower()

    # Determine which cuisines to search
    if cuisine_type and cuisine_type in RECIPES_DATABASE:
        cuisines_to_search = [cuisine_type]
    else:
        cuisines_to_search = list(RECIPES_DATABASE.keys())

    # Search for matching recipes
    results = []
    for cuisine in cuisines_to_search:
        for recipe in RECIPES_DATABASE.get(cuisine, []):
            name_matches = query_lower in recipe["name"].lower()
            ingredient_matches = any(query_lower in ing.lower() for ing in recipe["ingredients"])
            cuisine_matches = query_lower in cuisine.lower()

            if name_matches or ingredient_matches or cuisine_matches:
                results.append({**recipe, "cuisine": cuisine})

    # Fallback: return default recipes if no matches found
    if not results:
        if cuisine_type and cuisine_type in RECIPES_DATABASE:
            results = [{**r, "cuisine": cuisine_type} for r in RECIPES_DATABASE[cuisine_type][:3]]
        else:
            results = [{**r, "cuisine": "Quick"} for r in RECIPES_DATABASE["Quick"]]

    return json.dumps(results[:5], ensure_ascii=False)


@tool
def check_nutrition(dish_name: str) -> str:
    """
    Check the nutritional information of a dish.

    Args:
        dish_name: Name of the dish to check

    Returns:
        JSON string containing nutritional information
    """
    logger.info(f"Tool: check_nutrition called with dish_name='{dish_name}'")

    if dish_name in NUTRITION_DATABASE:
        result = {
            "dish": dish_name,
            "nutrition": NUTRITION_DATABASE[dish_name],
            "unit": "per serving",
        }
    else:
        result = {
            "dish": dish_name,
            "nutrition": DEFAULT_NUTRITION,
            "note": "推定値（データベースにない料理のため）",
            "unit": "per serving",
        }

    return json.dumps(result, ensure_ascii=False)


@tool
def get_seasonal_ingredients(season: str | None = None) -> str:
    """
    Get a list of ingredients that are currently in season.

    Args:
        season: Optional season name (spring, summer, fall, winter).
                If not provided, uses current season.

    Returns:
        JSON string containing seasonal ingredients
    """
    logger.info(f"Tool: get_seasonal_ingredients called with season='{season}'")

    # Determine current season if not provided
    if not season:
        month = datetime.now().month
        season = MONTH_TO_SEASON[month]

    result = {
        "season": season,
        "season_japanese": SEASON_TO_JAPANESE.get(season, season),
        "ingredients": SEASONAL_INGREDIENTS.get(season, SEASONAL_INGREDIENTS["fall"]),
    }

    return json.dumps(result, ensure_ascii=False)


@tool
def estimate_cooking_time(dish_name: str, skill_level: str = "intermediate") -> str:
    """
    Estimate the cooking time for a specific dish.

    Args:
        dish_name: Name of the dish
        skill_level: Cooking skill level (beginner, intermediate, advanced)

    Returns:
        JSON string containing time estimates
    """
    logger.info(f"Tool: estimate_cooking_time called with dish_name='{dish_name}', skill_level='{skill_level}'")

    multiplier = SKILL_LEVEL_MULTIPLIERS.get(skill_level, 1.0)

    # Get base times or use defaults
    times = BASE_COOKING_TIMES.get(dish_name, DEFAULT_COOKING_TIMES)
    prep_time = int(times["prep"] * multiplier)
    cook_time = times["cook"]

    result = {
        "dish": dish_name,
        "skill_level": skill_level,
        "prep_time_minutes": prep_time,
        "cooking_time_minutes": cook_time,
        "total_time_minutes": prep_time + cook_time,
    }

    return json.dumps(result, ensure_ascii=False)


# =============================================================================
# ReAct Agent Implementation
# =============================================================================

# Define available tools (excluding DinnerRecommendation which is the response tool)
tools = [search_recipes, check_nutrition, get_seasonal_ingredients, estimate_cooking_time]
tools_by_name = {tool.name: tool for tool in tools}

# Response tool name for structured output
RESPONSE_TOOL_NAME = "DinnerRecommendation"

# All tools including the response tool for binding to model
all_tools = tools + [DinnerRecommendation]


def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """
    Call the LLM model with the current state.

    This is the "Thought" and "Action" part of the ReAct loop.
    The model decides whether to use a tool or provide a final answer using structured output.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with model response
    """
    logger.info("Agent: Calling model for reasoning...")

    # Get model from config or use default
    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_5_MINI)

    # Initialize the model with all tools (including DinnerRecommendation for structured output)
    # Use tool_choice="any" to force the model to always use a tool
    model = ChatOpenAI(model=model_name)
    model_with_tools = model.bind_tools(all_tools, tool_choice="any")

    # Build messages
    system_message = SystemMessage(content=make_dinner_advisor_system_prompt())
    messages = [system_message] + list(state["messages"])

    # Call the model
    response = model_with_tools.invoke(messages, config)
    logger.info(f"Agent: Model response received (has_tool_calls={bool(response.tool_calls)})")

    return {"messages": [response]}


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


def should_continue(state: AgentState) -> Literal["tools", "respond"]:
    """
    Determine whether to continue the ReAct loop or respond with structured output.

    If the last message calls the DinnerRecommendation tool, go to respond node.
    If the last message has other tool calls, continue to execute tools.

    Args:
        state: Current agent state

    Returns:
        "tools" to continue with tool execution or "respond" to return structured output
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check iteration count to prevent infinite loops
    tool_message_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    if tool_message_count >= MAX_ITERATIONS:
        logger.warning(f"Agent: Max iterations ({MAX_ITERATIONS}) reached, forcing response")
        return "respond"

    # Check if the model is calling the response tool (DinnerRecommendation)
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == RESPONSE_TOOL_NAME:
                logger.info("Agent: DinnerRecommendation tool called, proceeding to respond")
                return "respond"

        logger.info("Agent: Tool calls detected, continuing to tool execution")
        return "tools"

    # Fallback: if no tool calls (shouldn't happen with tool_choice="any"), go to respond
    logger.warning("Agent: No tool calls detected, proceeding to respond")
    return "respond"


def respond(state: AgentState) -> dict:
    """
    Extract the structured dinner recommendation from the agent's response.

    This function finds the DinnerRecommendation tool call and constructs
    a validated Pydantic model from its arguments.

    Args:
        state: Current agent state

    Returns:
        Updated state with final_response as DinnerRecommendation
    """
    messages = state["messages"]

    # Find the last AI message with DinnerRecommendation tool call
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call["name"] == RESPONSE_TOOL_NAME:
                    logger.info("Agent: Extracting structured DinnerRecommendation from tool call")
                    try:
                        recommendation = DinnerRecommendation(**tool_call["args"])
                        logger.info(f"Agent: Successfully created DinnerRecommendation: {recommendation.menu_name}")
                        return {"final_response": recommendation}
                    except Exception as e:
                        logger.error(f"Agent: Failed to parse DinnerRecommendation: {e}")
                        return {"final_response": None}

    logger.warning("Agent: No DinnerRecommendation tool call found")
    return {"final_response": None}


def create_dinner_advisor_graph() -> StateGraph:
    """
    Create the ReAct agent graph for dinner menu advice with structured output.

    The graph follows the ReAct pattern with structured output:
    1. Agent (Thought + Action): LLM reasons about the request and decides on actions
    2. Tools (Observation): Execute tools and observe results
    3. Loop back to Agent until ready to respond
    4. Respond: Extract structured DinnerRecommendation from the final tool call

    Returns:
        Compiled StateGraph for the dinner advisor agent
    """
    logger.info("Creating dinner advisor ReAct agent graph with structured output...")

    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("respond", respond)

    # Set entry point
    graph.set_entry_point("agent")

    # Add conditional edges from agent
    # The agent either continues with tools or responds with structured output
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "respond": "respond",
        },
    )

    # Tools always go back to agent
    graph.add_edge("tools", "agent")

    # Respond goes to END
    graph.add_edge("respond", END)

    logger.info("Dinner advisor graph created successfully")
    return graph.compile()


async def run_dinner_advisor(
    user_request: str,
    model: str = OpenAIModel.GPT_5_MINI,
) -> DinnerRecommendation | None:
    """
    Run the dinner advisor agent with a user's request.

    Args:
        user_request: The user's dinner request (e.g., "今日は疲れているので簡単な料理がいい")
        model: The OpenAI model to use

    Returns:
        The agent's structured DinnerRecommendation or None if failed
    """
    logger.info(f"Starting dinner advisor for request: {user_request}")
    logger.info(f"Using model: {model}")

    # Create initial state
    initial_state: AgentState = {
        "messages": [("user", make_user_request_prompt(user_request))],
        "user_request": user_request,
        "final_response": None,
    }

    # Create and run the graph
    graph = create_dinner_advisor_graph()
    config = RunnableConfig(configurable={"model": model})

    try:
        final_state = await graph.ainvoke(initial_state, config)

        recommendation = final_state.get("final_response")
        if recommendation:
            logger.info(f"Dinner advisor completed successfully: {recommendation.menu_name}")
            return recommendation
        else:
            logger.warning("Dinner advisor completed but no recommendation was generated")
            return None

    except Exception as e:
        logger.error(f"Dinner advisor failed: {str(e)}")
        raise

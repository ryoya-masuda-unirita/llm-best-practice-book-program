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
from src.model.model import (
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
from src.prompt.prompt import (
    make_dinner_advisor_system_prompt,
    make_user_request_prompt,
)

logger = make_logger(__name__)


@tool
def search_recipes(query: str, cuisine_type: str | None = None) -> str:
    """Search for recipes based on keywords and optional cuisine type."""
    logger.info(f"Tool: search_recipes called with query='{query}', cuisine_type='{cuisine_type}'")

    query_lower = query.lower()

    if cuisine_type and cuisine_type in RECIPES_DATABASE:
        cuisines_to_search = [cuisine_type]
    else:
        cuisines_to_search = list(RECIPES_DATABASE.keys())

    results = []
    for cuisine in cuisines_to_search:
        for recipe in RECIPES_DATABASE.get(cuisine, []):
            name_matches = query_lower in recipe["name"].lower()
            ingredient_matches = any(query_lower in ing.lower() for ing in recipe["ingredients"])
            cuisine_matches = query_lower in cuisine.lower()

            if name_matches or ingredient_matches or cuisine_matches:
                results.append({**recipe, "cuisine": cuisine})

    if not results:
        if cuisine_type and cuisine_type in RECIPES_DATABASE:
            results = [{**r, "cuisine": cuisine_type} for r in RECIPES_DATABASE[cuisine_type][:3]]
        else:
            results = [{**r, "cuisine": "Quick"} for r in RECIPES_DATABASE["Quick"]]

    return json.dumps(results[:5], ensure_ascii=False)


@tool
def check_nutrition(dish_name: str) -> str:
    """Check the nutritional information of a dish."""
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
    """Get a list of ingredients that are currently in season."""
    logger.info(f"Tool: get_seasonal_ingredients called with season='{season}'")

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
    """Estimate the cooking time for a specific dish."""
    logger.info(f"Tool: estimate_cooking_time called with dish_name='{dish_name}', skill_level='{skill_level}'")

    multiplier = SKILL_LEVEL_MULTIPLIERS.get(skill_level, 1.0)

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


tools = [search_recipes, check_nutrition, get_seasonal_ingredients, estimate_cooking_time]
tools_by_name = {tool.name: tool for tool in tools}

RESPONSE_TOOL_NAME = "DinnerRecommendation"

all_tools = tools + [DinnerRecommendation]


def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """Call the LLM model with the current state (Thought + Action part of ReAct loop)."""
    logger.info("Agent: Calling model for reasoning...")

    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_5_MINI)

    model = ChatOpenAI(model=model_name)
    model_with_tools = model.bind_tools(all_tools, tool_choice="any")

    system_message = SystemMessage(content=make_dinner_advisor_system_prompt())
    messages = [system_message] + list(state["messages"])

    response = model_with_tools.invoke(messages, config)
    logger.info(f"Agent: Model response received (has_tool_calls={bool(response.tool_calls)})")

    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    """Execute the tools called by the model (Observation part of ReAct loop)."""
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
    """Determine whether to continue the ReAct loop or respond with structured output."""
    messages = state["messages"]
    last_message = messages[-1]

    tool_message_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    if tool_message_count >= MAX_ITERATIONS:
        logger.warning(f"Agent: Max iterations ({MAX_ITERATIONS}) reached, forcing response")
        return "respond"

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == RESPONSE_TOOL_NAME:
                logger.info("Agent: DinnerRecommendation tool called, proceeding to respond")
                return "respond"

        logger.info("Agent: Tool calls detected, continuing to tool execution")
        return "tools"

    logger.warning("Agent: No tool calls detected, proceeding to respond")
    return "respond"


def respond(state: AgentState) -> dict:
    """Extract the structured dinner recommendation from the agent's response."""
    messages = state["messages"]

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
    """Create the ReAct agent graph for dinner menu advice with structured output."""
    logger.info("Creating dinner advisor ReAct agent graph with structured output...")

    graph = StateGraph(AgentState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("respond", respond)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "respond": "respond",
        },
    )

    graph.add_edge("tools", "agent")
    graph.add_edge("respond", END)

    logger.info("Dinner advisor graph created successfully")
    return graph.compile()


async def run_dinner_advisor(
    user_request: str,
    model: str = OpenAIModel.GPT_5_MINI,
) -> DinnerRecommendation | None:
    """Run the dinner advisor agent with a user's request."""
    logger.info(f"Starting dinner advisor for request: {user_request}")
    logger.info(f"Using model: {model}")

    initial_state: AgentState = {
        "messages": [("user", make_user_request_prompt(user_request))],
        "user_request": user_request,
        "final_response": None,
    }

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

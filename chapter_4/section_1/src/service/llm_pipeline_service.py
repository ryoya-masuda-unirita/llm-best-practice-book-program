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
from src.model.llm_pipeline_model import AgentState
from src.prompt.llm_pipeline_prompt import (
    make_dinner_advisor_system_prompt,
    make_user_request_prompt,
)

logger = make_logger(__name__)

# Maximum number of agent iterations to prevent infinite loops
MAX_ITERATIONS = 10


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

    # Simulated recipe database
    recipes = {
        "Japanese": [
            {"name": "鶏の照り焼き", "ingredients": ["鶏もも肉", "醤油", "みりん", "砂糖"], "time": 25},
            {"name": "豚の生姜焼き", "ingredients": ["豚ロース", "生姜", "醤油", "みりん"], "time": 20},
            {"name": "肉じゃが", "ingredients": ["牛肉", "じゃがいも", "玉ねぎ", "にんじん"], "time": 40},
            {"name": "親子丼", "ingredients": ["鶏肉", "卵", "玉ねぎ", "だし"], "time": 20},
            {"name": "サバの味噌煮", "ingredients": ["サバ", "味噌", "生姜", "砂糖"], "time": 30},
        ],
        "Italian": [
            {"name": "カルボナーラ", "ingredients": ["パスタ", "ベーコン", "卵", "チーズ"], "time": 25},
            {"name": "ペペロンチーノ", "ingredients": ["パスタ", "にんにく", "唐辛子", "オリーブオイル"], "time": 15},
            {"name": "トマトソースパスタ", "ingredients": ["パスタ", "トマト缶", "にんにく", "バジル"], "time": 20},
            {"name": "リゾット", "ingredients": ["米", "玉ねぎ", "チーズ", "白ワイン"], "time": 35},
        ],
        "Chinese": [
            {"name": "麻婆豆腐", "ingredients": ["豆腐", "ひき肉", "豆板醤", "花椒"], "time": 20},
            {"name": "回鍋肉", "ingredients": ["豚バラ", "キャベツ", "甜麺醤", "豆板醤"], "time": 25},
            {"name": "青椒肉絲", "ingredients": ["牛肉", "ピーマン", "たけのこ", "オイスターソース"], "time": 20},
            {"name": "餃子", "ingredients": ["ひき肉", "キャベツ", "ニラ", "餃子の皮"], "time": 45},
        ],
        "Quick": [
            {"name": "オムライス", "ingredients": ["卵", "ご飯", "ケチャップ", "鶏肉"], "time": 20},
            {"name": "チャーハン", "ingredients": ["ご飯", "卵", "ネギ", "ハム"], "time": 15},
            {"name": "焼きそば", "ingredients": ["中華麺", "キャベツ", "豚肉", "ソース"], "time": 15},
        ],
    }

    query_lower = query.lower()

    # Determine which cuisines to search
    if cuisine_type and cuisine_type in recipes:
        cuisines_to_search = [cuisine_type]
    else:
        cuisines_to_search = list(recipes.keys())

    # Search for matching recipes
    results = []
    for cuisine in cuisines_to_search:
        for recipe in recipes.get(cuisine, []):
            name_matches = query_lower in recipe["name"].lower()
            ingredient_matches = any(query_lower in ing.lower() for ing in recipe["ingredients"])
            cuisine_matches = query_lower in cuisine.lower()

            if name_matches or ingredient_matches or cuisine_matches:
                results.append({**recipe, "cuisine": cuisine})

    # Fallback: return default recipes if no matches found
    if not results:
        if cuisine_type and cuisine_type in recipes:
            results = [{**r, "cuisine": cuisine_type} for r in recipes[cuisine_type][:3]]
        else:
            results = [{**r, "cuisine": "Quick"} for r in recipes["Quick"]]

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

    # Simulated nutrition database (per serving)
    nutrition_data = {
        "鶏の照り焼き": {"calories": 350, "protein": 28, "carbs": 15, "fat": 18, "fiber": 1},
        "豚の生姜焼き": {"calories": 380, "protein": 25, "carbs": 12, "fat": 22, "fiber": 1},
        "肉じゃが": {"calories": 320, "protein": 18, "carbs": 35, "fat": 12, "fiber": 4},
        "親子丼": {"calories": 480, "protein": 28, "carbs": 55, "fat": 15, "fiber": 2},
        "カルボナーラ": {"calories": 550, "protein": 22, "carbs": 60, "fat": 25, "fiber": 2},
        "麻婆豆腐": {"calories": 280, "protein": 18, "carbs": 12, "fat": 18, "fiber": 2},
        "オムライス": {"calories": 520, "protein": 20, "carbs": 65, "fat": 18, "fiber": 2},
    }

    if dish_name in nutrition_data:
        result = {
            "dish": dish_name,
            "nutrition": nutrition_data[dish_name],
            "unit": "per serving",
        }
    else:
        result = {
            "dish": dish_name,
            "nutrition": {"calories": 400, "protein": 20, "carbs": 40, "fat": 15, "fiber": 3},
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
        month_to_season = {
            3: "spring",
            4: "spring",
            5: "spring",
            6: "summer",
            7: "summer",
            8: "summer",
            9: "fall",
            10: "fall",
            11: "fall",
            12: "winter",
            1: "winter",
            2: "winter",
        }
        season = month_to_season[month]

    seasonal_ingredients = {
        "spring": {
            "vegetables": ["たけのこ", "菜の花", "アスパラガス", "新玉ねぎ", "春キャベツ"],
            "fish": ["鯛", "初鰹", "さわら", "しらす"],
            "fruits": ["いちご", "びわ"],
        },
        "summer": {
            "vegetables": ["トマト", "きゅうり", "なす", "ピーマン", "オクラ", "とうもろこし"],
            "fish": ["鰻", "あじ", "いわし"],
            "fruits": ["スイカ", "メロン", "桃", "ぶどう"],
        },
        "fall": {
            "vegetables": ["さつまいも", "かぼちゃ", "きのこ類", "れんこん", "ごぼう"],
            "fish": ["さんま", "鮭", "さば"],
            "fruits": ["柿", "梨", "りんご", "栗"],
        },
        "winter": {
            "vegetables": ["大根", "白菜", "ほうれん草", "ねぎ", "ブロッコリー"],
            "fish": ["ぶり", "たら", "牡蠣", "ふぐ"],
            "fruits": ["みかん", "りんご", "いちご"],
        },
    }

    season_to_japanese = {"spring": "春", "summer": "夏", "fall": "秋", "winter": "冬"}

    result = {
        "season": season,
        "season_japanese": season_to_japanese.get(season, season),
        "ingredients": seasonal_ingredients.get(season, seasonal_ingredients["fall"]),
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

    # Base cooking times (for intermediate level)
    base_times = {
        "鶏の照り焼き": {"prep": 10, "cook": 15},
        "豚の生姜焼き": {"prep": 10, "cook": 10},
        "肉じゃが": {"prep": 15, "cook": 25},
        "親子丼": {"prep": 10, "cook": 10},
        "カルボナーラ": {"prep": 10, "cook": 15},
        "麻婆豆腐": {"prep": 10, "cook": 10},
        "オムライス": {"prep": 10, "cook": 10},
        "餃子": {"prep": 30, "cook": 15},
    }

    # Skill level multipliers
    multipliers = {"beginner": 1.5, "intermediate": 1.0, "advanced": 0.8}
    multiplier = multipliers.get(skill_level, 1.0)

    # Get base times or use defaults
    times = base_times.get(dish_name, {"prep": 15, "cook": 20})
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

# Define available tools
tools = [search_recipes, check_nutrition, get_seasonal_ingredients, estimate_cooking_time]
tools_by_name = {tool.name: tool for tool in tools}


def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """
    Call the LLM model with the current state.

    This is the "Thought" and "Action" part of the ReAct loop.
    The model decides whether to use a tool or provide a final answer.

    Args:
        state: Current agent state
        config: Runtime configuration

    Returns:
        Updated state with model response
    """
    logger.info("Agent: Calling model for reasoning...")

    # Get model from config or use default
    model_name = config.get("configurable", {}).get("model", OpenAIModel.GPT_4O)

    # Initialize the model with tools
    model = ChatOpenAI(model=model_name, temperature=0.7)
    model_with_tools = model.bind_tools(tools)

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


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Determine whether to continue the ReAct loop or end.

    If the last message has tool calls, continue to execute tools.
    Otherwise, end the loop (the model has provided a final answer).

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

    logger.info("Agent: No tool calls, ending loop with final answer")
    return "end"


def extract_final_recommendation(state: AgentState) -> dict:
    """
    Extract the final recommendation from the agent's response.

    Args:
        state: Current agent state

    Returns:
        Updated state with final recommendation
    """
    messages = state["messages"]

    # Find the last AI message without tool calls (the final answer)
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            return {"final_recommendation": message.content}

    return {"final_recommendation": None}


def create_dinner_advisor_graph() -> StateGraph:
    """
    Create the ReAct agent graph for dinner menu advice.

    The graph follows the ReAct pattern:
    1. Agent (Thought + Action): LLM reasons about the request and decides on actions
    2. Tools (Observation): Execute tools and observe results
    3. Loop back to Agent until the task is complete

    Returns:
        Compiled StateGraph for the dinner advisor agent
    """
    logger.info("Creating dinner advisor ReAct agent graph...")

    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", extract_final_recommendation)

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

    logger.info("Dinner advisor graph created successfully")
    return graph.compile()


async def run_dinner_advisor(
    user_request: str,
    model: str = OpenAIModel.GPT_4O,
) -> str | None:
    """
    Run the dinner advisor agent with a user's request.

    Args:
        user_request: The user's dinner request (e.g., "今日は疲れているので簡単な料理がいい")
        model: The OpenAI model to use

    Returns:
        The agent's dinner recommendation or None if failed
    """
    logger.info(f"Starting dinner advisor for request: {user_request}")
    logger.info(f"Using model: {model}")

    # Create initial state
    initial_state: AgentState = {
        "messages": [("user", make_user_request_prompt(user_request))],
        "user_request": user_request,
        "final_recommendation": None,
    }

    # Create and run the graph
    graph = create_dinner_advisor_graph()
    config = RunnableConfig(configurable={"model": model})

    try:
        final_state = await graph.ainvoke(initial_state, config)

        recommendation = final_state.get("final_recommendation")
        if recommendation:
            logger.info("Dinner advisor completed successfully")
            return recommendation
        else:
            logger.warning("Dinner advisor completed but no recommendation was generated")
            return None

    except Exception as e:
        logger.error(f"Dinner advisor failed: {str(e)}")
        raise

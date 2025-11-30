from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

# =============================================================================
# Constants
# =============================================================================

# Maximum number of agent iterations to prevent infinite loops
MAX_ITERATIONS = 10

# =============================================================================
# Recipe Data
# =============================================================================

RECIPES_DATABASE: dict[str, list[dict]] = {
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

# =============================================================================
# Nutrition Data
# =============================================================================

NUTRITION_DATABASE: dict[str, dict[str, int]] = {
    "鶏の照り焼き": {"calories": 350, "protein": 28, "carbs": 15, "fat": 18, "fiber": 1},
    "豚の生姜焼き": {"calories": 380, "protein": 25, "carbs": 12, "fat": 22, "fiber": 1},
    "肉じゃが": {"calories": 320, "protein": 18, "carbs": 35, "fat": 12, "fiber": 4},
    "親子丼": {"calories": 480, "protein": 28, "carbs": 55, "fat": 15, "fiber": 2},
    "カルボナーラ": {"calories": 550, "protein": 22, "carbs": 60, "fat": 25, "fiber": 2},
    "麻婆豆腐": {"calories": 280, "protein": 18, "carbs": 12, "fat": 18, "fiber": 2},
    "オムライス": {"calories": 520, "protein": 20, "carbs": 65, "fat": 18, "fiber": 2},
}

DEFAULT_NUTRITION: dict[str, int] = {"calories": 400, "protein": 20, "carbs": 40, "fat": 15, "fiber": 3}

# =============================================================================
# Seasonal Ingredients Data
# =============================================================================

SEASONAL_INGREDIENTS: dict[str, dict[str, list[str]]] = {
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

MONTH_TO_SEASON: dict[int, str] = {
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

SEASON_TO_JAPANESE: dict[str, str] = {"spring": "春", "summer": "夏", "fall": "秋", "winter": "冬"}

# =============================================================================
# Cooking Time Data
# =============================================================================

BASE_COOKING_TIMES: dict[str, dict[str, int]] = {
    "鶏の照り焼き": {"prep": 10, "cook": 15},
    "豚の生姜焼き": {"prep": 10, "cook": 10},
    "肉じゃが": {"prep": 15, "cook": 25},
    "親子丼": {"prep": 10, "cook": 10},
    "カルボナーラ": {"prep": 10, "cook": 15},
    "麻婆豆腐": {"prep": 10, "cook": 10},
    "オムライス": {"prep": 10, "cook": 10},
    "餃子": {"prep": 30, "cook": 15},
}

DEFAULT_COOKING_TIMES: dict[str, int] = {"prep": 15, "cook": 20}

SKILL_LEVEL_MULTIPLIERS: dict[str, float] = {"beginner": 1.5, "intermediate": 1.0, "advanced": 0.8}


# =============================================================================
# Type Definitions
# =============================================================================


class DinnerRecommendation(BaseModel):
    """
    Final structured dinner recommendation to respond to the user.

    Use this tool when you have gathered enough information and are ready
    to provide your final dinner recommendation to the user.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    menu_name: str = Field(..., description="Name of the recommended dinner menu (in Japanese)")
    ingredients: list[str] = Field(..., description="List of main ingredients needed (in Japanese)")
    cooking_time_minutes: int = Field(..., description="Estimated total cooking time in minutes")
    difficulty: str = Field(..., description="Difficulty level: easy (簡単), medium (普通), or hard (難しい)")
    reason: str = Field(..., description="Why this menu is recommended based on user's request (in Japanese)")
    recipe_steps: list[str] = Field(..., description="Step-by-step cooking instructions (in Japanese)")

    def to_markdown(self) -> str:
        """Convert the recommendation to markdown format."""
        ingredients_md = "\n".join(f"- {ing}" for ing in self.ingredients)
        steps_md = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(self.recipe_steps))

        return f"""# おすすめ夕食メニュー: {self.menu_name}

## 概要
- **調理時間**: {self.cooking_time_minutes}分
- **難易度**: {self.difficulty}

## おすすめ理由
{self.reason}

## 材料
{ingredients_md}

## 作り方
{steps_md}
"""


class AgentState(TypedDict):
    """ReAct agent state for dinner menu advisor."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_request: str
    final_response: DinnerRecommendation | None

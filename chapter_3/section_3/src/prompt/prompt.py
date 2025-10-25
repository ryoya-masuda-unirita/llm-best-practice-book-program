import json

from src.model.model import CharacterRequest, CharacterResponse


def make_generation_prompt(
    character_request: CharacterRequest,
) -> list:
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return [
        {
            "role": "system",
            "content": f"""あなたは創造的なキャラクタージェネレーターです。
あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
1. 応答は有効なJSONであること
2. すべてのフィールドが含まれていること
3. 性別は指定された値であること
4. 年齢は指定された値であること
5. 正確に3つの性格特性が提供されていること
6. JSON構造の外に説明や追加のテキストを含めないこと
""",
        },
        {
            "role": "user",
            "content": f"""ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。
性別は「{character_request.gender.value}」、年齢は「{character_request.age}」歳です。
{character_request.additional_instructions}
""",
        },
    ]


def make_classification_prompt(text: str, categories: list[str]) -> list:
    """Create a prompt for text classification with structured output.

    Args:
        text: The text to classify
        categories: List of possible categories

    Returns:
        list: Prompt messages for the LLM
    """
    categories_str = ", ".join([f'"{cat}"' for cat in categories])

    # Create schema description for structured output
    schema_description = json.dumps(
        {
            "category": f"string; Must be exactly one of: {categories_str}",
            "confidence": "string; Optional confidence level: 'high', 'medium', or 'low'",
            "reasoning": "string; Optional brief explanation for why this category was chosen",
        },
        indent=2,
        ensure_ascii=False,
    )

    return [
        {
            "role": "system",
            "content": f"""あなたはテキスト分類の専門家です。
与えられたテキストを以下のカテゴリのいずれか一つに分類してください：{categories_str}

以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{schema_description}

重要な注意事項：
1. categoryフィールドは必須で、提供されたカテゴリリストから正確に一つを選択すること
2. カテゴリ名は大文字小文字を含めて完全に一致させること
3. confidenceとreasoningは任意ですが、提供すると分類の質が向上します
4. JSON構造の外に説明や追加のテキストを含めないこと
""",
        },
        {
            "role": "user",
            "content": f"""以下のテキストを分類してください：

{text}

利用可能なカテゴリ：{categories_str}
""",
        },
    ]

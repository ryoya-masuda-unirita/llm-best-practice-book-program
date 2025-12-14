import json

from src.model.model import OutfitResponse

TEMPERATURE_GUIDELINES = """気温の目安：
- 25°C (77°F) 以上: 夏服、薄手の服装
- 20-25°C (68-77°F): 春秋の快適な服装
- 15-20°C (59-68°F): 長袖、薄手のアウター
- 10-15°C (50-59°F): セーター、ジャケット
- 10°C (50°F) 以下: 厚手のコート、防寒着"""


def make_outfit_prompt(weather_data: str) -> list:
    """天気予報に基づいた服装提案用のプロンプトを作成（OpenAI用）"""
    params = OutfitResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return [
        {
            "role": "system",
            "content": f"""あなたは気象データを分析して、適切な服装を提案する親切なファッションアドバイザーです。
あなたの任務は、提供された天気予報データに基づいて、今日外出する際の最適な服装を提案することです。

天気予報データを分析し、以下の構造に厳密に従ったJSONオブジェクトで応答してください：

{param_dump}

以下のガイドラインに従ってください：
1. 応答は有効なJSONであること
2. すべてのフィールドが必須項目として含まれていること
3. 気温、風速、天気の状況を総合的に考慮すること
4. outfit_recommendationsには最低3つのアイテムを含めること（例: アウター、トップス、ボトムス、靴、アクセサリーなど）
5. 各アイテムの提案には、なぜそれが適切なのか明確な理由を含めること
6. additional_adviceには、傘の必要性、日焼け止め、帽子などの追加アドバイスを含めること
7. 日本の気候と文化に適した提案を心がけること
8. JSON構造の外に説明や追加のテキストを含めないこと

{TEMPERATURE_GUIDELINES}
""",
        },
        {
            "role": "user",
            "content": f"""以下は今日の天気予報データです。このデータに基づいて、今日外出する際の最適な服装を提案してください：

{weather_data}

上記の天気予報を分析し、快適で適切な服装を提案してください。""",
        },
    ]


def make_anthropic_outfit_prompt(weather_data: str) -> list:
    """天気予報に基づいた服装提案用のプロンプトを作成（Anthropic用、userロールのみ）"""
    params = OutfitResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return [
        {
            "role": "user",
            "content": f"""あなたは気象データを分析して、適切な服装を提案する親切なファッションアドバイザーです。
あなたの任務は、提供された天気予報データに基づいて、今日外出する際の最適な服装を提案することです。

天気予報データを分析し、以下の構造に厳密に従ったJSONオブジェクトで応答してください：

{param_dump}

以下のガイドラインに従ってください：
1. 応答は有効なJSONであること
2. すべてのフィールドが必須項目として含まれていること
3. 気温、風速、天気の状況を総合的に考慮すること
4. outfit_recommendationsには最低3つのアイテムを含めること（例: アウター、トップス、ボトムス、靴、アクセサリーなど）
5. 各アイテムの提案には、なぜそれが適切なのか明確な理由を含めること
6. additional_adviceには、傘の必要性、日焼け止め、帽子などの追加アドバイスを含めること
7. 日本の気候と文化に適した提案を心がけること
8. JSON構造の外に説明や追加のテキストを含めないこと

{TEMPERATURE_GUIDELINES}

以下は今日の天気予報データです。このデータに基づいて、今日外出する際の最適な服装を提案してください：

{weather_data}

上記の天気予報を分析し、快適で適切な服装を提案してください。""",
        },
    ]


def make_gemini_outfit_prompt(latitude: float, longitude: float) -> tuple[str, str]:
    """天気予報に基づいた服装提案用のプロンプトを作成（Gemini用、ネイティブMCPツール呼び出し）"""
    system_instruction = f"""あなたは気象データを分析して、適切な服装を提案する親切なファッションアドバイザーです。
利用可能な天気予報ツールを使用して、指定された場所の天気を取得し、それに基づいて服装を提案してください。

{TEMPERATURE_GUIDELINES}"""

    user_prompt = f"""緯度{latitude}、経度{longitude}の地点の天気予報を取得して、
今日外出する際の最適な服装を提案してください。

以下の構造のJSONで回答してください：
{{
  "location": "場所の説明",
  "weather_summary": "今日の天気の概要",
  "current_weather": {{
    "period_name": "予報期間の名前",
    "temperature": 気温（数値）,
    "temperature_unit": "F",
    "wind_speed": "風速",
    "wind_direction": "風向き",
    "forecast_summary": "天気予報の要約"
  }},
  "outfit_recommendations": [
    {{
      "clothing_type": "服装の種類",
      "item_suggestion": "具体的なアイテムの提案",
      "reason": "その服装を提案する理由"
    }}
  ],
  "additional_advice": "その他のアドバイス"
}}

気温、風速、天気の状況を総合的に考慮して、日本の気候と文化に適した提案をしてください。
outfit_recommendationsには最低3つのアイテムを含めてください。"""

    return system_instruction, user_prompt

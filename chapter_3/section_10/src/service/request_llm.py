import json

from google.genai.types import GenerateContentConfig
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.client.llm_client import GeminiModel, OpenAIModel, google_genai_client, openai_client
from src.logger import make_logger
from src.model.model import OutfitResponse
from src.prompt.prompt import make_outfit_prompt

logger = make_logger(__name__)


async def request_openai_outfit(model: OpenAIModel, latitude: float, longitude: float) -> OutfitResponse:
    """天気予報に基づいた服装提案（OpenAI + MCP）

    OpenAI SDKにはネイティブMCPサポートがないため、MCPツールを手動で呼び出して
    結果をプロンプトに含めて送信する方式を使用
    """
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "tool_server/weather_server.py"],
    )

    # MCPサーバーから天気予報を取得
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            logger.info(f"MCP session initialized. Calling get_forecast with lat={latitude}, lon={longitude}")

            # get_forecast ツールを呼び出し
            result = await session.call_tool("get_forecast", arguments={"latitude": latitude, "longitude": longitude})

            logger.info(f"Weather forecast result: {result}")

            # MCPツールの結果からコンテンツを抽出
            if result.content and len(result.content) > 0:
                weather_data = result.content[0].text
            else:
                weather_data = "天気予報データの取得に失敗しました。"

    logger.info(f"Weather data retrieved: {weather_data}")

    # 天気データの取得に失敗している場合はエラーを投げる
    if "天気予報データの取得に失敗" in weather_data or "Unable to fetch" in weather_data:
        raise ValueError(
            "天気予報データの取得に失敗しました。\n"
            "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
            f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
            "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）"
        )

    # 天気データを使ってプロンプトを作成
    prompt = make_outfit_prompt(weather_data)

    # OpenAI APIで服装提案を生成
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=OutfitResponse,
    )
    return result.output_parsed


async def request_gemini_outfit(model: GeminiModel, latitude: float, longitude: float) -> OutfitResponse:
    """天気予報に基づいた服装提案（Gemini + MCP）

    Gemini SDKはネイティブMCPサポートを持っており、ClientSessionを直接tools引数に渡すことができる
    ツール呼び出しと構造化出力（response_mime_type）は同時に使用できないため、
    ツール呼び出し後にテキストレスポンスをパースする
    """
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "tool_server/weather_server.py"],
    )

    # MCPサーバーと接続し、Geminiのツールとして使用
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            logger.info(
                f"MCP session initialized for Gemini. Requesting outfit recommendation for lat={latitude}, lon={longitude}"
            )

            # プロンプトを作成（天気データは含めず、LLMがMCPツールを呼び出す）
            system_instruction = """あなたは気象データを分析して、適切な服装を提案する親切なファッションアドバイザーです。
利用可能な天気予報ツールを使用して、指定された場所の天気を取得し、それに基づいて服装を提案してください。

気温の目安：
- 25°C (77°F) 以上: 夏服、薄手の服装
- 20-25°C (68-77°F): 春秋の快適な服装
- 15-20°C (59-68°F): 長袖、薄手のアウター
- 10-15°C (50-59°F): セーター、ジャケット
- 10°C (50°F) 以下: 厚手のコート、防寒着"""

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

            # Gemini APIにMCPセッションをツールとして渡す（自動ツール呼び出し有効）
            result = await google_genai_client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[session],  # MCPセッションを直接ツールとして渡す
                ),
            )

            logger.info(f"Gemini response: {result}")

            # レスポンスからJSONテキストを抽出してパース
            response_text = result.text

            # 天気データの取得失敗を示すメッセージをチェック
            if "天気予報データを取得できませんでした" in response_text or "天気予報を取得できません" in response_text:
                raise ValueError(
                    "天気予報データの取得に失敗しました。\n"
                    "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
                    f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
                    "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）"
                )

            # JSONブロックを抽出（```json ... ``` の場合に対応）
            json_text = None
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # JSONブロックがない場合、{ } で囲まれた部分を抽出
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_text = response_text[json_start:json_end].strip()
                else:
                    # JSONが全く含まれていない場合
                    raise ValueError(
                        "天気予報データの取得に失敗しました。\n"
                        "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
                        f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
                        "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）"
                    )

            # JSONをパースしてOutfitResponseモデルに変換
            try:
                outfit_data = json.loads(json_text)

                # 天気データの取得に失敗している場合をチェック
                if outfit_data.get("current_weather", {}).get("temperature") is None:
                    raise ValueError(
                        "天気予報データの取得に失敗しました。\n"
                        "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
                        f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
                        "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）"
                    )

                return OutfitResponse(**outfit_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text}")
                logger.error(f"Extracted JSON text: {json_text}")
                raise ValueError(f"レスポンスのJSON解析に失敗しました。\nエラー: {e}")
            except ValueError:
                # すでに適切なエラーメッセージが設定されている場合はそのまま再スロー
                raise
            except Exception as e:
                logger.error(f"Failed to create OutfitResponse: {e}")
                logger.error(f"Outfit data: {outfit_data if 'outfit_data' in locals() else 'N/A'}")
                raise ValueError(
                    f"服装提案データの生成に失敗しました。\n"
                    f"座標が正しいか確認してください。\n"
                    f"注意: このツールは米国内の座標のみ対応しています。\n"
                    f"エラー: {e}"
                )

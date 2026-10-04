# from google.genai.types import GenerateContentConfig
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.client.llm_client import (
    AnthropicModel,
    # GeminiModel,
    OpenAIModel,
    anthropic_client,
    # google_genai_client,
    openai_client,
)
from src.logger import make_logger
from src.model.model import OutfitResponse
from src.prompt.prompt import make_anthropic_outfit_prompt, make_outfit_prompt  # , make_gemini_outfit_prompt

logger = make_logger(__name__)

MCP_SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["run", "python", "tool_server/weather_server.py"],
)


def _make_us_only_error_message(latitude: float, longitude: float) -> str:
    """米国内座標のみ対応エラーメッセージを生成"""
    return (
        "天気予報データの取得に失敗しました。\n"
        "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
        f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
        "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）"
    )


async def _fetch_weather_data_via_mcp(latitude: float, longitude: float, provider_name: str) -> str:
    """MCPサーバーから天気予報データを取得（OpenAI/Anthropic用の手動ツール呼び出し）"""
    async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info(
                f"MCP session initialized for {provider_name}. Calling get_forecast with lat={latitude}, lon={longitude}"
            )

            result = await session.call_tool("get_forecast", arguments={"latitude": latitude, "longitude": longitude})
            logger.info(f"Weather forecast result: {result}")

            if result.content and len(result.content) > 0:
                weather_data = result.content[0].text
            else:
                weather_data = "天気予報データの取得に失敗しました。"

    logger.info(f"Weather data retrieved: {weather_data}")

    if "天気予報データの取得に失敗" in weather_data or "Unable to fetch" in weather_data:
        raise ValueError(_make_us_only_error_message(latitude, longitude))

    return weather_data


async def request_openai_outfit(model: OpenAIModel, latitude: float, longitude: float) -> OutfitResponse:
    """天気予報に基づいた服装提案（OpenAI + MCP、手動ツール呼び出し）"""
    weather_data = await _fetch_weather_data_via_mcp(latitude, longitude, "OpenAI")
    prompt = make_outfit_prompt(weather_data)
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=OutfitResponse,
    )
    return result.output_parsed


# async def request_gemini_outfit(model: GeminiModel, latitude: float, longitude: float) -> OutfitResponse:
#     """天気予報に基づいた服装提案（Gemini + MCP、ネイティブツール統合）
#
#     ツール呼び出しと構造化出力は同時使用不可のため、テキストレスポンスをパースする
#     """
#     async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
#         async with ClientSession(read, write) as session:
#             await session.initialize()
#             logger.info(
#                 f"MCP session initialized for Gemini. Requesting outfit recommendation for lat={latitude}, lon={longitude}"
#             )
#
#             system_instruction, user_prompt = make_gemini_outfit_prompt(latitude, longitude)
#             result = await google_genai_client.aio.models.generate_content(
#                 model=model,
#                 contents=user_prompt,
#                 config=GenerateContentConfig(
#                     system_instruction=system_instruction,
#                     tools=[session],
#                 ),
#             )
#
#             logger.info(f"Gemini response: {result}")
#             response_text = result.text
#
#             if "天気予報データを取得できませんでした" in response_text or "天気予報を取得できません" in response_text:
#                 raise ValueError(_make_us_only_error_message(latitude, longitude))
#
#             json_text = None
#             if "```json" in response_text:
#                 json_start = response_text.find("```json") + 7
#                 json_end = response_text.find("```", json_start)
#                 json_text = response_text[json_start:json_end].strip()
#             elif "```" in response_text:
#                 json_start = response_text.find("```") + 3
#                 json_end = response_text.find("```", json_start)
#                 json_text = response_text[json_start:json_end].strip()
#             elif "{" in response_text and "}" in response_text:
#                 json_start = response_text.find("{")
#                 json_end = response_text.rfind("}") + 1
#                 json_text = response_text[json_start:json_end].strip()
#             else:
#                 raise ValueError(_make_us_only_error_message(latitude, longitude))
#
#             try:
#                 outfit_data = json.loads(json_text)
#                 if outfit_data.get("current_weather", {}).get("temperature") is None:
#                     raise ValueError(_make_us_only_error_message(latitude, longitude))
#                 return OutfitResponse(**outfit_data)
#             except json.JSONDecodeError as e:
#                 logger.error(f"Failed to parse JSON response: {e}")
#                 logger.error(f"Response text: {response_text}")
#                 logger.error(f"Extracted JSON text: {json_text}")
#                 raise ValueError(f"レスポンスのJSON解析に失敗しました。\nエラー: {e}")
#             except ValueError:
#                 raise
#             except Exception as e:
#                 logger.error(f"Failed to create OutfitResponse: {e}")
#                 logger.error(f"Outfit data: {outfit_data if 'outfit_data' in locals() else 'N/A'}")
#                 raise ValueError(
#                     f"服装提案データの生成に失敗しました。\n"
#                     f"座標が正しいか確認してください。\n"
#                     f"注意: このツールは米国内の座標のみ対応しています。\n"
#                     f"エラー: {e}"
#                 )


async def request_anthropic_outfit(model: AnthropicModel, latitude: float, longitude: float) -> OutfitResponse:
    """天気予報に基づいた服装提案（Anthropic + MCP、手動ツール呼び出し）"""
    weather_data = await _fetch_weather_data_via_mcp(latitude, longitude, "Anthropic")
    prompt = make_anthropic_outfit_prompt(weather_data)
    result = await anthropic_client.messages.parse(
        model=model,
        max_tokens=1024,
        messages=prompt,
        output_format=OutfitResponse,
    )
    logger.info(f"Anthropic response: {result}")
    return result.parsed_output

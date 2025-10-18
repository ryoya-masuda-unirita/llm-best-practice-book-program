import asyncio
from typing import AsyncIterator

from google.genai.types import GenerateContentConfig
from src.client.llm_client import google_genai_client, openai_client
from src.logger import make_logger

logger = make_logger(__name__)


async def stream_openai_response(
    prompt: str,
    model: str = "gpt-4o-mini",
) -> AsyncIterator[str]:
    """
    OpenAI APIからストリーミングで応答を取得する非同期ジェネレータ

    Args:
        prompt: ユーザーのプロンプト
        model: 使用するOpenAIモデル

    Yields:
        生成されたテキストのチャンク
    """
    try:
        stream = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=1.0,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield content
                # イベントループのブロッキングを防ぐために微小な待機時間を入れます
                await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"Error in OpenAI streaming: {e}")
        yield f"data: [ERROR] {str(e)}\n\n"


async def stream_gemini_response(
    prompt: str,
    model: str = "gemini-2.5-flash",
    system_instruction: str | None = None,
) -> AsyncIterator[str]:
    """
    Gemini APIからストリーミングで応答を取得する非同期ジェネレータ

    Args:
        prompt: ユーザーのプロンプト
        model: 使用するGeminiモデル
        system_instruction: システム命令（オプション）

    Yields:
        生成されたテキストのチャンク
    """
    try:
        config = GenerateContentConfig(temperature=2.0)

        if system_instruction:
            config = GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=2.0,
            )

        response = google_genai_client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=config,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        logger.error(f"Error in Gemini streaming: {e}")
        yield f"data: [ERROR] {str(e)}\n\n"

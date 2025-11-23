import asyncio
from typing import AsyncIterator

from src.client.llm_client import OpenAIModel, openai_client
from src.logger import make_logger

logger = make_logger(__name__)


async def get_openai_response(
    prompt: str,
    model: str = OpenAIModel.GPT_4O_MINI,
) -> str:
    """
    OpenAI APIから非ストリーミングで応答を取得する非同期関数

    Args:
        prompt: ユーザーのプロンプト
        model: 使用するOpenAIモデル

    Returns:
        生成されたテキスト全体

    Raises:
        Exception: OpenAI API呼び出しでエラーが発生した場合
    """
    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )

        return response.choices[0].message.content or ""

    except Exception as e:
        logger.error(f"Error in OpenAI non-streaming: {e}")
        raise


async def stream_openai_response(
    prompt: str,
    model: str = OpenAIModel.GPT_4O_MINI,
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

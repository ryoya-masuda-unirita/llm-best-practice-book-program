"""
LLM Streaming APIのテストクライアント

このスクリプトは、FastAPIサーバーにリクエストを送信し、
ストリーミングレスポンスをリアルタイムで受信して表示します。

使用方法:
    python test_client.py --provider openai --prompt "こんにちは"
    python test_client.py --provider gemini --prompt "Pythonについて教えて"
"""

import asyncio

import aiohttp
import click


async def stream_request(
    url: str,
    prompt: str,
    provider: str = "gemini",
    model: str | None = None,
    system_instruction: str | None = None,
):
    """
    APIサーバーにストリーミングリクエストを送信し、レスポンスを表示する

    Args:
        url: APIエンドポイントのURL
        prompt: ユーザーのプロンプト
        provider: LLMプロバイダー (openai または gemini)
        model: 使用するモデル名
        system_instruction: システム命令（Geminiのみ）
    """
    payload = {
        "prompt": prompt,
        "provider": provider,
    }

    if model:
        payload["model"] = model

    if system_instruction:
        payload["system_instruction"] = system_instruction

    print(f"\n{'=' * 60}")
    print(f"Provider: {provider}")
    print(f"Prompt: {prompt}")
    if model:
        print(f"Model: {model}")
    print(f"{'=' * 60}\n")
    print("Response:")
    print("-" * 60)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(error_text)
                    return

                # ストリーミングレスポンスを逐次的に表示
                async for chunk in response.content.iter_any():
                    if chunk:
                        text = chunk.decode("utf-8")
                        print(text, end="", flush=True)

        print("\n" + "-" * 60)
        print("Stream completed successfully!")

    except aiohttp.ClientError as e:
        print(f"\nConnection error: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


@click.command()
@click.option(
    "--url",
    default="http://127.0.0.1:8000/stream",
    help="APIエンドポイントのURL",
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "gemini"]),
    default="gemini",
    help="LLMプロバイダー",
)
@click.option(
    "--prompt",
    required=True,
    help="LLMに送信するプロンプト",
)
@click.option(
    "--model",
    default=None,
    help="使用するモデル名（オプション）",
)
@click.option(
    "--system-instruction",
    default=None,
    help="システム命令（Geminiのみ、オプション）",
)
def main(
    url: str,
    provider: str,
    prompt: str,
    model: str | None,
    system_instruction: str | None,
):
    """LLM Streaming APIのテストクライアント"""
    asyncio.run(
        stream_request(
            url=url,
            prompt=prompt,
            provider=provider,
            model=model,
            system_instruction=system_instruction,
        )
    )


if __name__ == "__main__":
    main()

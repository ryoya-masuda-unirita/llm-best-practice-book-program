"""
LLM APIのサンプルクライアント

このスクリプトは、FastAPIサーバーにリクエストを送信し、
ストリーミングまたは非ストリーミングレスポンスを受信して表示します。

使用方法:
    # ストリーミング
    python example_client.py --prompt "こんにちは"
    python example_client.py --model gpt-5.4 --prompt "Pythonについて教えて"

    # 非ストリーミング (同期)
    python example_client.py --mode completion --prompt "こんにちは"
    python example_client.py --mode completion --model gpt-5.4 --prompt "Pythonについて教えて"
"""

import asyncio

import aiohttp
import click


async def stream_request(
    url: str,
    prompt: str,
    model: str | None = None,
):
    """APIサーバーにストリーミングリクエストを送信し、レスポンスを表示する"""
    payload = {
        "prompt": prompt,
        "provider": "openai",
    }

    if model:
        payload["model"] = model

    print(f"\n{'=' * 60}")
    print("Provider: openai")
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


async def completion_request(
    url: str,
    prompt: str,
    model: str | None = None,
):
    """APIサーバーに非ストリーミングリクエストを送信し、レスポンスを表示する"""
    payload = {
        "prompt": prompt,
        "provider": "openai",
    }

    if model:
        payload["model"] = model

    print(f"\n{'=' * 60}")
    print("Provider: openai")
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

                response_data = await response.json()
                print(response_data["content"])

        print("\n" + "-" * 60)
        print("Completion request successful!")
        print(f"Model used: {response_data.get('model', 'unknown')}")
        print(f"Provider: {response_data.get('provider', 'unknown')}")

    except aiohttp.ClientError as e:
        print(f"\nConnection error: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["stream", "completion"], case_sensitive=False),
    default="stream",
    help="リクエストモード: stream（ストリーミング）またはcompletion（非ストリーミング）",
)
@click.option(
    "--url",
    default=None,
    help="APIエンドポイントのURL（未指定の場合はmodeに応じて自動設定）",
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
def main(
    mode: str,
    url: str | None,
    prompt: str,
    model: str | None,
):
    """LLM APIのサンプルクライアント"""
    if url is None:
        if mode == "stream":
            url = "http://127.0.0.1:8000/stream"
        else:
            url = "http://127.0.0.1:8000/completions"

    if mode == "stream":
        asyncio.run(
            stream_request(
                url=url,
                prompt=prompt,
                model=model,
            )
        )
    else:
        asyncio.run(
            completion_request(
                url=url,
                prompt=prompt,
                model=model,
            )
        )


if __name__ == "__main__":
    main()

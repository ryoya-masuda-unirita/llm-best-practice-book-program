"""
LLM Streaming APIサーバーを起動するスクリプト

使用方法:
    python run_server.py

    オプション:
    --host: ホストアドレス (デフォルト: 127.0.0.1)
    --port: ポート番号 (デフォルト: 8000)
    --reload: 自動リロード機能を有効化 (開発時に便利)
"""

import click
import uvicorn


@click.command()
@click.option("--host", default="127.0.0.1", help="ホストアドレス")
@click.option("--port", default=8000, help="ポート番号")
@click.option("--reload", is_flag=True, help="自動リロード機能を有効化")
def main(host: str, port: int, reload: bool):
    """FastAPI サーバーを起動します"""
    click.echo(f"Starting LLM Streaming API server on {host}:{port}")
    click.echo("Press CTRL+C to quit")

    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

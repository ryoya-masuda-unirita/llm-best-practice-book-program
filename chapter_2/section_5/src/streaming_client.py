import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict
from uuid import uuid4

import click
import httpx

from src.logger import log_stream_complete, log_stream_error, log_stream_start, log_token_received, make_logger
from src.model import LLMProvider

logger = make_logger(__name__)


class SSEParser:
    def __init__(self):
        self.buffer = ""

    def parse_line(self, line: str) -> Dict[str, str]:
        """Parse a single SSE line and return event data."""
        if line.startswith("event: "):
            return {"type": "event", "value": line[7:]}
        elif line.startswith("data: "):
            return {"type": "data", "value": line[6:]}
        elif line.startswith("id: "):
            return {"type": "id", "value": line[4:]}
        elif line.startswith("retry: "):
            return {"type": "retry", "value": line[7:]}
        elif line == "":
            return {"type": "message_end", "value": ""}
        else:
            return {"type": "unknown", "value": line}


class StreamingClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def stream_response(
        self, provider: LLMProvider, user_id: str = None, session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        client_stream_id = uuid4().hex
        start_time = time.time()
        token_count = 0

        try:
            log_stream_start(logger, client_stream_id, user_id, session_id, f"client_{provider.value}")

            payload = {"provider": provider.value, "user_id": user_id, "session_id": session_id}

            parser = SSEParser()
            current_event = None
            current_data = None

            async with self.client.stream(
                "POST",
                f"{self.base_url}/stream",
                json=payload,
                headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
            ) as response:
                response.raise_for_status()

                async for chunk in response.aiter_lines():
                    parsed = parser.parse_line(chunk)

                    if parsed["type"] == "event":
                        current_event = parsed["value"]
                    elif parsed["type"] == "data":
                        current_data = parsed["value"]
                    elif parsed["type"] == "message_end" and current_event and current_data:
                        # Complete SSE message received
                        if current_event == "stream-start":
                            yield {"event": "stream-start", "data": current_data, "client_stream_id": client_stream_id}
                        elif current_event == "token":
                            token_count += 1
                            log_token_received(logger, client_stream_id, current_data, token_count)
                            yield {"event": "token", "data": current_data, "token_count": token_count}
                        elif current_event == "stream-end":
                            duration = time.time() - start_time
                            log_stream_complete(logger, client_stream_id, duration, token_count)
                            yield {
                                "event": "stream-end",
                                "data": json.loads(current_data) if current_data else {},
                                "client_duration": duration,
                                "token_count": token_count,
                            }
                            break
                        elif current_event == "error":
                            error_data = json.loads(current_data) if current_data else {}
                            error_msg = error_data.get("error", "Unknown error")
                            log_stream_error(logger, client_stream_id, Exception(error_msg), "server_error")
                            yield {"event": "error", "data": error_data}
                            break

                        # Reset for next message
                        current_event = None
                        current_data = None

        except Exception as e:
            log_stream_error(logger, client_stream_id, e, "client_stream_error")
            raise


async def demo_streaming(provider: LLMProvider, user_id: str = None, session_id: str = None):
    async with StreamingClient() as client:
        print(f"Starting streaming with {provider.value}...")
        print("-" * 50)

        try:
            async for event in client.stream_response(provider, user_id, session_id):
                if event["event"] == "stream-start":
                    print(f"Stream started (ID: {event['data']})")
                elif event["event"] == "token":
                    print(event["data"], end="", flush=True)
                    await asyncio.sleep(0.01)  # Small delay for visual effect
                elif event["event"] == "stream-end":
                    server_stats = event["data"]
                    print("\n\nStream completed:")
                    print(f"  Server duration: {server_stats.get('duration', 'N/A'):.2f}s")
                    print(f"  Server tokens: {server_stats.get('tokens', 'N/A')}")
                    print(f"  Client duration: {event['client_duration']:.2f}s")
                    print(f"  Client tokens: {event['token_count']}")
                elif event["event"] == "error":
                    error_info = event["data"]
                    print(f"\nError: {error_info.get('error', 'Unknown error')}")
                    print(f"Type: {error_info.get('type', 'Unknown')}")

        except Exception as e:
            print(f"\nClient error occurred: {str(e)}")

        print("\n" + "-" * 50)


@click.command()
@click.option(
    "--provider",
    "-p",
    type=click.Choice([p.value for p in LLMProvider]),
    default=LLMProvider.OPENAI.value,
    help="LLM provider to use",
)
@click.option("--user-id", "-u", default=None, help="User ID for logging")
@click.option("--session-id", "-s", default=None, help="Session ID for logging")
def main(provider: str, user_id: str, session_id: str):
    provider_enum = LLMProvider(provider)
    asyncio.run(demo_streaming(provider_enum, user_id, session_id))


if __name__ == "__main__":
    main()

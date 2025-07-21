import asyncio
import time
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.llms import google_genai_client, openai_client
from src.logger import log_stream_complete, log_stream_error, log_stream_start, log_token_received, make_logger
from src.model import LLMProvider
from src.monitoring import health_checker, periodic_cleanup, periodic_health_check, stream_metrics
from src.prompt import make_prompt

app = FastAPI(title="LLM Streaming Server")
logger = make_logger(__name__)


class StreamRequest(BaseModel):
    provider: LLMProvider = LLMProvider.OPENAI
    user_id: str = None
    session_id: str = None


async def stream_openai_response(
    stream_id: str, user_id: str = None, session_id: str = None
) -> AsyncGenerator[str, None]:
    start_time = time.time()
    token_count = 0

    try:
        log_stream_start(logger, stream_id, user_id, session_id, "openai")
        stream_metrics.start_stream(stream_id, "openai", user_id, session_id)

        prompt = make_prompt()
        stream = await openai_client.chat.completions.create(
            model="gpt-4o-mini", messages=prompt, temperature=1.0, stream=True
        )

        # SSE connection start event
        yield f"event: stream-start\ndata: {stream_id}\n\n"

        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                token = chunk.choices[0].delta.content
                token_count += 1

                log_token_received(logger, stream_id, token, token_count)
                stream_metrics.update_token_count(stream_id, token_count)

                # Proper SSE format for token data
                yield f"event: token\ndata: {token}\n\n"

        duration = time.time() - start_time
        log_stream_complete(logger, stream_id, duration, token_count)
        stream_metrics.complete_stream(stream_id, token_count, duration)

        # SSE completion event
        yield f'event: stream-end\ndata: {{"duration": {duration}, "tokens": {token_count}}}\n\n'

    except Exception as e:
        log_stream_error(logger, stream_id, e, "openai_stream_error")
        stream_metrics.error_stream(stream_id, "openai_stream_error")

        # SSE error event
        error_data = f'{{"error": "{str(e)}", "type": "openai_stream_error"}}'
        yield f"event: error\ndata: {error_data}\n\n"


async def stream_gemini_response(
    stream_id: str, user_id: str = None, session_id: str = None
) -> AsyncGenerator[str, None]:
    start_time = time.time()
    token_count = 0

    try:
        log_stream_start(logger, stream_id, user_id, session_id, "gemini")
        stream_metrics.start_stream(stream_id, "gemini", user_id, session_id)

        prompt = make_prompt()
        response = google_genai_client.aio.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt[-1]["content"],
            config={
                "system_instruction": prompt[0]["content"],
                "temperature": 2.0,
            },
        )

        # SSE connection start event
        yield f"event: stream-start\ndata: {stream_id}\n\n"

        async for chunk in response:
            if hasattr(chunk, "text") and chunk.text:
                token = chunk.text
                token_count += 1

                log_token_received(logger, stream_id, token, token_count)
                stream_metrics.update_token_count(stream_id, token_count)

                # Proper SSE format for token data
                yield f"event: token\ndata: {token}\n\n"

        duration = time.time() - start_time
        log_stream_complete(logger, stream_id, duration, token_count)
        stream_metrics.complete_stream(stream_id, token_count, duration)

        # SSE completion event
        yield f'event: stream-end\ndata: {{"duration": {duration}, "tokens": {token_count}}}\n\n'

    except Exception as e:
        log_stream_error(logger, stream_id, e, "gemini_stream_error")
        stream_metrics.error_stream(stream_id, "gemini_stream_error")

        # SSE error event
        error_data = f'{{"error": "{str(e)}", "type": "gemini_stream_error"}}'
        yield f"event: error\ndata: {error_data}\n\n"


@app.post("/stream")
async def stream_llm_response(request: StreamRequest):
    stream_id = uuid4().hex

    logger.info(
        "Stream request received",
        extra={
            "stream_id": stream_id,
            "provider": request.provider.value,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "event_type": "stream_request",
        },
    )

    try:
        if request.provider == LLMProvider.OPENAI:
            generator = stream_openai_response(stream_id, request.user_id, request.session_id)
        elif request.provider == LLMProvider.GEMINI:
            generator = stream_gemini_response(stream_id, request.user_id, request.session_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")

        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Stream-ID": stream_id,
            },
        )

    except Exception as e:
        log_stream_error(logger, stream_id, e, "stream_setup_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    health_status = health_checker.check_system_health()
    return health_status


@app.get("/metrics")
async def get_metrics():
    return {
        "active_streams": stream_metrics.get_active_streams_count(),
        "provider_stats": stream_metrics.get_provider_stats(),
        "recent_streams": len(stream_metrics.get_recent_streams()),
        "error_counts": dict(stream_metrics.error_counts),
    }


@app.get("/metrics/{provider}")
async def get_provider_metrics(provider: str):
    stats = stream_metrics.get_provider_stats(provider)
    if not stats["total_requests"]:
        raise HTTPException(status_code=404, detail=f"No data found for provider: {provider}")
    return stats


@app.get("/")
async def serve_example():
    import os

    from fastapi.responses import FileResponse

    html_path = os.path.join(os.path.dirname(__file__), "..", "example_sse_client.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return {"message": "LLM Streaming Server is running", "endpoints": ["/stream", "/health", "/metrics"]}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_cleanup())
    asyncio.create_task(periodic_health_check())

    logger.info("LLM Streaming Server started", extra={"event_type": "server_startup"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

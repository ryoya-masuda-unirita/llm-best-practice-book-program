from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from src.client.llm_client import LLMProvider
from src.logger import make_logger
from src.model.model import HealthResponse, StreamRequest
from src.service.streaming_service import stream_gemini_response, stream_openai_response

logger = make_logger(__name__)

app = FastAPI(
    title="LLM Streaming API",
    description="OpenAIとGemini APIを使用したストリーミングレスポンスのデモAPI",
    version="1.0.0",
)

# CORS設定（必要に応じて調整してください）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    ヘルスチェックエンドポイント

    Returns:
        サービスのステータス情報
    """
    return HealthResponse(status="healthy", message="LLM Streaming API is running")


@app.post("/stream")
async def stream_response(request: StreamRequest):
    """
    LLMからストリーミングで応答を取得するエンドポイント

    Args:
        request: ストリーミングリクエスト

    Returns:
        StreamingResponse: Server-Sent Events形式のストリーミングレスポンス

    Raises:
        HTTPException: サポートされていないプロバイダーが指定された場合
    """
    logger.info(f"Streaming request received: provider={request.provider}, model={request.model}")

    try:
        if request.provider == LLMProvider.OPENAI:
            model = request.model or "gpt-4o-mini"
            return StreamingResponse(
                stream_openai_response(request.prompt, model=model),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # nginxのバッファリングを無効化
                },
            )

        elif request.provider == LLMProvider.GEMINI:
            model = request.model or "gemini-2.5-flash"
            return StreamingResponse(
                stream_gemini_response(
                    request.prompt,
                    model=model,
                    system_instruction=request.system_instruction,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {request.provider}",
            )

    except Exception as e:
        logger.error(f"Error in stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/openai")
async def stream_openai(request: StreamRequest):
    """
    OpenAI専用のストリーミングエンドポイント

    Args:
        request: ストリーミングリクエスト

    Returns:
        StreamingResponse: Server-Sent Events形式のストリーミングレスポンス
    """
    logger.info(f"OpenAI streaming request received: model={request.model}")

    try:
        model = request.model or "gpt-4o-mini"
        return StreamingResponse(
            stream_openai_response(request.prompt, model=model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Error in OpenAI stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/gemini")
async def stream_gemini(request: StreamRequest):
    """
    Gemini専用のストリーミングエンドポイント

    Args:
        request: ストリーミングリクエスト

    Returns:
        StreamingResponse: Server-Sent Events形式のストリーミングレスポンス
    """
    logger.info(f"Gemini streaming request received: model={request.model}")

    try:
        model = request.model or "gemini-2.5-flash"
        return StreamingResponse(
            stream_gemini_response(
                request.prompt,
                model=model,
                system_instruction=request.system_instruction,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Error in Gemini stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

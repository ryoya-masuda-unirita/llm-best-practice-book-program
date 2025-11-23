from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from src.client.llm_client import LLMProvider, OpenAIModel
from src.logger import make_logger
from src.model.model import CompletionResponse, HealthResponse, StreamRequest
from src.service.streaming_service import get_openai_response, stream_openai_response

logger = make_logger(__name__)

app = FastAPI(
    title="LLM Streaming API",
    description="OpenAI APIを使用したストリーミング/非ストリーミングレスポンスのデモAPI",
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
            model = request.model or OpenAIModel.GPT_4O_MINI
            return StreamingResponse(
                stream_openai_response(request.prompt, model=model),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # nginxのバッファリングを無効化
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


@app.post("/completions", response_model=CompletionResponse)
async def get_completion(request: StreamRequest):
    """
    LLMから非ストリーミングで応答を取得するエンドポイント

    Args:
        request: リクエスト

    Returns:
        CompletionResponse: 完全な応答テキスト

    Raises:
        HTTPException: サポートされていないプロバイダーが指定された場合、またはエラーが発生した場合
    """
    logger.info(f"Completion request received: provider={request.provider}, model={request.model}")

    try:
        if request.provider == LLMProvider.OPENAI:
            model = request.model or OpenAIModel.GPT_4O_MINI
            content = await get_openai_response(request.prompt, model=model)
            return CompletionResponse(
                content=content,
                model=str(model),
                provider="openai",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {request.provider}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in completion endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

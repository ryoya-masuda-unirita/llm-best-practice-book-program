from pydantic import BaseModel, ConfigDict, Field
from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel


class StreamRequest(BaseModel):
    """ストリーミングリクエストのモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
    )

    prompt: str = Field(..., description="ユーザーのプロンプト", min_length=1)
    provider: LLMProvider = Field(
        default=LLMProvider.GEMINI,
        description="使用するLLMプロバイダー (openai または gemini)",
    )
    model: OpenAIModel | GeminiModel | None = Field(
        default=None,
        description="使用するモデル名（未指定の場合はプロバイダーのデフォルトモデルを使用）",
    )
    system_instruction: str | None = Field(
        default=None,
        description="システム命令（Geminiのみ有効）",
    )


class HealthResponse(BaseModel):
    """ヘルスチェックのレスポンスモデル"""

    status: str = Field(..., description="サービスのステータス")
    message: str = Field(..., description="メッセージ")

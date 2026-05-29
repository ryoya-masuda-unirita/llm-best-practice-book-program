from pydantic import BaseModel, ConfigDict, Field
from src.client.llm_client import LLMProvider, OpenAIModel


class StreamRequest(BaseModel):
    """ストリーミングリクエストのモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
    )

    prompt: str = Field(..., description="ユーザーのプロンプト", min_length=1)
    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="使用するLLMプロバイダー (openai)",
    )
    model: OpenAIModel | None = Field(
        default=None,
        description="使用するモデル名（未指定の場合はプロバイダーのデフォルトモデルを使用）",
    )


class CompletionResponse(BaseModel):
    """非ストリーミング完了レスポンスのモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="ignore",
    )

    content: str = Field(..., description="生成されたテキスト")
    model: str = Field(..., description="使用されたモデル名")
    provider: str = Field(..., description="使用されたプロバイダー")


class HealthResponse(BaseModel):
    """ヘルスチェックのレスポンスモデル"""

    status: str = Field(..., description="サービスのステータス")
    message: str = Field(..., description="メッセージ")

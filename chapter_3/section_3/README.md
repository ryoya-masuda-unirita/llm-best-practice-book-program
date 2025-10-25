# Chapter 3 Section 3: LLM APIサービスインターフェイスの分離

## 概要

このプロジェクトは、**インターフェイス分離の原則（Interface Segregation Principle: ISP）** を適用したLLM APIサービスの実装を示すサンプルコードです。OpenAI GPT-4シリーズとGoogle Gemini 2.5シリーズの両方に対応し、機能ごとに独立したインターフェイスを設計することで、保守性と拡張性に優れたシステムを実現します。

テキスト生成（キャラクター生成）とテキスト分類の2つの機能を通じて、LLMサービスを責務ごとに分離し、依存性注入（DI）パターンを用いてサービスを管理する実践的な実装方法を学ぶことができます。

## 機能

- **インターフェイス分離**: 機能ごとに独立したサービスインターフェイスを定義（ITextGenerationService、ITextClassificationService）
- **依存性注入コンテナ**: ServiceContainerによる集中的なサービス管理
- **プランベースのモデル制限**: ユーザープラン（Free/Standard）に応じた利用可能モデルの制御
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **構造化出力**: Pydanticモデルを活用した型安全なLLM応答
- **RESTful API**: FastAPIによる2つの独立したエンドポイント（/generate、/classify）
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **Docker対応**: コンテナ化による簡単なデプロイメント

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_3/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（APIキー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py        # FastAPI アプリケーション
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── interfaces.py        # サービスインターフェイス定義（ISP）
│       ├── container.py         # 依存性注入コンテナ
│       ├── text_generation_service.py    # テキスト生成サービス実装
│       └── text_classification_service.py # テキスト分類サービス実装
├── .env.example                 # 環境変数設定のサンプル
├── .envrc.example               # direnv用環境変数設定のサンプル
├── docker-compose.yml           # Docker Compose設定
├── Dockerfile.web               # Webサーバー用Dockerfile
├── Makefile                     # 開発用コマンド定義
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
└── CLAUDE.md                    # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、インターフェイス分離の原則に基づいた以下の4層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────┐
│      API Layer (llm_server.py)          │
│   - FastAPIエンドポイント                │
│   - リクエスト/レスポンス処理             │
│   - エラーハンドリング                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│   Service Container Layer (container.py)│
│   - 依存性注入コンテナ                   │
│   - サービスインスタンス管理             │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Service Interface Layer            │
│  ┌────────────────────────────────────┐ │
│  │ ITextGenerationService             │ │
│  │  - generate_character()            │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │ ITextClassificationService         │ │
│  │  - classify()                      │ │
│  └────────────────────────────────────┘ │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Concrete Implementation Layer        │
│  - TextGenerationService                │
│  - TextClassificationService            │
│  - プロンプト生成 (prompt.py)           │
│  - LLMクライアント (llm_client.py)      │
│  - データモデル (model.py)              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - 外部API (OpenAI, Gemini)             │
└─────────────────────────────────────────┘
```

### 実装の詳細

#### 1. サービスインターフェイス (`src/service/interfaces.py`)

インターフェイス分離の原則に基づき、機能ごとに独立したインターフェイスを定義します：

```python
from abc import ABC, abstractmethod

class ITextGenerationService(ABC):
    """テキスト生成サービスのインターフェイス"""

    @abstractmethod
    async def generate_character(
        self,
        gender: str,
        age: int,
        additional_instructions: str | None,
        model: str,
        user_plan: UserPlan,
    ) -> CharacterResponse:
        """キャラクターを生成する"""
        pass

class ITextClassificationService(ABC):
    """テキスト分類サービスのインターフェイス"""

    @abstractmethod
    async def classify(
        self,
        text: str,
        categories: list[str],
        model: str,
        user_plan: UserPlan
    ) -> ClassificationResult:
        """テキストを分類する"""
        pass
```

**ポイント**:
- 各インターフェイスは単一の責務のみを持つ（単一責任の原則）
- クライアントは必要なインターフェイスのみに依存できる
- テストやモックの作成が容易になる
- 新しい機能追加時に既存インターフェイスへの影響を最小化

#### 2. プランベースのモデル制限 (`src/client/llm_client.py`)

ユーザープランに応じて利用可能なモデルを制限します：

```python
class UserPlan(StrEnum):
    FREE = "free"
    STANDARD = "standard"

class OpenAIModel(StrEnum):
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1 = "gpt-4.1"
    GPT_5 = "gpt-5"
    # ... その他のモデル

    @staticmethod
    def free_plan_models() -> list[str]:
        """Freeプランで利用可能なモデル"""
        return [OpenAIModel.GPT_4_1_MINI]

    @staticmethod
    def standard_plan_models() -> list[str]:
        """Standardプランで利用可能なモデル（全モデル）"""
        return OpenAIModel.list_str()
```

**制限内容**:
- **Free Plan**: `gpt-4.1-mini`, `gemini-2.5-flash-lite` のみ
- **Standard Plan**: 全モデル利用可能

#### 3. 具象サービス実装 (`src/service/text_generation_service.py`)

インターフェイスを実装した具体的なサービスクラス：

```python
class TextGenerationService(ITextGenerationService):
    """テキスト生成サービスの具象実装"""

    def __init__(self, llm_client: LLMClient, provider: LLMProvider):
        super().__init__(llm_client=llm_client, provider=provider)

    async def generate_character(
        self,
        gender: str,
        age: int,
        additional_instructions: str | None,
        model: str,
        user_plan: UserPlan,
    ) -> CharacterResponse:
        # モデルの利用可能性チェック
        available_models = get_available_models(self.provider, user_plan)
        if model not in available_models:
            raise ValueError(f"Model '{model}' is not available for {user_plan.value} plan")

        # プロンプト生成
        character_request = CharacterRequest(gender=gender, age=age, ...)
        prompt = make_generation_prompt(character_request=character_request)

        # LLM呼び出し
        if self.provider == LLMProvider.OPENAI:
            return await self.request_openai(model=model, prompt=prompt)
        elif self.provider == LLMProvider.GEMINI:
            return await self.request_gemini(model=model, prompt=prompt)
```

**ポイント**:
- インターフェイスで定義された契約を遵守
- プロバイダーごとの実装の違いを内部で吸収
- ユーザープランに基づくモデル制限を実装

#### 4. 依存性注入コンテナ (`src/service/container.py`)

サービスインスタンスを集中管理するコンテナパターン：

```python
class ServiceContainer:
    """LLMサービスインスタンスの管理コンテナ"""

    def __init__(self):
        self._text_generation_services: dict[LLMProvider, ITextGenerationService] = {}
        self._text_classification_services: dict[LLMProvider, ITextClassificationService] = {}
        self._llm_client = LLMClient()
        self._initialize_services()

    def _initialize_services(self):
        """全プロバイダーのサービスを初期化"""
        for provider in LLMProvider:
            self._text_generation_services[provider] = TextGenerationService(
                llm_client=self._llm_client, provider=provider
            )
            self._text_classification_services[provider] = TextClassificationService(
                llm_client=self._llm_client, provider=provider
            )

    def get_text_generation_service(self, provider: LLMProvider) -> ITextGenerationService:
        """テキスト生成サービスを取得"""
        return self._text_generation_services[provider]

    def get_text_classification_service(self, provider: LLMProvider) -> ITextClassificationService:
        """テキスト分類サービスを取得"""
        return self._text_classification_services[provider]

# グローバルコンテナインスタンス
service_container = ServiceContainer()
```

**ポイント**:
- サービスライフサイクルの集中管理
- LLMクライアントの再利用によるリソース効率化
- テスト時のモック注入が容易
- サービスの取得方法を統一

#### 5. FastAPI エンドポイント (`src/api/llm_server.py`)

分離されたサービスインターフェイスを利用するAPIエンドポイント：

```python
@app.post("/generate", response_model=LLMResponse)
async def generate_character(request: LLMRequest):
    """キャラクター生成エンドポイント（ITextGenerationService使用）"""

    # ユーザープランのパース
    user_plan = UserPlan(request.user_plan)

    # コンテナからサービスを取得（依存性注入）
    service = service_container.get_text_generation_service(provider=request.provider)

    # サービスインターフェイス経由で機能を呼び出し
    character = await service.generate_character(
        gender=request.character_request.gender,
        age=request.character_request.age,
        additional_instructions=request.character_request.additional_instructions,
        model=request.model,
        user_plan=user_plan,
    )

    return LLMResponse(character=character, ...)

@app.post("/classify", response_model=TextClassificationResponse)
async def classify_text(request: TextClassificationRequest):
    """テキスト分類エンドポイント（ITextClassificationService使用）"""

    user_plan = UserPlan(request.user_plan)

    # 分類専用のサービスを取得
    service = service_container.get_text_classification_service(provider=request.provider)

    # 分類機能のみを使用
    classification_result = await service.classify(
        text=request.text,
        categories=request.categories,
        model=request.model,
        user_plan=user_plan,
    )

    return TextClassificationResponse(...)
```

**ポイント**:
- 各エンドポイントは必要なインターフェイスのみに依存
- ServiceContainerによるサービスの取得（依存性注入パターン）
- インターフェイス経由の呼び出しによる疎結合
- 一つのサービスの変更が他方に影響しない

#### 6. データモデル (`src/model/model.py`)

Pydanticを使用した型安全なデータモデル：

```python
class UserPlan(StrEnum):
    """ユーザープランの種類"""
    FREE = "free"
    STANDARD = "standard"

class CharacterResponse(BaseModel):
    """キャラクター生成のレスポンスモデル"""
    first_name: str
    last_name: str
    gender: Gender
    age: int
    personalities: list[CharacterPersonality]

class ClassificationResult(BaseModel):
    """テキスト分類の結果モデル"""
    category: str
    confidence: Optional[str]
    reasoning: Optional[str]
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - httpx>=0.28.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .env.exampleをコピーして.envrcを作成
cp .env.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

#### 開発サーバーの起動

```bash
# Makefileを使用（推奨）
make run-llm-server

# または直接uvicornで起動
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

サーバーが起動すると、以下のURLでアクセスできます：
- API: http://localhost:8000
- ドキュメント: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

#### Docker を使用した起動

```bash
# Dockerイメージのビルド
make docker-build

# コンテナの起動
make docker-up

# ログの確認
make docker-logs

# コンテナの停止
make docker-down
```

#### API の使用例

##### 1. ヘルスチェック

```bash
curl http://localhost:8000/health
```

**レスポンス例**:
```json
{
  "status": "healthy",
  "timestamp": 1698765432.123
}
```

##### 2. キャラクター生成（Free Plan）

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "user_plan": "free",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "冒険家で勇敢な性格にしてください"
    }
  }'
```

**レスポンス例**:
```json
{
  "character": {
    "first_name": "アリサ",
    "last_name": "高橋",
    "gender": "female",
    "age": 25,
    "personalities": [
      {
        "short_personality": "勇敢な冒険家",
        "description": "未知の場所や危険な状況でも臆することなく前進する。新しい経験を求め、常に挑戦を楽しむ。"
      },
      {
        "short_personality": "楽観的なリーダー",
        "description": "困難な状況でも明るさを失わず、周囲を勇気づける。チームをまとめ、目標に向かって導く力がある。"
      },
      {
        "short_personality": "好奇心旺盛",
        "description": "世界中の文化や歴史に強い興味を持ち、常に新しい知識を吸収しようとする。質問を恐れず、学び続ける姿勢を持つ。"
      }
    ]
  },
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "processing_time_ms": 1234.56
}
```

##### 3. キャラクター生成（Standard Plan）

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-pro",
    "user_plan": "standard",
    "character_request": {
      "gender": "male",
      "age": 40,
      "additional_instructions": "知的で落ち着いた科学者にしてください"
    }
  }'
```

##### 4. テキスト分類（Free Plan）

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "user_plan": "free",
    "text": "この製品は素晴らしい!期待以上の品質でした。",
    "categories": ["ポジティブ", "ネガティブ", "中立"]
  }'
```

**レスポンス例**:
```json
{
  "category": "ポジティブ",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "processing_time_ms": 567.89,
  "classification_result": {
    "category": "ポジティブ",
    "confidence": "high",
    "reasoning": "「素晴らしい」「期待以上」などの明確に肯定的な表現が含まれているため"
  }
}
```

##### 5. テキスト分類（Standard Plan）

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "user_plan": "standard",
    "text": "配送は早かったですが、商品に小さな傷がありました。",
    "categories": ["ポジティブ", "ネガティブ", "中立", "混在"]
  }'
```

**レスポンス例**:
```json
{
  "category": "混在",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "processing_time_ms": 789.12,
  "classification_result": {
    "category": "混在",
    "confidence": "high",
    "reasoning": "配送の速さについては肯定的だが、商品の傷については否定的な内容が含まれている"
  }
}
```

#### プラン制限のエラー例

Free Planユーザーが上位モデルを使用しようとした場合：

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-5",
    "user_plan": "free",
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": null
    }
  }'
```

**エラーレスポンス**:
```json
{
  "detail": "Model 'gpt-5' is not available for free plan. Available models: gpt-4.1-mini"
}
```

### 出力例

#### コンソールログ出力

```
[2025-10-25 10:30:45] [INFO] [src.service.text_generation_service] Generating character using OpenAI model: gpt-4.1-mini
[2025-10-25 10:30:47] [INFO] [src.api.llm_server] Successfully generated character using openai/gpt-4.1-mini for free plan in 1234.56ms

[2025-10-25 10:31:12] [INFO] [src.service.text_classification_service] Classifying text using Gemini model: gemini-2.5-flash
[2025-10-25 10:31:13] [INFO] [src.service.text_classification_service] Classification result: ポジティブ (confidence: high) - 「素晴らしい」などの肯定的表現が含まれているため
[2025-10-25 10:31:13] [INFO] [src.api.llm_server] Successfully classified text using gemini/gemini-2.5-flash for standard plan in 789.12ms. Result: ポジティブ
```

#### プラン制限の警告ログ

```
[2025-10-25 10:32:00] [WARNING] [src.api.llm_server] Validation error: Model 'gpt-5' is not available for free plan. Available models: gpt-4.1-mini
```

### テスト方法

現在、このセクションには包括的なユニットテストが含まれています。以下の方法でテストを実行します：

#### 1. 全テストの実行

```bash
# uvを使用してpytestを実行
uv run pytest

# 詳細な出力付き
uv run pytest -v

# カバレッジレポート付き
uv run pytest --cov=src --cov-report=html
```

#### 2. 特定のテストファイルのみ実行

```bash
# サービスレイヤーのテストのみ
uv run pytest tests/test_services.py

# APIエンドポイントのテストのみ
uv run pytest tests/test_api.py
```

#### 3. 手動テスト

##### サーバーの動作確認

```bash
# 1. サーバーを起動
make run-llm-server

# 2. 別のターミナルでヘルスチェック
curl http://localhost:8000/health
```

期待される動作：
- HTTPステータス200が返される
- `{"status": "healthy", "timestamp": ...}` のレスポンスが返される

##### OpenAI APIのテスト（Free Plan）

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "user_plan": "free",
    "character_request": {"gender": "male", "age": 30, "additional_instructions": null}
  }'
```

期待される動作：
- HTTPステータス200が返される
- `CharacterResponse`スキーマに準拠したJSONが返される
- `processing_time_ms`フィールドが含まれる

##### Gemini APIのテスト（Standard Plan）

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "user_plan": "standard",
    "text": "素晴らしい製品です!",
    "categories": ["ポジティブ", "ネガティブ", "中立"]
  }'
```

期待される動作：
- HTTPステータス200が返される
- `classification_result`に`category`、`confidence`、`reasoning`が含まれる
- `category`が提供したカテゴリのいずれかと一致する

##### プラン制限の検証

```bash
# Free Planで上位モデルを使用しようとする
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-5",
    "user_plan": "free",
    "character_request": {"gender": "female", "age": 25, "additional_instructions": null}
  }'
```

期待される動作：
- HTTPステータス400（Bad Request）が返される
- エラーメッセージに利用可能なモデルリストが含まれる

##### インターフェイス分離の確認

```bash
# キャラクター生成エンドポイントはITextGenerationServiceのみを使用
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "model": "gpt-4.1-mini", "user_plan": "free", "character_request": {"gender": "male", "age": 30, "additional_instructions": null}}'

# テキスト分類エンドポイントはITextClassificationServiceのみを使用
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "model": "gpt-4.1-mini", "user_plan": "free", "text": "良い商品です", "categories": ["ポジティブ", "ネガティブ"]}'
```

期待される動作：
- 各エンドポイントが独立して正常に動作する
- 一方のサービスの変更が他方に影響しない
- ログから使用しているサービスインターフェイスが確認できる

#### 4. 統合テスト

```bash
# HTTPXを使用した統合テストの実行
uv run pytest tests/integration/

# または、実際のAPIキーを使用したエンドツーエンドテスト
# （.envrcに実際のAPIキーが設定されている必要があります）
uv run pytest tests/e2e/ --run-e2e
```

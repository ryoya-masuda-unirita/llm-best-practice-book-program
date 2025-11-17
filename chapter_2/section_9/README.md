# Chapter 2 Section 5: LLMストリーミングレスポンスの実装

## 概要

このプロジェクトは、**FastAPI**を使用したLLM（大規模言語モデル）の**ストリーミングレスポンス**実装を示すサンプルコードです。OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応し、Server-Sent Events (SSE)形式でリアルタイムにテキスト生成結果をクライアントに配信します。

ストリーミング機能により、ユーザーは完全な応答を待つことなく、生成されたテキストを逐次的に受け取ることができ、より良いユーザーエクスペリエンスを提供できます。

## 機能

- **ストリーミングレスポンス**: Server-Sent Events (SSE)形式でリアルタイムにテキストを配信
- **FastAPI統合**: 高性能な非同期WebフレームワークによるAPI実装
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **複数のエンドポイント**: 統合エンドポイントとプロバイダー専用エンドポイントを提供
- **非同期処理**: async/awaitパターンによる効率的なストリーミング処理
- **CORS対応**: クロスオリジンリクエストのサポート
- **エラーハンドリング**: 堅牢なエラー処理とロギング
- **テストクライアント**: ストリーミングAPIをテストするためのCLIツール
- **使用例**: さまざまなユースケースを示すサンプルコード

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_5/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py               # FastAPIアプリケーション（メインAPI）
│   ├── service/
│   │   ├── __init__.py
│   │   └── streaming_service.py # ストリーミングロジック
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   └── model/
│       ├── __init__.py
│       └── model.py             # Pydanticデータモデル定義
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytestフィクスチャ設定
│   ├── test_api.py              # APIエンドポイントのテスト
│   ├── test_models.py           # データモデルのテスト
│   └── test_streaming_service.py # ストリーミングサービスのテスト
├── .envrc.example               # 環境変数設定のサンプル
├── __init__.py                  # パッケージルート初期化
├── Makefile                     # 共通タスク定義
├── pyproject.toml               # プロジェクト依存関係
├── pytest.ini                   # pytest設定ファイル
├── run_server.py                # サーバー起動スクリプト
├── test_client.py               # テストクライアントCLI
├── README.md                    # このファイル
└── CLAUDE.md                    # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、以下の4層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────┐
│         API Layer (api/)                │
│  - FastAPI アプリケーション              │
│  - エンドポイント定義                    │
│  - リクエスト/レスポンスハンドリング     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Service Layer (service/)           │
│  - ストリーミングロジック                │
│  - 非同期ジェネレータ実装                │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Business Logic Layer               │
│  - LLMクライアント管理 (client/)        │
│  - データモデル (model/)                │
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

#### 1. FastAPIアプリケーション (`src/api/app.py`)

FastAPIを使用してRESTful APIを提供します：

```python
app = FastAPI(
    title="LLM Streaming API",
    description="OpenAIとGemini APIを使用したストリーミングレスポンスのデモAPI",
    version="1.0.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**提供されるエンドポイント**:

- `GET /health` - ヘルスチェックエンドポイント
- `POST /stream` - 統合ストリーミングエンドポイント（プロバイダーを選択可能）
- `POST /stream/openai` - OpenAI専用ストリーミングエンドポイント
- `POST /stream/gemini` - Gemini専用ストリーミングエンドポイント

#### 2. ストリーミングサービス (`src/service/streaming_service.py`)

非同期ジェネレータを使用してストリーミング処理を実装します：

##### OpenAI実装

```python
async def stream_openai_response(prompt: str, model: str = "gpt-4o-mini") -> AsyncIterator[str]:
    """OpenAI APIからストリーミングで応答を取得"""
    stream = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        temperature=1.0,
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            yield content
            await asyncio.sleep(0.01)  # イベントループのブロッキング防止
```

**特徴**:
- `stream=True`でストリーミングモードを有効化
- `async for`でチャンクを逐次処理
- `yield`でクライアントにデータを送信

##### Gemini実装

```python
async def stream_gemini_response(
    prompt: str,
    model: str = "gemini-2.5-flash",
    system_instruction: str | None = None,
) -> AsyncIterator[str]:
    """Gemini APIからストリーミングで応答を取得"""
    config = GenerateContentConfig(temperature=2.0)

    if system_instruction:
        config = GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=2.0,
        )

    response = google_genai_client.models.generate_content_stream(
        model=model,
        contents=prompt,
        config=config,
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text
```

**特徴**:
- `generate_content_stream`でストリーミング応答を取得
- システム命令のサポート
- 同期的なイテレーション（Gemini SDKの仕様）

#### 3. APIエンドポイント実装

```python
@app.post("/stream")
async def stream_response(request: StreamRequest):
    """統合ストリーミングエンドポイント"""
    logger.info(f"Streaming request received: provider={request.provider}")

    if request.provider == LLMProvider.OPENAI:
        model = request.model or "gpt-4o-mini"
        return StreamingResponse(
            stream_openai_response(request.prompt, model=model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # nginxのバッファリング無効化
            },
        )
    # Gemini実装も同様
```

**ポイント**:
- `StreamingResponse`でSSE形式の応答を返す
- 適切なヘッダーでキャッシュとバッファリングを制御
- プロバイダーに応じて適切なサービス関数を呼び出し

#### 4. データモデル (`src/model/model.py`)

Pydanticモデルでリクエスト/レスポンスを定義します：

```python
class StreamRequest(BaseModel):
    """ストリーミングリクエストのモデル"""
    prompt: str = Field(..., description="ユーザーのプロンプト", min_length=1)
    provider: LLMProvider = Field(
        default=LLMProvider.GEMINI,
        description="使用するLLMプロバイダー (openai または gemini)",
    )
    model: str | None = Field(
        default=None,
        description="使用するモデル名（未指定の場合はプロバイダーのデフォルトモデル）",
    )
    system_instruction: str | None = Field(
        default=None,
        description="システム命令（Geminiのみ有効）",
    )

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンスのモデル"""
    status: str
    message: str
```

**特徴**:
- 型安全なリクエスト検証
- デフォルト値のサポート
- 詳細なフィールド説明

#### 5. テストクライアント (`test_client.py`)

ストリーミングAPIをテストするためのCLIツール：

```python
async def stream_request(url: str, prompt: str, provider: str = "gemini"):
    """APIサーバーにストリーミングリクエストを送信"""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            # ストリーミングレスポンスを逐次的に表示
            async for chunk in response.content.iter_any():
                if chunk:
                    text = chunk.decode("utf-8")
                    print(text, end="", flush=True)
```

**特徴**:
- `aiohttp`を使用した非同期HTTPクライアント
- リアルタイムでチャンクを表示
- 使いやすいCLIインターフェース

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - aiohttp>=3.11.17
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - click>=8.3.0

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

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

3. **開発ツール（オプション）**

プロジェクトには開発タスクを簡素化するMakefileが含まれています：

```bash
# コードのリント（自動修正付き）
make lint

# コードのフォーマット
make fmt

# リントとフォーマットの両方を実行
make fix

# 型チェック
make mypy
```

### 使用方法、実行方法

#### 1. サーバーの起動

```bash
# デフォルト設定で起動（127.0.0.1:8000）
python run_server.py

# カスタムホストとポートを指定
python run_server.py --host 0.0.0.0 --port 8080

# 開発モード（自動リロード有効）
python run_server.py --reload
```

**出力例**:
```
Starting LLM Streaming API server on 127.0.0.1:8000
Press CTRL+C to quit
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

#### 2. テストクライアントの使用

別のターミナルでテストクライアントを実行します：

```bash
# Gemini APIを使用（デフォルト）
python test_client.py --prompt "Pythonの非同期プログラミングについて説明してください"

# OpenAI APIを使用
python test_client.py --provider openai --prompt "AIの未来について教えて"

# カスタムモデルを指定
python test_client.py --provider openai --model gpt-4o --prompt "こんにちは"

# システム命令を使用（Geminiのみ）
python test_client.py --provider gemini \
  --prompt "今日のランチにおすすめのメニューは？" \
  --system-instruction "あなたは健康的な食事を提案する栄養士です"

# カスタムURLを指定
python test_client.py --url http://localhost:8080/stream --prompt "こんにちは"
```

#### 3. APIの直接利用

##### curlを使用

```bash
# 統合エンドポイント
curl -X POST http://127.0.0.1:8000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Pythonについて教えてください",
    "provider": "gemini"
  }'

# OpenAI専用エンドポイント
curl -X POST http://127.0.0.1:8000/stream/openai \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "こんにちは",
    "model": "gpt-4o-mini"
  }'
```

##### Pythonスクリプトから利用

```python
import asyncio
import aiohttp

async def test_streaming():
    url = "http://127.0.0.1:8000/stream"
    payload = {
        "prompt": "ストリーミングAPIの利点を教えてください",
        "provider": "gemini"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            async for chunk in response.content.iter_any():
                if chunk:
                    print(chunk.decode("utf-8"), end="", flush=True)

asyncio.run(test_streaming())
```

### 出力例

#### テストクライアントの実行結果

```
============================================================
Provider: gemini
Prompt: Pythonの非同期プログラミングについて説明してください
============================================================

Response:
------------------------------------------------------------
Pythonの非同期プログラミングは、複数のタスクを並行して実行する
ための強力な手法です。asyncioモジュールを使用することで、
I/O待機時間を有効活用し、アプリケーションのパフォーマンスを
大幅に向上させることができます。

主要な概念：

1. **async/await構文**: 非同期関数を定義し、await で非同期
   処理を待機します。

2. **イベントループ**: すべての非同期タスクを管理・実行する
   中心的な機構です。

3. **コルーチン**: async def で定義された特殊な関数で、
   実行を一時停止・再開できます。

非同期プログラミングは、Webスクレイピング、API呼び出し、
データベースアクセスなど、I/Oバウンドな処理に特に効果的です。
------------------------------------------------------------
Stream completed successfully!
```

#### ヘルスチェックの実行

```bash
curl http://127.0.0.1:8000/health
```

**レスポンス**:
```json
{
  "status": "healthy",
  "message": "LLM Streaming API is running"
}
```

### テスト方法

このプロジェクトには、ユニットテストと手動テストの両方が含まれています。

#### ユニットテストの実行

プロジェクトには以下のユニットテストが含まれています：

```bash
# すべてのテストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=src --cov-report=html

# 特定のテストファイルのみ実行
pytest tests/test_api.py
pytest tests/test_models.py
pytest tests/test_streaming_service.py

# 詳細な出力で実行
pytest -v
```

**テスト内容**:
- `tests/test_api.py`: FastAPIエンドポイントのテスト
- `tests/test_models.py`: Pydanticモデルのバリデーションテスト
- `tests/test_streaming_service.py`: ストリーミングサービスのロジックテスト

#### 手動テスト

#### 1. サーバーの起動確認

```bash
python run_server.py
# 別のターミナルで
curl http://127.0.0.1:8000/health
```

期待される動作：
- サーバーが正常に起動する
- ヘルスチェックが `{"status":"healthy",...}` を返す

#### 2. OpenAI ストリーミングのテスト

```bash
python test_client.py --provider openai --prompt "Hello, world!"
```

期待される動作：
- OpenAI APIに接続してストリーミング応答を受信
- テキストがリアルタイムで表示される
- エラーなく完了する

#### 3. Gemini ストリーミングのテスト

```bash
python test_client.py --provider gemini --prompt "こんにちは"
```

期待される動作：
- Gemini APIに接続してストリーミング応答を受信
- テキストがリアルタイムで表示される
- エラーなく完了する

#### 4. エラーハンドリングのテスト

```bash
# 空のプロンプトでエラーをテスト
curl -X POST http://127.0.0.1:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "", "provider": "gemini"}'
```

期待される動作：
- バリデーションエラーが返される
- 適切なHTTPステータスコード（422）が返される

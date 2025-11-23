# Chapter 2 Section 9: LLMストリーミング・非ストリーミングレスポンスの実装

## 概要

このプロジェクトは、**FastAPI**を使用したLLM（大規模言語モデル）の**ストリーミング・非ストリーミングレスポンス**実装を示すサンプルコードです。OpenAI GPT-4o-miniに対応し、以下の2つのモードでテキスト生成結果をクライアントに配信します：

- **ストリーミングモード**: Server-Sent Events (SSE)形式でリアルタイムにテキストを配信
- **非ストリーミングモード**: 完全な応答を一度に返す従来型のレスポンス

ストリーミング機能により、ユーザーは完全な応答を待つことなく、生成されたテキストを逐次的に受け取ることができ、より良いユーザーエクスペリエンスを提供できます。一方、非ストリーミングモードは、完全な応答が必要な場合や、シンプルな実装が求められる場合に適しています。

## 機能

- **ストリーミングレスポンス**: Server-Sent Events (SSE)形式でリアルタイムにテキストを配信
- **非ストリーミングレスポンス**: 完全な応答を一度に返すJSONレスポンス
- **FastAPI統合**: 高性能な非同期WebフレームワークによるAPI実装
- **OpenAI API対応**: GPT-4o-mini, GPT-4oなどのOpenAIモデルをサポート
- **複数のエンドポイント**: ストリーミング (`/stream`) と非ストリーミング (`/completions`) を提供
- **非同期処理**: async/awaitパターンによる効率的な処理
- **CORS対応**: クロスオリジンリクエストのサポート
- **エラーハンドリング**: 堅牢なエラー処理とロギング
- **統合テストクライアント**: ストリーミング・非ストリーミング両方をサポートするCLIツール
- **包括的なテスト**: pytestによるユニットテスト・統合テスト

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_9/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py               # FastAPIアプリケーション（メインAPI）
│   ├── service/
│   │   ├── __init__.py
│   │   └── streaming_service.py # ストリーミング・非ストリーミングロジック
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
├── pyproject.toml               # プロジェクト依存関係
├── pytest.ini                   # pytest設定ファイル
├── run_server.py                # サーバー起動スクリプト
├── example_client.py            # 統合テストクライアントCLI
└── README.md                    # このファイル
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
    description="OpenAI APIを使用したストリーミング/非ストリーミングレスポンスのデモAPI",
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
- `POST /stream` - ストリーミングエンドポイント（SSE形式）
- `POST /completions` - 非ストリーミングエンドポイント（JSON形式）

#### 2. ストリーミング・非ストリーミングサービス (`src/service/streaming_service.py`)

非同期ジェネレータとawait呼び出しを使用して両方のレスポンス形式を実装します：

##### ストリーミング実装

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

##### 非ストリーミング実装

```python
async def get_openai_response(prompt: str, model: str = "gpt-4o-mini") -> str:
    """OpenAI APIから非ストリーミングで完全な応答を取得"""
    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            temperature=1.0,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Error in get_openai_response: {e}")
        raise
```

**特徴**:
- `stream=False`で非ストリーミングモードを使用
- 完全な応答を文字列として返す
- シンプルな実装で即座に完全な結果を取得

#### 3. APIエンドポイント実装

##### ストリーミングエンドポイント

```python
@app.post("/stream")
async def stream_response(request: StreamRequest):
    """ストリーミングエンドポイント"""
    logger.info(f"Streaming request received: provider={request.provider}")

    if request.provider == LLMProvider.OPENAI:
        model = request.model or OpenAIModel.GPT_4O_MINI
        return StreamingResponse(
            stream_openai_response(request.prompt, model=model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # nginxのバッファリング無効化
            },
        )
```

**ポイント**:
- `StreamingResponse`でSSE形式の応答を返す
- 適切なヘッダーでキャッシュとバッファリングを制御
- リアルタイムでテキストを配信

##### 非ストリーミングエンドポイント

```python
@app.post("/completions", response_model=CompletionResponse)
async def get_completion(request: StreamRequest):
    """非ストリーミング完了エンドポイント"""
    logger.info(f"Completion request received: provider={request.provider}")

    if request.provider == LLMProvider.OPENAI:
        model = request.model or OpenAIModel.GPT_4O_MINI
        content = await get_openai_response(request.prompt, model=model)
        return CompletionResponse(
            content=content,
            model=str(model),
            provider="openai",
        )
```

**ポイント**:
- JSON形式で完全な応答を返す
- Pydanticモデルによる型安全なレスポンス
- シンプルで実装が容易

#### 4. データモデル (`src/model/model.py`)

Pydanticモデルでリクエスト/レスポンスを定義します：

```python
class StreamRequest(BaseModel):
    """ストリーミング/非ストリーミングリクエストのモデル"""
    prompt: str = Field(..., description="ユーザーのプロンプト", min_length=1)
    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="使用するLLMプロバイダー (openai)",
    )
    model: OpenAIModel | None = Field(
        default=None,
        description="使用するモデル名（未指定の場合はデフォルトモデル）",
    )

class CompletionResponse(BaseModel):
    """非ストリーミング完了レスポンスのモデル"""
    content: str = Field(..., description="生成されたテキスト")
    model: str = Field(..., description="使用されたモデル名")
    provider: str = Field(..., description="使用されたプロバイダー")

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンスのモデル"""
    status: str = Field(..., description="サービスのステータス")
    message: str = Field(..., description="メッセージ")
```

**特徴**:
- 型安全なリクエスト・レスポンス検証
- デフォルト値のサポート
- 詳細なフィールド説明
- `CompletionResponse`で非ストリーミング応答を構造化

#### 5. 統合テストクライアント (`example_client.py`)

ストリーミング・非ストリーミング両方をサポートするCLIツール：

##### ストリーミングリクエスト

```python
async def stream_request(url: str, prompt: str, model: str | None = None):
    """APIサーバーにストリーミングリクエストを送信"""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            # ストリーミングレスポンスを逐次的に表示
            async for chunk in response.content.iter_any():
                if chunk:
                    text = chunk.decode("utf-8")
                    print(text, end="", flush=True)
```

##### 非ストリーミングリクエスト

```python
async def completion_request(url: str, prompt: str, model: str | None = None):
    """APIサーバーに非ストリーミングリクエストを送信"""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            # 完全なレスポンスをJSON形式で取得
            response_data = await response.json()
            print(response_data["content"])
```

**特徴**:
- `aiohttp`を使用した非同期HTTPクライアント
- ストリーミング・非ストリーミング両方のモードをサポート
- `--mode`オプションでモード切り替え
- リアルタイムでチャンクを表示（ストリーミング）
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

##### ストリーミングモード（デフォルト）

```bash
# 基本的な使用方法
python example_client.py --prompt "Pythonの非同期プログラミングについて説明してください"

# モデルを明示的に指定
python example_client.py --model gpt-4o --prompt "AIの未来について教えて"

# カスタムURLを指定
python example_client.py --url http://localhost:8080/stream --prompt "こんにちは"
```

##### 非ストリーミングモード

```bash
# 非ストリーミングモードを使用
python example_client.py --mode completion --prompt "Pythonについて教えてください"

# カスタムモデルを指定
python example_client.py --mode completion --model gpt-4o --prompt "こんにちは"

# カスタムURLを指定
python example_client.py --mode completion --url http://localhost:8080/completions --prompt "こんにちは"
```

#### 3. APIの直接利用

##### curlを使用

**ストリーミングエンドポイント**:

```bash
curl -X POST http://127.0.0.1:8000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Pythonについて教えてください",
    "provider": "openai"
  }'

# カスタムモデルを指定
curl -X POST http://127.0.0.1:8000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "こんにちは",
    "provider": "openai",
    "model": "gpt-4o"
  }'
```

**非ストリーミングエンドポイント**:

```bash
curl -X POST http://127.0.0.1:8000/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Pythonについて教えてください",
    "provider": "openai"
  }'

# カスタムモデルを指定
curl -X POST http://127.0.0.1:8000/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "こんにちは",
    "provider": "openai",
    "model": "gpt-4o"
  }'
```

##### Pythonスクリプトから利用

**ストリーミングリクエスト**:

```python
import asyncio
import aiohttp

async def test_streaming():
    url = "http://127.0.0.1:8000/stream"
    payload = {
        "prompt": "ストリーミングAPIの利点を教えてください",
        "provider": "openai"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            async for chunk in response.content.iter_any():
                if chunk:
                    print(chunk.decode("utf-8"), end="", flush=True)

asyncio.run(test_streaming())
```

**非ストリーミングリクエスト**:

```python
import asyncio
import aiohttp

async def test_completion():
    url = "http://127.0.0.1:8000/completions"
    payload = {
        "prompt": "非ストリーミングAPIの利点を教えてください",
        "provider": "openai"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            print(result["content"])
            print(f"\nModel: {result['model']}")
            print(f"Provider: {result['provider']}")

asyncio.run(test_completion())
```

### 出力例

#### ストリーミングモードの実行結果

```
============================================================
Provider: openai
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

#### 非ストリーミングモードの実行結果

```
============================================================
Provider: openai
Prompt: Pythonについて教えてください
============================================================

Response:
------------------------------------------------------------
Pythonは、シンプルで読みやすい構文を持つ高水準プログラミング言語です。
1991年にGuido van Rossumによって開発され、現在では世界中で広く使用されています。

主な特徴：
- 読みやすく書きやすい文法
- 豊富な標準ライブラリとサードパーティパッケージ
- データサイエンス、Web開発、自動化など幅広い用途
- クロスプラットフォーム対応
- 動的型付け

Pythonは初心者にも学びやすく、同時にプロフェッショナルな開発にも
適した強力な言語です。
------------------------------------------------------------
Completion request successful!
Model used: gpt-4o-mini
Provider: openai
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

## ストリーミング vs 非ストリーミング

### それぞれの特徴と使い分け

| 特徴 | ストリーミング (`/stream`) | 非ストリーミング (`/completions`) |
|------|---------------------------|----------------------------------|
| **レスポンス形式** | Server-Sent Events (SSE) | JSON |
| **配信方式** | リアルタイム・逐次配信 | 完全な応答を一度に返す |
| **初回応答速度** | 速い（即座に開始） | 遅い（完全生成後） |
| **ユーザー体験** | リアルタイム表示で待ち時間が短く感じる | 生成完了まで待機が必要 |
| **実装の複雑さ** | 高い（チャンク処理が必要） | 低い（通常のHTTPリクエスト） |
| **クライアント要件** | SSE対応が必要 | 標準的なHTTPクライアント |
| **キャンセル** | 途中で接続を切断可能 | 完全生成まで待つ必要がある |
| **適用場面** | チャットボット、リアルタイムUI | バッチ処理、API統合、完全な応答が必要な場合 |

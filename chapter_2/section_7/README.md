# Chapter 2 Section 7: LLM出力をストリーミングにする

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

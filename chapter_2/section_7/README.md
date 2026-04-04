# Chapter 2 Section 7: LLM出力をストリーミングにする

## 概要

このプロジェクトは、**FastAPI**を使用したLLM（大規模言語モデル）の**ストリーミング・非ストリーミングレスポンス**実装を示すサンプルコードです。OpenAI GPT-5.4-miniに対応し、以下の2つのモードでテキスト生成結果をクライアントに配信します：

- **ストリーミングモード**: Server-Sent Events (SSE)形式でリアルタイムにテキストを配信
- **非ストリーミングモード**: 完全な応答を一度に返す従来型のレスポンス

ストリーミング機能により、ユーザーは完全な応答を待つことなく、生成されたテキストを逐次的に受け取ることができ、より良いユーザーエクスペリエンスを提供できます。一方、非ストリーミングモードは、完全な応答が必要な場合や、シンプルな実装が求められる場合に適しています。

## 機能

- **ストリーミングレスポンス**: Server-Sent Events (SSE)形式でリアルタイムにテキストを配信
- **非ストリーミングレスポンス**: 完全な応答を一度に返すJSONレスポンス
- **FastAPI統合**: 高性能な非同期WebフレームワークによるAPI実装
- **OpenAI API対応**: GPT-5.4-mini, GPT-5.4などのOpenAIモデルをサポート
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
# uvを使用
uv sync
```

### 使用方法、実行方法

#### 1. サーバーの起動

```bash
# デフォルト設定で起動（127.0.0.1:8000）
$ uv run python run_server.py

# カスタムホストとポートを指定
$ uv run python run_server.py --host 0.0.0.0 --port 8080

# 開発モード（自動リロード有効）
$ uv run python run_server.py --reload

$ uv run python run_server.py --help
Usage: run_server.py [OPTIONS]

  FastAPI サーバーを起動します

Options:
  --host TEXT     ホストアドレス
  --port INTEGER  ポート番号
  --reload        自動リロード機能を有効化
  --help          Show this message and exit.
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
$ uv run python example_client.py --help                                                  
Usage: example_client.py [OPTIONS]

  LLM APIのサンプルクライアント

Options:
  --mode [stream|completion]  リクエストモード: stream（ストリーミング）またはcompletion（非ストリーミング）
  --url TEXT                  APIエンドポイントのURL（未指定の場合はmodeに応じて自動設定）
  --prompt TEXT               LLMに送信するプロンプト  [required]
  --model TEXT                使用するモデル名（オプション）
  --help                      Show this message and exit.

# 基本的な使用方法
$ uv run python example_client.py --prompt "Pythonの非同期プログラミングについて説明してください"

# モデルを明示的に指定
$ uv run python example_client.py --model gpt-5-mini --prompt "AIの未来について教えて"
```

##### 非ストリーミングモード

```bash
# 非ストリーミングモードを使用
$ uv run python example_client.py --mode completion --prompt "Pythonについて教えてください"

# カスタムモデルを指定
$ uv run python example_client.py --mode completion --model gpt-5-mini --prompt "こんにちは"
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
    "model": "gpt-5-mini"
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
    "model": "gpt-5-mini"
  }'
```

### 出力例

#### ストリーミングモードの実行結果

```bash
$ uv run python example_client.py --prompt "日本の未来について" 

============================================================
Provider: openai
Prompt: 日本の未来について
============================================================

Response:
------------------------------------------------------------
日本の未来については、さまざまな側面から考えることができます。以下にいくつかの重要なポイントを挙げてみます。

1. **高齢化社会**: 日本は世界でも有数の高齢化が進んでいる国です。これにより、福祉制度や医療制度の見直しが必要となり、労働力不足も懸念されています。高齢者が活躍できる社会を構築するための施策が求められています。

2. **経済の変化**: テクノロジーの発展やグローバル化により、日本の産業構造は大きく変化しています。特にAIやロボティクスの導入が進むことで、効率化や新たなビジネスモデルの創出が期待されています。

3. **環境問題**: 環境問題への対応は日本にとって重要な課題です。再生可能エネルギーの導入や脱炭素化の取り組みが進められ、持続可能な社会の実現を目指しています。

4. **国際関係**: 地政学的な緊張が高まる中、日本の外交政策や安全保障戦略も重要です。周辺国との関係や国際的な協力が、一層重要になるでしょう。

5. **文化と社会**: 日本の伝統文化と現代文化の融合が進み、国際的な影響も受けながら新しい文化が生まれています。これにより、国内外からの観光客を惹きつける要素にもなっています。

これらの課題や展望に対処するためには、政府、企業、市民が一体となって取り組むことが不可欠です。未来の日本は、これらの要素をどうバランスさせていくかにかかっ ています。
------------------------------------------------------------
Stream completed successfully!
```

#### 非ストリーミングモードの実行結果

```bash
$ uv run python example_client.py --mode completion --prompt "日本の未来について"          

============================================================
Provider: openai
Prompt: 日本の未来について
============================================================

Response:
------------------------------------------------------------
日本の未来について考える際、いくつかの重要な要素が浮かび上がります。以下は、そのいくつかの側面です。

1. **高齢化社会と人口減少**: 日本は急速に高齢化が進んでおり、労働力の減少や社会保障制度への影響が懸念されています。この問題を解決するためには、移民政策の見直しや、AI・ロボット技術の導入が考えられます。

2. **経済の変革**: 世界経済の変化に伴い、日本経済も新しいビジネスモデルや産業の育成が求められています。特にデジタル化やグリーン経済が進展する中で、企業の競争力を高めるための取り組みが重要です。

3. **環境問題**: 環境への配慮がますます重要視される中、日本も脱炭素社会の実現に向けた努力が必要です。再生可能エネルギーの導入や、プラスチック削減などの取り組みが進められています。

4. **国際関係と安全保障**: 地政学的な緊張が高まる中、日本はアジアの中での役割や、アメリカとの同盟関係を再評価する必要があります。また、地域の安全保障のために、協力や対話を重視した外交が求められています。

5. **文化と社会の多様性**: グローバル化が進む中で、日本の文化や社会も多様性を受け入れ、多くの異なる価値観を尊重する姿勢が必要です。これは、国際理解や共生社会の実現につながります。

日本の未来は、これらの課題にどのように取り組むかによって大きく変わるでしょう。政府や企業、そして市民一人ひとりが積極的に関与することで、より良い未来を築い ていくことが可能です。

------------------------------------------------------------
Completion request successful!
Model used: gpt-5.4-mini
Provider: openai
```

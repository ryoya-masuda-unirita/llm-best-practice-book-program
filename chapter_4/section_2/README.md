# Chapter 4 Section 1: LLMシステムのストレージと実行を分離する(CQRSパターンの応用)

## 概要

このプロジェクトは、**LLMシステムのストレージと実行を分離する(CQRSパターンの応用)** を用いたLLMシステムの実装サンプルです。キャッシュやデータベースへのアクセス処理と、LLM APIの呼び出し処理を疎結合に保つことで、コンポーネントの独立性を高め、柔軟でテストしやすく、保守性の高いシステムを実現します。

本実装では、FastAPIベースのREST APIサーバーを提供し、OpenAI GPTモデル（GPT-5、GPT-4.1、GPT-4oシリーズ）に対応しています。また、インメモリキャッシュとRedisキャッシュの両方をサポートし、環境に応じて柔軟に切り替えることができます。

## 機能

- **ストレージと実行の分離**: Bridge Patternを用いた責務の明確な分離
- **キャッシング機能**: インメモリとRedisベースの2種類のキャッシュバックエンドをサポート
- **OpenAI対応**: OpenAI GPTモデル（GPT-5、GPT-4.1、GPT-4oシリーズ）をサポート
- **依存性注入（DI）**: Factoryパターンによる柔軟なサービスインスタンス管理
- **REST APIサーバー**: FastAPIによる高性能なAPIエンドポイント
- **キャッシュメトリクス**: キャッシュヒット率、ミス数などの監視機能
- **キャッシュ無効化**: 任意のキャッシュキーを手動で無効化する機能
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **Docker対応**: Docker Composeによる簡単なデプロイメント

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_2/
├── src/
│   ├── __init__.py                # パッケージ初期化
│   ├── config.py                  # 設定管理（API キー、キャッシュ設定）
│   ├── logger.py                  # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py          # FastAPI サーバー実装
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLMクライアント初期化
│   │   └── cache_client.py        # キャッシュクライアント（Redis、インメモリ）
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py               # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py              # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── interface.py           # ILLMService インターフェース（Bridge）
│       ├── storage.py             # ストレージ層実装（キャッシュ）
│       ├── execution.py           # 実行層実装（LLM API呼び出し）
│       └── factory.py             # Factoryパターン実装
├── .env.example                    # 環境変数設定のサンプル
├── .envrc.example                  # direnv設定のサンプル
├── docker-compose.yml              # Docker Compose設定
├── Dockerfile.web                  # Webサーバー用Dockerfile
├── Makefile                        # 開発用コマンド
├── pyproject.toml                  # プロジェクト依存関係
├── README.md                       # このファイル
└── CLAUDE.md                       # プロジェクト設計書

```

### アーキテクチャ

本プロジェクトは、**Bridge Pattern** を中核とした3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────┐
│        API Layer (FastAPI)                      │
│    - エンドポイント定義                         │
│    - リクエスト/レスポンス処理                  │
│    - ヘルスチェック、メトリクス                 │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│        Service Layer (Bridge Pattern)           │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │   ILLMService (Interface)                │  │
│  │   - generate_character()                 │  │
│  │   - invalidate_cache()                   │  │
│  └──────────────┬───────────┬────────────────┘  │
│                 │           │                    │
│    ┌────────────▼──────┐  ┌▼──────────────────┐ │
│    │ CachedLLMService  │  │ ExecutionLLMService│ │
│    │ (Storage Layer)   │  │ (Execution Layer)  │ │
│    │ - キャッシュ管理  │  │ - OpenAI API呼び出し│ │
│    │ - メトリクス収集  │  │                    │ │
│    └────────────┬──────┘  └────────────────────┘ │
│                 │                                 │
│    ┌────────────▼──────────────┐                 │
│    │  LLMServiceFactory (DI)   │                 │
│    │  - サービスインスタンス作成│                 │
│    │  - 環境に応じた実装切替   │                 │
│    └───────────────────────────┘                 │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│      Infrastructure Layer                       │
│  - Cache Backend (InMemory / Redis)             │
│  - LLM Client (OpenAI)                          │
│  - Config (環境変数管理)                        │
│  - Logger (ログ出力)                            │
└─────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - redis>=7.0.0
  - click>=8.3.0
  - httpx>=0.28.1
- **オプション**:
  - Docker & Docker Compose（コンテナデプロイメント用）
  - Redis Server（Redisキャッシュ使用時）

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env

# エディタで.envを開き、APIキーを設定
# .env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# キャッシュ設定（デフォルト）
CACHE_ENABLED=true
CACHE_BACKEND=memory
CACHE_TTL=3600

# Redis設定（CACHE_BACKEND=redisの場合）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

3. **Redisのセットアップ（Redisキャッシュ使用時のみ）**

```bash
# ローカルでRedisを起動
docker run -d -p 6379:6379 redis:latest

# または、Homebrewでインストール（macOS）
brew install redis
brew services start redis
```

### 使用方法、実行方法

#### 方法1: ローカル実行

```bash
# LLM APIサーバーを起動
make run-llm-server

# または直接uvicornで起動
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

#### 方法2: Docker Compose実行

```bash
# Dockerイメージをビルド
make docker-build

# サービスを起動（APIサーバー + Redis）
make docker-up

# ログを確認
make docker-logs

# サービスを停止
make docker-down
```

#### API使用例

サーバーが起動したら、以下のようにAPIを呼び出します：

**1. キャラクター生成（OpenAI）**

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": "ファンタジー世界の魔法使い"
    }
  }'
```

**2. ヘルスチェック**

```bash
curl http://localhost:8000/health
```

**3. キャッシュメトリクスの確認**

```bash
curl http://localhost:8000/metrics
```

**4. キャッシュの無効化**

```bash
curl -X DELETE "http://localhost:8000/cache/{cache_key}"
```

#### APIドキュメント

サーバー起動後、以下のURLで自動生成されたAPIドキュメントを参照できます：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 出力例

#### 1. キャラクター生成レスポンス

```json
{
  "character": {
    "first_name": "アリス",
    "last_name": "スターフィールド",
    "gender": "female",
    "age": 22,
    "personalities": [
      {
        "short_personality": "好奇心旺盛な探究者",
        "description": "未知の領域や新しい発見に対して常に興味を持ち、リスクを恐れずチャレンジする。"
      },
      {
        "short_personality": "冷静な判断力",
        "description": "緊急事態でも感情に流されず、論理的かつ迅速に最適解を導き出す能力を持つ。"
      },
      {
        "short_personality": "チームプレイヤー",
        "description": "仲間との協力を重視し、全員が安全に任務を遂行できるようサポートする。"
      }
    ]
  },
  "provider": "openai",
  "model": "gpt-4o-mini",
  "processing_time_ms": 1234.56
}
```

#### 2. キャッシュメトリクスレスポンス

```json
{
  "cache_enabled": true,
  "cache_backend": "redis",
  "cache_hits": 42,
  "cache_misses": 8,
  "cache_hit_rate": 0.84,
  "total_requests": 50
}
```

#### 3. サーバーログ出力例

```
[2025-10-25 15:30:45] [INFO] Starting up LLM API server...
[2025-10-25 15:30:45] [INFO] Cache enabled: True
[2025-10-25 15:30:45] [INFO] Cache backend: redis
[2025-10-25 15:30:45] [INFO] Redis connection initialized successfully
[2025-10-25 15:30:47] [INFO] Cache miss for openai/gpt-4o-mini (hits: 0, misses: 1, hit_rate: 0.00%)
[2025-10-25 15:30:47] [INFO] Executing LLM request: model=gpt-4o-mini
[2025-10-25 15:30:49] [INFO] OpenAI API call successful: gpt-4o-mini
[2025-10-25 15:30:49] [INFO] Successfully generated character using openai/gpt-4o-mini in 1234.56ms
[2025-10-25 15:30:52] [INFO] Cache hit for openai/gpt-4o-mini (hits: 1, misses: 1, hit_rate: 50.00%)
```

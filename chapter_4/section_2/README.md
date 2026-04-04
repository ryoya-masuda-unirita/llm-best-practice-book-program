# Chapter 4 Section 1: LLMシステムのストレージと実行を分離する(CQRSパターンの応用)

## 概要

このプロジェクトは、**LLMシステムのストレージと実行を分離する(CQRSパターンの応用)** を用いたLLMシステムの実装サンプルです。キャッシュやデータベースへのアクセス処理と、LLM APIの呼び出し処理を疎結合に保つことで、コンポーネントの独立性を高め、柔軟でテストしやすく、保守性の高いシステムを実現します。

本実装では、FastAPIベースのREST APIサーバーを提供し、OpenAI GPTモデル（GPT-5.4、GPT-5.2、GPT-5.1、GPT-5シリーズ）に対応しています。また、インメモリキャッシュとRedisキャッシュの両方をサポートし、環境に応じて柔軟に切り替えることができます。

## 機能

- **ストレージと実行の分離**: Bridge Patternを用いた責務の明確な分離
- **キャッシング機能**: インメモリとRedisベースの2種類のキャッシュバックエンドをサポート
- **OpenAI対応**: OpenAI GPTモデル（GPT-5.4、GPT-5.2、GPT-5.1、GPT-5シリーズ）をサポート
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
cp .env.example .env
cp .envrc.example .envrc
# .envファイルを編集してAPIキーを設定
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
# uvを使用
uv sync
```

### 使用方法、実行方法

#### Docker Compose実行

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
    "model": "gpt-5.4-mini",
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

### 出力例

#### 1. キャラクター生成レスポンス

```bash
$ curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-5.4-mini",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": "ファンタジー世界の魔法使い"
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1232  100  1024  100   208   172k  35812 --:--:-- --:--:-- --:--:--  240k
{
  "character": {
    "first_name": "Kaelan",
    "last_name": "Morrigan",
    "gender": "male",
    "age": 28,
    "personalities": [
      {
        "short_personality": "Curious",
        "description": "Kaelan possesses an insatiable curiosity about the mystical forces of the world. This drives him to explore ancient texts and forgotten ruins, seeking knowledge that many deem forbidden or too dangerous."                                                                
      },
      {
        "short_personality": "Witty",
        "description": "His sharp wit often emerges in conversations, allowing him to defuse tense situations with humor. He enjoys clever banter and has a knack for turning mundane discussions into engaging debates, making him a beloved figure among friends."                                
      },
      {
        "short_personality": "Reclusive",
        "description": "Despite his social nature, Kaelan often retreats into solitude to practice his magic. He takes time away from the bustling city to connect with nature, believing that true power comes from understanding the balance between magic and the world around him."             
      }
    ]
  },
  "provider": "openai",
  "model": "gpt-5.4-mini",
  "processing_time_ms": 0.5803108215332031
}
```

#### 2. キャッシュメトリクスレスポンス

```bash
$ curl http://localhost:8000/metrics | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   120  100   120    0     0  15455      0 --:--:-- --:--:-- --:--:-- 17142
{
  "cache_enabled": true,
  "cache_backend": "memory",
  "cache_hits": 3,
  "cache_misses": 1,
  "cache_hit_rate": 0.75,
  "total_requests": 4
}
```

#### 3. サーバーログ出力例

```
[2025-10-25 15:30:45] [INFO] Starting up LLM API server...
[2025-10-25 15:30:45] [INFO] Cache enabled: True
[2025-10-25 15:30:45] [INFO] Cache backend: redis
[2025-10-25 15:30:45] [INFO] Redis connection initialized successfully
[2025-10-25 15:30:47] [INFO] Cache miss for openai/gpt-5.4-mini (hits: 0, misses: 1, hit_rate: 0.00%)
[2025-10-25 15:30:47] [INFO] Executing LLM request: model=gpt-5.4-mini
[2025-10-25 15:30:49] [INFO] OpenAI API call successful: gpt-5.4-mini
[2025-10-25 15:30:49] [INFO] Successfully generated character using openai/gpt-5.4-mini in 1234.56ms
[2025-10-25 15:30:52] [INFO] Cache hit for openai/gpt-5.4-mini (hits: 1, misses: 1, hit_rate: 50.00%)
```

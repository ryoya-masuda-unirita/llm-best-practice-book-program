# Chapter 3 Section 6: LLM APIゲートウェイ

## 概要

このプロジェクトは、**LLM APIゲートウェイ**の実装例を示すサンプルコードです。OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashへのアクセスを一元管理するゲートウェイサーバーを構築し、複数のアプリケーションサービスが安全かつ効率的にLLMを利用できる環境を提供します。

ゲートウェイパターンを採用することで、APIキーの一元管理、構造化ログによる監視、統一されたエラーハンドリング、そしてLLMプロバイダの変更に対する柔軟性を実現します。マイクロサービスアーキテクチャや複数チームでLLMを活用する環境において、セキュリティとガバナンスを強化するベストプラクティスを学ぶことができます。

## 機能

- **一元的なAPIキー管理**: APIキーをゲートウェイサーバーに集約し、クライアントアプリケーションから完全に隠蔽
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方を統一インターフェースで利用可能
- **構造化ログと監視**: 全てのLLM APIリクエスト・レスポンスを詳細にログ記録
- **一意なリクエストID**: UUIDベースのリクエストIDによる追跡可能性の確保
- **統一的なエラーハンドリング**: プロバイダ固有のエラーを抽象化し、一貫したエラーレスポンスを提供
- **FastAPI実装**: 高パフォーマンスな非同期APIサーバー
- **Docker対応**: Gateway・Backendサーバーをコンテナ化し、容易なデプロイを実現
- **ヘルスチェックエンドポイント**: サービスの死活監視をサポート
- **型安全性**: Pydanticによる厳密なリクエスト・レスポンスのバリデーション
- **JSON Schema変換**: クライアントから送信されたJSON SchemaをPydanticモデルに動的変換

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_4/
├── src/
│   ├── __init__.py
│   ├── config.py                      # 設定管理（環境変数、API キー）
│   ├── logger.py                      # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py              # バックエンドLLM APIサーバー
│   ├── api_gateway/
│   │   ├── __init__.py
│   │   ├── gateway_server.py          # ゲートウェイサーバー（FastAPIアプリケーション）
│   │   ├── gateway_service.py         # ゲートウェイコアサービス
│   │   ├── api_key_manager.py         # APIキー管理
│   │   ├── monitoring.py              # 監視・ロギング
│   │   └── models.py                  # ゲートウェイ用Pydanticモデル
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py              # LLMプロバイダー定義
│   │   └── gateway_client.py          # ゲートウェイクライアント
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py                   # データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py                  # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── request_llm.py             # LLMリクエスト処理
├── .envrc.example                      # 環境変数設定のサンプル
├── docker-compose.yml                  # Docker Compose設定
├── Dockerfile.backend                  # バックエンドサーバー用Dockerfile
├── Dockerfile.gateway                  # ゲートウェイサーバー用Dockerfile
├── Makefile                            # 開発・デプロイコマンド
├── pyproject.toml                      # プロジェクト依存関係
├── README.md                           # このファイル
└── CLAUDE.md                           # プロジェクト設計ドキュメント
```

### アーキテクチャ

このプロジェクトは、**ゲートウェイパターン**を採用した3層アーキテクチャで構成されています：

```
┌───────────────────────────────────────────────────────────┐
│                  Client Applications                       │
│         (Frontend, Microservices, etc.)                    │
└─────────────────────┬─────────────────────────────────────┘
                      │ HTTP Requests
                      │ (No API Keys Required)
                      ▼
┌───────────────────────────────────────────────────────────┐
│              LLM Backend Server (Port 8000)                │
│  - Character generation API                                │
│  - Business logic layer                                    │
│  - Uses Gateway Client to request LLM                      │
└─────────────────────┬─────────────────────────────────────┘
                      │ Internal HTTP Requests
                      │ (via Gateway Client)
                      ▼
┌───────────────────────────────────────────────────────────┐
│              LLM API Gateway (Port 8080)                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Gateway Server (gateway_server.py)                 │  │
│  │  - FastAPI endpoints (/health, /v1/generate)        │  │
│  │  - Request validation                               │  │
│  │  - JSON Schema → Pydantic conversion                │  │
│  └───────────────────┬─────────────────────────────────┘  │
│                      │                                     │
│  ┌───────────────────▼─────────────────────────────────┐  │
│  │  Gateway Service (gateway_service.py)               │  │
│  │  - Request routing by provider                      │  │
│  │  - LLM API calls (OpenAI, Gemini)                   │  │
│  │  - Response parsing                                 │  │
│  └───────────────────┬─────────────────────────────────┘  │
│                      │                                     │
│  ┌───────────────────▼─────────────────────────────────┐  │
│  │  API Key Manager (api_key_manager.py)               │  │
│  │  - Centralized API key storage                      │  │
│  │  - Provider validation                              │  │
│  │  - Secure key retrieval                             │  │
│  └───────────────────┬─────────────────────────────────┘  │
│                      │                                     │
│  ┌───────────────────▼─────────────────────────────────┐  │
│  │  Gateway Monitor (monitoring.py)                    │  │
│  │  - Request/response logging                         │  │
│  │  - Performance metrics                              │  │
│  │  - Error tracking                                   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────┬─────────────────────────────────────┘
                      │ External API Calls
                      │ (with API Keys)
                      ▼
┌───────────────────────────────────────────────────────────┐
│              External LLM Providers                        │
│         OpenAI API         │         Gemini API            │
└───────────────────────────────────────────────────────────┘
```

**主要な設計原則**:
1. **関心の分離**: APIキー管理、監視、ビジネスロジックを明確に分離
2. **セキュリティバイデザイン**: APIキーは常にゲートウェイ内部に隠蔽
3. **拡張性**: 新しいLLMプロバイダの追加が容易
4. **監視可能性**: 全てのリクエストが構造化ログで追跡可能

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Docker**: 20.10以上（Docker Composeを使用する場合）
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - pydantic>=2.12.2
  - httpx>=0.28.1
  - openai>=2.4.0
  - google-genai>=1.45.0
  - click>=8.3.0
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
GATEWAY_URL=http://localhost:8080
BACKEND_URL=http://localhost:8000
GATEWAY_TIMEOUT=30.0
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

```bash
# Dockerイメージをビルド
make docker-build

# サービスを起動
make docker-up

# ログを確認
make docker-logs

# サービスを停止
make docker-down
```

#### API利用例

**1. ヘルスチェック**

```bash
# ゲートウェイのヘルスチェック
curl http://localhost:8080/health

# バックエンドのヘルスチェック
curl http://localhost:8000/health
```

**2. キャラクター生成（バックエンドAPI経由）**

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": "Create a mysterious character"
    }
  }'
```

**3. 直接ゲートウェイAPI経由でLLMを呼び出す**

```bash
curl -X POST http://localhost:8080/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Write a haiku about programming."}
    ],
    "response_format": {
      "type": "object",
      "properties": {
        "haiku": {"type": "string"}
      },
      "required": ["haiku"]
    },
    "client_id": "my-app"
  }'
```

### 出力例

#### 1. ゲートウェイのヘルスチェック

**リクエスト**:
```bash
curl http://localhost:8080/health
```

**レスポンス**:
```json
{
  "status": "healthy",
  "timestamp": 1729123456.789,
  "providers_available": {
    "openai": true,
    "gemini": true
  }
}
```

#### 2. キャラクター生成のレスポンス

**リクエスト**:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": null
    }
  }'
```

**レスポンス**:
```json
{
  "character": {
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 28,
    "personalities": [
      {
        "short_personality": "内向的な思索家",
        "description": "常に深く物事を考え、静かな場所を好む。表面的な会話よりも、哲学的な議論に心を開く。"
      },
      {
        "short_personality": "完璧主義者",
        "description": "すべてのタスクに最高の基準を求め、細部にこだわる。しばしば自分自身に対して厳しすぎることがある。"
      },
      {
        "short_personality": "忠実な友人",
        "description": "一度信頼関係を築くと、どんな困難な状況でも友人を支える。約束を何よりも大切にする。"
      }
    ]
  },
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "processing_time_ms": 1234.56
}
```

#### 3. ゲートウェイのログ出力例

```
[2025-10-26 10:30:45] [INFO] [src.api_gateway.monitoring] [REQUEST] id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 | provider=gemini | model=gemini-2.5-flash | client=llm_server
[2025-10-26 10:30:47] [INFO] [src.api_gateway.gateway_service] Gemini client initialized
[2025-10-26 10:30:48] [INFO] [src.api_gateway.monitoring] [RESPONSE] id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 | status=SUCCESS | provider=gemini | model=gemini-2.5-flash | time=1234.56ms
```

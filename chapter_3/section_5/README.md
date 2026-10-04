# Chapter 3 Section 5: LLM APIゲートウェイ

## 概要

このプロジェクトは、**LLM APIゲートウェイ**の実装例を示すサンプルコードです。OpenAI GPT-5.4-miniとGoogle Gemini 2.5 Flashへのアクセスを一元管理するゲートウェイサーバーを構築し、複数のアプリケーションサービスが安全かつ効率的にLLMを利用できる環境を提供します。

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
cp .env.example .env
cp .envrc.example .envrc
```

`.env`ファイルを編集してAPIキーを設定:

```bash
# .env
AWS_REGION=us-east-1
GATEWAY_URL=http://localhost:8080
BACKEND_URL=http://localhost:8000
GATEWAY_TIMEOUT=30.0
```

> **注意**: Docker Composeは`.env`ファイルから環境変数を読み込みます。`.envrc`はdirenv用（ローカル開発の便利ツール）で、中身は`dotenv`コマンドのみです。`.env`ファイルにAPIキーを設定すれば、ローカル実行・Docker実行の両方で動作します。

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
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
$ curl http://localhost:8080/health
{"status":"healthy","timestamp":1769323495.0489843,"providers_available":{"openai":true,"gemini":true}}

# バックエンドのヘルスチェック
$ curl http://localhost:8000/health
{"status":"healthy","timestamp":1769323492.3572245}
```

**2. キャラクター生成（バックエンドAPI経由）**

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
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
    "model": "openai.gpt-5.4",
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
$ curl http://localhost:8080/health | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   102  100   102    0     0  20719      0 --:--:-- --:--:-- --:--:-- 25500
{
  "status": "healthy",
  "timestamp": 1769323559.985998,
  "providers_available": {
    "openai": true,
    "gemini": true
  }
}
```

#### 2. キャラクター生成のレスポンス

**リクエスト**:
```bash
$ curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": null
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1029  100   853  100   176    324     66  0:00:02  0:00:02 --:--:--   391
{
  "character": {
    "first_name": "Kaito",
    "last_name": "Tanaka",
    "gender": "male",
    "age": 28,
    "personalities": [
      {
        "short_personality": "Observant",
        "description": "Kaito possesses a remarkable ability to notice minute details and patterns that often escape others' attention, making him an excellent analyst and problem-solver."                                                                                                        
      },
      {
        "short_personality": "Resourceful",
        "description": "He is incredibly adept at utilizing available resources, no matter how limited, to achieve his goals or overcome obstacles, demonstrating creativity and adaptability."                                                                                                     
      },
      {
        "short_personality": "Calm Under Pressure",
        "description": "Even in the most chaotic or high-stakes situations, Kaito maintains a serene demeanor, allowing him to think clearly and make rational decisions without succumbing to panic."                                                                                              
      }
    ]
  },
  "provider": "gemini",
  "model": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
  "processing_time_ms": 2624.802589416504
}
```

#### 3. ゲートウェイのログ出力例

```
[2025-10-26 10:30:45] [INFO] [src.api_gateway.monitoring] [REQUEST] id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 | provider=gemini | model=global.anthropic.claude-haiku-4-5-20251001-v1:0 | client=llm_server
[2025-10-26 10:30:47] [INFO] [src.api_gateway.gateway_service] Gemini client initialized
[2025-10-26 10:30:48] [INFO] [src.api_gateway.monitoring] [RESPONSE] id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 | status=SUCCESS | provider=gemini | model=global.anthropic.claude-haiku-4-5-20251001-v1:0 | time=1234.56ms
```

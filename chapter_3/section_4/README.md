# Chapter 3 Section 4: LLMのリクエスト量を制御する

## 概要

このプロジェクトは、**プロキシサーバーによるLLM APIリクエスト制御**の実装サンプルです。LLM APIのレートリミット（利用制限）に対処するため、アプリケーションとLLM APIの間に専用のプロキシサーバーを設置し、システム全体の安定性を確保します。

プロキシサーバーは、流量制御（スロットリング）、サーキットブレーカー、リクエストキューイング、自動リトライといった機能を一元的に提供します。これにより、レートリミット超過によるエラーを防ぎ、複数のユーザーやサービスが共通のAPI契約を安定的に利用できるようになります。

このサンプルでは、FastAPIを用いた2つのサーバー（LLM APIサーバーとプロキシサーバー）を実装し、実践的なレート制御パターンを学ぶことができます。

## 機能

- **流量制御（Rate Limiting）**: トークンバケットアルゴリズムによる秒間リクエスト数の制限
- **サーキットブレーカー**: エラー多発時の自動遮断で連鎖障害を防止（Closed/Open/Half-Open状態管理）
- **リクエストキューイング**: バーストトラフィックの吸収と順次処理
- **自動リトライ**: 指数バックオフによる429エラーと5xxエラーの自動再試行
- **メトリクス収集**: リアルタイムな稼働状況の可視化（キューサイズ、エラー率、処理時間など）
- **Gemini API対応**: Google Gemini APIによるキャラクター生成
- **FastAPI実装**: RESTful APIエンドポイントによる使いやすいインターフェース
- **非同期処理**: async/awaitパターンによる高効率なリクエスト処理
- **構造化ログ**: 詳細なログ出力による運用監視とトラブルシューティング

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_1/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（APIキー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── proxy/
│   │   ├── __init__.py
│   │   ├── proxy_server.py      # プロキシサーバー本体（FastAPI）
│   │   ├── rate_limiter.py      # レート制限（トークンバケット）
│   │   ├── circuit_breaker.py   # サーキットブレーカー
│   │   └── request_queue.py     # リクエストキュー
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py        # LLM APIサーバー（FastAPI）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # Geminiクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── request_llm.py       # LLMリクエスト処理
├── .env.example                 # 環境変数設定のサンプル（ローカル用）
├── .envrc.example               # 環境変数設定のサンプル（Docker/direnv用）
├── .dockerignore                # Docker ビルド除外ファイル
├── Dockerfile.web               # LLM APIサーバー用Dockerfile
├── Dockerfile.proxy             # プロキシサーバー用Dockerfile
├── docker-compose.yml           # Docker Compose設定
├── Makefile                     # 開発・実行用コマンド
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
├── CLAUDE.md                    # プロジェクト状態レポート（英語）
└── DOCKER.md                    # Docker詳細ガイド（英語）
```

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャで構成されています：

```
┌──────────────────────────────────────────────────┐
│          Client Applications                      │
│     (ブラウザ、CLI、他のサービス)                  │
└──────────────────┬───────────────────────────────┘
                   │ HTTP Requests
┌──────────────────▼───────────────────────────────┐
│         Proxy Server (Port 8080)                  │
│  ┌─────────────────────────────────────────────┐ │
│  │  Request Queue (max: 100)                   │ │
│  │  - バーストトラフィックの吸収               │ │
│  │  - タイムアウト管理（300秒）                │ │
│  └────────────────┬────────────────────────────┘ │
│  ┌────────────────▼────────────────────────────┐ │
│  │  Rate Limiter (Token Bucket)                │ │
│  │  - 10 requests/sec                          │ │
│  │  - トークン補充による流量制御               │ │
│  └────────────────┬────────────────────────────┘ │
│  ┌────────────────▼────────────────────────────┐ │
│  │  Circuit Breaker                            │ │
│  │  - 状態管理（CLOSED/OPEN/HALF_OPEN）        │ │
│  │  - エラー率監視（閾値: 50%）                │ │
│  └────────────────┬────────────────────────────┘ │
│  ┌────────────────▼────────────────────────────┐ │
│  │  Retry Logic (Exponential Backoff)         │ │
│  │  - 最大3回リトライ                          │ │
│  │  - バックオフ: 1s, 2s, 4s                   │ │
│  └────────────────┬────────────────────────────┘ │
└───────────────────┼───────────────────────────────┘
                    │ Controlled Requests
┌───────────────────▼───────────────────────────────┐
│         LLM API Server (Port 8000)                │
│  - キャラクター生成エンドポイント (/generate)     │
│  - ヘルスチェック (/health)                       │
└───────────────────┬───────────────────────────────┘
                    │ LLM API Calls
┌───────────────────▼───────────────────────────────┐
│         External LLM APIs                         │
│  - Google Gemini API                              │
│    (gemini-2.5-pro, gemini-2.5-flash,            │
│     gemini-2.5-flash-lite)                        │
└───────────────────────────────────────────────────┘
```

**データフロー**:
1. クライアントからプロキシサーバー（Port 8080）へリクエスト送信
2. プロキシがリクエストをキューに追加
3. キューから取り出したリクエストがレート制限を通過
4. サーキットブレーカーが正常状態なら転送を許可
5. リトライロジックがLLM APIサーバー（Port 8000）へリクエスト
6. LLM APIサーバーが外部LLM APIを呼び出し
7. レスポンスがプロキシを経由してクライアントへ返却（メトリクス付加）

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - httpx>=0.28.1
  - httpx-retries>=0.2.0
  - google-genai>=1.45.0
  - pydantic>=2.12.2
  - python-dotenv>=1.0.0
  - click>=8.3.0

### セットアップ

#### クイックスタート比較

| 実行方法 | 準備時間 | 用途 | コマンド |
|---------|---------|------|---------|
| **Docker Compose** | ⚡ 最速 | 本番・デモ | `make docker-build && make docker-up` |
| **ローカル実行** | 🔧 中程度 | 開発・デバッグ | `uv sync && uvicorn ...` |
| **Docker個別** | 🎛️ 時間かかる | 詳細制御 | 個別にdockerコマンド実行 |

#### 共通セットアップ手順

**1. 環境変数ファイルの作成**

```bash
# ローカル実行の場合: .env.exampleをコピーして.envを作成
cp .env.example .env

# Docker実行の場合: .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタでファイルを開き、APIキーを設定
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

#### ローカル実行の場合の追加手順

**2. 依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

#### Docker実行の場合の追加手順

**2. Dockerイメージのビルド**

```bash
# 両方のイメージを一度にビルド
make docker-build

# または個別にビルド
make docker-build-web    # LLM APIサーバー
make docker-build-proxy  # プロキシサーバー
```

### 使用方法、実行方法

#### サーバーの起動

プロジェクトを実行する方法は3つあります：ローカル実行、Docker個別起動、Docker Compose一括起動。

**方法1: Docker Compose（最も簡単・推奨）**

両方のサーバーをコンテナとして一括起動します：

```bash
# イメージのビルド
make docker-build

# サーバーの起動（バックグラウンド）
make docker-up

# ログの確認
make docker-logs

# サーバーの停止
make docker-down
```

これにより以下が起動します：
- LLM APIサーバー: http://localhost:8000
- プロキシサーバー: http://localhost:8080

**方法2: ローカル実行（開発向け・ホットリロード対応）**

uvを使用してローカルで直接実行します：

```bash
# ターミナル1: LLM APIサーバー
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload

# ターミナル2: プロキシサーバー
uv run uvicorn src.proxy.proxy_server:app --host 0.0.0.0 --port 8080 --reload
```

**方法3: Docker個別起動（上級者向け）**

コンテナを個別に制御したい場合：

```bash
# イメージのビルド
docker build -t shibui/llm-best-practice:chapter3_section1_web -f Dockerfile.web .
docker build -t shibui/llm-best-practice:chapter3_section1_proxy -f Dockerfile.proxy .

# LLM APIサーバーの起動
docker run -d \
  --name llm-api-server \
  -p 8000:8000 \
  --env-file .envrc \
  shibui/llm-best-practice:chapter3_section1_web

# プロキシサーバーの起動
docker run -d \
  --name llm-proxy-server \
  -p 8080:8080 \
  --env-file .envrc \
  --link llm-api-server \
  -e BACKEND_URL=http://llm-api-server:8000 \
  shibui/llm-best-practice:chapter3_section1_proxy

# コンテナの停止と削除
docker stop llm-api-server llm-proxy-server
docker rm llm-api-server llm-proxy-server
```

#### APIエンドポイントの利用

**1. ヘルスチェック（プロキシ経由）**

```bash
# プロキシ自身の状態確認
curl http://localhost:8080/proxy-health

# バックエンドのヘルスチェック（制御機能を通過）
curl http://localhost:8080/health
```

**2. キャラクター生成（Gemini）**

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "male",
      "age": 25,
      "additional_instructions": "冒険好きな性格にしてください"
    }
  }'
```

利用可能なモデル: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`

**3. メトリクス確認**

```bash
# プロキシの稼働状況を確認
curl http://localhost:8080/metrics
```

**4. サーキットブレーカーのリセット**

```bash
# 手動でCLOSED状態に戻す
curl -X POST http://localhost:8080/circuit-breaker/reset
```

#### API ドキュメント

FastAPIの自動生成ドキュメントを利用できます：

- プロキシサーバー: http://localhost:8080/docs
- LLM APIサーバー: http://localhost:8000/docs

### 出力例

**成功レスポンス例（プロキシメタデータ付き）**:

```json
{
  "character": {
    "first_name": "太郎",
    "last_name": "山田",
    "gender": "male",
    "age": 25,
    "personalities": [
      {
        "short_personality": "冒険家",
        "description": "未知の場所を探索することに情熱を持ち、リスクを恐れず新しい経験を求める。"
      },
      {
        "short_personality": "楽観主義者",
        "description": "困難な状況でも前向きに考え、周囲の人々を励ます力を持っている。"
      },
      {
        "short_personality": "社交的",
        "description": "初対面の人ともすぐに打ち解け、多様な人脈を築くのが得意。"
      }
    ]
  },
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "processing_time_ms": 1234.56,
  "_proxy_metadata": {
    "processing_time_ms": 1456.78,
    "circuit_state": "closed",
    "queue_size": 2
  }
}
```

**メトリクスレスポンス例**:

```json
{
  "rate_limiter": {
    "available_tokens": 8.5,
    "max_requests": 10,
    "window_seconds": 1.0
  },
  "circuit_breaker": {
    "state": "closed",
    "total_requests": 1523,
    "failed_requests": 12,
    "error_rate": 0.00788,
    "failure_count": 1,
    "success_count": 0
  },
  "request_queue": {
    "current_size": 3,
    "max_size": 100,
    "total_queued": 1523,
    "total_processed": 1520,
    "total_timeouts": 0,
    "active_requests": 0
  },
  "timestamp": 1703001234.567
}
```

**実行ログ例**:

```
[2025-10-25 10:30:45] [INFO] Rate limiter initialized: 10 requests per 1.0s (refill rate: 10.00 tokens/s)
[2025-10-25 10:30:45] [INFO] Circuit breaker initialized: failure_threshold=5, timeout=60.0s
[2025-10-25 10:30:45] [INFO] Request queue initialized: max_size=100, timeout=300.0s
[2025-10-25 10:30:50] [INFO] Proxying POST request to http://localhost:8000/generate (with access controls)
[2025-10-25 10:30:50] [INFO] Request queued. Queue size: 1/100
[2025-10-25 10:30:51] [INFO] Token acquired. Remaining tokens: 9.00
[2025-10-25 10:30:52] [INFO] Generate request completed successfully in 1456.78ms (queue size: 0)
```

### Docker デプロイメント

#### Docker の利点

Dockerを使用することで、以下の利点が得られます：

1. **環境の一貫性**: 開発、ステージング、本番環境で同じ環境を保証
2. **依存関係の分離**: システムにPythonや依存ライブラリをインストール不要
3. **スケーラビリティ**: 複数インスタンスの起動が容易
4. **ポータビリティ**: どのプラットフォームでも同じように動作

#### Dockerfile の構成

このプロジェクトには2つのDockerfileがあります：

**Dockerfile.web** (LLM APIサーバー):
- ベースイメージ: `ghcr.io/astral-sh/uv:python3.13-bookworm` (Builder)
- ランタイム: `python:3.13-slim` (最小サイズ)
- ポート: 8000
- マルチステージビルドで最適化（最終イメージサイズ削減）

**Dockerfile.proxy** (プロキシサーバー):
- 同様のマルチステージビルド構成
- ポート: 8080
- レート制限、サーキットブレーカー、リトライ機能を含む

#### Docker Compose の設定

`docker-compose.yml`は両方のサービスを統合管理します：

```yaml
services:
  llm-server:
    image: shibui/llm-best-practice:chapter3_section1_web
    ports: ["8000:8000"]
    networks: [llm-network]

  proxy-server:
    image: shibui/llm-best-practice:chapter3_section1_proxy
    ports: ["8080:8080"]
    environment:
      - BACKEND_URL=http://llm-server:8000
    networks: [llm-network]
```

#### Docker 利用時の注意点

1. **環境変数**: `.envrc`ファイルが必要（APIキーを含む）
2. **ネットワーク**: コンテナ間通信用に`llm-network`ブリッジネットワークを使用
3. **ポート競合**: ローカル実行中のサーバーを停止してからDockerを起動
4. **ログ確認**: `make docker-logs`でリアルタイムログを確認可能

#### 本番環境でのDocker利用

本番環境では以下の設定を追加することを推奨します：

```yaml
# docker-compose.prod.yml
services:
  llm-server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### Docker トラブルシューティング

| 問題 | 原因 | 解決方法 |
|-----|------|---------|
| ポート競合エラー | 8000/8080が使用中 | `lsof -i :8000` でプロセス確認後、停止 |
| 環境変数が読み込まれない | `.envrc`ファイルが無い | `cp .envrc.example .envrc` で作成 |
| イメージビルド失敗 | キャッシュ問題 | `docker builder prune` でキャッシュクリア |
| コンテナ起動失敗 | ログ確認不足 | `make docker-logs` でエラー詳細確認 |
| プロキシがバックエンドに接続できない | ネットワーク設定 | `docker network inspect llm-network` で確認 |

詳細なDocker利用ガイドは `DOCKER.md` を参照してください。

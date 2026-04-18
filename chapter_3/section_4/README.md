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
GEMINI_API_KEY=<your_gemini_api_key_here>
```

#### ローカル実行の場合の追加手順

**2. 依存関係のインストール**

```bash
# uvを使用
uv sync
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

```bash
$ curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "male",
      "age": 25,
      "additional_instructions": "冒険好きな性格にしてください"
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1395  100  1205  100   190    268     42  0:00:04  0:00:04 --:--:--   310
{
  "character": {
    "first_name": "エドガー",
    "last_name": "ブラックウッド",
    "gender": "male",
    "age": 25,
    "personalities": [
      {
        "short_personality": "探求心が旺盛",
        "description": "エドガーは未知への飽くなき好奇心を持ち、常に新しい場所や文化、そして挑戦を求めている。平凡な日常には満足せず、常に次なる冒険を探し求めている。"                                                                                                                             
      },
      {
        "short_personality": "不屈の精神を持つ",
        "description": "困難や予期せぬ障害に直面しても、決して諦めることなく、前向きな姿勢で立ち向かう。逆境を成長の機会と捉え、問題解決のために知恵と工夫を凝らすことができる。"                                                                                                                   
      },
      {
        "short_personality": "楽観的で機転が利く",
        "description": "常に明るい展望を持ち、周囲の人々を励ます。予期せぬ状況でも冷静さを保ち、ユーモアを交えながら適切な解決策を見つけ出す能力に長けている。状況に応じて素早く判断し、柔軟に対応する。"                                                                                           
      }
    ]
  },
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "processing_time_ms": 4471.30274772644,
  "_proxy_metadata": {
    "processing_time_ms": 4484.21311378479,
    "circuit_state": "closed",
    "queue_size": 0
  }
}
```

**メトリクスレスポンス例**:

```bash
$ curl http://localhost:8080/metrics | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   365  100   365    0     0  79038      0 --:--:-- --:--:-- --:--:-- 91250
{
  "rate_limiter": {
    "available_tokens": 10,
    "max_requests": 10,
    "window_seconds": 1.0
  },
  "circuit_breaker": {
    "state": "closed",
    "total_requests": 3,
    "failed_requests": 0,
    "error_rate": 0.0,
    "failure_count": 0,
    "success_count": 0
  },
  "request_queue": {
    "current_size": 0,
    "max_size": 100,
    "total_queued": 3,
    "total_processed": 3,
    "total_timeouts": 0,
    "active_requests": 0
  },
  "timestamp": 1769322289.1304708
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

# Chapter 3 Section 1: LLMのリクエスト量を制御する

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
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
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
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── request_llm.py       # LLMリクエスト処理
├── .envrc.example               # 環境変数設定のサンプル
├── Makefile                     # 開発・実行用コマンド
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
└── CLAUDE.md                    # プロジェクト概念説明
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
│  - OpenAI API (GPT-4o-mini, GPT-4o)              │
│  - Google Gemini API (gemini-2.5-flash)          │
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

### 実装の詳細

#### 1. レート制限（Token Bucket Algorithm） (`src/proxy/rate_limiter.py`)

トークンバケット方式を用いた流量制御を実装します：

```python
class TokenBucketRateLimiter:
    """
    トークンバケットアルゴリズムによるレート制限
    - 一定速度でトークンを補充
    - リクエストごとに1トークン消費
    - トークン不足時は待機
    """

    def __init__(self, config: RateLimiterConfig):
        self.config = config
        self.tokens = float(config.max_requests)  # 初期トークン数
        self.refill_rate = config.max_requests / config.window_seconds  # 補充速度

    async def acquire(self, timeout: float | None = None) -> bool:
        # トークンを時間経過に応じて補充
        elapsed = now - self.last_update
        self.tokens = min(self.config.max_requests,
                         self.tokens + elapsed * self.refill_rate)

        # トークンがあれば消費して許可
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True

        # トークン不足時は待機
        wait_time = (1.0 - self.tokens) / self.refill_rate
        await asyncio.sleep(wait_time)
```

**ポイント**:
- 設定例: 10 requests/sec → 毎秒10トークン補充
- トークン不足時は自動的に待機（ブロッキング）
- タイムアウト設定で最大待機時間を制限可能

#### 2. サーキットブレーカー (`src/proxy/circuit_breaker.py`)

障害の連鎖を防ぐための3状態管理を実装します：

```python
class CircuitState(Enum):
    CLOSED = "closed"        # 正常動作（リクエスト通過）
    OPEN = "open"            # 遮断状態（リクエスト即座に拒否）
    HALF_OPEN = "half_open"  # 回復試行中（限定的に通過）

class CircuitBreaker:
    async def call(self, func, *args, **kwargs):
        # OPEN状態なら即座に拒否
        if self.state == CircuitState.OPEN:
            # タイムアウト経過後にHALF_OPENへ遷移
            if elapsed >= self.config.timeout_seconds:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError()

        # 実行と結果に応じた状態遷移
        try:
            result = await func(*args, **kwargs)
            await self._on_success()  # HALF_OPEN → CLOSED
            return result
        except Exception:
            await self._on_failure()  # CLOSED/HALF_OPEN → OPEN
            raise
```

**状態遷移**:
- **CLOSED → OPEN**: 連続5回失敗 または エラー率50%超
- **OPEN → HALF_OPEN**: 30秒経過後に自動遷移
- **HALF_OPEN → CLOSED**: 連続2回成功
- **HALF_OPEN → OPEN**: 1回でも失敗

#### 3. リクエストキュー (`src/proxy/request_queue.py`)

バーストトラフィックを吸収する非同期キューを実装します：

```python
class RequestQueue:
    """
    asyncio.Queueベースのリクエスト管理
    - 最大100件まで待機可能
    - 300秒でタイムアウト
    """

    async def enqueue(self, request_data: Any) -> Any:
        if self.queue.full():
            raise RequestQueueFullError()

        # Futureを使った非同期待機
        future = asyncio.Future()
        await self.queue.put({"data": request_data, "future": future})

        # 処理完了まで待機（タイムアウト付き）
        result = await asyncio.wait_for(future, timeout=self.config.request_timeout)
        return result

    async def dequeue(self) -> dict:
        # バックグラウンドプロセッサが順次取り出し
        return await self.queue.get()
```

**ポイント**:
- キューフル時は503エラーを即座に返却
- タイムアウト時は504エラーを返却
- メトリクスで待機状況を監視可能

#### 4. 自動リトライ（指数バックオフ） (`src/proxy/proxy_server.py`)

httpx-retriesライブラリを用いた自動再試行を実装します：

```python
async def make_request_with_retry(method: str, url: str,
                                   json_data: dict | None = None,
                                   max_retries: int = 3) -> dict:
    # リトライポリシーの設定
    retry_policy = Retry(
        total=max_retries,
        backoff_factor=1.0,  # 1s, 2s, 4s, 8s...
        status_forcelist=[429] + list(range(500, 600)),  # 429, 5xx
    )

    retry_transport = RetryTransport(
        transport=httpx.AsyncHTTPTransport(),
        retry=retry_policy
    )

    async with httpx.AsyncClient(transport=retry_transport) as client:
        response = await client.post(url, json=json_data)
        response.raise_for_status()
        return response.json()
```

**リトライ対象**:
- 429 Too Many Requests（レート制限）
- 5xx Server Errors（サーバーエラー）

**リトライ間隔**:
- 1回目: 1秒後
- 2回目: 2秒後
- 3回目: 4秒後

#### 5. プロキシサーバー統合 (`src/proxy/proxy_server.py`)

すべての制御機能を統合したFastAPIアプリケーション：

```python
app = FastAPI(title="LLM Proxy Server")

# 各コンポーネントの初期化
rate_limiter = TokenBucketRateLimiter(
    RateLimiterConfig(max_requests=10, window_seconds=1.0)
)
circuit_breaker = CircuitBreaker(
    CircuitBreakerConfig(failure_threshold=5, timeout_seconds=30.0)
)
request_queue = RequestQueue(
    QueueConfig(max_queue_size=100, request_timeout=300.0)
)

@app.post("/generate")
async def backend_generate_character(request: LLMRequest):
    # 1. キューへ追加
    queue_item = await request_queue.enqueue(request_data)

    # 2. レート制限取得（バックグラウンド処理）
    acquired = await rate_limiter.acquire(timeout=30.0)

    # 3. サーキットブレーカー経由で実行
    result = await circuit_breaker.call(
        make_request_with_retry,
        method="POST",
        url=backend_url,
        json_data=request_body
    )

    # 4. メトリクス付きレスポンス返却
    return ProxiedLLMResponse(
        character=result["character"],
        _proxy_metadata=ProxyMetadata(
            processing_time_ms=processing_time,
            circuit_state=await circuit_breaker.get_state(),
            queue_size=request_queue.get_size()
        )
    )
```

#### 6. メトリクス監視エンドポイント

```python
@app.get("/metrics")
async def get_metrics():
    """プロキシの稼働状況を取得"""
    return ProxyMetrics(
        rate_limiter={
            "available_tokens": await rate_limiter.get_available_tokens(),
            "max_requests": 10,
            "window_seconds": 1.0
        },
        circuit_breaker={
            "state": "closed",
            "total_requests": 1234,
            "failed_requests": 5,
            "error_rate": 0.004
        },
        request_queue={
            "current_size": 3,
            "total_queued": 5678,
            "total_processed": 5670,
            "total_timeouts": 5
        }
    )
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - httpx>=0.28.1
  - httpx-retries>=0.2.0
  - openai>=2.4.0
  - google-genai>=1.45.0
  - pydantic>=2.12.2
  - python-dotenv>=1.0.0
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

### 使用方法、実行方法

#### サーバーの起動

**オプション1: 両方のサーバーを同時起動（推奨）**

```bash
make run-all
```

これにより以下が起動します：
- LLM APIサーバー: http://localhost:8000
- プロキシサーバー: http://localhost:8080

**オプション2: 個別に起動**

```bash
# ターミナル1: LLM APIサーバー
make run-llm-server

# ターミナル2: プロキシサーバー
make run-proxy
```

#### APIエンドポイントの利用

**1. ヘルスチェック（プロキシ経由）**

```bash
# プロキシ自身の状態確認
curl http://localhost:8080/proxy-health

# バックエンドのヘルスチェック（制御機能を通過）
curl http://localhost:8080/health
```

**2. キャラクター生成（OpenAI）**

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 25,
      "additional_instructions": "冒険好きな性格にしてください"
    }
  }'
```

**3. キャラクター生成（Gemini）**

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "female",
      "age": 30,
      "additional_instructions": "知的で落ち着いた性格にしてください"
    }
  }'
```

**4. メトリクス確認**

```bash
# プロキシの稼働状況を確認
curl http://localhost:8080/metrics
```

**5. サーキットブレーカーのリセット**

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
  "provider": "openai",
  "model": "gpt-4o-mini",
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
[2025-10-25 10:30:45] [INFO] Circuit breaker initialized: failure_threshold=5, timeout=30.0s
[2025-10-25 10:30:45] [INFO] Request queue initialized: max_size=100, timeout=300.0s
[2025-10-25 10:30:50] [INFO] Proxying POST request to http://localhost:8000/generate (with access controls)
[2025-10-25 10:30:50] [INFO] Request queued. Queue size: 1/100
[2025-10-25 10:30:51] [INFO] Token acquired. Remaining tokens: 9.00
[2025-10-25 10:30:52] [INFO] Generate request completed successfully in 1456.78ms (queue size: 0)
```

### テスト方法

#### 1. 基本的な動作確認

```bash
# 両サーバー起動
make run-all

# 別ターミナルでヘルスチェック
curl http://localhost:8080/health
# 期待: {"status":"healthy","timestamp":...,"_proxy_metadata":{...}}
```

#### 2. レート制限のテスト

```bash
# 短時間に20リクエスト送信（制限: 10 req/sec）
for i in {1..20}; do
  curl -X POST http://localhost:8080/generate \
    -H "Content-Type: application/json" \
    -d '{"provider":"gemini","model":"gemini-2.5-flash","character_request":{"gender":"male","age":25,"additional_instructions":""}}' &
done

# メトリクス確認（キューサイズが増加しているはず）
curl http://localhost:8080/metrics | jq '.request_queue'
```

期待される動作：
- 最初の10リクエストは即座に処理
- 残り10リクエストはキューで待機
- レート制限により順次処理（約2秒で完了）

#### 3. サーキットブレーカーのテスト

```bash
# バックエンドサーバーを停止してエラーを発生させる
# (LLM APIサーバーを停止)

# 10回リクエスト送信
for i in {1..10}; do
  curl -X POST http://localhost:8080/generate \
    -H "Content-Type: application/json" \
    -d '{"provider":"gemini","model":"gemini-2.5-flash","character_request":{"gender":"male","age":25,"additional_instructions":""}}'
done

# サーキットブレーカーの状態確認
curl http://localhost:8080/metrics | jq '.circuit_breaker'
# 期待: "state": "open"
```

期待される動作：
- 5回失敗後にサーキットブレーカーがOPEN状態へ遷移
- 以降のリクエストは503エラーで即座に拒否
- 30秒後にHALF_OPEN状態へ自動遷移

#### 4. リトライ機能のテスト

プロキシのログを監視しながら、一時的なエラーが発生する状況をシミュレートします：

```bash
# ログ監視（別ターミナル）
# プロキシサーバーの標準出力を確認

# バックエンドを一時停止・再開しながらリクエスト送信
# → リトライログが出力されることを確認
```

期待されるログ：
```
[ERROR] Request error: Connection refused
[INFO] Retrying request (attempt 1/3) after 1.0s...
[INFO] Retrying request (attempt 2/3) after 2.0s...
```

#### 5. 統合テスト（推奨）

pytest実装例（`tests/test_proxy.py`）:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rate_limiting():
    """レート制限が正常に動作することを確認"""
    async with AsyncClient(base_url="http://localhost:8080") as client:
        # 20リクエスト送信
        responses = []
        for _ in range(20):
            resp = await client.post("/generate", json={...})
            responses.append(resp)

        # すべて成功することを確認（キューイングにより）
        assert all(r.status_code == 200 for r in responses)

@pytest.mark.asyncio
async def test_circuit_breaker():
    """サーキットブレーカーが正常に動作することを確認"""
    # テスト実装...
```

実行:
```bash
# テストの実行
uv run pytest tests/ -v
```

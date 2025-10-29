# Chapter 3 Section 6: 非同期バッチ処理を用いたLLM実装

## 概要

このプロジェクトは、**非同期バッチ処理（Asynchronous Batch Processing）** を用いたLLM実装のサンプルコードです。Redisをメッセージキューとして活用し、大量のLLMリクエストをバックグラウンドで効率的に処理するアーキテクチャを実現します。

リアルタイムの同期APIと非同期のバッチAPIを併用することで、用途に応じた最適な処理方式を選択できます。フィクションのキャラクター情報を大量生成するユースケースを通じて、スケーラブルなLLMアプリケーションの実装方法を学ぶことができます。

## 機能

- **同期API**: リアルタイムでキャラクター1件を生成するREST API
- **非同期バッチAPI**: 複数のキャラクター生成リクエストをバッチで受け付け、バックグラウンドで処理
- **タスクキュー**: Redisを使用した信頼性の高いメッセージキューシステム
- **バックグラウンドワーカー**: キューからタスクを取り出して並列処理
- **ジョブ管理**: ジョブステータスの追跡、進捗確認、結果取得機能
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **冪等性保証**: ユニークなジョブIDによる処理の重複防止
- **エラーハンドリング**: タスク単位での失敗処理とリトライ機構
- **ヘルスチェック**: 各サービスの稼働状況確認エンドポイント
- **Docker Compose対応**: コンテナベースでの簡単なデプロイ

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_6/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー、Redis接続情報）
│   ├── logger.py                # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   ├── llm_server.py        # 同期APIサーバー（FastAPI）
│   │   └── batch_server.py      # 非同期バッチAPIサーバー（FastAPI）
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # LLMクライアント初期化
│   │   └── redis_client.py      # Redisクライアントラッパー
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py             # キャラクターモデル、API基本モデル
│   │   └── batch_model.py       # バッチ処理用モデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   ├── service/
│   │   ├── __init__.py
│   │   └── request_llm.py       # LLMリクエスト処理
│   └── worker/
│       ├── __init__.py
│       └── batch_worker.py      # バックグラウンドワーカー
├── .env.example                  # 環境変数設定のサンプル
├── .envrc.example                # direnv用設定サンプル
├── docker-compose.yml            # Docker Compose設定
├── Dockerfile                    # Dockerイメージ定義
├── Makefile                      # 開発用コマンド集
├── pyproject.toml                # プロジェクト依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト背景・設計思想
```

### アーキテクチャ

このプロジェクトは、マイクロサービスアーキテクチャに基づいた3つのコンポーネントで構成されています：

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  - HTTP Client (curl, httpx, etc.)                              │
└───────────────┬─────────────────────────────────┬───────────────┘
                │                                 │
        ┌───────▼────────┐               ┌───────▼────────┐
        │  LLM Server    │               │  Batch Server  │
        │  (Port 8000)   │               │  (Port 8001)   │
        │                │               │                │
        │  - /health     │               │  - /health     │
        │  - /generate   │               │  - /batch/     │
        └────────┬───────┘               │    submit      │
                 │                       │  - /batch/     │
                 │                       │    {job_id}/   │
                 │                       │    status      │
                 │                       │  - /batch/     │
                 │                       │    {job_id}/   │
                 │                       │    result      │
                 │                       └────────┬───────┘
                 │                                │
                 │                                │ Enqueue
                 │                       ┌────────▼───────┐
                 │                       │  Redis Queue   │
                 │                       │  (Port 6379)   │
                 │                       │                │
                 │                       │  - Task Queue  │
                 │                       │  - Job Status  │
                 │                       │  - Job Results │
                 │                       └────────┬───────┘
                 │                                │ Dequeue
                 │                       ┌────────▼───────┐
                 │                       │ Batch Worker   │
                 │                       │                │
                 │                       │ - Process Jobs │
                 │                       │ - Update Status│
                 │                       │ - Store Results│
                 └───────────────────────┴────────┬───────┘
                                                  │
                                  ┌───────────────▼───────────────┐
                                  │     LLM API Providers         │
                                  │  - OpenAI API                 │
                                  │  - Google Gemini API          │
                                  └───────────────────────────────┘
```

**コンポーネントの役割**:

1. **LLM Server (llm_server.py)**: 同期的なキャラクター生成APIを提供。リアルタイムの応答が必要な場合に使用。
2. **Batch Server (batch_server.py)**: 大量のリクエストを受け付け、Redisキューに投入。ジョブの状態管理と結果取得を担当。
3. **Redis**: メッセージキュー、ジョブステータス、結果データの永続化を担当。
4. **Batch Worker (batch_worker.py)**: キューからジョブを取得し、LLM APIを呼び出して処理。結果をRedisに保存。

### 実装の詳細

#### 1. バッチ処理モデル (`src/model/batch_model.py`)

バッチ処理に特化したデータモデルを定義：

```python
class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BatchJobRequest(BaseModel):
    provider: str  # LLMプロバイダー
    model: str     # モデル名
    character_requests: list[CharacterRequest]  # 1-100件のリクエスト

class BatchJobResponse(BaseModel):
    job_id: str           # ユニークなジョブID
    status: JobStatus     # ジョブステータス
    total_tasks: int      # タスク総数
    submitted_at: float   # 投入時刻

class TaskStatus(BaseModel):
    task_index: int                        # タスクインデックス
    status: JobStatus                      # タスクステータス
    character: Optional[CharacterResponse] # 生成結果（成功時）
    error: Optional[str]                   # エラーメッセージ（失敗時）
    processing_time_ms: Optional[float]    # 処理時間
```

**ポイント**:
- ジョブレベルとタスクレベルで二段階の状態管理
- 各タスクの成功/失敗を個別に追跡
- タイムスタンプによる処理時間の計測

#### 2. Redisクライアント (`src/client/redis_client.py`)

Redisを使用したキューとステータス管理：

```python
class RedisClient:
    async def enqueue_job(self, queue_name: str, job_data: dict) -> None:
        """ジョブをキューに追加（RPUSH）"""
        await self.redis.rpush(queue_name, json.dumps(job_data))

    async def dequeue_job(self, queue_name: str, timeout: int) -> Optional[dict]:
        """ジョブをキューから取得（BLPOP）"""
        result = await self.redis.blpop(queue_name, timeout=timeout)
        return json.loads(result[1]) if result else None

    async def set_job_status(self, job_id: str, status_data: dict, ttl: int) -> None:
        """ジョブステータスを保存（SETEX）"""
        await self.redis.setex(f"job:{job_id}:status", ttl, json.dumps(status_data))

    async def set_job_result(self, job_id: str, result_data: dict, ttl: int) -> None:
        """ジョブ結果を保存（SETEX）"""
        await self.redis.setex(f"job:{job_id}:result", ttl, json.dumps(result_data))
```

**特徴**:
- `BLPOP`によるブロッキング待機で効率的なポーリング
- TTL（Time To Live）設定により自動的にデータをクリーンアップ（デフォルト24時間）
- キー設計: `job:{job_id}:{type}` パターンで管理

#### 3. バッチAPIサーバー (`src/api/batch_server.py`)

非同期ジョブ管理API：

```python
@app.post("/batch/submit")
async def submit_batch_job(request: BatchJobRequest) -> BatchJobResponse:
    """
    バッチジョブを投入
    1. ユニークなジョブIDを生成
    2. 初期ステータスをRedisに保存
    3. ジョブデータをキューに投入
    4. 即座にレスポンスを返す
    """
    job_id = str(uuid.uuid4())
    await redis_client.set_job_status(job_id, status_data)
    await redis_client.enqueue_job(QUEUE_NAME, job_data)
    return BatchJobResponse(job_id=job_id, ...)

@app.get("/batch/{job_id}/status")
async def get_batch_job_status(job_id: str) -> BatchJobStatusResponse:
    """ジョブの進捗状況を確認"""
    status_data = await redis_client.get_job_status(job_id)
    return BatchJobStatusResponse(**status_data)

@app.get("/batch/{job_id}/result")
async def get_batch_job_result(job_id: str) -> BatchJobResultResponse:
    """完了したジョブの結果を取得"""
    result_data = await redis_client.get_job_result(job_id)
    return BatchJobResultResponse(**result_data)
```

**ポイント**:
- ジョブの投入は即座に完了（非ブロッキング）
- 状態確認と結果取得は別エンドポイント
- 未完了ジョブへの結果リクエストは適切なエラーを返す

#### 4. バッチワーカー (`src/worker/batch_worker.py`)

バックグラウンドでジョブを処理：

```python
class BatchWorker:
    async def start(self) -> None:
        """ワーカーを起動してジョブを処理"""
        while self.running:
            # ジョブをキューから取得（5秒タイムアウト）
            job_data = await redis_client.dequeue_job(QUEUE_NAME, timeout=5)
            if job_data:
                await self._process_job(job_data)

    async def _process_job(self, job_data: dict) -> None:
        """ジョブ全体を処理"""
        # 1. ステータスをPROCESSINGに更新
        # 2. 各タスクを順次処理
        # 3. 結果を集計
        # 4. 最終ステータスと結果をRedisに保存

    async def _process_task(self, ...) -> TaskStatus:
        """個別タスクを処理"""
        try:
            character = await request_openai(...)  # or request_gemini(...)
            return TaskStatus(status=COMPLETED, character=character)
        except Exception as e:
            return TaskStatus(status=FAILED, error=str(e))
```

**特徴**:
- シグナルハンドラによるグレースフルシャットダウン
- タスク単位でのエラーハンドリング（一部失敗でも処理継続）
- リアルタイムな進捗更新（各タスク完了時にステータスを更新）

#### 5. 同期APIサーバー (`src/api/llm_server.py`)

リアルタイム処理用のシンプルなAPI：

```python
@app.post("/generate")
async def generate_character(request: LLMRequest) -> LLMResponse:
    """
    同期的にキャラクターを1件生成
    - 即座にLLM APIを呼び出し
    - 結果を直接レスポンスとして返す
    """
    prompt = make_prompt(character_request=request.character_request)
    character = await request_openai(model=request.model, prompt=prompt)
    return LLMResponse(character=character, ...)
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Docker**: 20.10以上
- **Docker Compose**: 2.0以上
- **依存ライブラリ**:
  - redis>=7.0.0
  - fastapi>=0.115.0
  - uvicorn>=0.30.0
  - pydantic>=2.10.0
  - openai>=1.0.0
  - google-genai>=1.0.0

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env

# エディタで.envを開き、APIキーを設定
# .env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **Dockerイメージのビルド**

```bash
make docker-build
```

3. **サービスの起動**

```bash
make docker-up
```

これにより、以下のサービスが起動します：
- Redis（ポート6379）
- LLM Server（ポート8000）
- Batch Server（ポート8001）
- Batch Worker（バックグラウンド）

### 使用方法、実行方法

#### 1. ヘルスチェック

各サービスの稼働状況を確認：

```bash
# 同期APIサーバー
curl http://localhost:8000/health

# バッチAPIサーバー
curl http://localhost:8001/health
```

**レスポンス例**:
```json
{
  "status": "healthy",
  "timestamp": 1729843205.123
}
```

#### 2. 同期API: 単一キャラクター生成

リアルタイムで1件のキャラクターを生成：

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "ファンタジー世界の魔法使い"
    }
  }'
```

**レスポンス例**:
```json
{
  "character": {
    "first_name": "エリア",
    "last_name": "フェルナンド",
    "gender": "female",
    "age": 25,
    "personalities": [
      {
        "short_personality": "好奇心旺盛",
        "description": "未知の魔法に強い興味を示し、常に新しい呪文を研究している"
      },
      {
        "short_personality": "思慮深い",
        "description": "行動する前に慎重に状況を分析し、最善の策を練る"
      },
      {
        "short_personality": "献身的",
        "description": "困っている人を見過ごせず、自分の魔法で助けようとする"
      }
    ]
  },
  "provider": "openai",
  "model": "gpt-4o-mini",
  "processing_time_ms": 1234.56
}
```

#### 3. バッチAPI: 大量キャラクター生成

複数のキャラクターを非同期で一括生成：

```bash
# ジョブを投入
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.0-flash-exp",
    "character_requests": [
      {
        "gender": "male",
        "age": 30,
        "additional_instructions": "戦士"
      },
      {
        "gender": "female",
        "age": 22,
        "additional_instructions": "盗賊"
      },
      {
        "gender": "male",
        "age": 45,
        "additional_instructions": "賢者"
      }
    ]
  }'
```

**レスポンス例**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "total_tasks": 3,
  "submitted_at": 1729843205.123
}
```

#### 4. ジョブステータスの確認

処理の進捗を確認：

```bash
curl http://localhost:8001/batch/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status
```

**レスポンス例**（処理中）:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "total_tasks": 3,
  "completed_tasks": 1,
  "failed_tasks": 0,
  "pending_tasks": 2,
  "submitted_at": 1729843205.123,
  "started_at": 1729843206.456
}
```

**レスポンス例**（完了）:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "total_tasks": 3,
  "completed_tasks": 3,
  "failed_tasks": 0,
  "pending_tasks": 0,
  "submitted_at": 1729843205.123,
  "started_at": 1729843206.456,
  "completed_at": 1729843215.789
}
```

#### 5. ジョブ結果の取得

完了したジョブの結果を取得：

```bash
curl http://localhost:8001/batch/a1b2c3d4-e5f6-7890-abcd-ef1234567890/result
```

**レスポンス例**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "provider": "gemini",
  "model": "gemini-2.0-flash-exp",
  "tasks": [
    {
      "task_index": 0,
      "status": "completed",
      "character": {
        "first_name": "カイト",
        "last_name": "ストームブレード",
        "gender": "male",
        "age": 30,
        "personalities": [...]
      },
      "processing_time_ms": 1123.45
    },
    {
      "task_index": 1,
      "status": "completed",
      "character": {
        "first_name": "リナ",
        "last_name": "シャドウ",
        "gender": "female",
        "age": 22,
        "personalities": [...]
      },
      "processing_time_ms": 1089.67
    },
    {
      "task_index": 2,
      "status": "completed",
      "character": {
        "first_name": "マーリン",
        "last_name": "ワイズマン",
        "gender": "male",
        "age": 45,
        "personalities": [...]
      },
      "processing_time_ms": 1234.89
    }
  ],
  "submitted_at": 1729843205.123,
  "completed_at": 1729843215.789
}
```

#### 6. キュー統計の取得

現在のキュー状況を確認：

```bash
curl http://localhost:8001/batch/queue/stats
```

**レスポンス例**:
```json
{
  "queue_name": "llm_batch_jobs",
  "pending_jobs": 5
}
```

### 出力例

#### 成功時のワーカーログ

```
[2025-10-29 18:30:12] [INFO] [batch_worker] Batch worker started, waiting for jobs...
[2025-10-29 18:30:15] [INFO] [redis_client] Dequeued job from llm_batch_jobs: a1b2c3d4-e5f6-7890-abcd-ef1234567890
[2025-10-29 18:30:15] [INFO] [batch_worker] Processing job a1b2c3d4-e5f6-7890-abcd-ef1234567890 with 3 tasks
[2025-10-29 18:30:16] [INFO] [batch_worker] Task 0 of job a1b2c3d4-e5f6-7890-abcd-ef1234567890 completed successfully in 1123.45ms
[2025-10-29 18:30:17] [INFO] [batch_worker] Task 1 of job a1b2c3d4-e5f6-7890-abcd-ef1234567890 completed successfully in 1089.67ms
[2025-10-29 18:30:18] [INFO] [batch_worker] Task 2 of job a1b2c3d4-e5f6-7890-abcd-ef1234567890 completed successfully in 1234.89ms
[2025-10-29 18:30:18] [INFO] [batch_worker] Job a1b2c3d4-e5f6-7890-abcd-ef1234567890 completed with status completed. Completed: 3, Failed: 0
```

#### エラー時のタスク結果

一部のタスクが失敗した場合の例：

```json
{
  "task_index": 1,
  "status": "failed",
  "character": null,
  "error": "Rate limit exceeded. Please try again later.",
  "processing_time_ms": 234.56
}
```

### テスト方法

#### 1. 統合テスト（全サービス起動）

```bash
# サービスを起動
make docker-up

# ログを監視
make docker-logs

# 別ターミナルでAPIテスト
# 同期API
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"gpt-4o-mini","character_request":{"gender":"male","age":25}}'

# バッチAPI
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"gemini-2.0-flash-exp","character_requests":[{"gender":"female","age":30}]}'

# サービスを停止
make docker-down
```

#### 2. 負荷テスト

大量のバッチジョブを投入してスケーラビリティを確認：

```bash
# 10件のキャラクター生成を含むバッチジョブを投入
for i in {1..10}; do
  curl -X POST http://localhost:8001/batch/submit \
    -H "Content-Type: application/json" \
    -d '{
      "provider": "gemini",
      "model": "gemini-2.0-flash-exp",
      "character_requests": [
        {"gender": "male", "age": 20},
        {"gender": "female", "age": 25},
        {"gender": "male", "age": 30},
        {"gender": "female", "age": 35},
        {"gender": "male", "age": 40}
      ]
    }' &
done
wait

# キュー統計を確認
curl http://localhost:8001/batch/queue/stats
```

#### 3. エラーリカバリーテスト

ワーカーを停止してジョブを投入し、再起動後に処理が再開されることを確認：

```bash
# ワーカーを停止
docker stop llm-batch-worker

# ジョブを投入（キューに溜まる）
curl -X POST http://localhost:8001/batch/submit -H "Content-Type: application/json" -d '...'

# ワーカーを再起動
docker start llm-batch-worker

# ログでジョブが処理されることを確認
docker logs -f llm-batch-worker
```

#### 4. 期待される動作の確認

- **同期API**: リクエストから数秒以内に結果が返される
- **バッチAPI**: ジョブ投入は即座に完了（100ms以内）
- **ステータス確認**: ジョブの進捗がリアルタイムで反映される
- **結果取得**: 完了したジョブの全タスク結果が取得できる
- **エラーハンドリング**: 一部タスクが失敗してもジョブ全体は完了する
- **TTL**: 24時間後にRedisからデータが自動削除される

# Chapter 3 Section 7: 優先的リクエストと制限

## 概要

このプロジェクトは、**優先的リクエストと制限（Priority-based Request Handling）** を実装したLLMアプリケーションのサンプルコードです。ユーザーの契約プラン（ENTERPRISE、PREMIUM、FREE）に応じてリクエストを優先度別のキューに振り分け、重み付けスケジューリングによって処理能力を動的に割り当てます。

Redis を用いた非同期タスクキューシステムにより、OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応し、FastAPIベースのREST APIサーバーとバックグラウンドワーカーによる分散処理を実現します。フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、マルチテナント型SaaSプラットフォームにおけるサービス品質管理の実践的な実装方法を学ぶことができます。

## 機能

- **3段階の優先度キュー**: HIGH、MEDIUM、LOWの優先度レベルに対応したRedisベースのキュー管理
- **ユーザーティアマッピング**: ENTERPRISE → HIGH、PREMIUM → MEDIUM、FREE → LOW の自動マッピング
- **重み付けスケジューリング**: 設定可能な処理比率（デフォルト: 70%/20%/10%）による公平な処理配分
- **非同期タスク処理**: FastAPI + バックグラウンドワーカーによる非同期リクエスト処理
- **タスク状態管理**: PENDING、PROCESSING、COMPLETED、FAILED、TIMEOUTの状態遷移管理
- **リトライ機構**: 設定可能なリトライ回数による障害耐性
- **リアルタイム監視**: キューサイズ、処理中タスク数、待ち時間推定などの統計情報API
- **Dockerコンテナ化**: Redis、APIサーバー、ワーカーのマルチコンテナ構成
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **型安全性**: Pydanticによる厳密な型検証とバリデーション

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_7/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー、Redis設定、優先度比率）
│   ├── logger.py                # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py        # FastAPI アプリケーション（REST API）
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
│       ├── queue_manager.py     # Redisベースの優先度キュー管理
│       ├── request_llm.py       # LLM API呼び出しロジック
│       └── worker.py            # バックグラウンドワーカー
├── .env.example                 # 環境変数設定のサンプル
├── .envrc.example               # direnv用環境変数設定のサンプル
├── docker-compose.yml           # Dockerコンテナ構成定義
├── Dockerfile.web               # Webサーバー/ワーカー用Dockerfile
├── Makefile                     # ビルド・実行コマンド集
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
└── CLAUDE.md                    # 設計ドキュメント（概念説明）
```

### アーキテクチャ

このプロジェクトは、以下のマイクロサービス型アーキテクチャで構成されています：

```
┌──────────────────────────────────────────────────────────┐
│                   Client Application                     │
│                   (HTTP Client / curl)                   │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP REST API
┌────────────────────▼─────────────────────────────────────┐
│              FastAPI Server (llm-server)                 │
│  - POST /generate/queue  (キューイング)                 │
│  - GET  /task/{task_id}  (ステータス確認)               │
│  - GET  /queue/stats     (統計情報)                      │
│  - POST /generate        (同期処理)                      │
└────────────────────┬─────────────────────────────────────┘
                     │ Redis Protocol
┌────────────────────▼─────────────────────────────────────┐
│                  Redis Server (redis)                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Priority Queues (Sorted Sets)                   │   │
│  │  - llm:queue:high    (70% 処理比率)              │   │
│  │  - llm:queue:medium  (20% 処理比率)              │   │
│  │  - llm:queue:low     (10% 処理比率)              │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Task Storage (Key-Value)                        │   │
│  │  - llm:task:{task_id}  (タスク詳細情報)         │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Processing Set                                  │   │
│  │  - llm:processing (処理中タスクID)               │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬─────────────────────────────────────┘
                     │ Redis Protocol
┌────────────────────▼─────────────────────────────────────┐
│           Background Worker (llm-worker)                 │
│  - 重み付けランダム選択による優先度スケジューリング     │
│  - リトライ機構付きタスク処理                            │
│  - LLM API呼び出し                                       │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTPS API
┌────────────────────▼─────────────────────────────────────┐
│              External LLM Providers                      │
│  - OpenAI API (gpt-4o-mini, gpt-4o, etc.)               │
│  - Google Gemini API (gemini-2.5-flash, etc.)           │
└──────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/model.py`)

##### 優先度とユーザーティア

```python
class Priority(StrEnum):
    """Priority levels for request processing."""
    HIGH = "high"      # 70% の処理能力
    MEDIUM = "medium"  # 20% の処理能力
    LOW = "low"        # 10% の処理能力

class UserTier(StrEnum):
    """User tier levels."""
    ENTERPRISE = "enterprise"  # → HIGH priority
    PREMIUM = "premium"        # → MEDIUM priority
    FREE = "free"              # → LOW priority
```

##### タスクモデル

```python
class QueuedTask(BaseModel):
    task_id: str                              # UUID
    priority: Priority                        # 優先度レベル
    user_tier: UserTier                       # ユーザーティア
    provider: str                             # "openai" or "gemini"
    model: str                                # モデル名
    character_request: CharacterRequest       # リクエストパラメータ
    status: TaskStatus                        # タスク状態
    created_at: float                         # 作成時刻（UNIXタイムスタンプ）
    started_at: Optional[float]               # 処理開始時刻
    completed_at: Optional[float]             # 完了時刻
    retry_count: int                          # リトライ回数
    error_message: Optional[str]              # エラーメッセージ
    result: Optional[dict[str, Any]]          # 処理結果
```

**ポイント**:
- タスクIDは自動生成されるUUID
- 優先度はユーザーティアから自動マッピング
- タイムスタンプによる処理時間の詳細な追跡

#### 2. 優先度キュー管理 (`src/service/queue_manager.py`)

Redisの**Sorted Set**を使用して、タスクを優先度別のキューで管理します：

```python
class PriorityQueueManager:
    # Redis key prefixes
    QUEUE_PREFIX = "llm:queue"           # キュー: llm:queue:{priority}
    TASK_PREFIX = "llm:task"             # タスク: llm:task:{task_id}
    PROCESSING_SET = "llm:processing"    # 処理中セット

    async def enqueue_task(self, task: QueuedTask) -> QueuedTask:
        """タスクを優先度キューに追加"""
        # ユーザーティアから優先度を自動決定
        if not task.priority:
            task.priority = self._priority_from_user_tier(task.user_tier)

        # タスク詳細をRedisに保存
        task_key = self._get_task_key(task.task_id)
        await self.redis.set(task_key, task.model_dump_json())

        # キューに追加（スコアは作成時刻 = FIFO保証）
        queue_key = self._get_queue_key(task.priority)
        await self.redis.zadd(queue_key, {task.task_id: task.created_at})

        return task

    async def dequeue_task(self, priority: Priority) -> Optional[QueuedTask]:
        """指定優先度キューから最古のタスクを取得"""
        queue_key = self._get_queue_key(priority)

        # 最も古いタスク（最小スコア）を取得
        tasks = await self.redis.zrange(queue_key, 0, 0)
        if not tasks:
            return None

        task_id = tasks[0]

        # キューから削除
        await self.redis.zrem(queue_key, task_id)

        # タスク詳細を取得
        task_data = await self.redis.get(self._get_task_key(task_id))
        task = QueuedTask.model_validate_json(task_data)

        # 処理中セットに追加
        await self.redis.sadd(self.PROCESSING_SET, task_id)
        task.status = TaskStatus.PROCESSING

        return task
```

**技術的な選択理由**:
- **Sorted Set**: タイムスタンプをスコアとして使用することで、同一優先度内でのFIFO順序を保証
- **Key-Value**: タスク詳細情報をJSON形式で保存し、柔軟なデータ構造を実現
- **Set**: 処理中タスクの追跡により、障害時の再処理を可能に

#### 3. 重み付けスケジューリング (`src/service/worker.py`)

ワーカーは、設定された処理比率に基づいて**重み付けランダム選択**を行います：

```python
class PriorityWorker:
    def _get_next_priority(self) -> Priority:
        """
        設定された比率に基づいて次に処理する優先度を決定

        デフォルト設定:
        - HIGH:   70% (0.7)
        - MEDIUM: 20% (0.2)
        - LOW:    10% (0.1)
        """
        priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        weights = [
            config.high_priority_ratio,    # 0.7
            config.medium_priority_ratio,  # 0.2
            config.low_priority_ratio,     # 0.1
        ]

        # 重みの正規化（合計を1.0にする）
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # 重み付けランダム選択
        return random.choices(priorities, weights=normalized_weights, k=1)[0]

    async def run(self, poll_interval: float = 1.0):
        """ワーカーのメインループ"""
        while self.running:
            # 次の優先度を決定
            priority = self._get_next_priority()

            # 該当キューからタスクを取得
            task = await queue_manager.dequeue_task(priority)

            if task:
                await self._process_task(task)
            else:
                # タスクがない場合は待機
                await asyncio.sleep(poll_interval)
```

**アルゴリズムの特性**:
- **確率的公平性**: 長期的には設定比率に収束
- **飢餓状態の回避**: 低優先度タスクも必ず処理される（10%の確率）
- **動的調整可能**: 環境変数で比率を変更可能

#### 4. REST API (`src/api/llm_server.py`)

##### タスクキューイング

```python
@app.post("/generate/queue", response_model=TaskSubmissionResponse)
async def queue_generate_character(request: LLMRequest):
    """
    キャラクター生成リクエストをキューに追加

    ユーザーティアに基づいて優先度を自動決定:
    - ENTERPRISE → HIGH priority (70% 処理能力)
    - PREMIUM    → MEDIUM priority (20% 処理能力)
    - FREE       → LOW priority (10% 処理能力)
    """
    # ユーザーティアから優先度をマッピング
    priority_map = {
        UserTier.ENTERPRISE: Priority.HIGH,
        UserTier.PREMIUM: Priority.MEDIUM,
        UserTier.FREE: Priority.LOW,
    }
    priority = priority_map.get(request.user_tier, Priority.LOW)

    # タスクを作成してキューに追加
    task = QueuedTask(
        priority=priority,
        user_tier=request.user_tier,
        provider=request.provider.value,
        model=request.model,
        character_request=request.character_request,
    )
    task = await queue_manager.enqueue_task(task)

    # キュー位置を取得して待ち時間を推定
    queue_position = await queue_manager.get_queue_position(task.task_id)
    estimated_wait = queue_position * 5.0 if queue_position else None

    return TaskSubmissionResponse(
        task_id=task.task_id,
        priority=priority,
        status=TaskStatus.PENDING,
        estimated_wait_time_seconds=estimated_wait,
        message=f"Task queued with {priority.value} priority",
    )
```

##### タスク状態確認

```python
@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """タスクの現在の状態を取得"""
    task = await queue_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # ステータスに応じた情報を返却
    queue_position = None
    if task.status == TaskStatus.PENDING:
        queue_position = await queue_manager.get_queue_position(task_id)

    result = None
    if task.status == TaskStatus.COMPLETED and task.result:
        result = LLMResponse(**task.result)

    return TaskStatusResponse(
        task_id=task.task_id,
        priority=task.priority,
        status=task.status,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=result,
        error_message=task.error_message,
        queue_position=queue_position,
    )
```

##### キュー統計情報

```python
@app.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """全キューの統計情報を取得"""
    queue_sizes = await queue_manager.get_all_queue_sizes()
    processing_count = await queue_manager.get_processing_count()

    return QueueStatsResponse(
        high_priority_count=queue_sizes.get("high", 0),
        medium_priority_count=queue_sizes.get("medium", 0),
        low_priority_count=queue_sizes.get("low", 0),
        total_pending=sum(queue_sizes.values()),
        processing_count=processing_count,
    )
```

#### 5. 設定管理 (`src/config.py`)

環境変数からAPI キー、Redis接続情報、優先度比率を読み込みます：

```python
class Config(BaseModel):
    # LLM API Keys
    gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"])
    openai_api_key: Secret[str] = Field(default=os.environ["OPENAI_API_KEY"])

    # Redis Configuration
    redis_host: str = Field(default=os.environ.get("REDIS_HOST", "localhost"))
    redis_port: int = Field(default=int(os.environ.get("REDIS_PORT", 6379)))
    redis_db: int = Field(default=int(os.environ.get("REDIS_DB", 0)))

    # Queue Priority Ratios (must sum to 1.0)
    high_priority_ratio: float = Field(default=float(os.environ.get("HIGH_PRIORITY_RATIO", 0.7)))
    medium_priority_ratio: float = Field(default=float(os.environ.get("MEDIUM_PRIORITY_RATIO", 0.2)))
    low_priority_ratio: float = Field(default=float(os.environ.get("LOW_PRIORITY_RATIO", 0.1)))

    # Task Configuration
    max_retry_attempts: int = Field(default=int(os.environ.get("MAX_RETRY_ATTEMPTS", 3)))
    task_timeout_seconds: int = Field(default=int(os.environ.get("TASK_TIMEOUT_SECONDS", 300)))
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Redis**: 8.x (Alpine Linux)
- **Docker**: 20.10以上（推奨）
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - redis>=7.0.0
  - openai>=2.4.0
  - google-genai>=1.45.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - httpx>=0.28.1
  - click>=8.3.0

### セットアップ

#### 1. 環境変数ファイルの作成

```bash
# .env.exampleをコピーして.envrcを作成
cp .env.example .envrc

# エディタで.envrcを開き、APIキーを設定
vim .envrc
```

`.envrc`の設定例：

```bash
# LLM API Keys
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Queue Processing Configuration (ratios must sum to 1.0)
HIGH_PRIORITY_RATIO=0.7
MEDIUM_PRIORITY_RATIO=0.2
LOW_PRIORITY_RATIO=0.1

# Task Configuration
MAX_RETRY_ATTEMPTS=3
TASK_TIMEOUT_SECONDS=300
```

#### 2. Docker環境の起動（推奨）

```bash
# Dockerイメージのビルド
make docker-build

# コンテナの起動（Redis + API Server + Worker）
make docker-up

# ログの確認
make docker-logs

# 個別のログ確認
make docker-logs-server   # APIサーバー
make docker-logs-worker   # バックグラウンドワーカー
make docker-logs-redis    # Redisサーバー

# コンテナの停止
make docker-down
```

#### 3. ローカル環境での実行（開発用）

```bash
# 依存関係のインストール
uv sync

# Redisサーバーを起動（別ターミナル）
redis-server

# APIサーバーを起動（別ターミナル）
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload

# ワーカーを起動（別ターミナル）
uv run python -m src.service.worker
```

### 使用方法、実行方法

#### 1. キューへのタスク投入

**ENTERPRISEユーザー（高優先度）**:

```bash
curl -X POST "http://localhost:8000/generate/queue" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "Create a strong and independent character"
    },
    "user_tier": "enterprise"
  }'
```

**レスポンス例**:

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "priority": "high",
  "status": "pending",
  "estimated_wait_time_seconds": 0.0,
  "message": "Task queued successfully with high priority. Use /task/{task_id} to check status."
}
```

**PREMIUMユーザー（中優先度）**:

```bash
curl -X POST "http://localhost:8000/generate/queue" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": "Create a mysterious character"
    },
    "user_tier": "premium"
  }'
```

**FREEユーザー（低優先度）**:

```bash
curl -X POST "http://localhost:8000/generate/queue" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "female",
      "age": 22,
      "additional_instructions": null
    },
    "user_tier": "free"
  }'
```

#### 2. タスク状態の確認

```bash
# タスクIDを指定して状態を取得
curl "http://localhost:8000/task/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**PENDING状態のレスポンス**:

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "priority": "high",
  "status": "pending",
  "created_at": 1699000000.123,
  "started_at": null,
  "completed_at": null,
  "result": null,
  "error_message": null,
  "queue_position": 2
}
```

**COMPLETED状態のレスポンス**:

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "priority": "high",
  "status": "completed",
  "created_at": 1699000000.123,
  "started_at": 1699000002.456,
  "completed_at": 1699000005.789,
  "result": {
    "character": {
      "first_name": "エレナ",
      "last_name": "シルバーストーン",
      "gender": "female",
      "age": 25,
      "personalities": [
        {
          "short_personality": "決断力のあるリーダー",
          "description": "困難な状況でも冷静に判断し、チームを導く強い意志を持つ。"
        },
        {
          "short_personality": "知的な戦略家",
          "description": "複雑な問題を分析し、最適な解決策を見出す能力に優れている。"
        },
        {
          "short_personality": "思いやりのある保護者",
          "description": "仲間を大切にし、彼らの安全と幸福を常に気にかける。"
        }
      ]
    },
    "provider": "openai",
    "model": "gpt-4o-mini",
    "processing_time_ms": 3333.45
  },
  "error_message": null,
  "queue_position": null
}
```

#### 3. キュー統計情報の取得

```bash
curl "http://localhost:8000/queue/stats"
```

**レスポンス例**:

```json
{
  "high_priority_count": 3,
  "medium_priority_count": 8,
  "low_priority_count": 15,
  "total_pending": 26,
  "processing_count": 2
}
```

#### 4. 同期処理（キューを使わない即時実行）

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": "Create a tech-savvy character"
    },
    "user_tier": "enterprise"
  }'
```

**レスポンス例**:

```json
{
  "character": {
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 28,
    "personalities": [
      {
        "short_personality": "革新的な技術者",
        "description": "最新技術に精通し、常に新しい解決策を模索する。"
      },
      {
        "short_personality": "論理的思考者",
        "description": "感情よりもデータと論理に基づいて意思決定を行う。"
      },
      {
        "short_personality": "夜型の作業者",
        "description": "深夜に最も集中力が高まり、複雑な問題を解決する。"
      }
    ]
  },
  "provider": "openai",
  "model": "gpt-4o-mini",
  "processing_time_ms": 2845.67
}
```

### 出力例

#### ワーカーログの例

```
[2025-11-01 10:30:00] [INFO] [worker] Worker started with priority ratios - High: 70%, Medium: 20%, Low: 10%
[2025-11-01 10:30:02] [INFO] [queue_manager] Enqueued task a1b2c3d4-e5f6-7890-abcd-ef1234567890 to high priority queue
[2025-11-01 10:30:03] [INFO] [queue_manager] Dequeued task a1b2c3d4-e5f6-7890-abcd-ef1234567890 from high priority queue
[2025-11-01 10:30:03] [INFO] [worker] Processing task a1b2c3d4-e5f6-7890-abcd-ef1234567890 (priority: high, provider: openai/gpt-4o-mini)
[2025-11-01 10:30:06] [INFO] [queue_manager] Updated task a1b2c3d4-e5f6-7890-abcd-ef1234567890 with status completed
[2025-11-01 10:30:06] [INFO] [worker] Successfully processed task a1b2c3d4-e5f6-7890-abcd-ef1234567890 in 3333.45ms (total processed: 1)
```

#### APIサーバーログの例

```
[2025-11-01 10:30:00] [INFO] [llm_server] API server started and connected to queue manager
[2025-11-01 10:30:02] [INFO] [llm_server] Queued task a1b2c3d4-e5f6-7890-abcd-ef1234567890 for enterprise user with high priority (position: 0)
[2025-11-01 10:30:15] [INFO] [llm_server] Queued task b2c3d4e5-f6a7-8901-bcde-f23456789012 for free user with low priority (position: 5)
```

### テスト方法

#### 1. ヘルスチェック

```bash
curl "http://localhost:8000/health"
```

期待される出力：

```json
{
  "status": "healthy",
  "timestamp": 1699000000.123
}
```

#### 2. 優先度処理の検証

異なる優先度のタスクを複数投入して、処理順序を確認します：

```bash
# 1. 低優先度タスクを10個投入
for i in {1..10}; do
  curl -X POST "http://localhost:8000/generate/queue" \
    -H "Content-Type: application/json" \
    -d '{"provider":"openai","model":"gpt-4o-mini","character_request":{"gender":"male","age":25,"additional_instructions":null},"user_tier":"free"}'
done

# 2. 統計を確認（低優先度キューに10タスク）
curl "http://localhost:8000/queue/stats"

# 3. 高優先度タスクを1個投入
curl -X POST "http://localhost:8000/generate/queue" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"gpt-4o-mini","character_request":{"gender":"female","age":30,"additional_instructions":null},"user_tier":"enterprise"}'

# 4. 統計を再確認
curl "http://localhost:8000/queue/stats"

# 5. ワーカーログを監視して、高優先度タスクが優先的に処理されることを確認
make docker-logs-worker
```

期待される動作：
- 高優先度タスクが約70%の確率で選択される
- 低優先度タスクも約10%の確率で処理される（飢餓状態にならない）

#### 3. リトライ機構の検証

無効なAPIキーを設定して、リトライが正しく動作することを確認します：

```bash
# 1. 意図的に失敗するタスクを投入
# （一時的に無効なAPIキーを設定）

# 2. タスク状態を確認
curl "http://localhost:8000/task/{task_id}"

# 3. ワーカーログでリトライが3回実行され、最終的にFAILEDになることを確認
make docker-logs-worker
```

期待される動作：
- `retry_count`が0 → 1 → 2 → 3 と増加
- 3回のリトライ後、`status`が`failed`になる
- `error_message`にエラー詳細が記録される

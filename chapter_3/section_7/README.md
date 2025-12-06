# Chapter 3 Section 7: 優先度ベースのリクエスト処理

## 概要

本プロジェクトは、LLMアプリケーションにおける**優先度ベースのリクエスト処理**の本番レベル実装を示しています。Redisを使用した3層のプライオリティキューシステムにより、異なるビジネス重要度を持つリクエストを管理し、プレミアムユーザーへのサービス品質を維持しながら、低優先度リクエストの「飢餓状態」を防ぎます。

実世界のLLMアプリケーションでは、すべてのリクエストが同等ではありません。高額を支払うエンタープライズ顧客は、無料ユーザーよりも速いレスポンスタイムを期待します。本実装は、**重み付きランダム選択アルゴリズム**を使用して、公平性と優先度のバランスを実現しています。

Producer-Consumerパターンを採用し、FastAPI APIサーバーがリクエストを受け付けてRedisキューに投入し、バックグラウンドワーカーがタスクを処理します。

## 機能

- **3層優先度システム**: ユーザーティア（ENTERPRISE/PREMIUM/FREE）から優先度（HIGH/MEDIUM/LOW）への自動マッピング
- **重み付きスケジューリング**: 設定可能な処理比率（デフォルト: HIGH 70%, MEDIUM 20%, LOW 10%）
- **非同期タスク処理**: タスクIDによるステータス追跡と結果取得
- **リトライ機構**: 設定可能な最大リトライ回数（デフォルト: 3回）
- **キュー統計**: リアルタイムのキューサイズと処理中タスク数の監視
- **同期/非同期API**: キューをバイパスする同期処理と非同期キュー処理の両方をサポート
- **型安全性**: Pydanticによる厳密な型検証とバリデーション

## プロジェクト構成

### ディレクトリ構成

```
src/
├── __init__.py
├── config.py              # 環境変数ベースの設定管理
├── logger.py              # ロギング設定
├── api/
│   ├── __init__.py
│   └── llm_server.py      # FastAPI REST APIサーバー
├── client/
│   ├── __init__.py
│   └── llm_client.py      # OpenAI APIクライアント
├── model/
│   ├── __init__.py
│   └── model.py           # Pydanticデータモデル
├── prompt/
│   ├── __init__.py
│   └── prompt.py          # プロンプト生成
└── service/
    ├── __init__.py
    ├── queue_manager.py   # Redis優先度キュー管理
    ├── request_llm.py     # LLM APIリクエスト処理
    └── worker.py          # バックグラウンドワーカー
```

### アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   クライアント   │────▶│  FastAPI Server │────▶│     Redis       │
│                 │     │  (Producer)     │     │  Priority Queue │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌──────────────────────────┘
                              ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │     Worker      │────▶│   OpenAI API    │
                        │   (Consumer)    │     │                 │
                        └─────────────────┘     └─────────────────┘

Redis データ構造:
┌─────────────────────────────────────────────────────────────────┐
│  Sorted Set: llm:queue:high   (score=timestamp, member=task_id) │
│  Sorted Set: llm:queue:medium (score=timestamp, member=task_id) │
│  Sorted Set: llm:queue:low    (score=timestamp, member=task_id) │
│  Key-Value:  llm:task:{id}    (JSON serialized QueuedTask)      │
│  Set:        llm:processing   (task_ids currently processing)   │
└─────────────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. 優先度キュー管理 (`src/service/queue_manager.py`)

Redis Sorted Setを使用してFIFO順序を保証しながら優先度キューを実装しています。

```python
class PriorityQueueManager:
    QUEUE_PREFIX = "llm:queue"
    TASK_PREFIX = "llm:task"
    PROCESSING_SET = "llm:processing"
    TERMINAL_STATUSES = frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT})
    USER_TIER_PRIORITY_MAP = {
        UserTier.ENTERPRISE: Priority.HIGH,
        UserTier.PREMIUM: Priority.MEDIUM,
        UserTier.FREE: Priority.LOW,
    }

    async def enqueue_task(self, task: QueuedTask) -> QueuedTask:
        """Add a task to the appropriate priority queue."""
        redis = await self._ensure_connected()

        if not task.priority:
            task.priority = self.get_priority_for_user_tier(task.user_tier)

        await redis.set(self._get_task_key(task.task_id), task.model_dump_json())
        await redis.zadd(self._get_queue_key(task.priority), {task.task_id: task.created_at})

        return task

    async def dequeue_task(self, priority: Priority) -> Optional[QueuedTask]:
        """Remove and return the oldest task from the specified priority queue."""
        redis = await self._ensure_connected()
        queue_key = self._get_queue_key(priority)

        task_ids = await redis.zrange(queue_key, 0, 0)
        if not task_ids:
            return None

        task_id = task_ids[0]
        await redis.zrem(queue_key, task_id)

        task_data = await redis.get(self._get_task_key(task_id))
        task = QueuedTask.model_validate_json(task_data)
        await redis.sadd(self.PROCESSING_SET, task_id)
        task.status = TaskStatus.PROCESSING

        return task
```

**ポイント**:
- Sorted Setのスコアにタイムスタンプを使用し、同一優先度内でのFIFO順序を保証
- タスクデータは別途Key-Valueに保存し、キューのオーバーヘッドを削減
- Processing Setでクラッシュリカバリ用の追跡を実現

#### 2. 重み付きスケジューラ (`src/service/worker.py`)

飢餓状態を防ぎながら優先度を尊重するスケジューリングを実装しています。

```python
@dataclass
class PriorityWeights:
    high: float = field(default_factory=lambda: config.high_priority_ratio)
    medium: float = field(default_factory=lambda: config.medium_priority_ratio)
    low: float = field(default_factory=lambda: config.low_priority_ratio)

    def normalized(self) -> list[float]:
        total = self.high + self.medium + self.low
        return [w / total for w in self.as_list()]


class WeightedPriorityScheduler:
    PRIORITIES = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

    def select_priority(self) -> Priority:
        return random.choices(self.PRIORITIES, weights=self._weights.normalized(), k=1)[0]
```

**ポイント**:
- 重み付きランダム選択により、長期的に設定比率に収束
- LOW優先度も10%の処理機会を保証（飢餓状態を防止）

#### 3. REST API (`src/api/llm_server.py`)

FastAPIを使用した非同期APIサーバーを実装しています。

```python
@app.post("/generate/queue", response_model=TaskSubmissionResponse, tags=["Queue"])
async def queue_generate_character(request: LLMRequest):
    """Queue a character generation request with priority based on user tier."""
    validate_request(request)

    priority = queue_manager.get_priority_for_user_tier(request.user_tier)

    task = await queue_manager.enqueue_task(
        QueuedTask(
            priority=priority,
            user_tier=request.user_tier,
            provider=request.provider.value,
            model=request.model,
            character_request=request.character_request,
        )
    )

    queue_position = await queue_manager.get_queue_position(task.task_id)
    estimated_wait = queue_position * ESTIMATED_SECONDS_PER_TASK if queue_position is not None else None

    return TaskSubmissionResponse(
        task_id=task.task_id,
        priority=priority,
        status=TaskStatus.PENDING,
        estimated_wait_time_seconds=estimated_wait,
        message=f"Task queued with {priority.value} priority.",
    )
```

#### 4. データモデル (`src/model/model.py`)

Pydanticを使用した型安全なデータモデルを定義しています。

```python
class UserTier(StrEnum):
    ENTERPRISE = "enterprise"  # HIGH priority
    PREMIUM = "premium"        # MEDIUM priority
    FREE = "free"              # LOW priority

class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class QueuedTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: Priority
    user_tier: UserTier
    provider: str
    model: str
    character_request: CharacterRequest
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    result: Optional[dict[str, Any]] = None
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - fastapi >= 0.119.0
  - redis >= 7.0.0
  - openai >= 2.4.0
  - pydantic >= 2.12.2
  - uvicorn >= 0.37.0
  - httpx >= 0.28.1

### セットアップ

1. 環境変数の設定

```bash
# .envrc.example をコピーして編集
cp .envrc.example .envrc

# 必須の環境変数
export OPENAI_API_KEY="your_openai_api_key"

# Redis設定（デフォルト値あり）
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"

# キュー処理設定（合計1.0）
export HIGH_PRIORITY_RATIO="0.7"
export MEDIUM_PRIORITY_RATIO="0.2"
export LOW_PRIORITY_RATIO="0.1"

# タスク設定
export MAX_RETRY_ATTEMPTS="3"
export TASK_TIMEOUT_SECONDS="300"
```

2. 依存関係のインストール

```bash
uv sync
```

3. Redisの起動

```bash
docker run -d --name redis -p 6379:6379 redis:8-alpine
```

### 使用方法、実行方法

1. APIサーバーの起動

```bash
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000
```

2. ワーカーの起動（別ターミナル）

```bash
uv run python -m src.service.worker
```

3. APIへのリクエスト

```bash
# 非同期キュー処理（ENTERPRISEユーザー = 高優先度）
curl -X POST http://localhost:8000/generate/queue \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "user_tier": "enterprise",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "科学者のキャラクター"
    }
  }'

# タスクステータス確認
curl http://localhost:8000/task/{task_id}

# キュー統計
curl http://localhost:8000/queue/stats

# 同期処理（キューをバイパス）
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": null
    }
  }'
```

### 出力例

タスク投入レスポンス:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "priority": "high",
  "status": "pending",
  "estimated_wait_time_seconds": 5.0,
  "message": "Task queued with high priority. Use /task/{task_id} to check status."
}
```

タスク完了レスポンス:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "priority": "high",
  "status": "completed",
  "created_at": 1704067200.123,
  "started_at": 1704067201.456,
  "completed_at": 1704067204.789,
  "result": {
    "character": {
      "first_name": "Yuki",
      "last_name": "Tanaka",
      "gender": "female",
      "age": 25,
      "personalities": [
        {
          "short_personality": "知的好奇心旺盛",
          "description": "常に新しい知識を求め、未知の領域への探求を楽しむ"
        },
        {
          "short_personality": "冷静沈着",
          "description": "困難な状況でも落ち着いて論理的に対処する"
        },
        {
          "short_personality": "内向的",
          "description": "一人の時間を大切にし、深い思考に没頭することを好む"
        }
      ]
    },
    "provider": "openai",
    "model": "gpt-4o-mini",
    "processing_time_ms": 3456.78
  },
  "error_message": null,
  "queue_position": null
}
```

キュー統計レスポンス:

```json
{
  "high_priority_count": 2,
  "medium_priority_count": 5,
  "low_priority_count": 10,
  "total_pending": 17,
  "processing_count": 1
}
```

ワーカーログの例:

```
[INFO] Worker started with priority ratios - High: 70%, Medium: 20%, Low: 10%
[INFO] Enqueued task a1b2c3d4-... to high priority queue
[INFO] Processing task a1b2c3d4-... (priority: high, provider: openai/gpt-4o-mini)
[INFO] Completed task a1b2c3d4-... in 3333.45ms (total: 1)
```

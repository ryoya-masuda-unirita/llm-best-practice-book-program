# Chapter 3 Section 5: 優先的リクエストと制御

## 概要

本プロジェクトは、LLMアプリケーションにおける**優先的リクエストと制御**の本番レベル実装を示しています。Redisを使用した3層のプライオリティキューシステムにより、異なるビジネス重要度を持つリクエストを管理し、プレミアムユーザーへのサービス品質を維持しながら、低優先度リクエストの「飢餓状態」を防ぎます。

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

```bash
$ curl -X POST http://localhost:8000/generate/queue \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "user_tier": "premium",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "科学者のキャラクター"
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   435  100   206  100   229  31373  34876 --:--:-- --:--:-- --:--:-- 72500
{
  "task_id": "e0480150-d87f-437c-a6a5-c3fa65a950a7",
  "priority": "medium",
  "status": "pending",
  "estimated_wait_time_seconds": 0.0,
  "message": "Task queued with medium priority. Use /task/{task_id} to check status."
}
```

タスク完了レスポンス:

```bash
$ curl http://localhost:8000/task/e0480150-d87f-437c-a6a5-c3fa65a950a7 | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1247  100  1247    0     0   228k      0 --:--:-- --:--:-- --:--:--  243k
{
  "task_id": "e0480150-d87f-437c-a6a5-c3fa65a950a7",
  "priority": "medium",
  "status": "completed",
  "created_at": 1769323127.3165317,
  "started_at": 1769323130.756634,
  "completed_at": 1769323136.0602348,
  "result": {
    "character": {
      "first_name": "Luna",
      "last_name": "Navarro",
      "gender": "female",
      "age": 25,
      "personalities": [
        {
          "short_personality": "好奇心旺盛",
          "description": "Lunaは新しい知識を追求することに情熱を持ち、未知の世界に足を踏み入れることを恐れない。科学の奥深さに惹かれ、多くの実験を自ら進んで行う。"                                                                                                                                 
        },
        {
          "short_personality": "冷静沈着",
          "description": "困難な状況でも冷静に考え、素早く適切な判断ができる。実験が予期せず失敗しても、感情をコントロールし、次のステップを冷静に計画することができる。"                                                                                                                           
        },
        {
          "short_personality": "協調性がある",
          "description": "チームワークを大切にし、同僚とのコミュニケーションを重視する。他の研究者と協力してプロジェクトを進めることで、より創造的な解決策を見つけ出す能力に優れている。"                                                                                                           
        }
      ]
    },
    "provider": "openai",
    "model": "gpt-4o-mini",
    "processing_time_ms": 5303.569555282593
  },
  "error_message": null,
  "queue_position": null
}
```

キュー統計レスポンス:

```bash
$ curl http://localhost:8000/queue/stats | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   113  100   113    0     0  17028      0 --:--:-- --:--:-- --:--:-- 18833
{
  "high_priority_count": 0,
  "medium_priority_count": 0,
  "low_priority_count": 0,
  "total_pending": 0,
  "processing_count": 0
}
```

ワーカーログの例:

```
[INFO] Worker started with priority ratios - High: 70%, Medium: 20%, Low: 10%
[INFO] Enqueued task a1b2c3d4-... to high priority queue
[INFO] Processing task a1b2c3d4-... (priority: high, provider: openai/gpt-4o-mini)
[INFO] Completed task a1b2c3d4-... in 3333.45ms (total: 1)
```

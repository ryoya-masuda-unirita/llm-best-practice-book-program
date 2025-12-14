# Chapter 2 Section 6: 非同期バッチ処理

## 概要

本プロジェクトは、LLMアプリケーションにおける**非同期バッチ処理**の実装例です。Redisをメッセージキューとして使用し、大量のLLMリクエストを効率的に処理するアーキテクチャを示しています。

リアルタイム応答が不要な大規模タスク（ドキュメント要約、データ分析、コンテンツ生成など）において、リクエストの受付と処理を分離することで、システムのスケーラビリティと耐障害性を向上させます。クライアントはジョブを登録後、ジョブIDを使って非同期に進捗確認と結果取得を行います。

本実装では、架空のキャラクター生成をユースケースとして採用しています。ユーザーは複数のキャラクター生成リクエスト（性別、年齢、性格特性など）をバッチで投入し、バックグラウンドワーカーがGemini Batch APIを呼び出して処理を実行します。

## 機能

- **バッチジョブ登録API**: 複数のキャラクター生成リクエストを一括登録し、即座にジョブIDを返却
- **ジョブステータス追跡**: リアルタイムで処理進捗（完了数、失敗数、保留数）を確認
- **結果取得API**: 完了したジョブの結果を取得
- **バックグラウンドワーカー**: Redisキューを監視し、Gemini Batch APIでジョブを並行処理
- **水平スケーリング**: ワーカーを複数起動することでスループットを向上
- **自動クリーンアップ**: TTL（24時間）によりジョブデータを自動削除

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_6/
├── src/
│   ├── api/
│   │   ├── batch_server.py    # バッチジョブ管理API（ポート8001）
│   │   └── llm_server.py      # 同期LLM API（ポート8000）
│   ├── worker/
│   │   └── batch_worker.py    # バックグラウンドワーカー
│   ├── client/
│   │   ├── llm_client.py      # Geminiクライアント
│   │   └── redis_client.py    # Redisクライアント
│   ├── model/
│   │   ├── model.py           # キャラクターモデル
│   │   └── batch_model.py     # バッチジョブモデル
│   ├── service/
│   │   └── request_llm.py     # Gemini Batch API呼び出し
│   ├── prompt/
│   │   └── prompt.py          # プロンプト生成
│   ├── config.py              # 設定管理
│   └── logger.py              # ロガー
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
└── .env.example
```

### アーキテクチャ

```
+------------------+
|     Clients      |
+--------+---------+
         |
         +------------------+----------------------+
         |                  |                      |
+--------v--------+  +------v-------+  +-----------v----------+
|   LLM Server    |  | Batch Server |  |    Batch Worker      |
|   (Port 8000)   |  | (Port 8001)  |  |    (Background)      |
|                 |  |              |  |                      |
| POST /generate  |  | POST /submit |  | - ジョブ取得ループ     |
|                 |  | GET /status  |  | - ポーリングループ     |
|                 |  | GET /result  |  | - Gemini API送信      |
+--------+--------+  +------+-------+  +-----------+----------+
         |                  |                      |
         +------------------+----------------------+
                            |
                     +------v------+
                     |    Redis    |
                     | (Port 6379) |
                     |             |
                     | - ジョブキュー |
                     | - ステータス  |
                     | - 結果       |
                     +-------------+
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Redis**: 7.0以上
- **依存ライブラリ**:
  - `redis>=7.0.0`
  - `fastapi>=0.115.0`
  - `uvicorn>=0.30.0`
  - `pydantic>=2.10.0`
  - `google-genai>=1.0.0`

### セットアップ

1. **環境変数の設定**

```bash
cp .env.example .env
# .envファイルを編集してAPIキーを設定
```

```bash
# .env
GEMINI_API_KEY=<your_gemini_api_key>
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

2. **依存関係のインストール**

```bash
uv sync
```

### 実行方法

#### Docker Composeを使用する場合

```bash
# サービスを起動
make docker-up

# ログを確認
make docker-logs

# サービスを停止
make docker-down
```

#### ローカルで実行する場合

```bash
# Redisを起動（別ターミナル）
redis-server

# Batch Serverを起動（別ターミナル）
uvicorn src.api.batch_server:app --host 0.0.0.0 --port 8001

# Batch Workerを起動（別ターミナル）
python -m src.worker.batch_worker
```

### APIエンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/health` | GET | ヘルスチェック |
| `/batch/submit` | POST | バッチジョブを登録 |
| `/batch/{job_id}/status` | GET | ジョブステータスを取得 |
| `/batch/{job_id}/result` | GET | ジョブ結果を取得 |
| `/batch/queue/stats` | GET | キュー統計を取得 |
| `/batch/jobs` | GET | 全ジョブIDを取得 |

### 使用例

#### 1. バッチジョブの登録

```bash
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_requests": [
      {"gender": "female", "age": 25, "additional_instructions": "明るい性格"},
      {"gender": "male", "age": 30, "additional_instructions": "知的な性格"}
    ]
  }'
```

レスポンス:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "total_tasks": 2,
  "submitted_at": 1699999999.123
}
```

#### 2. ジョブステータスの確認

```bash
curl http://localhost:8001/batch/550e8400-e29b-41d4-a716-446655440000/status
```

レスポンス:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_tasks": 2,
  "completed_tasks": 1,
  "failed_tasks": 0,
  "pending_tasks": 1,
  "submitted_at": 1699999999.123,
  "started_at": 1699999999.456,
  "completed_at": null
}
```

#### 3. 結果の取得

```bash
curl http://localhost:8001/batch/550e8400-e29b-41d4-a716-446655440000/result
```

レスポンス:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "tasks": [
    {
      "task_index": 0,
      "status": "completed",
      "character": {
        "first_name": "Sakura",
        "last_name": "Tanaka",
        "gender": "female",
        "age": 25,
        "personalities": [
          {"short_personality": "陽気", "description": "常に明るく周囲を笑顔にする"},
          {"short_personality": "好奇心旺盛", "description": "新しいことに挑戦するのが大好き"},
          {"short_personality": "思いやり", "description": "他者の気持ちに寄り添える優しさを持つ"}
        ]
      },
      "processing_time_ms": 1234.56
    }
  ],
  "submitted_at": 1699999999.123,
  "completed_at": 1700000005.789
}
```

#### 4. キュー統計の取得

```bash
curl http://localhost:8001/batch/queue/stats
```

レスポンス:
```json
{
  "queue_name": "llm_batch_jobs",
  "pending_jobs": 5
}
```

#### 5. 全ジョブIDの取得

```bash
curl http://localhost:8001/batch/jobs
```

レスポンス:
```json
{
  "job_ids": ["550e8400-e29b-41d4-a716-446655440000", "..."],
  "count": 3
}
```

### Makeコマンド

```bash
make lint          # リントチェック
make fmt           # コードフォーマット
make fix           # lint + fmt
make mypy          # 型チェック
make docker-build  # Dockerイメージをビルド
make docker-up     # Docker Composeでサービスを起動
make docker-down   # サービスを停止
make docker-logs   # ログを表示
make docker-restart # サービスを再起動
```

### 出力例

#### ワーカーログ

```
[INFO] [batch_worker] Batch worker started, waiting for jobs...
[INFO] [batch_worker] Submitting job 550e8400-... with 2 tasks to Gemini
[INFO] [batch_worker] Job 550e8400-... submitted to Gemini as batches/xxx
[INFO] [batch_worker] Gemini batch job succeeded: batches/xxx
[INFO] [batch_worker] Batch API completed in 5234.56ms for 2 tasks
[INFO] [batch_worker] Job 550e8400-... completed: 2 succeeded, 0 failed
```

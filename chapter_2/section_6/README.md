# Chapter 2 Section 6: 非同期バッチ処理

## 概要

本プロジェクトは、LLMアプリケーションにおける**非同期バッチ処理**の実装例です。Redisをメッセージキューとして使用し、大量のLLMリクエストを効率的に処理するアーキテクチャを示しています。

リアルタイム応答が不要な大規模タスク（ドキュメント要約、データ分析、コンテンツ生成など）において、リクエストの受付と処理を分離することで、システムのスケーラビリティと耐障害性を向上させます。クライアントはジョブを登録後、ジョブIDを使って非同期に進捗確認と結果取得を行います。

本実装では、架空のキャラクター生成をユースケースとして採用しています。ユーザーは複数のキャラクター生成リクエスト（性別、年齢、性格特性など）をバッチで投入し、バックグラウンドワーカーが各プロバイダーのBatch APIを呼び出して処理を実行します。

### 対応プロバイダー

| プロバイダー | モデル | Batch API方式 |
|------------|--------|---------------|
| OpenAI | gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano | JSONLファイルアップロード → バッチ作成 → ポーリング → 結果JSONL取得 |
| Gemini | gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite | インラインリクエスト → バッチ作成 → ポーリング → インライン結果取得 |
| Anthropic | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5 | リクエストリスト → バッチ作成 → ポーリング → 結果ストリーミング取得 |

## 機能

- **マルチプロバイダー対応**: OpenAI、Gemini、Anthropicの3つのBatch APIに対応
- **バッチジョブ登録API**: 複数のキャラクター生成リクエストを一括登録し、即座にジョブIDを返却
- **ジョブステータス追跡**: リアルタイムで処理進捗（完了数、失敗数、保留数）を確認
- **結果取得API**: 完了したジョブの結果を取得
- **バックグラウンドワーカー**: Redisキューを監視し、各プロバイダーのBatch APIでジョブを並行処理
- **水平スケーリング**: ワーカーを複数起動することでスループットを向上
- **自動クリーンアップ**: TTL（24時間）によりジョブデータを自動削除

## プロジェクト構成

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
|                 |  | GET /result  |  | - プロバイダー別送信   |
+--------+--------+  +------+-------+  +-----------+----------+
         |                  |                      |
         +------------------+----------+-----------+
                            |          |
                     +------v------+   |
                     |    Redis    |   |
                     | (Port 6379) |   |
                     |             |   |
                     | - ジョブキュー |   |
                     | - ステータス  |   |
                     | - 結果       |   |
                     +-------------+   |
                                       |
              +------------------------+------------------------+
              |                        |                        |
      +-------v-------+       +-------v-------+       +--------v------+
      |  OpenAI API   |       |  Gemini API   |       | Anthropic API |
      | Batch API     |       | Batch API     |       | Batch API     |
      +---------------+       +---------------+       +---------------+
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
  - `openai>=2.4.0`
  - `anthropic>=0.74.1`

### セットアップ

1. **環境変数の設定**

```bash
cp .env.example .env
cp .envrc.example .envrc
# .envファイルを編集してAPIキーを設定
```

```bash
# .env
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

> **注意**: Docker Composeは`.env`ファイルから環境変数を読み込みます。`.envrc`はdirenv用（ローカル開発の便利ツール）で、中身は`dotenv`コマンドのみです。`.env`ファイルにAPIキーを設定すれば、ローカル実行・Docker実行の両方で動作します。

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

# 利用可能なMakeコマンド一覧
make help
Docker Commands:
  make docker-build    - Build Docker image
  make docker-up       - Start services with docker-compose
  make docker-down     - Stop services
  make docker-logs     - View service logs
  make docker-restart  - Restart services (down + up)
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

```bash
# Dockerイメージのビルド
make docker-build

# サービスを起動
make docker-up
```

#### OpenAI Batch API

```bash
# バッチジョブを登録（OpenAI）
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-5.4-mini",
    "character_requests": [
      {"gender": "female", "age": 25, "additional_instructions": "cheerful"},
      {"gender": "male", "age": 30, "additional_instructions": "intellectual"}
    ]
  }'
```

#### Gemini Batch API

```bash
# バッチジョブを登録（Gemini）
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_requests": [
      {"gender": "female", "age": 25, "additional_instructions": "cheerful"},
      {"gender": "male", "age": 30, "additional_instructions": "intellectual"}
    ]
  }'
```

#### Anthropic Batch API

```bash
# バッチジョブを登録（Anthropic）
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "character_requests": [
      {"gender": "female", "age": 22, "additional_instructions": "brave warrior"},
      {"gender": "male", "age": 35, "additional_instructions": "wise scholar"}
    ]
  }'
```

#### ジョブ管理

```bash
# ジョブステータスを取得
curl http://localhost:8001/batch/{job_id}/status

# ジョブ結果を取得
curl http://localhost:8001/batch/{job_id}/result

# キュー統計を取得
curl http://localhost:8001/batch/queue/stats

# 全ジョブIDを取得
curl http://localhost:8001/batch/jobs
```

#### Swagger UI
API: `http://localhost:8000/docs`

### 出力例

```bash
$ curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-5.4-mini",
    "character_requests": [
      {"gender": "male", "age": 30, "additional_instructions": "cheerful"}
    ]
  }'

{"job_id":"7b3f25d3-b05c-4599-9902-627371352c3d","status":"pending","total_tasks":1,"submitted_at":1775269281.5831172}

$ curl http://localhost:8001/batch/7b3f25d3-b05c-4599-9902-627371352c3d/status

{"job_id":"7b3f25d3-b05c-4599-9902-627371352c3d","status":"completed","total_tasks":1,"completed_tasks":1,"failed_tasks":0,"pending_tasks":0,"submitted_at":1775269281.5831172,"started_at":1775269281.6482563,"completed_at":1775269361.8253925}

$ curl http://localhost:8001/batch/7b3f25d3-b05c-4599-9902-627371352c3d/result

{"job_id":"7b3f25d3-b05c-4599-9902-627371352c3d","status":"completed","provider":"openai","model":"gpt-5.4-mini","tasks":[{"task_index":0,"status":"completed","character":{"first_name":"Ren","last_name":"Mizuhara","gender":"male","age":30,"personalities":[{"short_personality":"cheerful, resilient, perceptive","description":"Ren maintains a bright, uplifting demeanor even in difficult situations..."},{"short_personality":"kind, improvisational, curious","description":"He is naturally kind and tends to assume the best in people..."},{"short_personality":"optimistic, loyal, quietly determined","description":"Ren believes problems can be solved and people can change..."}]},"error":null,"processing_time_ms":80210.7150554657}],"submitted_at":1775269281.5853896,"completed_at":1775269361.8253925}

$ curl http://localhost:8001/batch/queue/stats

{"queue_name":"llm_batch_jobs","pending_jobs":0}
```

### Batch APIのジョブ状態

各プロバイダーのBatch APIは異なる状態遷移を持ちます：

| プロバイダー | 処理中の状態 | 完了状態 | 失敗状態 |
|------------|------------|---------|---------|
| OpenAI | `validating`, `in_progress`, `finalizing` | `completed` | `failed`, `expired`, `cancelled` |
| Gemini | `JOB_STATE_PENDING`, `JOB_STATE_RUNNING` | `JOB_STATE_SUCCEEDED` | `JOB_STATE_FAILED`, `JOB_STATE_CANCELLED`, `JOB_STATE_EXPIRED` |
| Anthropic | `in_progress` | `ended` | — （結果内の各リクエスト単位で成功/失敗を判定） |

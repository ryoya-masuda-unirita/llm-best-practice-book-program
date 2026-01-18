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

#### コマンドライン

```bash
# バッチジョブを登録
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
API: `http://localhost:8001/docs`

### 出力例

```bash
$ curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_requests": [
      {"gender": "female", "age": 25, "additional_instructions": "cheerful"},
      {"gender": "male", "age": 30, "additional_instructions": "intellectual"}
    ]
  }'

{"job_id":"eadc410c-0bb6-4c98-86d9-c8e783c7fbab","status":"pending","total_tasks":2,"submitted_at":1768636286.8760014}

$ curl http://localhost:8001/batch/eadc410c-0bb6-4c98-86d9-c8e783c7fbab/status

{"job_id":"eadc410c-0bb6-4c98-86d9-c8e783c7fbab","status":"completed","total_tasks":1,"completed_tasks":1,"failed_tasks":0,"pending_tasks":0,"submitted_at":1768635937.4919648,"started_at":1768635937.4952552,"completed_at":1768636173.9760518}

$ curl http://localhost:8001/batch/eadc410c-0bb6-4c98-86d9-c8e783c7fbab/result
{"job_id":"eadc410c-0bb6-4c98-86d9-c8e783c7fbab","status":"completed","provider":"gemini","model":"gemini-2.5-flash","tasks":[{"task_index":0,"status":"completed","character":{"first_name":"Elara","last_name":"Vance","gender":"female","age":100,"personalities":[{"short_personality":"Wise & Observant","description":"Elara possesses a profound wisdom cultivated over a century of life, allowing her to offer insightful advice and see through superficialities. She is incredibly observant, noticing subtle details others often miss, which contributes to her sharp understanding of people and situations."},{"short_personality":"Playful & Mischievous","description":"Despite her advanced age, Elara retains a surprisingly youthful and playful spirit. She enjoys lighthearted banter and has a mischievous glint in her eyes, often orchestrating harmless pranks or witty remarks to entertain herself and those around her, much like a clever, curious cat."},{"short_personality":"Independent & Resilient","description":"Having navigated a full century of change, Elara is fiercely independent, preferring to rely on her own wit and strength rather than becoming a burden. Her resilience is legendary, having faced countless challenges with an unwavering spirit and a quiet determination that has seen her through all of life's ups and downs."}]},"error":null,"processing_time_ms":236478.39045524597}],"submitted_at":1768635937.4920466,"completed_at":1768636173.9760518}

$ curl http://localhost:8001/batch/queue/stats

{"queue_name":"llm_batch_jobs","pending_jobs":0}

$ curl http://localhost:8001/batch/jobs

{"job_ids":["687c6962-0a58-416e-a054-50a49dfeaf42","eadc410c-0bb6-4c98-86d9-c8e783c7fbab","2ea22c25-52b6-4686-a933-62726a0075c6","e61a060b-99de-4b57-a6e5-90e83aa5a347","3b39c27f-2ea6-4597-8c5d-520128c2621d"],"count":5}
```

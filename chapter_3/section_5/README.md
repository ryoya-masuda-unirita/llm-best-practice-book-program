# Chapter 3 Section 5: 状態変化と読み取りの責任分離（LLMシステムのCQRS）

## 概要

このプロジェクトは、**CQRS（Command Query Responsibility Segregation）パターン**を用いたLLMシステムの実装サンプルです。状態を変更する処理（Command）とデータを読み取る処理（Query）を明確に分離することで、高スループットと低レイテンシを両立させるアーキテクチャを実現します。

キャラクター生成システムを通じて、大規模なLLMアプリケーションにおける知識ベースの管理手法を学ぶことができます。生成されたキャラクター情報は、Gemini Embedding APIを使用してベクトル化され、ChromaDBに非同期で保存されます。ユーザーは保存された知識ベースに対して、セマンティック検索を用いて高速に情報を取得できます。

## 機能

### コア機能
- **CQRS実装**: Command（書き込み）とQuery（読み取り）の完全な責任分離
- **非同期知識登録**: バックグラウンドでの高スループット書き込み処理
- **同期知識検索**: 低レイテンシの検索API
- **カスタムEmbedding**: Gemini APIによる高品質なベクトル生成（768次元）
- **ベクトルデータベース**: ChromaDBを使用したセマンティック検索

### LLM統合
- **Gemini対応**: Google Gemini（2.5 Pro, 2.5 Flash, 2.5 Flash Lite）をサポート
- **構造化出力**: Pydanticモデルによる型安全なLLM応答
- **自動知識保存**: キャラクター生成時に自動的に知識ベースへ保存

### インフラストラクチャ
- **Docker Compose対応**: ChromaDB、LLMサーバー、知識ベースサーバーの統合デプロイ
- **永続化**: Docker volumeによるデータ永続化
- **ヘルスチェック**: サービス間の依存関係管理と健全性監視
- **環境切り替え**: ローカル開発とDocker環境のシームレスな切り替え

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_5/
├── src/
│   ├── __init__.py                 # パッケージ初期化、共有ThreadPoolExecutor
│   ├── config.py                   # 設定管理（APIキー読み込み）
│   ├── logger.py                   # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   ├── llm_server.py           # LLM APIサーバー（Port 8000）
│   │   └── knowledge_server.py     # 知識ベースAPIサーバー（Port 8001）
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py           # Gemini APIクライアント初期化
│   │   └── chromadb_client.py      # ChromaDBクライアント（ローカル/リモート対応）
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                # LLMデータモデル定義
│   │   └── knowledge.py            # 知識ベース用データモデル（Command/Query）
│   ├── service/
│   │   ├── __init__.py
│   │   ├── request_llm.py          # LLMリクエストハンドラ
│   │   ├── embedding_service.py    # Gemini Embedding生成サービス
│   │   ├── knowledge_command.py    # Commandサイド（非同期書き込み）
│   │   └── knowledge_query.py      # Queryサイド（同期読み取り）
│   └── prompt/
│       ├── __init__.py
│       └── prompt.py               # プロンプト生成ロジック
├── data/
│   └── chromadb/                   # ローカル開発時のChromaDBデータ（自動作成）
├── docker-compose.yml              # Docker Compose設定
├── pyproject.toml                  # プロジェクト依存関係
└── README.md                       # このファイル
```

### アーキテクチャ

このプロジェクトは、CQRSパターンに基づく3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────────────┐
│                     ユーザーリクエスト                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────┴────────────┐
       │                        │
       ▼                        ▼
┌─────────────┐        ┌─────────────────┐
│ LLMサーバー  │        │知識ベースサーバー│
│  Port 8000  │        │   Port 8001     │
│             │        │                 │
│キャラクター  │        │  ┌───────────┐  │
│    生成     │        │  │ Command   │  │
│  (Gemini)   │        │  │  (書込)   │  │
│             │        │  │  非同期   │  │
└──────┬──────┘        │  └─────┬─────┘  │
       │               │        │        │
       │ バックグラウンド│        │        │
       │   タスク      │◄───────┘        │
       │               │                 │
       │               │  ┌───────────┐  │
       │               │  │  Query    │  │
       │               │  │  (読取)   │  │
       │               │  │   同期    │  │
       │               │  └─────┬─────┘  │
       └───────────────┴────────┴─────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    ChromaDB     │
              │  Vector Store   │
              │  Port 8002      │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Gemini API     │
              │  Embedding/LLM  │
              └─────────────────┘
```

**処理フロー**:

1. **キャラクター生成（LLMサーバー）**
   - ユーザーがキャラクター生成をリクエスト
   - Gemini を使用してキャラクター情報を生成
   - レスポンスを即座にユーザーに返却
   - バックグラウンドでCommand処理を実行

2. **Command処理（非同期書き込み）**
   - キャラクター情報からテキスト表現を生成
   - Gemini Embedding APIでベクトル化（768次元）
   - ChromaDBにベクトルとメタデータを保存
   - 高スループット、結果整合性

3. **Query処理（同期読み取り）**
   - ユーザーが検索クエリを送信
   - Gemini Embedding APIでクエリをベクトル化
   - ChromaDBでベクトル類似度検索を実行
   - 類似度スコア付きで結果を返却
   - 低レイテンシ、即座に応答

### 実装の詳細

#### 1. CQRS パターン実装

**Command Side（書き込み）** - `src/service/knowledge_command.py`:

```python
async def register_knowledge_async(command: KnowledgeRegisterCommand) -> str:
    """
    知識を非同期で登録。

    即座にjob_idを返し、実際の処理はバックグラウンドで実行。
    高スループットを実現。
    """
    job_id = str(uuid.uuid4())

    # バックグラウンドタスクとして実行
    asyncio.create_task(_store_in_chromadb_async(command, job_id))

    return job_id
```

**Query Side（読み取り）** - `src/service/knowledge_query.py`:

```python
async def search_knowledge(query: KnowledgeSearchQuery) -> KnowledgeSearchResponse:
    """
    知識ベースを同期的に検索。

    低レイテンシで結果を返却。
    クエリのEmbeddingを生成し、ベクトル類似度検索を実行。
    """
    start_time = time.time()

    # Gemini Embedding APIでクエリをベクトル化
    query_embedding = await get_embedding(query.query_text)

    # ChromaDBで検索
    results = await loop.run_in_executor(executor, _search_chromadb, query_embedding, query)

    query_time = (time.time() - start_time) * 1000
    return KnowledgeSearchResponse(results=items, total_count=len(items), query_time_ms=query_time)
```

#### 2. Gemini Embedding 統合

**Embedding生成** - `src/service/embedding_service.py`:

```python
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_EMBEDDING_DIMENSION = 768

async def get_embedding(text: str) -> list[float]:
    """Gemini APIを使用して埋め込みベクトルを生成"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_gemini_embedding_sync, text)

def _get_gemini_embedding_sync(text: str) -> list[float]:
    result = google_genai_client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
    )
    return result.embeddings[0].values
```

**ポイント**:
- Gemini Embedding: 768次元、多言語（日本語含む）に最適化
- キャラクター生成と検索で同じEmbeddingモデルを使用

#### 3. ChromaDB クライアント

**ローカル/リモート自動切り替え** - `src/client/chromadb_client.py`:

```python
# 環境変数でChromaDBの接続先を制御
CHROMA_HOST = os.getenv("CHROMA_HOST", None)

if CHROMA_HOST:
    # Docker環境: HTTPクライアント
    chroma_client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=int(CHROMA_PORT),
    )
else:
    # ローカル開発: 永続クライアント
    chroma_client = chromadb.Client(
        Settings(persist_directory="./data/chromadb")
    )
```

**ポイント**:
- 同じコードでローカルとDockerの両方に対応
- Docker Composeで自動的に環境変数が設定される
- 開発時は `./data/chromadb` にデータを保存

#### 4. データモデル

**Command モデル** - `src/model/knowledge.py`:

```python
class KnowledgeRegisterCommand(BaseModel):
    """知識登録のためのCommandモデル"""
    character_request: CharacterRequest
    character_response: CharacterResponse
    model: str
    prompt: list[dict]
    processing_time_ms: float
    metadata: Optional[dict] = None
```

**Query モデル**:

```python
class KnowledgeSearchQuery(BaseModel):
    """知識検索のためのQueryモデル"""
    query_text: str
    limit: int = Field(default=10, ge=1, le=100)
    filter_metadata: Optional[dict] = None
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Docker**: 20.10以上（Docker Compose使用時）
- **依存ライブラリ**:
  - chromadb >= 1.3.0
  - fastapi >= 0.119.0
  - google-genai >= 1.45.0
  - pydantic >= 2.12.2
  - uvicorn >= 0.37.0

### セットアップ

#### 方法1: ローカル開発

1. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

2. **環境変数の設定**

```bash
export GEMINI_API_KEY="AIza..."
```

3. **サーバーの起動**

```bash
# ターミナル1: LLMサーバー
uv run python -m src.api.llm_server

# ターミナル2: 知識ベースサーバー
uv run python -m src.api.knowledge_server
```

#### 方法2: Docker Compose

1. **環境変数の設定**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **サービスの起動**

```bash
# すべてのサービスを起動
docker-compose up -d

# サービスの状態確認
docker-compose ps
```

3. **ヘルスチェック**

```bash
# LLMサーバー
curl http://localhost:8000/health

# 知識ベースサーバー
curl http://localhost:8001/health
```

### 使用方法、実行方法

#### 1. キャラクターの生成（自動的に知識ベースに保存）

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "勇敢な戦士キャラクターを作成してください"
    }
  }'
```

**レスポンス例**:
```json
{
  "character": {
    "first_name": "アリア",
    "last_name": "ストームボーン",
    "gender": "female",
    "age": 25,
    "personalities": [
      {
        "short_personality": "勇敢な戦士",
        "description": "どんな困難にも立ち向かう不屈の精神を持つ..."
      }
    ]
  },
  "model": "gemini-2.5-flash",
  "processing_time_ms": 1250.5
}
```

**処理フロー**:
1. キャラクターが即座に生成され、レスポンスが返却される
2. バックグラウンドでGemini Embedding APIでベクトル化（768次元）
3. ChromaDBにベクトルとメタデータが保存される

#### 2. 知識ベースの検索

```bash
# 数秒待ってから検索（非同期処理の完了を待つ）
sleep 5

curl -X POST "http://localhost:8001/query/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "勇敢な戦士",
    "limit": 5
  }'
```

**レスポンス例**:
```json
{
  "results": [
    {
      "id": "uuid-here",
      "character_request": {...},
      "character_response": {...},
      "model": "gemini-2.5-flash",
      "processing_time_ms": 1250.5,
      "similarity_score": 0.95,
      "created_at": 1234567890.0
    }
  ],
  "total_count": 1,
  "query_time_ms": 45.2
}
```

#### 3. 統計情報の取得

```bash
curl http://localhost:8001/query/stats
```

**レスポンス例**:
```json
{
  "total_items": 100,
  "models_distribution": {
    "gemini-2.5-flash": 80,
    "gemini-2.5-pro": 20
  },
  "timestamp": 1234567890.0
}
```

#### 4. 直接知識を登録（Command API）

```bash
curl -X POST "http://localhost:8001/command/register" \
  -H "Content-Type: application/json" \
  -d '{
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": "冷静沈着"
    },
    "character_response": {
      "first_name": "太郎",
      "last_name": "山田",
      "gender": "male",
      "age": 30,
      "personalities": [
        {"short_personality": "冷静", "description": "どんな状況でも冷静さを保つ"},
        {"short_personality": "論理的", "description": "論理的思考を重視する"},
        {"short_personality": "誠実", "description": "約束を必ず守る"}
      ]
    },
    "model": "gemini-2.5-flash",
    "prompt": [],
    "processing_time_ms": 1000.0
  }'
```

**レスポンス例**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "accepted",
  "message": "Knowledge registration queued for processing"
}
```

### 出力例

#### キャラクター生成のログ

```
[2025-10-29 10:30:45] [INFO] [llm_server] Generating character with gemini/gemini-2.5-flash
[2025-10-29 10:30:47] [INFO] [llm_server] Successfully generated character in 1250.50ms
[2025-10-29 10:30:47] [INFO] [llm_server] Queued knowledge registration for background processing
```

#### Command処理（非同期）のログ

```
[2025-10-29 10:30:47] [INFO] [knowledge_command] Accepting knowledge registration command with job_id: a1b2c3d4-...
[2025-10-29 10:30:47] [INFO] [knowledge_command] Generating Gemini embedding for job_id: a1b2c3d4-...
[2025-10-29 10:30:48] [INFO] [knowledge_command] Successfully stored knowledge with job_id: a1b2c3d4-... (embedding dim: 768)
```

#### Query処理（同期）のログ

```
[2025-10-29 10:31:00] [INFO] [knowledge_query] Searching knowledge base with query: 勇敢な戦士...
[2025-10-29 10:31:00] [INFO] [knowledge_query] Search completed in 45.20ms, found 3 results
```

## 注意点

### 結果整合性（Eventual Consistency）

Command処理は非同期で実行されるため、データが書き込まれてからQuery処理で参照可能になるまでに若干の遅延（2-5秒程度）が発生します。この特性を理解した上でシステムを設計してください。

### ChromaDBの動作モード

- **ローカルモード**: `CHROMA_HOST`環境変数が未設定の場合、`./data/chromadb`にデータを永続化
- **リモートモード**: `CHROMA_HOST`と`CHROMA_PORT`を設定することで、外部のChromaDBサーバーに接続

```bash
# リモートChromaDBを使用する場合
export CHROMA_HOST="chromadb-server"
export CHROMA_PORT="8000"
```

### 利用可能なGeminiモデル

| モデル | 用途 |
|--------|------|
| `gemini-2.5-pro` | 高精度なキャラクター生成 |
| `gemini-2.5-flash` | バランスの取れた高速生成 |
| `gemini-2.5-flash-lite` | 軽量で最速の生成 |

# Chapter 3 Section 5: 状態変化と読み取りの責任分離（LLMシステムのCQRS）

## 概要

このプロジェクトは、**CQRS（Command Query Responsibility Segregation）パターン**を用いたLLMシステムの実装サンプルです。状態を変更する処理（Command）とデータを読み取る処理（Query）を明確に分離することで、高スループットと低レイテンシを両立させるアーキテクチャを実現します。

キャラクター生成システムを通じて、大規模なLLMアプリケーションにおける知識ベースの管理手法を学ぶことができます。生成されたキャラクター情報は、OpenAIまたはGeminiのEmbedding APIを使用してベクトル化され、ChromaDBに非同期で保存されます。ユーザーは保存された知識ベースに対して、セマンティック検索を用いて高速に情報を取得できます。

## 機能

### コア機能
- **CQRS実装**: Command（書き込み）とQuery（読み取り）の完全な責任分離
- **非同期知識登録**: バックグラウンドでの高スループット書き込み処理
- **同期知識検索**: 低レイテンシの検索API
- **カスタムEmbedding**: OpenAIとGemini APIによる高品質なベクトル生成
- **ベクトルデータベース**: ChromaDBを使用したセマンティック検索

### LLM統合
- **マルチプロバイダー対応**: OpenAI（GPT-4o-mini等）とGoogle Gemini（2.5 Flash等）の両方をサポート
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
│   ├── __init__.py
│   ├── config.py                    # 設定管理（API キー読み込み）
│   ├── logger.py                    # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   ├── llm_server.py            # LLM API サーバー（キャラクター生成）
│   │   └── knowledge_server.py      # 知識ベース API サーバー（CQRS）
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py            # LLM クライアント初期化
│   │   └── chromadb_client.py       # ChromaDB クライアント（ローカル/リモート対応）
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                 # LLM データモデル定義
│   │   └── knowledge.py             # 知識ベース用データモデル（Command/Query）
│   ├── service/
│   │   ├── __init__.py
│   │   ├── request_llm.py           # LLM リクエストハンドラ
│   │   ├── embedding_service.py     # Embedding 生成サービス
│   │   ├── knowledge_command.py     # Command サイド（非同期書き込み）
│   │   └── knowledge_query.py       # Query サイド（同期読み取り）
│   └── prompt/
│       ├── __init__.py
│       └── prompt.py                # プロンプト生成ロジック
├── data/
│   └── chromadb/                    # ローカル開発時のChromaDBデータ（自動作成）
├── docker-compose.yml               # Docker Compose設定
├── Dockerfile.web                   # アプリケーション用Dockerfile
├── Makefile                         # ビルド・実行タスク
├── .envrc.example                   # 環境変数設定のサンプル
├── pyproject.toml                   # プロジェクト依存関係
├── README.md                        # このファイル
└── CLAUDE.md                        # プロジェクト状態レポート
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
│             │        │  │  (書込)   │  │
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
              │  Embedding API  │
              │  OpenAI/Gemini  │
              └─────────────────┘
```

**処理フロー**:

1. **キャラクター生成（LLMサーバー）**
   - ユーザーがキャラクター生成をリクエスト
   - OpenAI または Gemini を使用してキャラクター情報を生成
   - レスポンスを即座にユーザーに返却
   - バックグラウンドでCommand処理を実行

2. **Command処理（非同期書き込み）**
   - キャラクター情報からテキスト表現を生成
   - 同じプロバイダー（OpenAI/Gemini）でEmbeddingを生成
   - ChromaDBにベクトルとメタデータを保存
   - 高スループット、結果整合性

3. **Query処理（同期読み取り）**
   - ユーザーが検索クエリを送信
   - 指定されたプロバイダーでクエリのEmbeddingを生成
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
    # クエリのEmbedding生成
    query_embedding = await get_embedding(query.query_text, query.embedding_provider)

    # ChromaDBで検索
    results = await search_chromadb(query_embedding, query)

    return results
```

#### 2. カスタム Embedding 統合

**OpenAI Embeddings** - `src/service/embedding_service.py`:

```python
async def get_openai_embedding(text: str) -> list[float]:
    """OpenAI の text-embedding-3-small を使用（1536次元）"""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
```

**Gemini Embeddings**:

```python
def get_gemini_embedding(text: str) -> list[float]:
    """Gemini の gemini-embedding-001 を使用（768次元）"""
    result = google_genai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values
```

**ポイント**:
- キャラクター生成と同じプロバイダーでEmbeddingを生成
- OpenAI: 1536次元、汎用的で高品質
- Gemini: 768次元、多言語（日本語含む）に最適化
- プロバイダー一致で検索精度が向上

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
    provider: str
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
    embedding_provider: str = Field(default="openai")  # 検索用プロバイダー
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Docker**: 20.10以上
- **Docker Compose**: 2.0以上
- **依存ライブラリ**:
  - fastapi>=0.115.0
  - uvicorn>=0.32.0
  - chromadb>=0.5.0
  - openai>=2.4.0
  - google-genai>=1.45.0
  - pydantic>=2.12.2

### セットアップ

#### 方法1: Docker Compose（推奨）

1. **環境変数の設定**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **ChromaDBイメージの取得**

```bash
docker pull chromadb/chroma:1.3.0-amd64
```

3. **サービスの起動**

```bash
# すべてのサービスを起動
docker-compose up -d

# サービスの状態確認
docker-compose ps

# 期待される出力:
# chromadb-server        Up (healthy)
# llm-api-server         Up
# knowledge-api-server   Up
```

4. **ヘルスチェック**

```bash
# LLMサーバー
curl http://localhost:8000/health

# 知識ベースサーバー
curl http://localhost:8001/health

# ChromaDB
curl http://localhost:8002/api/v1/heartbeat
```

#### 方法2: ローカル開発

1. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

2. **環境変数の設定**

```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."
```

3. **サーバーの起動**

```bash
# ターミナル1: LLMサーバー
python -m src.api.llm_server

# ターミナル2: 知識ベースサーバー
python -m src.api.knowledge_server
```

### 使用方法、実行方法

#### 1. キャラクターの生成（自動的に知識ベースに保存）

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
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
      },
      ...
    ]
  },
  "provider": "openai",
  "model": "gpt-4o-mini",
  "processing_time_ms": 1250.5
}
```

**処理フロー**:
1. キャラクターが即座に生成され、レスポンスが返却される
2. バックグラウンドでEmbeddingが生成される（OpenAI text-embedding-3-small）
3. ChromaDBにベクトルとメタデータが保存される

#### 2. 知識ベースの検索

```bash
# 数秒待ってから検索（非同期処理の完了を待つ）
sleep 5

curl -X POST "http://localhost:8001/query/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "勇敢な戦士",
    "embedding_provider": "openai",
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
      "provider": "openai",
      "model": "gpt-4o-mini",
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
  "providers_distribution": {
    "openai": 60,
    "gemini": 40
  },
  "models_distribution": {
    "gpt-4o-mini": 50,
    "gpt-4o": 10,
    "gemini-2.5-flash": 40
  },
  "timestamp": 1234567890.0
}
```

#### 4. プロバイダーごとの検索

**OpenAI で生成 → OpenAI で検索（推奨）**:
```bash
# 生成
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "openai", "model": "gpt-4o-mini", ...}'

# 検索（同じプロバイダー）
curl -X POST "http://localhost:8001/query/search" \
  -d '{"query_text": "...", "embedding_provider": "openai"}'
```

**Gemini で生成 → Gemini で検索（推奨）**:
```bash
# 生成
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "gemini", "model": "gemini-2.5-flash", ...}'

# 検索（同じプロバイダー）
curl -X POST "http://localhost:8001/query/search" \
  -d '{"query_text": "...", "embedding_provider": "gemini"}'
```

### 出力例

#### キャラクター生成のログ

```
[2025-10-29 10:30:45] [INFO] [llm_server] Generating character with openai/gpt-4o-mini
[2025-10-29 10:30:47] [INFO] [llm_server] Successfully generated character in 1250.50ms
[2025-10-29 10:30:47] [INFO] [llm_server] Queued knowledge registration for background processing
```

#### Command処理（非同期）のログ

```
[2025-10-29 10:30:47] [INFO] [knowledge_command] Accepting knowledge registration command with job_id: a1b2c3d4-...
[2025-10-29 10:30:47] [INFO] [embedding_service] Generating embedding using openai API
[2025-10-29 10:30:48] [INFO] [knowledge_command] Successfully stored knowledge with job_id: a1b2c3d4-... using openai embedding (dim: 1536)
```

#### Query処理（同期）のログ

```
[2025-10-29 10:31:00] [INFO] [knowledge_query] Searching knowledge base with query: 勇敢な戦士... using openai embeddings
[2025-10-29 10:31:00] [INFO] [knowledge_query] Search completed in 45.20ms, found 3 results
```

### テスト方法

#### 1. エンドツーエンドテスト

```bash
# サービスの起動
docker-compose up -d && sleep 30

# OpenAIでキャラクター生成
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": "魔法使い"
    }
  }'

# 非同期処理の完了を待つ
sleep 5

# 統計を確認
curl http://localhost:8001/query/stats | jq

# 検索テスト
curl -X POST "http://localhost:8001/query/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "魔法使い",
    "embedding_provider": "openai",
    "limit": 5
  }' | jq
```

#### 2. CQRS動作の確認

**Commandの非同期性を確認**:
```bash
# 時間測定
time curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", ...}'

# レスポンスタイムは短い（~1-2秒）
# 実際のEmbedding生成と保存はバックグラウンドで実行
```

**Queryの同期性を確認**:
```bash
# 時間測定
time curl -X POST "http://localhost:8001/query/search" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "...", "embedding_provider": "openai"}'

# レスポンスタイムにEmbedding生成時間が含まれる（~100-300ms）
```

#### 3. Embeddingの一貫性テスト

```bash
# 同じプロバイダーで生成と検索
./test_consistency.sh openai

# 異なるプロバイダーで比較
./test_consistency.sh gemini
```

#### 4. スケーリングテスト

```bash
# 複数のキャラクターを並行生成
for i in {1..10}; do
  curl -X POST "http://localhost:8000/generate" \
    -H "Content-Type: application/json" \
    -d '{"provider": "openai", ...}' &
done
wait

# 統計で確認
curl http://localhost:8001/query/stats
```

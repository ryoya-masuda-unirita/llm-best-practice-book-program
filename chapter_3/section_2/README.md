# Chapter 3 Section 2: LLMシステムのストレージと実行を分離する

## 概要

このプロジェクトは、**ストレージ層と実行層を分離した設計パターン（Bridge Pattern）** を用いたLLMシステムの実装サンプルです。キャッシュやデータベースへのアクセス処理と、LLM APIの呼び出し処理を疎結合に保つことで、コンポーネントの独立性を高め、柔軟でテストしやすく、保守性の高いシステムを実現します。

本実装では、FastAPIベースのREST APIサーバーを提供し、OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応しています。また、インメモリキャッシュとRedisキャッシュの両方をサポートし、環境に応じて柔軟に切り替えることができます。

## 機能

- **ストレージと実行の分離**: Bridge Patternを用いた責務の明確な分離
- **キャッシング機能**: インメモリとRedisベースの2種類のキャッシュバックエンドをサポート
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **依存性注入（DI）**: Factoryパターンによる柔軟なサービスインスタンス管理
- **REST APIサーバー**: FastAPIによる高性能なAPIエンドポイント
- **キャッシュメトリクス**: キャッシュヒット率、ミス数などの監視機能
- **キャッシュ無効化**: 任意のキャッシュキーを手動で無効化する機能
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **Docker対応**: Docker Composeによる簡単なデプロイメント

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_2/
├── src/
│   ├── __init__.py                # パッケージ初期化
│   ├── config.py                  # 設定管理（API キー、キャッシュ設定）
│   ├── logger.py                  # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py          # FastAPI サーバー実装
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py          # LLMクライアント初期化
│   │   └── cache_client.py        # キャッシュクライアント（Redis、インメモリ）
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py               # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py              # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── interface.py           # ILLMService インターフェース（Bridge）
│       ├── storage.py             # ストレージ層実装（キャッシュ）
│       ├── execution.py           # 実行層実装（LLM API呼び出し）
│       ├── factory.py             # Factoryパターン実装
│       └── request_llm.py         # リクエスト処理
├── .env.example                    # 環境変数設定のサンプル
├── .envrc.example                  # direnv設定のサンプル
├── docker-compose.yml              # Docker Compose設定
├── Dockerfile.web                  # Webサーバー用Dockerfile
├── Makefile                        # 開発用コマンド
├── pyproject.toml                  # プロジェクト依存関係
├── README.md                       # このファイル
└── CLAUDE.md                       # プロジェクト設計書

```

### アーキテクチャ

本プロジェクトは、**Bridge Pattern** を中核とした3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────┐
│        API Layer (FastAPI)                      │
│    - エンドポイント定義                         │
│    - リクエスト/レスポンス処理                  │
│    - ヘルスチェック、メトリクス                 │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│        Service Layer (Bridge Pattern)           │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │   ILLMService (Interface)                │  │
│  │   - generate_character()                 │  │
│  │   - invalidate_cache()                   │  │
│  └──────────────┬───────────┬────────────────┘  │
│                 │           │                    │
│    ┌────────────▼──────┐  ┌▼──────────────────┐ │
│    │ CachedLLMService  │  │ ExecutionLLMService│ │
│    │ (Storage Layer)   │  │ (Execution Layer)  │ │
│    │ - キャッシュ管理  │  │ - LLM API呼び出し │ │
│    │ - メトリクス収集  │  │ - プロバイダー管理│ │
│    └────────────┬──────┘  └────────────────────┘ │
│                 │                                 │
│    ┌────────────▼──────────────┐                 │
│    │  LLMServiceFactory (DI)   │                 │
│    │  - サービスインスタンス作成│                 │
│    │  - 環境に応じた実装切替   │                 │
│    └───────────────────────────┘                 │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│      Infrastructure Layer                       │
│  - Cache Backend (InMemory / Redis)             │
│  - LLM Client (OpenAI / Gemini)                 │
│  - Config (環境変数管理)                        │
│  - Logger (ログ出力)                            │
└─────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. Bridgeインターフェース (`src/service/interface.py`)

ストレージ層と実行層を繋ぐ共通インターフェースを定義します：

```python
class ILLMService(ABC):
    """LLMサービス操作の抽象インターフェース"""

    @abstractmethod
    async def generate_character(
        self,
        prompt: list[dict],
        model: str,
        provider: str,
        cache_key: Optional[str] = None,
    ) -> CharacterResponse:
        """キャラクターを生成"""
        pass

    @abstractmethod
    async def invalidate_cache(self, cache_key: str) -> bool:
        """キャッシュを無効化"""
        pass
```

**ポイント**:
- アプリケーションはこのインターフェースのみに依存
- 実装の詳細（キャッシュ or 直接実行）を隠蔽
- テスト時のモック化が容易

#### 2. ストレージ層実装 (`src/service/storage.py`)

キャッシュを管理する責務を持つ層です：

```python
class CachedLLMService(ILLMService):
    """キャッシング機能を持つストレージ層実装"""

    def __init__(self, execution_service: ILLMService):
        self._execution_service = execution_service
        # キャッシュバックエンドの初期化
        if config.cache_backend == CacheBackend.MEMORY:
            self._cache = InMemoryCache()
        else:
            self._cache = redis_client

    async def generate_character(
        self, prompt, model, provider, cache_key=None
    ) -> CharacterResponse:
        key = self._generate_cache_key(prompt, model, provider, cache_key)

        # キャッシュチェック
        if self._cache_enabled:
            cached_data = await self._cache.get(key)
            if cached_data:
                self._cache_hits += 1
                return CharacterResponse(**cached_data)
            self._cache_misses += 1

        # キャッシュミス → 実行層に委譲
        character = await self._execution_service.generate_character(
            prompt, model, provider, cache_key
        )

        # 結果をキャッシュに保存
        if self._cache_enabled:
            await self._cache.set(key, character.model_dump())

        return character
```

**ポイント**:
- 実行層サービスをコンストラクタで受け取る（DI）
- キャッシュヒット/ミスのメトリクスを自動収集
- キャッシュキーはリクエストパラメータのハッシュで生成
- インメモリとRedisのバックエンドを透過的に切り替え可能

#### 3. 実行層実装 (`src/service/execution.py`)

LLM APIを呼び出す責務を持つ層です：

```python
class ExecutionLLMService(ILLMService):
    """LLM API呼び出しを行う実行層実装"""

    async def generate_character(
        self, prompt, model, provider, cache_key=None
    ) -> CharacterResponse:
        logger.info(f"Executing LLM request: provider={provider}, model={model}")

        if provider == LLMProvider.OPENAI:
            return await self._request_openai(model, prompt)
        elif provider == LLMProvider.GEMINI:
            return await self._request_gemini(model, prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _request_openai(self, model, prompt):
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=1.0,
        )
        return result.choices[0].message.parsed
```

**ポイント**:
- キャッシュの存在を一切知らない（単一責任原則）
- プロバイダーごとの実装を内部メソッドで分離
- 構造化出力を使用して型安全な応答を取得

#### 4. Factoryパターン (`src/service/factory.py`)

依存性注入とサービスインスタンスの生成を管理します：

```python
class LLMServiceFactory:
    """LLMサービスインスタンスを生成するFactory"""

    @staticmethod
    def create_service() -> ILLMService:
        # 実行サービスを作成
        execution_service = ExecutionLLMService()

        # 設定に応じてキャッシュ層でラップ
        if config.cache_enabled:
            return CachedLLMService(execution_service)
        else:
            return execution_service

# シングルトンインスタンス管理
_service_instance: ILLMService = None

def get_llm_service() -> ILLMService:
    """シングルトンサービスインスタンスを取得"""
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMServiceFactory.create_service()
    return _service_instance
```

**ポイント**:
- 環境変数の設定に基づいて適切な実装を選択
- シングルトンパターンでアプリケーション全体で単一インスタンスを共有
- テスト用に `reset_llm_service()` で再初期化可能

#### 5. キャッシュクライアント (`src/client/cache_client.py`)

2種類のキャッシュバックエンドを提供します：

```python
class InMemoryCache:
    """TTLサポート付きインメモリキャッシュ"""

    def __init__(self):
        self._cache: dict[str, tuple[dict, float]] = {}

    async def get(self, key: str) -> Optional[dict]:
        if key in self._cache:
            value, expire_at = self._cache[key]
            if expire_at == 0 or time.time() < expire_at:
                return value
            del self._cache[key]  # 期限切れを削除
        return None

class RedisClient:
    """非同期Redisクライアント"""

    async def connect(self):
        self._client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=password,
        )
        await self._client.ping()

    async def get(self, key: str) -> Optional[dict]:
        value = await self._client.get(key)
        return json.loads(value) if value else None
```

**ポイント**:
- 両クライアントは同一のインターフェース（`get`, `set`, `delete`）を実装
- InMemoryCache: 開発・テスト環境向け、TTL機能付き
- RedisClient: 本番環境向け、永続化と分散キャッシュに対応

#### 6. REST APIサーバー (`src/api/llm_server.py`)

FastAPIベースのエンドポイントを提供します：

```python
@app.post("/generate", response_model=LLMResponse)
async def generate_character(request: LLMRequest):
    """キャラクター生成エンドポイント"""
    prompt = make_prompt(character_request=request.character_request)

    # Factoryからサービスを取得（DI）
    llm_service = get_llm_service()

    # サービス層に処理を委譲
    character = await llm_service.generate_character(
        prompt=prompt,
        model=request.model,
        provider=request.provider.value
    )

    return LLMResponse(character=character, ...)

@app.get("/metrics")
async def get_cache_metrics():
    """キャッシュメトリクスを取得"""
    llm_service = get_llm_service()
    if isinstance(llm_service, CachedLLMService):
        return llm_service.get_cache_metrics()
    return {"cache_enabled": False}

@app.delete("/cache/{cache_key}")
async def invalidate_cache(cache_key: str):
    """キャッシュを手動で無効化"""
    llm_service = get_llm_service()
    result = await llm_service.invalidate_cache(cache_key)
    return {"invalidated": result}
```

**ポイント**:
- サービス層の抽象インターフェースのみに依存
- キャッシュの有無を意識せずに実装できる
- メトリクス取得とキャッシュ無効化のエンドポイントを提供

#### 7. 設定管理 (`src/config.py`)

環境変数からAPIキーとキャッシュ設定を読み込みます：

```python
class CacheBackend(StrEnum):
    MEMORY = "memory"
    REDIS = "redis"

class Config(BaseModel):
    gemini_api_key: Secret[str]
    openai_api_key: Secret[str]

    # キャッシュ設定
    cache_enabled: bool = True
    cache_backend: CacheBackend = CacheBackend.MEMORY
    cache_ttl: int = 3600  # 1時間

    # Redis設定
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Secret[str] | None = None
```

**ポイント**:
- `Secret[str]`型でAPIキーを保護
- デフォルト値により最小限の設定で動作
- 環境変数の検証をPydanticが自動実行

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - redis>=7.0.0
  - click>=8.3.0
  - httpx>=0.28.1
- **オプション**:
  - Docker & Docker Compose（コンテナデプロイメント用）
  - Redis Server（Redisキャッシュ使用時）

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env

# エディタで.envを開き、APIキーを設定
# .env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX

# キャッシュ設定（デフォルト）
CACHE_ENABLED=true
CACHE_BACKEND=memory
CACHE_TTL=3600

# Redis設定（CACHE_BACKEND=redisの場合）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

3. **Redisのセットアップ（Redisキャッシュ使用時のみ）**

```bash
# ローカルでRedisを起動
docker run -d -p 6379:6379 redis:latest

# または、Homebrewでインストール（macOS）
brew install redis
brew services start redis
```

### 使用方法、実行方法

#### 方法1: ローカル実行

```bash
# LLM APIサーバーを起動
make run-llm-server

# または直接uvicornで起動
uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload
```

#### 方法2: Docker Compose実行

```bash
# Dockerイメージをビルド
make docker-build

# サービスを起動（APIサーバー + Redis）
make docker-up

# ログを確認
make docker-logs

# サービスを停止
make docker-down
```

#### API使用例

サーバーが起動したら、以下のようにAPIを呼び出します：

**1. キャラクター生成（OpenAI）**

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "character_request": {
      "gender": "male",
      "age": 28,
      "additional_instructions": "ファンタジー世界の魔法使い"
    }
  }'
```

**2. キャラクター生成（Gemini）**

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "female",
      "age": 22,
      "additional_instructions": "SF世界の宇宙飛行士"
    }
  }'
```

**3. ヘルスチェック**

```bash
curl http://localhost:8000/health
```

**4. キャッシュメトリクスの確認**

```bash
curl http://localhost:8000/metrics
```

**5. キャッシュの無効化**

```bash
curl -X DELETE "http://localhost:8000/cache/{cache_key}"
```

#### APIドキュメント

サーバー起動後、以下のURLで自動生成されたAPIドキュメントを参照できます：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 出力例

#### 1. キャラクター生成レスポンス

```json
{
  "character": {
    "first_name": "アリス",
    "last_name": "スターフィールド",
    "gender": "female",
    "age": 22,
    "personalities": [
      {
        "short_personality": "好奇心旺盛な探究者",
        "description": "未知の領域や新しい発見に対して常に興味を持ち、リスクを恐れずチャレンジする。"
      },
      {
        "short_personality": "冷静な判断力",
        "description": "緊急事態でも感情に流されず、論理的かつ迅速に最適解を導き出す能力を持つ。"
      },
      {
        "short_personality": "チームプレイヤー",
        "description": "仲間との協力を重視し、全員が安全に任務を遂行できるようサポートする。"
      }
    ]
  },
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "processing_time_ms": 1234.56
}
```

#### 2. キャッシュメトリクスレスポンス

```json
{
  "cache_enabled": true,
  "cache_backend": "redis",
  "cache_hits": 42,
  "cache_misses": 8,
  "cache_hit_rate": 0.84,
  "total_requests": 50
}
```

#### 3. サーバーログ出力例

```
[2025-10-25 15:30:45] [INFO] Starting up LLM API server...
[2025-10-25 15:30:45] [INFO] Cache enabled: True
[2025-10-25 15:30:45] [INFO] Cache backend: redis
[2025-10-25 15:30:45] [INFO] Redis connection initialized successfully
[2025-10-25 15:30:47] [INFO] Cache miss for gemini/gemini-2.5-flash (hits: 0, misses: 1, hit_rate: 0.00%)
[2025-10-25 15:30:47] [INFO] Executing LLM request: provider=gemini, model=gemini-2.5-flash
[2025-10-25 15:30:49] [INFO] Gemini API call successful: gemini-2.5-flash
[2025-10-25 15:30:49] [INFO] Successfully generated character using gemini/gemini-2.5-flash in 1234.56ms
[2025-10-25 15:30:52] [INFO] Cache hit for gemini/gemini-2.5-flash (hits: 1, misses: 1, hit_rate: 50.00%)
```

### テスト方法

現在、このセクションにはユニットテストは含まれていません。手動テストは以下の方法で行います：

#### 1. インメモリキャッシュのテスト

```bash
# .envでインメモリキャッシュを有効化
CACHE_ENABLED=true
CACHE_BACKEND=memory

# サーバーを起動
make run-llm-server

# 同じリクエストを2回実行（2回目はキャッシュヒット）
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "model": "gpt-4o-mini", "character_request": {"gender": "male", "age": 25, "additional_instructions": "test"}}'

# メトリクスを確認（cache_hits=1, cache_misses=1が期待値）
curl http://localhost:8000/metrics
```

期待される動作：
- 1回目のリクエスト: `Cache miss` ログが出力され、LLM APIを呼び出し
- 2回目のリクエスト: `Cache hit` ログが出力され、API呼び出しなし
- `processing_time_ms` が2回目は大幅に短縮されている

#### 2. Redisキャッシュのテスト

```bash
# Redisを起動
docker run -d -p 6379:6379 redis:latest

# .envでRedisキャッシュを有効化
CACHE_ENABLED=true
CACHE_BACKEND=redis

# サーバーを起動
make run-llm-server

# 同じテストを実行
curl -X POST "http://localhost:8000/generate" ...

# Redisに直接アクセスしてキャッシュを確認
docker exec -it <redis_container_id> redis-cli
> KEYS *
> GET <cache_key>
```

期待される動作：
- サーバー起動時に `Redis connection initialized successfully` ログ
- キャッシュがRedisに永続化されている
- サーバーを再起動してもキャッシュが保持されている

#### 3. キャッシュ無効化のテスト

```bash
# キャッシュキーを確認（サーバーログから取得）
curl http://localhost:8000/metrics

# キャッシュを無効化
curl -X DELETE "http://localhost:8000/cache/a1b2c3d4e5f6..."

# 同じリクエストを再実行（再度APIを呼び出し）
curl -X POST "http://localhost:8000/generate" ...
```

期待される動作：
- キャッシュ無効化後は `Cache miss` が発生
- LLM APIが再度呼び出される

#### 4. キャッシュ無効時のテスト

```bash
# .envでキャッシュを無効化
CACHE_ENABLED=false

# サーバーを起動
make run-llm-server

# リクエストを複数回実行
curl -X POST "http://localhost:8000/generate" ...

# メトリクスを確認
curl http://localhost:8000/metrics
```

期待される動作：
- すべてのリクエストでLLM APIを呼び出し
- メトリクスエンドポイントが `{"cache_enabled": false}` を返す

#### 5. プロバイダー切り替えのテスト

```bash
# OpenAIでリクエスト
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "openai", "model": "gpt-4o-mini", ...}'

# Geminiでリクエスト
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "gemini", "model": "gemini-2.5-flash", ...}'
```

期待される動作：
- 両方のプロバイダーで正常にキャラクターが生成される
- キャッシュキーはプロバイダー + モデルで異なる
- ログに適切なプロバイダー名とモデル名が出力される

#### 6. バリデーションテスト

```bash
# 無効なプロバイダー
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "invalid", "model": "test", ...}'
# 期待: 400 Bad Request

# 無効なモデル
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "openai", "model": "invalid-model", ...}'
# 期待: 400 Bad Request

# 無効な年齢
curl -X POST "http://localhost:8000/generate" \
  -d '{"provider": "openai", "model": "gpt-4o-mini", "character_request": {"gender": "male", "age": 150, ...}}'
# 期待: 422 Validation Error
```

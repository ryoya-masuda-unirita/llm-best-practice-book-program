# Chapter 2 Section 4: LLMリクエストの適応的バックオフによるリトライ

## 概要

このプロジェクトは、**適応的エクスポネンシャルバックオフ（Adaptive Exponential Backoff）** を用いたLLM APIリクエストの堅牢な実装を示すサンプルコードです。OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応し、レート制限や一時的な障害に対して自動的に再試行する仕組みを実装しています。

大量のキャラクター生成リクエストを並列バッチ処理するユースケースを通じて、本番環境で必要とされるリトライロジック、並行処理制御、エラーハンドリングの実践的な実装方法を学ぶことができます。

## 機能

- **エクスポネンシャルバックオフ**: 指数関数的に待機時間を増やす再試行戦略（1秒 → 2秒 → 4秒 → ...）
- **ランダムジッター**: 10-50%のランダムな揺らぎで複数クライアントの再試行を分散
- **Retry-Afterヘッダー対応**: API側の指示に従った適切な待機時間の設定
- **インテリジェントなエラー判定**: リトライすべきエラーと即座に失敗すべきエラーを自動判別
- **セマフォによる並行処理制御**: 同時実行数を制限して過負荷を防止
- **バッチ処理**: 複数リクエストを効率的に並列処理
- **部分的失敗への対応**: 一部のリクエストが失敗しても処理を継続
- **詳細なログ出力**: リトライ状況、成功/失敗統計を可視化
- **包括的なテストスイート**: 29個のテストケースでリトライロジックを検証

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_4/
├── src/
│   ├── __init__.py
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント（バッチ処理）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py             # Pydanticデータモデル定義
│   │   └── llmops_log.py        # LLMOpsログモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py       # リトライロジック＆バッチ処理（核心部分）
│       ├── llmops_logger.py     # LLMOps用ロガー
│       └── prompt_storage.py    # プロンプト保存機能
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytestフィクスチャ
│   └── test_request_llm.py      # リトライロジックのテスト（29ケース）
├── outputs/                      # 生成結果の保存先（自動作成）
├── prompt_storage/               # プロンプト保存先（自動作成）
├── character_requests.yaml       # キャラクター生成リクエスト定義（33件）
├── .envrc.example                # 環境変数設定のサンプル
├── pytest.ini                    # pytest設定
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # 開発用タスク
├── README.md                     # このファイル
└── CLAUDE.md                     # 開発ガイドライン
```

### アーキテクチャ

このプロジェクトは、以下の多層アーキテクチャで構成されています：

```
┌────────────────────────────────────────────────┐
│         CLI Layer (main.py)                    │
│  - コマンドライン引数解析                       │
│  - バッチ処理のオーケストレーション             │
│  - 出力ファイル管理                             │
└──────────────────┬─────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────┐
│      Service Layer (request_llm.py)            │
│  - リトライロジック                             │
│    ├── エクスポネンシャルバックオフ             │
│    ├── ランダムジッター                         │
│    └── エラー判定                               │
│  - バッチ処理                                   │
│    ├── 並列実行制御（セマフォ）                 │
│    ├── 部分的失敗のハンドリング                 │
│    └── 統計情報のログ出力                       │
└──────────────────┬─────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────┐
│      Business Logic Layer                      │
│  - プロンプト生成 (prompt.py)                  │
│  - LLMクライアント管理 (llm_client.py)         │
│  - データモデル (model.py)                     │
│  - LLMOpsロギング (llmops_logger.py)           │
└──────────────────┬─────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────┐
│      Infrastructure Layer                      │
│  - 設定管理 (config.py)                        │
│  - ログ管理 (logger.py)                        │
│  - 外部API (OpenAI, Gemini)                    │
└────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. リトライロジック (`src/service/request_llm.py`)

##### エクスポネンシャルバックオフの計算

```python
def calculate_backoff_with_jitter(attempt: int, base: float = 1.0) -> float:
    """エクスポネンシャルバックオフ時間をランダムジッターと共に計算"""
    # 指数関数的バックオフ: base * 2^attempt
    backoff = min(base * (2 ** attempt), 60)  # 最大60秒

    # ランダムジッター（10-50%）を追加
    jitter_range = backoff * (0.5 - 0.1)
    jitter = random.uniform(backoff * 0.1, backoff * 0.1 + jitter_range)

    return backoff + jitter
```

**ポイント**:
- attempt 0: ~1.1-1.5秒
- attempt 1: ~2.2-3.0秒
- attempt 2: ~4.4-6.0秒
- attempt 3: ~8.8-12.0秒
- attempt 4+: ~60秒（上限）

##### インテリジェントなエラー判定

```python
def should_retry_error(error: Exception) -> tuple[bool, int | None]:
    """エラーがリトライ可能か判定し、Retry-After値を抽出"""

    # OpenAI RateLimitError - Retry-Afterヘッダーを優先
    if isinstance(error, RateLimitError):
        retry_after = None
        if hasattr(error, 'response') and error.response:
            retry_after_header = error.response.headers.get('Retry-After')
            if retry_after_header:
                retry_after = int(retry_after_header)
        return True, retry_after

    # タイムアウト、接続エラー → リトライ可能
    if isinstance(error, (APITimeoutError, APIConnectionError)):
        return True, None

    # サーバーエラー (429, 500, 503等) → リトライ可能
    if isinstance(error, APIError):
        if hasattr(error, 'status_code') and error.status_code in {429, 500, 503, 502, 504}:
            return True, None
        return False, None  # 400, 401等 → リトライ不可

    # Geminiエラー
    if isinstance(error, google_exceptions.ResourceExhausted):
        return True, None

    return False, None  # 未知のエラー → リトライ不可
```

**リトライ可能なエラー**:
- HTTP 429 (Too Many Requests)
- HTTP 500, 502, 503, 504 (サーバーエラー)
- タイムアウト、接続エラー
- Google ResourceExhausted, ServiceUnavailable

**リトライ不可のエラー**:
- HTTP 400 (Bad Request)
- HTTP 401 (Unauthorized)
- その他のクライアントエラー

##### リトライデコレータ

```python
@retry_with_exponential_backoff(max_retries=5)
async def request_openai(
    character_request: CharacterRequest,
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """リトライロジック付きOpenAIリクエスト"""
    prompt = make_prompt(character_request)

    async with llmops_logger.track_llm_request(...) as tracking:
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=1.0,
        )
        return result.choices[0].message.parsed
```

#### 2. バッチ処理とセマフォ制御 (`src/service/request_llm.py`)

```python
async def batch_request_openai(
    character_requests: list[CharacterRequest],
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
    parallelism: int = 5,  # デフォルト5並列
) -> list[CharacterResponse]:
    """複数リクエストをバッチ処理（並行処理制御付き）"""

    # セマフォで並行実行数を制限
    semaphore = asyncio.Semaphore(parallelism)

    async def request_with_semaphore(req: CharacterRequest):
        async with semaphore:
            return await request_openai(
                character_request=req,
                model=model,
                llmops_logger=llmops_logger,
                user_id=user_id,
            )

    # 全リクエストを並列実行（セマフォで制御）
    tasks = [request_with_semaphore(req) for req in character_requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 成功/失敗を分離
    successful_results = []
    failed_requests = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Request {i + 1} failed: {result}")
            failed_requests.append(i)
        else:
            successful_results.append(result)

    logger.info(f"Successful: {len(successful_results)}, Failed: {len(failed_requests)}")
    return successful_results
```

**ポイント**:
- `asyncio.Semaphore(parallelism)`で同時実行数を制御
- `return_exceptions=True`で一部失敗しても処理継続
- 成功したリクエストのみを返却

#### 3. リクエスト定義 (`character_requests.yaml`)

```yaml
requests:
  - gender: female
    age: 25
    additional_instructions: "謎めいた過去を持つ熟練の弓使いのキャラクターを作成してください。"
  - gender: male
    age: 30
    additional_instructions: "贖罪を求める勇敢な騎士のキャラクターを設計してください。"
  # ... 全33件のリクエスト
```

**特徴**:
- YAMLファイルで複数のリクエストを定義
- Pydanticモデルで自動バリデーション
- 多様なキャラクター設定（年齢16-78歳、性別バランス、様々な職業）

#### 4. データモデル (`src/model/model.py`)

```python
class CharacterRequests(BaseModel):
    """バッチ処理用のリクエストコレクション"""
    requests: list[CharacterRequest]

    @staticmethod
    def load_from_yaml(file_path: str) -> "CharacterRequests":
        """YAMLファイルからリクエストを読み込み"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return CharacterRequests.model_validate(data)
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-api-core>=2.26.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - pyyaml>=6.0.3
- **開発依存**:
  - pytest>=8.4.2
  - pytest-asyncio>=1.2.0
  - pytest-mock>=3.15.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync --all-extras

# pipを使用する場合
pip install -e .[dev]
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用してバッチ処理（並行5リクエスト）
python -m src.main \
  --request-file character_requests.yaml \
  --llm-provider gemini \
  --model gemini-2.5-flash \
  --parallelism 5

# OpenAI APIを使用してバッチ処理（並行10リクエスト）
python -m src.main \
  --request-file character_requests.yaml \
  --llm-provider openai \
  --model gpt-4o-mini \
  --parallelism 10
```

#### 短縮オプション

```bash
# 短縮オプションを使用
python -m src.main \
  -rf character_requests.yaml \
  -lp gemini \
  -m gemini-2.5-flash \
  -p 5 \
  -od outputs
```

#### 並行処理数の調整

```bash
# 低速・安全（並行2リクエスト）
python -m src.main -rf character_requests.yaml -lp gemini -m gemini-2.5-flash -p 2

# 標準（並行5リクエスト）
python -m src.main -rf character_requests.yaml -lp gemini -m gemini-2.5-flash -p 5

# 高速（並行10リクエスト）※レート制限に注意
python -m src.main -rf character_requests.yaml -lp gemini -m gemini-2.5-flash -p 10
```

#### ヘルプの表示

```bash
python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -rf, --request-file PATH        Path to the YAML file containing character
                                  generation requests.  [required]
  -lp, --llm-provider [openai|gemini]
                                  The LLM provider to use.  [required]
  -m, --model TEXT                The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -p, --parallelism INTEGER       Number of parallel requests to make.
  -u, --user-id TEXT              User ID for logging purposes.
  -st, --storage-type [local|s3]  The storage type for prompt logging.
  --help                          Show this message and exit.
```

### 出力例

#### 実行ログ

```
[2025-10-18 16:30:45] [INFO] Request file: character_requests.yaml
LLM provider: gemini
Model: gemini-2.5-flash
Output directory: outputs
Parallelism: 5
User ID: default_user
Storage type: local

[2025-10-18 16:30:45] [INFO] Loading character requests from character_requests.yaml
[2025-10-18 16:30:45] [INFO] Loaded 33 character requests

[2025-10-18 16:30:45] [INFO] Starting batch processing of 33 requests using Gemini gemini-2.5-flash (parallelism: 5)

[2025-10-18 16:30:48] [WARNING] Request failed (attempt 1/6). Error: ServiceUnavailable: 503 Service unavailable. Retrying in 1.34s...

[2025-10-18 16:31:15] [INFO] Batch processing completed. Successful: 33, Failed: 0

[2025-10-18 16:31:15] [INFO] Saving 33 character responses to outputs
[2025-10-18 16:31:15] [INFO] Saved character 1 to outputs/gemini_001_a1b2c3d4.json
[2025-10-18 16:31:15] [INFO] Saved character 2 to outputs/gemini_002_e5f6g7h8.json
...
[2025-10-18 16:31:16] [INFO] Batch processing complete. Generated 33 characters.
```

#### 生成されたJSONファイル例

**ファイル名**: `outputs/gemini_001_a1b2c3d4.json`

```json
{
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "神秘的な弓使い",
            "description": "過去について語ることは少ないが、その弓の腕前は伝説的。静かな森で修行を積んだと噂されている。"
        },
        {
            "short_personality": "寡黙な戦士",
            "description": "無駄な言葉を話さず、行動で示すタイプ。仲間からの信頼は厚い。"
        },
        {
            "short_personality": "孤高の守護者",
            "description": "一人で行動することを好むが、弱者を見過ごすことはできない正義感の持ち主。"
        }
    ]
}
```

#### リトライ発生時のログ詳細

```
[2025-10-18 16:30:50] [WARNING] Rate limit hit (attempt 1/6). Retry-After: 3s. Waiting...
[2025-10-18 16:30:53] [INFO] Request succeeded after retry

[2025-10-18 16:30:55] [WARNING] Request failed (attempt 1/6). Error: APITimeoutError: Request timed out. Retrying in 1.42s...
[2025-10-18 16:30:56] [WARNING] Request failed (attempt 2/6). Error: APITimeoutError: Request timed out. Retrying in 2.89s...
[2025-10-18 16:30:59] [INFO] Request succeeded after 2 retries
```

### テスト方法

このプロジェクトには包括的なテストスイートが含まれています。

#### 1. 全テストの実行

```bash
# 全29ケースを実行
pytest tests/test_request_llm.py -v

# より詳細な出力
pytest tests/test_request_llm.py -vv

# 特定のテストクラスのみ実行
pytest tests/test_request_llm.py::TestRetryWithExponentialBackoff -v
```

#### 2. テストカバレッジの確認

```bash
# カバレッジレポート付きで実行
pytest tests/test_request_llm.py --cov=src/service/request_llm --cov-report=html

# ブラウザでレポートを表示
open htmlcov/index.html
```

#### 3. テストケース一覧

**TestCalculateBackoffWithJitter** (4テスト)
- 指数関数的な増加の検証
- 最大バックオフ時間の制限
- ジッターのランダム性確認
- カスタムベース時間のサポート

**TestShouldRetryError** (10テスト)
- レート制限エラー（Retry-Afterあり/なし）
- タイムアウト・接続エラー
- サーバーエラー（500, 503等）のリトライ可否
- クライアントエラー（400, 401等）のリトライ不可
- Gemini固有エラー
- 未知のエラーの扱い

**TestRetryWithExponentialBackoff** (5テスト)
- 初回成功の動作
- 複数回リトライ後の成功
- 最大リトライ回数超過
- リトライ不可エラーの即座の失敗
- Retry-Afterヘッダーの尊重

**TestRequestOpenAI** (2テスト)
- 成功ケース
- リトライ後の成功

**TestRequestGemini** (2テスト)
- 成功ケース
- リトライ後の成功

**TestBatchRequestOpenAI** (3テスト)
- バッチ処理の成功
- 部分的失敗のハンドリング
- セマフォによる並行数制御

**TestBatchRequestGemini** (3テスト)
- バッチ処理の成功
- 部分的失敗のハンドリング
- セマフォによる並行数制御

#### 4. 統合テスト（実際のAPI呼び出し）

```bash
# 少量のリクエストでテスト（実際のAPIを呼び出す）
# まず、テスト用のYAMLファイルを作成
cat > test_requests.yaml << 'EOF'
requests:
  - gender: female
    age: 25
    additional_instructions: "Test character"
  - gender: male
    age: 30
    additional_instructions: "Another test character"
EOF

# Gemini APIでテスト
python -m src.main -rf test_requests.yaml -lp gemini -m gemini-2.5-flash -p 2 -od test_outputs

# OpenAI APIでテスト
python -m src.main -rf test_requests.yaml -lp openai -m gpt-4o-mini -p 2 -od test_outputs

# 結果の検証
ls -lh test_outputs/
cat test_outputs/gemini_001_*.json | jq .
```

#### 5. リトライロジックの動作確認

意図的にレート制限を発生させてリトライを確認：

```bash
# 高い並行数で実行（レート制限が発生しやすい）
python -m src.main -rf character_requests.yaml -lp gemini -m gemini-2.5-flash -p 20 -od test_outputs

# ログでリトライの様子を確認
# [WARNING] Request failed (attempt 1/6). Error: ... Retrying in X.XXs...
# のようなログが出力されるはず
```

#### 6. 期待される結果

- 全29テストがパス（✅）
- リトライロジックが正しく動作
- エラーハンドリングが適切
- セマフォによる並行数制御が機能
- 部分的失敗時も処理が継続

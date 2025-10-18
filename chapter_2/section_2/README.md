# Chapter 2 Section 2: LLMOps構造化ログの実装

## 概要

このプロジェクトは、**構造化ログ（Structured Logging）を用いたLLMOps実装**を示すサンプルコードです。本番環境のLLMアプリケーションにおいて、可観測性（Observability）、デバッグ、コンプライアンス、パフォーマンス監視を実現するための包括的なログシステムを提供します。

従来のログアプローチでは、プロンプトとレスポンスが長すぎる、非構造化ログでは分析が困難、機密データの扱いが難しいなどの課題がありました。本システムでは、**メタデータ（構造化ログ）とコンテンツ（プロンプトストレージ）の二層アーキテクチャ**により、これらの課題を解決します。

フィクションのキャラクター生成を通じて、構造化ログの実践的な実装方法と、LLM運用における観測可能性の確保方法を学ぶことができます。

## 機能

### コアロギング機能

- **構造化JSON形式のログ**: 機械可読なJSON形式でメタデータを記録
- **分離されたプロンプトストレージ**: 長いプロンプト/レスポンスを別ファイルに保存
- **自動レイテンシ計測**: コンテキストマネージャーによる自動的なタイミング計測
- **エラーハンドリング**: 例外発生時も確実にログを記録
- **ユニークID管理**: request_idとprompt_idによる完全なトレーサビリティ

### セキュリティ機能

- **自動PII（個人情報）マスキング**: SSN、メール、クレジットカード番号などを自動検出・マスキング
- **再帰的マスキング**: ネストされた構造（リスト、辞書）にも対応
- **設定可能なマスキング**: 本番環境では有効化、開発環境では無効化可能

### ストレージ機能

- **日付ベースのパーティショニング**: `YYYY/MM/DD`形式でプロンプトを整理
- **非同期I/O処理**: リクエストレイテンシに影響を与えない非同期ストレージ
- **拡張可能な設計**: 抽象ベースクラスによるS3、GCSなどへの拡張対応
- **検索機能**: prompt_idによる高速なプロンプト検索

### LLM統合機能

- **マルチプロバイダー対応**: OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashをサポート
- **構造化出力**: Pydanticモデルによる型安全なLLM応答
- **非同期処理**: async/awaitによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリによる使いやすいコマンドラインツール

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_2/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── main.py                        # メインエントリーポイント（CLI）
│   ├── config.py                      # 設定管理（APIキー読み込み）
│   ├── logger.py                      # 基本ロガー設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                   # キャラクターレスポンスモデル
│   │   ├── llmops_log.py              # 構造化ログエントリモデル
│   │   └── prompt_data.py             # プロンプトデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py                  # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── llmops_logger.py           # メインロギングインターフェース
│       └── prompt_storage.py          # プロンプトストレージ実装
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # テストフィクスチャ（tempfile使用）
│   ├── test_llmops_log.py             # ログエントリモデルのテスト
│   ├── test_llmops_logger.py          # ロガーインターフェースのテスト
│   └── test_prompt_storage.py         # ストレージ実装のテスト
├── prompt_storage/                     # プロンプト保存先（実行時に自動作成、gitignore）
│   └── YYYY/MM/DD/*.json              # 日付パーティショニング構造
├── outputs/                            # キャラクター生成結果の保存先
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── pytest.ini                          # テスト設定
├── README.md                           # このファイル
└── CLAUDE.md                           # 設計仕様書
```

### アーキテクチャ

このプロジェクトは、以下の二層ロギングアーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                          │
│                      (main.py)                              │
│    - CLI引数解析                                            │
│    - LLMリクエスト実行                                      │
│    - 出力ファイル管理                                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLMOpsLogger                              │
│              (service/llmops_logger.py)                     │
│    - track_llm_request() コンテキストマネージャー          │
│    - 自動タイミング計測                                     │
│    - エラーハンドリング                                     │
│    - ID生成                                                 │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   Structured Log         │  │     Prompt Storage           │
│   (model/llmops_log.py)  │  │  (service/prompt_storage.py) │
│                          │  │                              │
│  • LLMOpsLogEntry        │  │  • PromptData                │
│    - timestamp           │  │  • LocalFilePromptStorage    │
│    - request_id          │  │  • mask_sensitive_data()     │
│    - prompt_id           │  │                              │
│    - model               │  │  ストレージ構造:             │
│    - temperature         │  │  prompt_storage/             │
│    - latency_ms          │  │    └── YYYY/                 │
│    - status_code         │  │        └── MM/               │
│    - level               │  │            └── DD/           │
│    - metadata            │  │                └── {id}.json │
└──────────┬───────────────┘  └──────────┬───────────────────┘
           │                             │
           ▼                             ▼
   JSON to stdout              非同期ファイルI/O
   (ストリーミングログ)         (日付パーティション)
```

### データフロー

1. **リクエスト開始**: アプリケーションが`track_llm_request()`コンテキストマネージャーを使用
2. **タイミング開始**: 開始時刻を自動的に記録
3. **LLM呼び出し**: コンテキスト内でLLMリクエストを実行
4. **レスポンス取得**: レスポンスをトラッキング辞書に保存
5. **レイテンシ計算**: コンテキスト終了時に自動的に経過時間を計算
6. **並列処理**:
   - 構造化ログエントリを作成してstdoutに出力（同期）
   - プロンプト/レスポンス内容をファイルシステムに保存（非同期）
7. **エラーハンドリング**: 例外が発生した場合もERRORレベルでログを記録

### 実装の詳細

#### 1. 構造化ログエントリ (`src/model/llmops_log.py`)

Pydanticを使用して、LLM操作のメタデータを厳密に型付けします：

```python
class LLMOpsLogEntry(BaseModel):
    timestamp: str              # ISO 8601形式、自動生成
    request_id: str            # リクエストのユニークID
    prompt_id: str             # プロンプトの参照ID
    user_id: Optional[str]     # ユーザー識別子
    model: str                 # 使用したLLMモデル名
    temperature: float         # 温度パラメータ（0.0-2.0）
    latency_ms: Optional[float] # レスポンス時間（ミリ秒）
    status_code: Optional[int]  # HTTPステータスコード
    error_message: Optional[str] # エラーメッセージ
    level: LogLevel            # ログレベル
    metadata: dict[str, Any]   # 拡張可能なカスタムデータ
```

**ポイント**:
- プロンプト内容は含まない（メタデータのみ）
- JSON形式で出力し、ログ集約ツール（Datadog、BigQuery等）と連携可能
- `exclude_none=True`でクリーンな出力を実現
- バリデーション制約（temperature: 0.0-2.0など）

#### 2. プロンプトストレージ (`src/service/prompt_storage.py`)

プロンプトとレスポンスの内容を別ファイルに保存します：

**抽象ベースクラス**:
```python
class PromptStorage(ABC):
    @abstractmethod
    async def save_prompt(self, prompt_data, mask_sensitive=True) -> str:
        """プロンプトデータを保存し、保存パスを返す"""
        pass

    @abstractmethod
    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]:
        """prompt_idでプロンプトデータを取得"""
        pass
```

**ローカルファイル実装**:
```python
class LocalFilePromptStorage(PromptStorage):
    def _get_storage_path(self, prompt_id: str, date: datetime) -> Path:
        # prompt_storage/YYYY/MM/DD/prompt_id.json
        year_dir = self.base_dir / str(date.year)
        month_dir = year_dir / f"{date.month:02d}"
        day_dir = month_dir / f"{date.day:02d}"
        return day_dir / f"{prompt_id}.json"
```

**特徴**:
- 日付ベースのパーティショニングで効率的な検索
- 非同期I/Oによるパフォーマンス最適化
- データ保持ポリシーの実装が容易
- 将来的にS3、GCSなどへの拡張が可能

#### 3. PIIマスキング (`src/model/prompt_data.py`)

正規表現ベースの自動マスキング機能：

```python
class PromptData(BaseModel):
    def mask_sensitive_data(self) -> None:
        patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****"),  # SSN
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "***@***.***"),  # Email
            (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "****-****-****-****"),  # Credit card
        ]
        # 再帰的にマスキング（文字列、リスト、辞書に対応）
```

**対応パターン**:
- SSN（社会保障番号）: `123-45-6789` → `***-**-****`
- メールアドレス: `user@example.com` → `***@***.***`
- クレジットカード番号: `4111-1111-1111-1111` → `****-****-****-****`

#### 4. LLMOpsLogger (`src/service/llmops_logger.py`)

メインのロギングインターフェース：

**コンテキストマネージャー（推奨）**:
```python
async with llmops_logger.track_llm_request(
    model="gpt-4o-mini",
    temperature=1.0,
    prompt_content=prompt,
    user_id="user123",
    metadata={"provider": "openai"}
) as tracking:
    response = await llm_client.generate(...)
    tracking["response"] = response
```

**利点**:
- 自動タイミング計測（手動の開始/終了不要）
- 自動エラーハンドリング
- 確実なクリーンアップ（finally節）
- クリーンなAPI（手動のログ呼び出し不要）

**内部動作**:
1. request_idとprompt_idを自動生成（未指定の場合）
2. エントリー時に開始時刻を記録
3. トラッキング辞書をyieldしてレスポンス保存を可能に
4. 終了時（成功/失敗問わず）にレイテンシを計算
5. status_codeを設定（成功: 200、例外: 500）
6. 適切なログレベル（INFOまたはERROR）でログ出力

#### 5. アプリケーション統合 (`src/main.py`)

実際のLLM呼び出しでの使用例：

**OpenAI実装**:
```python
async def request_openai(user_id: str = "default_user") -> CharacterResponse:
    prompt = make_prompt()
    model = "gpt-4o-mini"
    temperature = 1.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "openai", "response_format": "CharacterResponse"},
    ) as tracking:
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=temperature,
        )
        parsed_response = result.choices[0].message.parsed
        tracking["response"] = parsed_response.model_dump() if parsed_response else None
        return parsed_response
```

**Gemini実装**:
```python
async def request_gemini(user_id: str = "default_user") -> CharacterResponse:
    prompt = make_prompt()
    model = "gemini-2.5-flash"
    temperature = 2.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "gemini", "response_format": "CharacterResponse"},
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=temperature,
            ),
        )
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        return result.parsed
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - pydantic>=2.0.0（データモデルとバリデーション）
  - python-dotenv>=1.0.0（環境変数管理）
  - openai>=1.0.0（OpenAI APIクライアント）
  - google-genai>=1.0.0（Google Gemini APIクライアント）
  - click>=8.0.0（CLIインターフェース）

**開発用依存関係**:
  - pytest>=8.4.2（テストフレームワーク）
  - pytest-asyncio>=1.2.0（非同期テストサポート）
  - pytest-mock>=3.15.1（モックユーティリティ）

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxx"
export GEMINI_API_KEY="AIzaSyXXXXXXXXXXXXXXXXXXXX"
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .

# 開発用依存関係も含める場合
uv sync --group dev
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用（デフォルト）
uv run python -m src.main

# OpenAI APIを使用
uv run python -m src.main --llm-provider openai

# 短縮オプション
uv run python -m src.main -lp openai

# ユーザーIDを指定
uv run python -m src.main --user-id user123
uv run python -m src.main -u user123
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -od ./my_characters
```

#### すべてのオプションを組み合わせる

```bash
uv run python -m src.main -lp gemini -od ./outputs -u alice
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5|GPT_5_MINI|GPT_5_NANO|GPT_4_1|GPT_4_1_MINI|GPT_4_1_NANO|GPT_4O|GPT_4O_MINI|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -u, --user-id TEXT              User ID for logging purposes.
  -st, --storage-type [LOCAL]     The storage type for prompt logging.
  --help                          Show this message and exit.
```

### 出力例

#### 1. キャラクター生成結果（outputs/）

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/gemini_a1b2c3d4e5f6.json`

```json
{
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 28,
    "personalities": [
        {
            "short_personality": "内向的な思索家",
            "description": "常に深く物事を考え、静かな場所を好む。表面的な会話よりも、哲学的な議論に心を開く。"
        },
        {
            "short_personality": "完璧主義者",
            "description": "すべてのタスクに最高の基準を求め、細部にこだわる。しばしば自分自身に対して厳しすぎることがある。"
        },
        {
            "short_personality": "忠実な友人",
            "description": "一度信頼関係を築くと、どんな困難な状況でも友人を支える。約束を何よりも大切にする。"
        }
    ]
}
```

#### 2. 構造化ログ（stdout）

LLM操作のメタデータがJSON形式でstdoutに出力されます：

```json
{
  "timestamp": "2025-10-17T10:30:45.123456+00:00",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "prompt_id": "p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890",
  "user_id": "user123",
  "model": "gpt-4o-mini",
  "temperature": 1.0,
  "latency_ms": 1234.56,
  "status_code": 200,
  "level": "INFO",
  "metadata": {
    "provider": "openai",
    "response_format": "CharacterResponse"
  }
}
```

**フィールドの説明**:
- `timestamp`: ログエントリの作成時刻（ISO 8601形式）
- `request_id`: リクエストのユニークID（トレーシング用）
- `prompt_id`: 保存されたプロンプトへの参照ID
- `user_id`: ユーザー識別子（監査・分析用）
- `model`: 使用したLLMモデル名
- `temperature`: 生成パラメータ
- `latency_ms`: リクエストからレスポンスまでの時間（ミリ秒）
- `status_code`: APIステータスコード（200: 成功、500: エラー）
- `level`: ログレベル（INFO、ERROR、WARNING、DEBUG）
- `metadata`: カスタム追加情報

#### 3. 保存されたプロンプト（prompt_storage/）

プロンプトとレスポンスの完全な内容が日付別に保存されます：

**ファイル名**: `prompt_storage/2025/10/17/p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890.json`

```json
{
  "prompt_id": "p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890",
  "prompt_content": [
    {
      "role": "system",
      "content": "あなたは創造的なキャラクタージェネレーターです。\nあなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。\n..."
    },
    {
      "role": "user",
      "content": "ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。"
    }
  ],
  "response_content": {
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 28,
    "personalities": [...]
  },
  "created_at": "2025-10-17T10:30:45.123456",
  "metadata": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

#### 4. 実行ログ例

コンソールには以下のようなログが出力されます：

```
[2025-10-17 10:30:45] [INFO] [__main__] [main.py:107] [main] LLM provider: gemini
Output directory: outputs
User ID: user123
[2025-10-17 10:30:47] [INFO] [llmops] {"timestamp":"2025-10-17T10:30:47.789012+00:00","request_id":"a1b2c3d4-...","prompt_id":"p1q2r3s4-...","user_id":"user123","model":"gemini-2.5-flash","temperature":2.0,"latency_ms":1234.56,"status_code":200,"level":"INFO","metadata":{"provider":"gemini","response_format":"CharacterResponse"}}
[2025-10-17 10:30:47] [INFO] [__main__] [main.py:123] [main] File saved to outputs/gemini_a1b2c3d4e5f6.json
```

### テスト方法

#### ユニットテストの実行

```bash
# すべてのテストを実行
uv run pytest

# 詳細な出力で実行
uv run pytest -v

# 特定のテストファイルのみ実行
uv run pytest tests/test_llmops_logger.py

# 特定のテスト関数のみ実行
uv run pytest tests/test_llmops_log.py::test_llmops_log_entry_creation -v

# カバレッジレポート付きで実行（pytest-covが必要）
uv run pytest --cov=src --cov-report=html

# 静かなモード（簡潔な出力）
uv run pytest -q
```

**テスト実行後の確認**:
```bash
# 作業ディレクトリがクリーンであることを確認
ls -la | grep -E "prompt_storage|test_"
# 期待される結果: テスト関連のディレクトリが存在しない（.pytest_cacheのみ）

# テストを複数回実行してもディレクトリが作成されないことを確認
uv run pytest -q && uv run pytest -q && ls -la
```

#### テストの構成

**全テスト共通の設計原則**:
- すべてのテストは`tempfile.mkdtemp()`を使用して一時ディレクトリを作成
- 作業ディレクトリを汚染せず、テスト後は自動的にクリーンアップ
- 111個のテストがすべて独立して実行可能
- 並列実行にも対応した安全な設計

**1. ログエントリのテスト** (`tests/test_llmops_log.py`) - 37テスト
- モデルのバリデーション（temperature範囲、必須フィールド）
- JSONシリアライゼーション
- タイムスタンプ生成
- フィールド除外（exclude_none）
- 日本語などの特殊文字対応

**2. プロンプトストレージのテスト** (`tests/test_prompt_storage.py`) - 39テスト
- 日付パーティショニングロジック
- 機密データのマスキング（SSN、メール、クレジットカード）
- 再帰的マスキング（ネスト構造）
- ファイルI/O操作（すべて一時ディレクトリ内）
- 非同期保存/取得操作
- ストレージファクトリーパターン

**3. LLMOpsLoggerのテスト** (`tests/test_llmops_logger.py`) - 35テスト
- コンテキストマネージャーのタイミング精度
- エラーハンドリングとステータスコード
- request_id/prompt_idの自動生成
- 非同期ストレージタスクの作成
- ログレベルルーティング（INFO、DEBUG、ERROR、WARNING）
- エンドツーエンド統合テスト
- 並行実行テスト

**テストインフラストラクチャの特徴**:

すべてのテストは`tempfile.mkdtemp()`を使用してOS管理の一時ディレクトリを作成します。これにより：

✅ **安全性**: 作業ディレクトリやユーザーデータを誤って削除するリスクがゼロ
✅ **隔離性**: 各テストが独自の一時ディレクトリを使用し、相互干渉なし
✅ **クリーンアップ**: テスト終了時に`try/finally`パターンで確実に一時ディレクトリを削除
✅ **再現性**: 複数回実行しても作業ディレクトリが汚染されない
✅ **CI/CD対応**: 並列実行でも安全に動作

**実装例**:
```python
def test_example(self):
    """テスト用の一時ディレクトリを使用する例"""
    temp_dir = tempfile.mkdtemp(prefix="test_specific_name_")
    try:
        # テストコード: temp_dirを使用
        storage = LocalFilePromptStorage(base_dir=temp_dir)
        # ... テストロジック ...
    finally:
        # クリーンアップ: 一時ディレクトリを削除
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
```

#### 手動テスト

##### 1. OpenAI APIのテスト

```bash
uv run python -m src.main -lp openai -od test_outputs -u test_user
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `openai_XXXXXXXX.json`形式のファイルが生成される
- 構造化ログがJSON形式でコンソールに出力される
- `prompt_storage/YYYY/MM/DD/`にプロンプトファイルが保存される

##### 2. Gemini APIのテスト

```bash
uv run python -m src.main -lp gemini -od test_outputs -u test_user
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `gemini_XXXXXXXX.json`形式のファイルが生成される
- 構造化ログがJSON形式でコンソールに出力される
- `prompt_storage/YYYY/MM/DD/`にプロンプトファイルが保存される

##### 3. ログ出力の確認

生成された構造化ログを確認：

```bash
# jqを使用してJSONを整形表示
uv run python -m src.main | grep -o '{.*}' | jq .

# 特定のフィールドを抽出
uv run python -m src.main | grep -o '{.*}' | jq '.latency_ms'
```

##### 4. プロンプトストレージの確認

保存されたプロンプトファイルを確認：

```bash
# 最新のプロンプトファイルを表示
find prompt_storage -name "*.json" -type f -exec ls -t {} + | head -1 | xargs cat | jq .

# 特定の日付のプロンプト数を確認
ls -la prompt_storage/2025/10/17/

# プロンプト内容の検証
cat prompt_storage/2025/10/17/[prompt_id].json | jq .
```

##### 5. PIIマスキングの検証

機密情報がマスキングされているか確認：

```python
# テスト用のPythonスクリプト
from src.model.prompt_data import PromptData

# テストデータ
test_prompt = {
    "prompt_id": "test",
    "prompt_content": "Contact me at john@example.com or 123-45-6789 or 4111-1111-1111-1111",
    "response_content": None
}

prompt_data = PromptData(**test_prompt)
prompt_data.mask_sensitive_data()

print(prompt_data.prompt_content)
# 期待される出力: "Contact me at ***@***.*** or ***-**-**** or ****-****-****-****"
```

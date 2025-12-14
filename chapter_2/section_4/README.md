# Chapter 2 Section 4: LLMOpsのための構造化ログ

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

- **マルチプロバイダー対応**: OpenAI GPT-4o-mini、Google Gemini 2.5 Flash、Anthropic Claude Sonnet 4.5をサポート
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
async def request_openai(
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    prompt = make_openai_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "openai", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await openai_client.responses.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
        )
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        return result.parsed
```

**Gemini実装**:
```python
async def request_gemini(
    model: GeminiModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    system_prompt, user_prompt = make_gemini_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=[system_prompt, user_prompt],
        user_id=user_id,
        metadata={"provider": "gemini", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=user_prompt,
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=CharacterResponse,
            ),
        )
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        await google_genai_client.aio.aclose()
        return result.parsed
```

**Anthropic実装**:
```python
async def request_anthropic(
    model: AnthropicModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    prompt = make_anthropic_prompt()

    async with llmops_logger.track_llm_request(
        model=model,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "gemini", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await anthropic_client.beta.messages.parse(
            model=model,
            max_tokens=1024,
            betas=["structured-outputs-2025-11-13"],
            messages=prompt,
            output_format=CharacterResponse,
        )
        tracking["response"] = result.parsed_output.model_dump() if result.parsed_output else None
        return result.parsed_output
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - pydantic>=2.0.0（データモデルとバリデーション）
  - python-dotenv>=1.0.0（環境変数管理）
  - openai>=1.0.0（OpenAI APIクライアント）
  - google-genai>=1.0.0（Google Gemini APIクライアント）
  - anthropic>=0.40.0（Anthropic Claude APIクライアント）
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
export ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxxxxxxxxx"
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# 開発用依存関係も含める場合
uv sync --group dev
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# OpenAI APIを使用
uv run python -m src.main --llm-provider OPENAI --model GPT_5_MINI --user-id user123 --output-directory ./custom_output

# Gemini APIを使用 
uv run python -m src.main --llm-provider GEMINI --model GEMINI_2_5_FLASH --user-id user123 --output-directory ./custom_output

# Anthropic APIを使用
uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_SONNET_4_5 --user-id user123 --output-directory ./custom_output
```

#### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5|GPT_5_MINI|GPT_5_NANO|GPT_4_1|GPT_4_1_MINI|GPT_4_1_NANO|GPT_4O|GPT_4O_MINI|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_4_5|CLAUDE_OPUS_4_1]
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

**ファイル名**: `outputs/anthropic_a1b2c3d4e5f6.json` または `outputs/openai_a1b2c3d4e5f6.json` または `outputs/gemini_a1b2c3d4e5f6.json`

```json
{
    "first_name": "Cassandra",
    "last_name": "Thornfield",
    "gender": "female",
    "age": 34,
    "personalities": [
        {
            "short_personality": "Analytical perfectionist",
            "description": "Cassandra possesses an incredibly sharp mind and approaches every problem with methodical precision. She cannot tolerate incomplete data or sloppy work, often spending hours refining details that others might overlook. This trait makes her exceptional at her work as a forensic archaeologist, but it also causes friction in personal relationships where emotional nuance matters more than factual accuracy."
        },
        {
            "short_personality": "Guarded optimist",
            "description": "Despite experiencing betrayal early in her career that nearly destroyed her reputation, Cassandra maintains a cautious hope about human nature. She believes in the potential for good in people but keeps emotional walls firmly in place, revealing her warmer side only to those who earn her trust through consistent actions over time. This duality makes her seem cold at first but deeply loyal once bonds are formed."
        },
        {
            "short_personality": "Compulsively curious",
            "description": "Cassandra is driven by an insatiable need to understand the 'why' behind everything she encounters. Whether it's an ancient artifact or a colleague's unusual behavior, she cannot rest until she has uncovered the underlying truth. This curiosity has led to groundbreaking discoveries in her field but has also gotten her into dangerous situations when her questions threaten powerful interests."
        }
    ]
}
```

#### 2. 構造化ログ（stdout）

LLM操作のメタデータがJSON形式でstdoutに出力されます：

```json
{"timestamp": "2025-11-17T05:48:24.147777+00:00", "request_id": "6081711d-b000-45cf-91cc-6bd3dd6853f1", "prompt_id": "0c18299b-06bc-4f56-b7f1-1981b2024675", "user_id": "user_0", "model": "claude-sonnet-4-5", "latency_ms": 9511.006116867065, "status_code": 200, "level": "INFO", "metadata": {"provider": "anthropic", "model": "claude-sonnet-4-5", "response_format": "CharacterResponse"}}
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
  "prompt_id": "0c18299b-06bc-4f56-b7f1-1981b2024675",
  "prompt_content": [
    {
      "role": "system",
      "content": "あなたは創造的なキャラクタージェネレーターです。"
    },
    {
      "role": "user",
      "content": "あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。\n以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：\n\n{\n  \"first_name\": \"string; The first name of the character.\",\n  \"last_name\": \"string; The last name of the character.\",\n  \"gender\": \"enum; The gender of the character.; ['female', 'male']\",\n  \"age\": \"number; The age of the character.; 0-100\",\n  \"personalities\": [\n    {\n      \"short_personality\": \"string; The three most important personality traits of the character. (personality 1)\",\n      \"description\": \"string; The three most important personality traits of the character. (detailed description for personality 1)\"\n    },\n    {\n      \"short_personality\": \"string; The three most important personality traits of the character. (personality 2)\",\n      \"description\": \"string; The three most important personality traits of the character. (detailed description for personality 2)\"\n    },\n    {\n      \"short_personality\": \"string; The three most important personality traits of the character. (personality 3)\",\n      \"description\": \"string; The three most important personality traits of the character. (detailed description for personality 3)\"\n    }\n  ]\n}\n\n以下を確認してください：\n1. 応答は有効なJSONであること\n2. すべてのフィールドが含まれていること\n3. 性別は「female」または「male」のいずれかであること\n4. 年齢は0から100の間であること\n5. 正確に3つの性格特性が提供されていること\n6. JSON構造の外に説明や追加のテキストを含めないこと\n\nユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。\n"
    }
  ],
  "response_content": {
    "first_name": "Cassandra",
    "last_name": "Thornfield",
    "gender": "female",
    "age": 34,
    "personalities": [
      {
        "short_personality": "Analytical perfectionist",
        "description": "Cassandra possesses an incredibly sharp mind and approaches every problem with methodical precision. She cannot tolerate incomplete data or sloppy work, often spending hours refining details that others might overlook. This trait makes her exceptional at her work as a forensic archaeologist, but it also causes friction in personal relationships where emotional nuance matters more than factual accuracy."
      },
      {
        "short_personality": "Guarded optimist",
        "description": "Despite experiencing betrayal early in her career that nearly destroyed her reputation, Cassandra maintains a cautious hope about human nature. She believes in the potential for good in people but keeps emotional walls firmly in place, revealing her warmer side only to those who earn her trust through consistent actions over time. This duality makes her seem cold at first but deeply loyal once bonds are formed."
      },
      {
        "short_personality": "Compulsively curious",
        "description": "Cassandra is driven by an insatiable need to understand the 'why' behind everything she encounters. Whether it's an ancient artifact or a colleague's unusual behavior, she cannot rest until she has uncovered the underlying truth. This curiosity has led to groundbreaking discoveries in her field but has also gotten her into dangerous situations when her questions threaten powerful interests."
      }
    ]
  },
  "created_at": "2025-11-17T05:48:24.147808",
  "metadata": {
    "request_id": "6081711d-b000-45cf-91cc-6bd3dd6853f1",
    "provider": "anthropic",
    "model": "claude-sonnet-4-5",
    "response_format": "CharacterResponse"
  }
}
```

#### 4. 実行ログ例

コンソールには以下のようなログが出力されます：

```
$ python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_5 -od outputs -u user_0 -st LOCAL
[2025-11-17 14:48:14,636] [INFO] [__main__] [main.py:71] [main] LLM provider: anthropic
Model: claude-sonnet-4-5
Output directory: outputs
User ID: user_0
Storage type: local
Prompt stored successfully at: prompt_storage/2025/11/17/0c18299b-06bc-4f56-b7f1-1981b2024675.json
{"timestamp": "2025-11-17T05:48:24.147777+00:00", "request_id": "6081711d-b000-45cf-91cc-6bd3dd6853f1", "prompt_id": "0c18299b-06bc-4f56-b7f1-1981b2024675", "user_id": "user_0", "model": "claude-sonnet-4-5", "latency_ms": 9511.006116867065, "status_code": 200, "level": "INFO", "metadata": {"provider": "gemini", "model": "claude-sonnet-4-5", "response_format": "CharacterResponse"}}
[2025-11-17 14:48:24,148] [INFO] [__main__] [main.py:99] [main] File saved to outputs/anthropic_282cd205f6f74a3abc9c97c7944f4aba.json
```

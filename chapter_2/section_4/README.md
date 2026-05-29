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

- **マルチプロバイダー対応**: OpenAI GPT-5.4-mini、Google Gemini 2.5 Flash、Anthropic Claude Sonnet 4.5をサポート
- **構造化出力**: Pydanticモデルによる型安全なLLM応答
- **非同期処理**: async/awaitによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリによる使いやすいコマンドラインツール

## プロジェクト構成

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
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用する
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# OpenAI APIを使用
uv run python -m src.main --llm-provider OPENAI --model GPT_5_MINI --user-id user123 --output-directory ./outputs

# Gemini APIを使用 
uv run python -m src.main --llm-provider GEMINI --model GEMINI_2_5_FLASH --user-id user123 --output-directory ./outputs

# Anthropic APIを使用
uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_SONNET_4_6 --user-id user123 --output-directory ./outputs
```

#### ヘルプの表示

```bash
$ uv run python -m src.main --help                                             
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_5|GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_OPUS_4_7|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
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
{"timestamp": "2025-11-17T05:48:24.147777+00:00", "request_id": "6081711d-b000-45cf-91cc-6bd3dd6853f1", "prompt_id": "0c18299b-06bc-4f56-b7f1-1981b2024675", "user_id": "user_0", "model": "claude-sonnet-4-6", "latency_ms": 9511.006116867065, "status_code": 200, "level": "INFO", "metadata": {"provider": "anthropic", "model": "claude-sonnet-4-6", "response_format": "CharacterResponse"}}
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
    "model": "claude-sonnet-4-6",
    "response_format": "CharacterResponse"
  }
}
```

#### 4. 実行ログ例

コンソールには以下のようなログが出力されます：

```
$ uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_SONNET_4_6 --user-id user123 --output-directory ./outputs

[2026-01-17 16:25:32,886] [INFO] [__main__] [main.py:70] [main] LLM provider: anthropic
Model: claude-sonnet-4-6
Output directory: ./outputs
User ID: user123
Storage type: local
Prompt stored successfully at: prompt_storage/2026/01/17/a5f48ef0-e54f-4653-8a3e-2543b5b70878.json
{"timestamp": "2026-01-17T07:25:41.607821+00:00", "request_id": "9a5b4376-21bd-4ccd-bffa-c976e91b0aa9", "prompt_id": "a5f48ef0-e54f-4653-8a3e-2543b5b70878", "user_id": "user123", "model": "claude-sonnet-4-6", "latency_ms": 8721.174955368042, "status_code": 200, "level": "INFO", "metadata": {"provider": "gemini", "model": "claude-sonnet-4-6", "response_format": "CharacterResponse"}}
[2026-01-17 16:25:41,609] [INFO] [__main__] [main.py:98] [main] File saved to ./outputs/anthropic_54cfc5f31cac41a5b1e8a25f7655eec0.json
```

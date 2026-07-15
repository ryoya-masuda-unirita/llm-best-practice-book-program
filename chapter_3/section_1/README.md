# Chapter 3 Section 1: LLM APIのためのAdaptorとFactoryパターン

## 概要

このプロジェクトは、**AdapterパターンとFactoryパターン**を用いた複数LLMプロバイダの統一的な管理手法を示すサンプルコードです。OpenAI、Anthropic Claude、Google Geminiの3つのプロバイダに対応し、各プロバイダのAPI仕様の違いを吸収しながら、共通のインターフェースを通じて柔軟にLLMを切り替えられる設計を実現しています。

フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、ベンダーロックインを回避し、保守性と拡張性を両立させるプラクティスを学ぶことができます。

## 機能

- **Adapterパターン**: 各LLMプロバイダの差異を吸収する統一インターフェース
- **Factoryパターン**: プロバイダとモデルに基づいたクライアント生成の一元管理
- **マルチプロバイダー対応**: OpenAI、Anthropic Claude、Google Gemini APIの3つをサポート
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **プロバイダー切り替え**: コマンドライン引数で簡単にプロバイダー/モデルを変更可能
- **構造化出力**: 各プロバイダの最新構造化出力APIを活用した型安全なLLM応答
- **包括的なテスト**: 包括的なユニットテストによる品質保証
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **リソース管理**: 各アダプターに`aclose()`メソッドを実装し適切なクリーンアップを実現
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化

## プロジェクト構成

### アーキテクチャ

このプロジェクトは、以下の4層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────┐
│         CLI Layer (main.py)                 │
│     - コマンドライン引数解析                │
│     - 出力ディレクトリ管理                  │
│     - プロバイダー/モデル検証               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Service Layer (service/)               │
│  - 統一されたLLMリクエスト処理              │
│  - プロンプト生成とレスポンス処理           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Adapter/Factory Layer (client/)        │
│  - LLMClient抽象インターフェース (base.py)  │
│  - プロバイダー別Adapter (adapters.py)      │
│  - クライアント生成Factory (factory.py)    │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Infrastructure Layer                   │
│  - 設定管理 (config.py)                     │
│  - ログ管理 (logger.py)                     │
│  - データモデル (model/)                    │
│  - 外部API (OpenAI, Gemini)                 │
└─────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - anthropic>=0.42.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
- **開発依存関係**:
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
# OpenAI GPT-5.4を使用
uv run python -m src.main --llm-provider OPENAI --model GPT_5_4

# 短縮オプション
uv run python -m src.main -lp OPENAI -m GPT_5_4

# Anthropic Claude Sonnet 4.5を使用
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6

# Gemini 2.5 Proを使用
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_PRO

# Gemini 2.5 Flash
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp OPENAI -m GPT_5_4 --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_PRO -od ./my_characters
```

#### プロバイダーとモデルの組み合わせ例

```bash
# OpenAI の各モデル
uv run python -m src.main -lp OPENAI -m GPT_5_4
uv run python -m src.main -lp OPENAI -m GPT_5
uv run python -m src.main -lp OPENAI -m GPT_5_MINI

# Anthropic の各モデル
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_OPUS_4_7

# Gemini の各モデル
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_PRO
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH_LITE
```

#### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use (openai, anthropic,
                                  or gemini).  [required]
  -m, --model [GPT_5_5|GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|
               GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|
               GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_5|CLAUDE_OPUS_4_8|CLAUDE_OPUS_4_7|CLAUDE_HAIKU_4_5|
               CLAUDE_SONNET_4_6]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/openai_gpt-5.4_a1b2c3d4.json`

```json
{
    "first_name": "エリカ",
    "last_name": "サトウ",
    "gender": "female",
    "age": 28,
    "personalities": [
        {
            "short_personality": "思慮深い",
            "description": "エリカは物事を深く考え、衝動的に行動することはめったにありません。常に状況を分析し、潜在的な結果を考慮してから結論を導き出します。"
        },
        {
            "short_personality": "共感的",
            "description": "他人の感情や視点に非常に敏感で、困っている人には自然と手を差し伸べます。彼女の共感力は、友人や同僚から信頼される理由の一つです。"
        },
        {
            "short_personality": "探求心旺盛",
            "description": "未知のものや新しい知識への強い好奇心を持っています。読書、旅行、多様な人々との交流を通じて、常に世界をより深く理解しようと努めています。"
        }
    ]
}
```

**実行ログ例**:
```bash
$ uv run python -m src.main -lp OPENAI -m GPT_5_4_MINI
[2026-01-18 15:46:30,144] [INFO] [__main__] [main.py:58] [main] LLM provider: openai
Model: gpt-5.4-mini
Output directory: outputs
[2026-01-18 15:46:30,144] [INFO] [src.client.factory] [factory.py:37] [create_client] Creating client: provider=openai, model=gpt-5.4-mini
[2026-01-18 15:46:30,272] [INFO] [src.client.adapters] [adapters.py:24] [__init__] Initialized OpenAI adapter with model: gpt-5.4-mini
[2026-01-18 15:46:30,273] [INFO] [src.service.request_llm] [request_llm.py:17] [request_llm] Making LLM request: provider=openai, model=gpt-5.4-mini
[2026-01-18 15:46:30,273] [DEBUG] [src.client.adapters] [adapters.py:32] [chat] OpenAI request: model=gpt-5.4-mini
[2026-01-18 15:46:36,320] [INFO] [src.service.request_llm] [request_llm.py:27] [request_llm] Successfully received response from openai
[2026-01-18 15:46:36,320] [INFO] [__main__] [main.py:77] [main] Character generated successfully!
[2026-01-18 15:46:36,320] [INFO] [__main__] [main.py:78] [main] File saved to: outputs/openai_gpt-5.4-mini_cb3b09ee.json
[2026-01-18 15:46:36,320] [INFO] [__main__] [main.py:79] [main] Character: Luna Calder, 28 years old
[2026-01-18 15:46:36,321] [DEBUG] [src.client.adapters] [adapters.py:49] [aclose] Closed OpenAI client
```

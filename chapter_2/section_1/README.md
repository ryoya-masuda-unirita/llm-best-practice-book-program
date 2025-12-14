# Chapter 2 Section 1: LLMの出力を構造化する

## 概要

このプロジェクトは、**構造化出力（Structured Outputs）** を用いたLLM（大規模言語モデル）の基本実装を示すサンプルコードです。OpenAI、Google Gemini、Anthropic Claudeの3つのLLMプロバイダーに対応し、Pydanticモデルを活用して型安全なLLM応答を実現します。

フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、構造化出力の実践的な実装方法を学ぶことができます。各プロバイダー固有のStructured Outputs APIを活用し、LLMからの応答を確実にPydanticモデルにパースします。

## 機能

- **構造化出力**: PydanticモデルをAPI応答形式として直接利用し、型安全なLLM出力を実現
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic Claude APIの3プロバイダーをサポート
- **複数モデル選択**: 各プロバイダーで複数のモデルから選択可能（全17モデル対応）
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果をJSON形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_1/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント（CLI）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化・モデル定義
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── request_llm.py       # LLMリクエスト処理（サービス層）
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────┐
│              CLI Layer (main.py)                    │
│         - コマンドライン引数解析                     │
│         - プロバイダー・モデル選択                   │
│         - 出力ディレクトリ管理                       │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│           Service Layer (service/)                  │
│    - request_llm.py: LLMリクエスト処理              │
│    - 各プロバイダー固有のAPI呼び出しロジック          │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│          Business Logic Layer                       │
│    - prompt/prompt.py: プロンプト生成               │
│    - client/llm_client.py: クライアント管理          │
│    - model/model.py: データモデル定義                │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│          Infrastructure Layer                       │
│    - config.py: 設定管理                            │
│    - logger.py: ログ管理                            │
│    - 外部API (OpenAI, Gemini, Anthropic)            │
└─────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.73.0
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Geminiで実行（モデルを指定）
uv run python -m src.main --llm-provider gemini --model gemini-2.5-flash

# OpenAIで実行
uv run python -m src.main --llm-provider openai --model gpt-4o-mini

# Anthropicで実行
uv run python -m src.main --llm-provider anthropic --model claude-sonnet-4-5

# 短縮オプションで実行
uv run python -m src.main -lp openai -m gpt-4o
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp gemini -m gemini-2.5-flash --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -lp gemini -m gemini-2.5-flash -od ./my_characters
```

#### 利用可能なモデル

| プロバイダー | モデル |
|-------------|--------|
| OpenAI | gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-4o, gpt-4o-mini |
| Gemini | gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite |
| Anthropic | claude-opus-4-5, claude-haiku-4-5, claude-sonnet-4-5, claude-opus-4-1 |

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [openai|gemini|anthropic]
                                  The LLM provider to use.  [required]
  -m, --model [gpt-5.2|gpt-5.1|gpt-5|gpt-5-mini|gpt-5-nano|gpt-4.1|gpt-4.1-mini|gpt-4.1-nano|gpt-4o|gpt-4o-mini|gemini-2.5-pro|gemini-2.5-flash|gemini-2.5-flash-lite|claude-opus-4-5|claude-haiku-4-5|claude-sonnet-4-5|claude-opus-4-1]
                                  The model to use for the request.  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/gemini_27ea9c6863a640fdb60d60d2d34f6991.json`

```json
{
    "first_name": "エララ",
    "last_name": "ヴァンス",
    "gender": "female",
    "age": 28,
    "personalities": [
        {
            "short_personality": "観察力",
            "description": "エララはめったに細部を見逃しません。彼女はしばしば状況や人々を黙って分析し、静かでありながら非常に知覚力があるように見えます。"
        },
        {
            "short_personality": "忠誠心",
            "description": "彼女は大切に思う人々に対して非常に献身的で、彼らを守り、約束を守るためにはあらゆる努力をします。裏切りは彼女にとって許せないものです。"
        },
        {
            "short_personality": "回復力",
            "description": "挫折や課題から立ち直る揺るぎない内なる強さを持っています。彼女は逆境に真正面から立ち向かい、しばしば革新的な解決策を見つけます。"
        }
    ]
}
```

**実行ログ例**:
```
[2025-11-17 10:30:45] [INFO] [src.main] [main.py:53] [main] LLM provider: gemini
Model: gemini-2.5-flash
Output directory: outputs
[2025-11-17 10:30:47] [INFO] [src.main] [main.py:78] [main] File saved to outputs/gemini_27ea9c6863a640fdb60d60d2d34f6991.json
```

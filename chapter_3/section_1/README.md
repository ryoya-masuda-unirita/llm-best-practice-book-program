# Chapter 3 Section 1: LLM APIのためのアダプターとファクトリーパターン

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

### ディレクトリ構成

```
chapter_2/section_11/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/                  # LLMクライアント関連
│   │   ├── __init__.py
│   │   ├── base.py              # 抽象基底クラス（LLMClient）
│   │   ├── adapters.py          # 具体的なAdapter実装（OpenAI, Anthropic, Gemini）
│   │   ├── factory.py           # Factoryパターン実装
│   │   └── model.py             # プロバイダー・モデル定義
│   ├── model/                   # データモデル
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/                  # プロンプト管理
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/                 # サービス層
│       ├── __init__.py
│       └── request_llm.py       # 統一されたLLMリクエスト処理
├── tests/                       # テストコード
│   ├── __init__.py
│   ├── test_adapters.py         # Adapterのテスト
│   └── test_factory.py          # Factoryのテスト
├── outputs/                     # 生成結果の保存先（自動作成）
├── .envrc.example               # 環境変数設定のサンプル
├── Makefile                     # 開発用タスク定義
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
└── CLAUDE.md                    # 設計ドキュメント
```

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
# OpenAI GPT-4oを使用
uv run python -m src.main --llm-provider openai --model gpt-4o

# 短縮オプション
uv run python -m src.main -lp openai -m gpt-4o

# Anthropic Claude Sonnet 4.5を使用
uv run python -m src.main -lp anthropic -m claude-sonnet-4-5

# Gemini 2.5 Proを使用
uv run python -m src.main -lp gemini -m gemini-2.5-pro

# Gemini 2.5 Flash（デフォルト）
uv run python -m src.main -lp gemini -m gemini-2.5-flash
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp openai -m gpt-4o --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -lp gemini -m gemini-2.5-pro -od ./my_characters
```

#### プロバイダーとモデルの組み合わせ例

```bash
# OpenAI の各モデル
uv run python -m src.main -lp openai -m gpt-5
uv run python -m src.main -lp openai -m gpt-4o
uv run python -m src.main -lp openai -m gpt-4o-mini

# Anthropic の各モデル
uv run python -m src.main -lp anthropic -m claude-sonnet-4-5
uv run python -m src.main -lp anthropic -m claude-opus-4-1

# Gemini の各モデル
uv run python -m src.main -lp gemini -m gemini-2.5-pro
uv run python -m src.main -lp gemini -m gemini-2.5-flash
uv run python -m src.main -lp gemini -m gemini-2.5-flash-lite
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [openai|anthropic|gemini]
                                  The LLM provider to use (openai, anthropic, or gemini).
  -m, --model [gpt-5|gpt-4o|claude-sonnet-4-5|gemini-2.5-pro|...]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/openai_gpt-4o_a1b2c3d4.json`

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

**実行ログ例**:
```
[2025-10-19 10:30:45] [INFO] [__main__] [main.py:76] [main] LLM provider: openai
Model: gpt-4o
Output directory: outputs
[2025-10-19 10:30:46] [INFO] [src.service.request_llm] [request_llm.py:41] [request_llm] Making LLM request: provider=openai, model=gpt-4o
[2025-10-19 10:30:48] [INFO] [src.service.request_llm] [request_llm.py:52] [request_llm] Successfully received response from openai
[2025-10-19 10:30:48] [INFO] [__main__] [main.py:102] [main] Character generated successfully!
[2025-10-19 10:30:48] [INFO] [__main__] [main.py:103] [main] File saved to: outputs/openai_gpt-4o_a1b2c3d4.json
[2025-10-19 10:30:48] [INFO] [__main__] [main.py:104] [main] Character: 蒼 雨宮, 28 years old
```

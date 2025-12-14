# Chapter 2 Section 8: LLMでLLMを評価する（LLM-as-a-Judge）

## 概要

このプロジェクトは、**LLM-as-a-Judge**（LLMを審査員として活用する設計手法）の実装を示すサンプルコードです。LLMが生成したコンテンツを別のLLMが自動的に評価することで、品質管理の自動化と効率化を実現します。

OpenAI、Google Gemini、Anthropic Claudeの3つのプロバイダーに対応し、**クロスプロバイダー評価**（異なるプロバイダーで生成と評価を行う）もサポートしています。キャラクター生成という具体的なユースケースを通じて、LLM-as-a-Judgeの実践的な実装方法を学ぶことができます。

## 機能

### 基本機能
- **自動品質評価**: 生成されたすべてのキャラクターを自動的に評価
- **構造化評価結果**: JSON形式で詳細な評価結果を出力
- **3つの評価軸**: 正確性（accuracy）、網羅性（comprehensiveness）、明瞭さ（clarity）
- **スコアリング**: 1-5点の5段階評価と総合スコア算出
- **品質閾値チェック**: 設定した閾値（デフォルト3.0/5.0）を下回る場合に警告

### 高度な機能
- **クロスプロバイダー評価**: 異なるLLMプロバイダーで生成と評価を実行
- **リクエストパラメータ評価**: 生成されたキャラクターが元のリクエスト要件（性別、年齢、追加指示）を満たしているかを自動検証
- **カスタム評価基準**: プログラマティックAPIでドメイン固有の評価基準を定義可能
- **温度パラメータ制御**: 評価の一貫性を高めるため低温度（0.0）で実行
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic Claude APIの3つをサポート
- **プロバイダー別プロンプト**: 各LLMプロバイダーの特性に最適化されたプロンプト形式を自動選択
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し

### システム機能
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果と評価結果をそれぞれJSON形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_7/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── config.py                      # 設定管理（API キー読み込み）
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # メインエントリーポイント（CLIとLLM-as-a-Judge統合）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                   # キャラクターデータモデル定義
│   │   └── llm_as_a_judge_model.py    # LLM-as-a-Judge評価モデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── prompt.py                  # キャラクター生成プロンプト
│   │   └── llm_as_a_judge_prompt.py   # LLM-as-a-Judge評価プロンプト
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py             # LLMリクエスト処理（統合ワークフロー）
│       └── llm_as_a_judge.py          # LLM-as-a-Judge評価サービス
├── outputs/                            # 生成結果と評価結果の保存先（自動作成）
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── README.md                           # このファイル
└── CLAUDE.md                           # コンセプト説明（日本語）
```

### アーキテクチャ

このプロジェクトは、以下の多層アーキテクチャで構成されています：

```
┌────────────────────────────────────────────────┐
│         CLI Layer (main.py)                    │
│  - コマンドライン引数解析                       │
│  - 生成と評価の統合ワークフロー                 │
│  - 出力ディレクトリ管理                         │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│      Business Logic Layer                      │
│  ┌──────────────────────────────────────────┐  │
│  │  生成サービス (request_llm.py)           │  │
│  │  - request_openai()                      │  │
│  │  - request_gemini()                      │  │
│  │  - request_with_judge() ★統合機能       │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  評価サービス (llm_as_a_judge.py)        │  │
│  │  - judge_with_openai()                   │  │
│  │  - judge_with_gemini()                   │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  プロンプト生成                           │  │
│  │  - make_prompt() (キャラクター生成)      │  │
│  │  - make_judge_prompt() (評価)            │  │
│  │  - make_custom_judge_prompt() (カスタム) │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  データモデル                             │  │
│  │  - CharacterRequest/Response             │  │
│  │  - JudgeRequest/Response                 │  │
│  │  - EvaluationCriterion                   │  │
│  └──────────────────────────────────────────┘  │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│      Infrastructure Layer                      │
│  - 設定管理 (config.py)                        │
│  - ログ管理 (logger.py)                        │
│  - LLMクライアント (llm_client.py)             │
│  - 外部API (OpenAI, Gemini)                    │
└────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.42.0
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

#### 基本的な使い方（同じプロバイダーで生成と評価）

```bash
# Geminiで生成し、Geminiで評価
python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH

# OpenAIで生成し、OpenAIで評価
python -m src.main -g FEMALE -a 25 -lp OPENAI -m GPT_4O_MINI

# Anthropicで生成し、Anthropicで評価
python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_SONNET_4_5
```

#### クロスプロバイダー評価（推奨）

異なるプロバイダーで生成と評価を行うことで、より客観的な評価が可能になります：

```bash
# Geminiで生成、OpenAIで評価
python -m src.main \
  -g FEMALE -a 25 \
  -lp GEMINI -m GEMINI_2_5_FLASH \
  -jp OPENAI -jm GPT_4O_MINI

# OpenAIで生成、Anthropicで評価
python -m src.main \
  -g MALE -a 40 \
  -lp OPENAI -m GPT_4O \
  -jp ANTHROPIC -jm CLAUDE_OPUS_4_1

# Anthropicで生成、Geminiで評価
python -m src.main \
  -g FEMALE -a 30 \
  -lp ANTHROPIC -m CLAUDE_SONNET_4_5 \
  -jp GEMINI -jm GEMINI_2_5_PRO
```

#### 追加指示の指定

```bash
python -m src.main \
  -g FEMALE -a 30 \
  -ai "mysterious artist" \
  -lp GEMINI -m GEMINI_2_5_FLASH \
  -jp OPENAI -jm GPT_4O_MINI
```

#### ヘルプの表示

```bash
python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -g, --gender [FEMALE|MALE]           キャラクターの性別 [required]
  -a, --age INTEGER RANGE              キャラクターの年齢 [0<=x<=100; required]
  -ai, --additional-instructions TEXT  追加の生成指示
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                       生成に使用するLLMプロバイダー [required]
  -m, --model [GPT_5|GPT_5_MINI|...|CLAUDE_SONNET_4_5|CLAUDE_OPUS_4_1]
                                       生成に使用するモデル [required]
  -od, --output-directory PATH         出力ディレクトリ
  -jp, --judge-provider [OPENAI|GEMINI|ANTHROPIC]
                                       評価に使用するLLMプロバイダー（省略時は生成と同じ）
  -jm, --judge-model [...]             評価に使用するモデル（省略時は生成と同じ）
  --help                               ヘルプを表示
```

### 出力例

実行すると、2つのJSONファイルが生成されます：

#### 1. キャラクターファイル

**ファイル名**: `outputs/gemini_character_a1b2c3d4e5f6.json`

```json
{
    "first_name": "サラ",
    "last_name": "コンラッド",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "好奇心旺盛",
            "description": "未知の世界や技術に強い興味を持つ探究心の塊"
        },
        {
            "short_personality": "冷静沈着",
            "description": "危機的状況でも論理的に判断できる思考力"
        },
        {
            "short_personality": "正義感が強い",
            "description": "弱者を守り、不正を許さない強い使命感"
        }
    ]
}
```

#### 2. 評価ファイル

**ファイル名**: `outputs/openai_judge_a1b2c3d4e5f6.json`（クロスプロバイダー評価の場合）

```json
{
    "evaluations": [
        {
            "criterion_name": "accuracy",
            "score": 5,
            "reasoning": "キャラクター設定が論理的で矛盾がなく、SF小説の主人公として適切です。"
        },
        {
            "criterion_name": "comprehensiveness",
            "score": 4,
            "reasoning": "基本的な性格特性は十分ですが、背景設定があればより良いでしょう。"
        },
        {
            "criterion_name": "clarity",
            "score": 5,
            "reasoning": "各性格特性が明確に記述されており、理解しやすいです。"
        }
    ],
    "overall_score": 4.67,
    "summary": "全体的に高品質なキャラクター設定です。SF小説の主人公として適切で、個性が明確です。"
}
```

#### 実行ログ例

```
[2025-10-18 14:30:00] [INFO] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: SF小説の主人公として適したキャラクターを生成してください。

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: openai / gpt-4o-mini
Output directory: outputs

[2025-10-18 14:30:01] [INFO] Step 1: Generating character...
[2025-10-18 14:30:03] [INFO] Character generation completed.
[2025-10-18 14:30:03] [INFO] Step 2: Evaluating character with LLM-as-a-Judge...
[2025-10-18 14:30:03] [INFO] Requesting judgment from OpenAI model: gpt-4o-mini
[2025-10-18 14:30:05] [INFO] Judgment completed. Overall score: 4.67/5.0
[2025-10-18 14:30:05] [INFO] Character file saved to outputs/gemini_character_a1b2c3d4e5f6.json
[2025-10-18 14:30:05] [INFO] Judge evaluation saved to outputs/openai_judge_a1b2c3d4e5f6.json
[2025-10-18 14:30:05] [INFO] Overall evaluation score: 4.67/5.0
```

品質閾値を下回った場合の警告例：
```
[2025-10-18 14:30:05] [WARNING] The generated character did not meet the quality threshold (3.0/5.0)
```

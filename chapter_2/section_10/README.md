# Chapter 2 Section 10: プロンプトの単体テスト

## 概要

このプロジェクトは、**プロンプトの単体テスト** の実装を示すサンプルコードです。LLM（大規模言語モデル）に与えるプロンプトの振る舞いを体系的に検証し、品質と安定性を継続的に保証するための設計プラクティスを実践します。

プロンプトの変更がシステム全体の出力に与える影響を自動的に検証する仕組みを導入することで、意図しない品質劣化（リグレッション）を早期に検出し、LLMシステムの信頼性を高めることができます。**LLM-as-a-Judge** パターンを活用し、別のLLMに出力品質を評価させることで、高度な品質検証を実現しています。

キャラクター生成のユースケースを通じて、プロンプトの構造検証、出力品質評価、リグレッション検出といった実践的なテスト手法を学ぶことができます。

## 機能

### コアの機能

- **プロンプトユニットテスト**: pytestベースの体系的なプロンプト品質検証
- **LLM-as-a-Judge**: 別のLLMを用いた自動品質評価システム
- **構造化出力**: PydanticモデルによるAPI応答形式の型安全性保証
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic APIの3つのプロバイダーをサポート
- **品質スコアリング**: 5段階評価による定量的な品質測定

### テスト機能

- **構造検証テスト**: プロンプトが必須フィールドを含むことを確認
- **品質閾値テスト**: 生成結果が最低品質基準を満たすことを保証
- **リグレッション検出テスト**: プロンプト変更による品質劣化を検出
- **代表的入力テスト**: 3-5個の重要なユースケースをカバー
- **カスタム評価基準**: ドメイン固有の要件に対応した評価

### その他の機能

- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリによる柔軟なコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **詳細なログ出力**: 実行状況の可視化
- **JSON出力**: 生成結果と評価結果をJSON形式で保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_8/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── config.py                      # 設定管理（APIキー読み込み）
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                   # キャラクターモデル定義
│   │   └── llm_as_a_judge_model.py    # Judge評価モデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── prompt.py                  # キャラクター生成プロンプト
│   │   └── llm_as_a_judge_prompt.py   # Judge評価プロンプト
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py             # LLMリクエスト処理
│       └── llm_as_a_judge.py          # Judge評価サービス
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # pytestフィクスチャ定義
│   ├── test_prompt_unit_testing.py    # プロンプトユニットテスト
│   └── test_llm_as_a_judge.py         # Judge機能テスト
├── outputs/                            # 生成結果の保存先（自動作成）
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── pytest.ini                          # pytest設定ファイル
├── Makefile                            # 開発用コマンド
├── README.md                           # このファイル
└── CLAUDE.md                           # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャ + テスト層で構成されています：

```
┌─────────────────────────────────────────────────┐
│         CLI Layer (main.py)                     │
│   - コマンドライン引数解析                      │
│   - 生成・評価ワークフロー制御                  │
│   - 出力ディレクトリ管理                        │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Business Logic Layer                       │
│  - プロンプト生成 (prompt.py)                   │
│  - Judge評価プロンプト (llm_as_a_judge_prompt) │
│  - LLMクライアント管理 (llm_client.py)         │
│  - リクエスト処理 (request_llm.py)             │
│  - Judge評価サービス (llm_as_a_judge.py)       │
│  - データモデル (model.py, judge_model.py)     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Infrastructure Layer                       │
│  - 設定管理 (config.py)                         │
│  - ログ管理 (logger.py)                         │
│  - 外部API (OpenAI, Gemini, Anthropic)          │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│      Test Layer (tests/)                        │
│  - プロンプト構造検証テスト                     │
│  - 出力品質テスト                               │
│  - リグレッション検出テスト                     │
│  - 代表的入力テスト                             │
│  - Judge機能テスト                              │
└─────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
- **開発依存ライブラリ**:
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
pip install -e ".[dev]"  # テスト用依存関係も含む
```

### 使用方法、実行方法

#### メインプログラムの実行

キャラクター生成とLLM-as-a-Judge評価を実行します：

##### 基本的な使い方

```bash
# Gemini APIを使用
uv run python -m src.main \
    --llm-provider gemini \
    --model gemini-2.5-flash \
    --gender female \
    --age 25

# OpenAI APIを使用
uv run python -m src.main \
    --llm-provider openai \
    --model gpt-4o-mini \
    --gender male \
    --age 30

# Anthropic APIを使用
uv run python -m src.main \
    --llm-provider anthropic \
    --model claude-sonnet-4-5 \
    --gender female \
    --age 28
```

##### 追加指示を指定

```bash
uv run python -m src.main \
    -lp openai \
    -m gpt-4o-mini \
    -g female \
    -a 25 \
    --additional-instructions "Generate a wizard from a fantasy world."
```

##### 異なるモデルで評価

```bash
# gpt-4o-miniで生成し、claude-sonnet-4-5で評価
uv run python -m src.main \
    -lp openai \
    -m gpt-4o-mini \
    -g female \
    -a 25 \
    --judge-provider anthropic \
    --judge-model claude-sonnet-4-5
```

##### 出力先の指定

```bash
uv run python -m src.main \
    -lp gemini \
    -m gemini-2.5-flash \
    -g male \
    -a 40 \
    --output-directory ./custom_output
```

##### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Options:
  -g, --gender [female|male]                    The gender of the character to generate.
  -a, --age INTEGER RANGE                       The age of the character to generate.  [0<=x<=100]
  -ai, --additional-instructions TEXT           Additional instructions for character generation.
  -lp, --llm-provider [openai|gemini|anthropic] The LLM provider to use.
  -m, --model TEXT                              The model to use for the request.
  -od, --output-directory PATH                  The directory to save output files.
  -jp, --judge-provider [openai|gemini|anthropic] The LLM provider to use for judgment.
  -jm, --judge-model TEXT                       The model to use for judgment.
  --help                                        Show this message and exit.
```

#### テストの実行

プロンプトのユニットテストを実行します：

##### すべてのテストを実行

```bash
# pytestで全テストを実行
uv run pytest

# より詳細な出力
uv run pytest -v

# ローカル変数を表示
uv run pytest -vl
```

##### 特定のテストクラスを実行

```bash
# プロンプト構造検証テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterPromptStructure -v

# 品質テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterOutputQuality -v

# リグレッション検出テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestRegressionDetection -v
```

##### 特定のテスト関数を実行

```bash
# 必須フィールド検証テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_includes_required_fields -v
```

##### マーカーでフィルタリング

```bash
# 非同期テストのみ
uv run pytest -m asyncio -v

# 統合テスト（スキップされているものも実行）
uv run pytest -m integration -v

# スモークテストのみ
uv run pytest -m smoke -v
```

##### テストをスキップせずに実行

```bash
# API呼び出しを伴うテストも含めて実行（コストに注意）
uv run pytest -v -k "not test_full_generation" --tb=short
```

##### テスト結果のサマリー

```bash
# すべてのテスト結果のサマリーを表示
uv run pytest -ra
```

### 出力例

#### キャラクター生成結果

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/abc123_gemini_character.json`

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

#### Judge評価結果

**ファイル名**: `outputs/abc123_gemini_judge.json`

```json
{
    "evaluations": [
        {
            "criterion_name": "accuracy",
            "score": 4,
            "reasoning": "指定された年齢（28歳）と性別（男性）が正確に反映されている。"
        },
        {
            "criterion_name": "comprehensiveness",
            "score": 5,
            "reasoning": "名前、性別、年齢、3つの性格特性がすべて含まれており、各性格には短い説明と詳細な説明の両方が記載されている。"
        },
        {
            "criterion_name": "clarity",
            "score": 4,
            "reasoning": "各性格特性が明確に記述されており、キャラクターの個性が理解しやすい。"
        }
    ],
    "overall_score": 4.33,
    "summary": "指定された条件を満たし、キャラクターの個性が適切に表現された高品質な生成結果。"
}
```

#### 実行ログ例

```
[2025-10-18 17:30:45] [INFO] [__main__] [main.py:102] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: Generate a wizard from a fantasy world.

Generation LLM: gemini / gemini-2.0-flash-exp
Judge LLM: gemini / gemini-2.0-flash-exp
Output directory: outputs

[2025-10-18 17:30:45] [INFO] [src.service.request_llm] [request_llm.py:59] Step 1: Generating character...
[2025-10-18 17:30:47] [INFO] [src.service.request_llm] [request_llm.py:67] Character generation completed.
[2025-10-18 17:30:47] [INFO] [src.service.request_llm] [request_llm.py:70] Step 2: Evaluating character with LLM-as-a-Judge...
[2025-10-18 17:30:49] [INFO] [src.service.request_llm] [request_llm.py:96] Evaluation completed. Overall score: 4.33/5.0
[2025-10-18 17:30:49] [INFO] [__main__] [main.py:144] Character file saved to outputs/abc123_gemini_character.json
[2025-10-18 17:30:49] [INFO] [__main__] [main.py:149] Judge evaluation saved to outputs/abc123_gemini_judge.json
[2025-10-18 17:30:49] [INFO] [__main__] [main.py:151] Overall evaluation score: 4.33/5.0
```

#### テスト実行結果例

```bash
$ uv run pytest -v

============================= test session starts ==============================
platform darwin -- Python 3.13.2, pytest-8.4.2
collected 25 items

tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_request_creation PASSED    [  4%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_response_structure PASSED  [  8%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_evaluation_score_values PASSED   [ 12%]
tests/test_llm_as_a_judge.py::TestJudgePrompts::test_make_judge_prompt_structure PASSED [ 16%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_includes_required_fields PASSED [ 20%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_specifies_personality_count PASSED [ 24%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_enforces_json_format PASSED [ 28%]
tests/test_prompt_unit_testing.py::TestCharacterOutputQuality::test_generated_character_meets_quality_threshold PASSED [ 32%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_young_female_fantasy_character PASSED [ 36%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_elderly_male_realistic_character PASSED [ 40%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_output_contains_all_required_fields PASSED [ 44%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_personality_traits_have_descriptions PASSED [ 48%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_output_is_valid_json_serializable PASSED [ 52%]

============================== 25 passed in 2.45s ===============================
```

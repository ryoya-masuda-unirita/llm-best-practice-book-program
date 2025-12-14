# Chapter 2 Section 2: LLMで構造化出力を定義する

## 概要

本プロジェクトは、**LLM自身に出力スキーマを動的に生成させる**アプローチを実装しています。従来、LLMの出力形式は開発者が事前に定義する必要がありましたが、AIエージェントのように用途が柔軟でドメインが多岐にわたる場合、すべてのスキーマを事前定義することは困難です。

このプロジェクトでは、処理を2つのステップに分割することでこの課題を解決します：

1. **Step 1: スキーマ生成** - LLMに自然言語プロンプトを与え、最適なJSON Schemaを生成させる
2. **Step 2: データ抽出** - 生成されたスキーマをPydanticモデルに変換し、構造化データを抽出する

この2段階アプローチにより、開発者は事前にすべての出力形式を設計する必要がなくなり、柔軟でスケーラブルなシステムを構築できます。

## 機能

- **動的スキーマ生成**: 自然言語プロンプトからOpenAI Structured Outputs準拠のJSON Schemaを自動生成
- **High Reasoningモード**: 曖昧なプロンプトに対してLLMがドメイン知識を活用し最適な構造を推論
- **マルチプロンプト対応**: 複数のプロンプトから統一スキーマを生成（共通フィールドは必須、ケース固有はオプショナル）
- **自動バリデーション**: 生成されたスキーマの検証とエラーフィードバックによる自動リトライ（最大3回）
- **Pydanticモデル変換**: JSON SchemaからPydanticモデルを動的に生成（ネスト、配列、Union型対応）
- **スキーマ永続化**: 生成したスキーマをJSONファイルとして保存・再利用

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_2/
├── src/
│   ├── main.py                          # CLIエントリーポイント
│   ├── config.py                        # 設定管理（環境変数）
│   ├── logger.py                        # ロギング設定
│   ├── auto_structured_output/          # コアモジュール
│   │   ├── extractor.py                 # メインオーケストレーター
│   │   ├── schema_generator.py          # スキーマ生成・リトライ
│   │   ├── model_builder.py             # JSON Schema → Pydantic変換
│   │   ├── validators.py                # スキーマバリデーション
│   │   ├── prompts.py                   # プロンプトテンプレート
│   │   └── model.py                     # 型定義（SupportedType, StringFormat）
│   ├── client/
│   │   └── llm_client.py                # OpenAIクライアント設定
│   └── examples/                        # 17個の実践的サンプル
│       ├── runner.py                    # 実行ロジック
│       ├── basic_usage.py               # 基本例（5例）
│       ├── advanced_examples.py         # 応用例（6例）
│       └── high_reasoning_examples.py   # 高度推論例（6例）
├── outputs/                             # 生成されたスキーマ出力先
├── .envrc.example                       # 環境変数テンプレート
├── Makefile                             # 開発タスク
└── pyproject.toml                       # 依存関係
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        ユーザープロンプト                          │
│         "ユーザー名、年齢、メールアドレスを抽出して"                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     StructureExtractor                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Step 1: スキーマ生成                                     │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌────────────┐   │   │
│  │  │   Prompt    │───▶│  OpenAI API │───▶│JSON Schema │   │   │
│  │  │  Templates  │    │  (gpt-4o)   │    │  生成      │   │   │
│  │  └─────────────┘    └─────────────┘    └────────────┘   │   │
│  │                                              │           │   │
│  │                                              ▼           │   │
│  │                                    ┌─────────────────┐   │   │
│  │                                    │  SchemaValidator│   │   │
│  │                                    │  (検証＆リトライ) │   │   │
│  │                                    └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                │                                │
│                                ▼                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Step 2: モデル構築 & データ抽出                          │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌────────────┐   │   │
│  │  │JSON Schema  │───▶│ModelBuilder │───▶│  Pydantic  │   │   │
│  │  │             │    │(create_model│    │   Model    │   │   │
│  │  └─────────────┘    └─────────────┘    └────────────┘   │   │
│  │                                              │           │   │
│  │                                              ▼           │   │
│  │                                    ┌─────────────────┐   │   │
│  │                                    │  OpenAI API     │   │   │
│  │                                    │  (parse)        │   │   │
│  │                                    └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        構造化データ出力                          │
│  {"name": "John Doe", "age": 21, "email": "john@example.com"}   │
└─────────────────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - `click>=8.3.0` - CLIフレームワーク
  - `openai>=2.4.0` - OpenAI API クライアント
  - `pydantic>=2.12.2` - データバリデーション
  - `python-dotenv>=1.1.1` - 環境変数管理
  - `google-genai>=1.45.0` - Google Generative AI（拡張用）

### セットアップ

1. 環境変数を設定

```bash
cp .envrc.example .envrc
```

`.envrc`を編集してAPIキーを設定:

```bash
export OPENAI_API_KEY="sk-your-openai-api-key-here"
BASIC_PREDICTION_MODEL="gpt-4o"
HIGH_PREDICTION_MODEL="gpt-5"
```

2. 依存関係をインストール

```bash
uv sync
```

### 使用方法、実行方法

#### CLIオプション

```bash
python -m src.main --help
```

```
Usage: python -m src.main [OPTIONS]

  Run auto-structured output examples

Options:
  -m, --model [gpt-5|gpt-5-mini|gpt-5-nano|gpt-4.1|gpt-4.1-mini|gpt-4.1-nano|gpt-4o|gpt-4o-mini]
                                  The model to use for the request.  [required]
  -e, --example [example_1_simple_user_model|example_2_product_with_enum|...]
                                  The example to run.
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### 基本的な実行例

```bash
# シンプルなユーザーモデルの生成
python -m src.main -m gpt-4o -e example_1_simple_user_model

# 出力ディレクトリを指定して実行
python -m src.main -m gpt-4o -e example_2_product_with_enum -od ./my_outputs

# 高推論モードのサンプル実行
python -m src.main -m gpt-4o -e example_1_customer_feedback_analysis
```

#### サンプル一覧

| カテゴリ | 例 | 説明 |
|---------|------|------|
| Basic | `example_1_simple_user_model` | シンプルなユーザープロファイル |
| Basic | `example_2_product_with_enum` | Enum型を持つ商品情報 |
| Basic | `example_3_optional_fields` | オプショナルフィールドを持つ書籍 |
| Basic | `example_4_array_fields` | 配列フィールドを持つコース情報 |
| Basic | `example_5_datetime_fields` | 日時フィールドを持つイベント |
| Advanced | `example_1_nested_objects` | ネストしたオブジェクト |
| Advanced | `example_2_complex_article` | 著者・コメントを含む記事 |
| Advanced | `example_3_array_of_objects` | オブジェクト配列を持つ注文 |
| Advanced | `example_4_deep_nesting` | 深いネスト構造（組織） |
| Advanced | `example_5_anyof_union_types` | Union型の支払い方法 |
| Advanced | `example_6_validation_constraints` | バリデーション制約付き商品 |
| High Reasoning | `example_1_customer_feedback_analysis` | 顧客フィードバック分析 |
| High Reasoning | `example_2_meeting_summary` | 会議サマリー抽出 |
| High Reasoning | `example_3_research_paper_metadata` | 学術論文メタデータ |
| High Reasoning | `example_4_job_application_evaluation` | マルチプロンプト求人評価 |
| High Reasoning | `example_5_financial_transaction_analysis` | マルチプロンプト金融取引分析 |
| High Reasoning | `example_6_high_reasoning` | 複合商品レビュー分析 |

### 出力例

`example_1_simple_user_model`を実行した場合：

**生成されるJSON Schema** (`outputs/simple_user_model.json`):

```json
{
  "$defs": {
    "NestedModel": {
      "properties": {
        "theme": {
          "description": "UI theme preference",
          "enum": ["light", "dark"],
          "type": "string"
        },
        "notificationsEnabled": {
          "description": "Whether notifications are enabled",
          "type": "boolean"
        }
      },
      "required": ["theme", "notificationsEnabled"],
      "type": "object"
    }
  },
  "properties": {
    "name": {
      "description": "User's full name",
      "type": "string"
    },
    "age": {
      "description": "User's age in years",
      "type": "integer"
    },
    "email": {
      "description": "User's email address",
      "type": "string"
    },
    "preferences": {
      "$ref": "#/$defs/NestedModel",
      "description": "User interface and notification preferences"
    }
  },
  "required": ["name", "age", "email", "preferences"],
  "title": "UserProfile",
  "type": "object"
}
```

**抽出される構造化データ**:

```python
{
    "name": "John Doe",
    "age": 21,
    "email": "johndoe@example.com",
    "preferences": {
        "theme": "light",
        "notificationsEnabled": False
    }
}
```

## プログラムでの使用

```python
from openai import OpenAI
from src.auto_structured_output import StructureExtractor

# OpenAIクライアントを初期化
client = OpenAI(api_key="your-api-key")

# StructureExtractorを作成
extractor = StructureExtractor(llm_client=client, model="gpt-4o")

# Step 1: プロンプトからPydanticモデルを動的に生成
prompt = "ユーザー名、年齢、メールアドレスを抽出してください"
T_Model = extractor.extract_structure([prompt])

# Step 2: 生成したモデルを使って構造化データを抽出
response = client.responses.parse(
    model="gpt-4o",
    input=[{"role": "user", "content": "John Doeは25歳で、john@example.comにメールできます"}],
    text_format=T_Model,
)

data = response.output_parsed.model_dump()
print(data)
# {"name": "John Doe", "age": 25, "email": "john@example.com"}

# スキーマを保存して再利用
extractor.save_extracted_json(T_Model, "my_schema.json")

# 保存したスキーマからモデルを復元
restored_model = StructureExtractor.load_from_json("my_schema.json")
```

### 高推論モードの使用

```python
# 曖昧なプロンプトに対して最適な構造を推論
T_Model = extractor.extract_structure(
    ["Analyze customer feedback and extract comprehensive business insights"],
    use_high_reasoning=True
)
# LLMが以下のような構造を自動推論:
# - product_quality_assessment
# - delivery_experience
# - customer_satisfaction_metrics
# - actionable_recommendations
# など
```

### マルチプロンプト統合の使用

```python
# 複数のユースケースをカバーする統一スキーマを生成
T_Model = extractor.extract_structure([
    "Extract junior engineer application: education, internships, projects",
    "Extract senior engineer application: career, large projects, leadership",
    "Extract expert engineer application: certifications, publications, patents"
])
# 共通フィールドは必須、ケース固有のフィールドはオプショナルとして設計
```

## 開発コマンド

```bash
# 出力ファイルとキャッシュのクリーンアップ
make clean

# Lintチェック（ruff）
make lint

# コードフォーマット（ruff）
make fmt

# Lint + フォーマット
make fix

# 型チェック（mypy）
make mypy
```

## カスタム例外

- `ExtractionError` - 構造抽出の一般エラー
- `SchemaValidationError` - スキーマ検証失敗（リトライ後も失敗）
- `ModelBuildError` - Pydanticモデル構築失敗

## 注意点

- **OpenAI専用**: 現在の実装はOpenAI APIのみをサポートしています
- **出力の安定性**: LLMが生成するスキーマは実行のたびに微妙に異なる可能性があります。安定性が必要な場合は、一度生成したスキーマを保存して再利用してください
- **APIコスト**: 2段階のAPI呼び出しが必要なため、通常の構造化出力より多くのトークンを消費します
- **バリデーションリトライ**: デフォルトで最大3回リトライしますが、複雑なスキーマでは失敗する可能性があります
- **uriフォーマット非対応**: OpenAI Structured Outputsでは`uri`フォーマットがサポートされていません。URLは`string`型で定義してください

## ライセンス

MIT License

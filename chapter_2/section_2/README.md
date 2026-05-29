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
│  │  │  Templates  │    │  (gpt-5.4)   │    │  生成      │   │   │
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
OPENAI_API_KEY=<your_openai_api_key_here>
BASIC_PREDICTION_MODEL=gpt-5.4
HIGH_PREDICTION_MODEL=gpt-5.4
```

2. 依存関係をインストール

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

#### CLIオプション

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Run auto-structured output examples

  This command executes examples from src/examples/ directory. Each example
  demonstrates the two-step auto-structured output approach.

Options:
  -m, --model [GPT_5_5|GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO]
                                  The model to use for the request.
                                  [required]
  -e, --example [example_1_simple_user_model|example_2_product_with_enum|example_3_optional_fields|example_4_array_fields|example_5_datetime_fields|example_1_nested_objects|example_2_complex_article|example_3_array_of_objects|example_4_deep_nesting|example_5_anyof_union_types|example_6_validation_constraints|example_1_customer_feedback_analysis|example_2_meeting_summary|example_3_research_paper_metadata|example_4_job_application_evaluation|example_5_financial_transaction_analysis|example_6_high_reasoning]
                                  The example to run.
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### 基本的な実行例

```bash
# シンプルなユーザーモデルの生成
uv run python -m src.main -m GPT_5_4 -e example_1_simple_user_model

# 出力ディレクトリを指定して実行
uv run python -m src.main -m GPT_5_4 -e example_2_product_with_enum -od ./my_outputs

# 高推論モードのサンプル実行
uv run python -m src.main -m GPT_5_4 -e example_1_customer_feedback_analysis
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
          "description": "Preferred theme",
          "enum": [
            "light",
            "dark"
          ],
          "title": "Theme",
          "type": "string"
        },
        "notificationsEnabled": {
          "description": "Whether notifications are enabled",
          "title": "Notificationsenabled",
          "type": "boolean"
        }
      },
      "required": [
        "theme",
        "notificationsEnabled"
      ],
      "title": "NestedModel",
      "type": "object"
    }
  },
  "properties": {
    "name": {
      "description": "User's name",
      "title": "Name",
      "type": "string"
    },
    "age": {
      "description": "User's age",
      "title": "Age",
      "type": "integer"
    },
    "email": {
      "description": "User's email address",
      "title": "Email",
      "type": "string"
    },
    "preferences": {
      "$ref": "#/$defs/NestedModel",
      "description": "User's preferences"
    }
  },
  "required": [
    "name",
    "age",
    "email",
    "preferences"
  ],
  "title": "UserProfile",
  "type": "object"
}
```

**抽出される構造化データ**:

```python
{'name': 'John Doe', 'age': 21, 'email': 'johndoe@example.com', 'preferences': {'theme': 'light', 'notificationsEnabled': False}}
```

### 実行例

```bash
$ uv run python -m src.main -m GPT_5_4 -e example_1_simple_user_model

[2026-01-17 16:12:27,600] [INFO] [__main__] [main.py:100] [main] Executing example: example_1_simple_user_model

=== Example 1: Simple User Model ===
[2026-01-17 16:12:30,476] [INFO] [src.examples.runner] [runner.py:20] [run] Generated model: UserProfile
[2026-01-17 16:12:30,478] [INFO] [src.examples.runner] [runner.py:21] [run] Fields: {'$defs': {'NestedModel': {'properties': {'theme': {'description': 'Preferred theme', 'enum': ['light', 'dark'], 'title': 'Theme', 'type': 'string'}, 'notificationsEnabled': {'description': 'Whether notifications are enabled', 'title': 'Notificationsenabled', 'type': 'boolean'}}, 'required': ['theme', 'notificationsEnabled'], 'title': 'NestedModel', 'type': 'object'}}, 'properties': {'name': {'description': "User's name", 'title': 'Name', 'type': 'string'}, 'age': {'description': "User's age", 'title': 'Age', 'type': 'integer'}, 'email': {'description': "User's email address", 'title': 'Email', 'type': 'string'}, 'preferences': {'$ref': '#/$defs/NestedModel', 'description': "User's preferences"}}, 'required': ['name', 'age', 'email', 'preferences'], 'title': 'UserProfile', 'type': 'object'}
[2026-01-17 16:12:32,725] [INFO] [src.examples.runner] [runner.py:33] [run] 
Generated data:
[2026-01-17 16:12:32,725] [INFO] [src.examples.runner] [runner.py:34] [run] {'name': 'John Doe', 'age': 21, 'email': 'johndoe@example.com', 'preferences': {'theme': 'light', 'notificationsEnabled': False}}
```

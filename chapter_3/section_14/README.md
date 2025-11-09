# Chapter 3 Section 14: LLMで構造化出力を定義する

## 概要

このプロジェクトは、**LLM自身に出力スキーマを動的に生成させる**先進的なアプローチを示すサンプルコードです。従来、開発者が事前に固定的な出力スキーマを定義する必要がありましたが、本プロジェクトではLLMに対して「どのような情報を抽出すべきか」を問いかけ、最適な出力構造（JSON SchemaやPydanticモデル）を自動生成させます。

この2段階アプローチにより、多様なドメインや要件の変化に対して、システムが動的に適応可能な出力構造を自ら生成できるようになります。OpenAI GPT-4oおよびGemini 2.5シリーズの両方に対応し、基本的な使用例から高度な推論を必要とする複雑なユースケースまで、17の実践的なサンプルを提供します。

## 機能

- **自動スキーマ生成**: LLMが自然言語プロンプトからJSON Schemaを自動生成
- **2段階処理**: (1) スキーマ生成 → (2) データ抽出の明確な分離
- **高推論モード**: 曖昧なプロンプトから最適な構造を推論
- **マルチプロンプト対応**: 複数のプロンプトから統合されたスキーマを生成
- **自動バリデーション**: 生成されたスキーマの妥当性を自動検証
- **リトライ機構**: バリデーション失敗時のエラーフィードバックと自動再試行
- **Pydantic変換**: JSON SchemaからPydanticモデルへの自動変換
- **デュアルプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **17の実践例**: 基本から高度なユースケースまで網羅
- **CLIインターフェース**: Clickによる使いやすいコマンドライン操作
- **スキーマ永続化**: 生成したスキーマのJSON形式での保存・再利用

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_14/
├── src/
│   ├── __init__.py
│   ├── main.py                          # メインエントリーポイント
│   ├── logger.py                        # ロギング設定
│   ├── auto_structured_output/          # 自動構造化出力コアモジュール
│   │   ├── __init__.py
│   │   ├── extractor.py                 # 構造抽出メインクラス
│   │   ├── schema_generator.py          # スキーマ生成とバリデーション
│   │   ├── model_builder.py             # JSON Schema → Pydantic変換
│   │   ├── validators.py                # スキーマバリデーター
│   │   ├── prompts.py                   # スキーマ抽出プロンプト定義
│   │   └── model.py                     # 基底データモデル
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py                # LLMクライアント初期化
│   └── examples/                        # 実践的な使用例
│       ├── __init__.py
│       ├── runner.py                    # 標準実行ロジック
│       ├── basic_usage.py               # 基本例（5例）
│       ├── advanced_examples.py         # 応用例（6例）
│       └── high_reasoning_examples.py   # 高推論例（6例）
├── outputs/                              # 生成結果の保存先（自動作成）
├── .envrc.example                        # 環境変数設定のサンプル
├── Makefile                              # 開発用タスク定義
├── pyproject.toml                        # プロジェクト依存関係
├── README.md                             # このファイル
└── CLAUDE.md                             # プロジェクト詳細ドキュメント
```

### アーキテクチャ

このプロジェクトは、以下の階層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────────┐
│              CLI Layer (main.py)                        │
│  - コマンドライン引数解析（Click）                        │
│  - 例題選択とプロバイダー指定                             │
│  - 出力ディレクトリ管理                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│           Example Layer (examples/)                     │
│  - 17の実践的な使用例                                     │
│  - runner.py: 標準モード実行                             │
│  - high_reasoning_examples.py: 高推論モード実行          │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│    Core Logic Layer (auto_structured_output/)           │
│  ┌──────────────────────────────────────────┐           │
│  │  StructureExtractor (extractor.py)       │           │
│  │  - 全体の処理フローを統括                 │           │
│  └─────┬───────────────┬────────────────────┘           │
│        │               │                                 │
│  ┌─────▼──────┐  ┌────▼──────────┐                     │
│  │ SchemaGen  │  │ ModelBuilder  │                     │
│  │ ・スキーマ  │  │ ・JSON Schema │                     │
│  │   生成     │  │   → Pydantic  │                     │
│  │ ・バリデー │  │   変換        │                     │
│  │   ション   │  │ ・動的クラス  │                     │
│  │ ・リトライ │  │   生成        │                     │
│  └────────────┘  └───────────────┘                     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│      Infrastructure Layer                               │
│  - LLMクライアント管理 (llm_client.py)                   │
│  - プロンプト管理 (prompts.py)                           │
│  - バリデーション (validators.py)                        │
│  - ログ管理 (logger.py)                                  │
│  - 外部API (OpenAI, Gemini)                             │
└─────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. 自動スキーマ抽出の2段階アプローチ

このプロジェクトの核心は、以下の2段階処理です：

**ステップ1: スキーマ生成**
```python
from src.auto_structured_output import StructureExtractor

extractor = StructureExtractor(llm_client=openai_client, model="gpt-4o")

# 自然言語プロンプトからスキーマを生成
T_Model = extractor.extract_structure([
    "ユーザー情報を抽出してください。名前、年齢、メールアドレスが必要です。"
])

# T_Model は動的に生成されたPydanticモデル
print(T_Model.model_json_schema())
```

**ステップ2: データ抽出**
```python
# 生成されたスキーマを使って実データを抽出
response = openai_client.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "田中太郎は30歳でtanaka@example.comです"}],
    response_format=T_Model
)

user = response.choices[0].message.parsed
# user.name = "田中太郎"
# user.age = 30
# user.email = "tanaka@example.com"
```

#### 2. コアモジュール (`src/auto_structured_output/`)

##### StructureExtractor (`extractor.py`)

全体の処理フローを統括するメインクラス：

```python
class StructureExtractor:
    def extract_structure(
        self,
        prompts: list[str],
        use_high_reasoning: bool = False,
    ) -> type[BaseModel]:
        """プロンプトから構造を抽出してPydanticモデルを返す

        Args:
            prompts: 自然言語プロンプトのリスト
            use_high_reasoning: 高推論モードを使用するか

        Returns:
            動的に生成されたPydanticモデルクラス
        """
        # 1. スキーマ生成
        schema_json = self._extract_schema_from_prompt(prompts, use_high_reasoning)

        # 2. バリデーション
        validated_schema = self._validate_schema(schema_json)

        # 3. Pydanticモデルに変換
        model_class = self._build_model(validated_schema)

        return model_class
```

**ポイント**:
- OpenAI専用の実装（Geminiサポートは例題レイヤーのみ）
- 3段階の明確な処理分離
- エラーハンドリングと例外の型付け

##### SchemaGenerator (`schema_generator.py`)

LLMを使ってJSON Schemaを生成し、自動バリデーションとリトライを実行：

```python
class SchemaGenerator:
    def extract_from_prompt(
        self,
        prompts: list[str],
        client: Any,
        model: str,
        use_high_reasoning: bool = False,
    ) -> dict[str, Any]:
        """プロンプトからスキーマを抽出（リトライ機能付き）"""
        messages = get_schema_extraction_messages(prompts, use_high_reasoning)

        for attempt in range(self.max_retries):
            try:
                # スキーマ生成
                schema = self._call_api(client, model, messages)

                # バリデーション
                SchemaValidator.validate_schema(schema)

                return schema

            except ValueError as e:
                # エラーフィードバックを含めて再試行
                messages = get_schema_retry_messages(
                    original_prompt=prompts,
                    previous_schema=schema,
                    error_message=str(e),
                    use_high_reasoning=use_high_reasoning,
                )
```

**ポイント**:
- 最大3回の自動リトライ
- バリデーションエラーをLLMにフィードバック
- `response_format={"type": "json_object"}`でJSON形式を強制

##### ModelBuilder (`model_builder.py`)

JSON SchemaからPydanticモデルを動的に生成：

```python
class ModelBuilder:
    def build_model(self, schema: dict[str, Any]) -> type[BaseModel]:
        """JSON SchemaからPydanticモデルを構築"""
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # フィールド定義を動的に作成
        fields = {}
        for field_name, field_info in properties.items():
            python_type = self._json_type_to_python(field_info)
            is_required = field_name in required

            if is_required:
                fields[field_name] = (python_type, ...)
            else:
                fields[field_name] = (python_type, None)

        # 動的にPydanticモデルを作成
        return create_model("DynamicModel", **fields, __base__=BaseModel)
```

**ポイント**:
- `create_model()`で実行時にクラスを生成
- ネストされたオブジェクトや配列にも対応
- anyOf（Union型）のサポート

#### 3. 実践例 (`src/examples/`)

プロジェクトには17の実践的な例が含まれています：

**基本例 (`basic_usage.py`)** - 5例
- `example_1_simple_user_model`: シンプルなユーザーモデル
- `example_2_product_with_enum`: Enum型を含む商品モデル
- `example_3_optional_fields`: オプションフィールドを含む書籍モデル
- `example_4_array_fields`: 配列フィールドを含むコースモデル
- `example_5_datetime_fields`: 日時フィールドを含むイベントモデル

**応用例 (`advanced_examples.py`)** - 6例
- `example_1_nested_objects`: ネストされたオブジェクト（ユーザープロフィール）
- `example_2_complex_article`: 複雑な記事構造（著者とコメント）
- `example_3_array_of_objects`: オブジェクト配列（注文システム）
- `example_4_deep_nesting`: 深いネスト構造（組織階層）
- `example_5_anyof_union_types`: Union型（支払い方法）
- `example_6_validation_constraints`: バリデーション制約（商品仕様）

**高推論例 (`high_reasoning_examples.py`)** - 6例
- `example_1_customer_feedback_analysis`: 顧客フィードバック分析
- `example_2_meeting_summary`: 会議議事録の構造化
- `example_3_research_paper_metadata`: 学術論文メタデータ抽出
- `example_4_job_application_evaluation`: 求人応募評価（マルチプロンプト）
- `example_5_financial_transaction_analysis`: 金融取引分析（マルチプロンプト）
- `example_6_high_reasoning`: 商品レビュー分析（マルチプロンプト）

#### 4. 高推論モードとマルチプロンプト対応

高推論モードでは、曖昧なプロンプトから最適な構造を推論します：

```python
# 単一プロンプト - 明確な構造が定義されていない
prompts = ["""
顧客フィードバックを分析して、ビジネス改善に役立つ洞察を抽出してください。
商品の品質、配送体験、顧客満足度、サービス品質、競合比較、改善提案など、
複数の観点から包括的に分析する必要があります。
"""]

extractor = StructureExtractor(llm_client=openai_client, model="gpt-4o")
T_Model = extractor.extract_structure(prompts, use_high_reasoning=True)

# LLMが自動的に最適なスキーマを推論
# → ProductQualityAssessment, DeliveryExperience, CustomerSatisfaction...
```

**マルチプロンプト統合スキーマ生成**:

```python
# 複数のプロンプトから統合されたスキーマを生成
prompts = [
    "ジュニアエンジニアの応募を評価。教育背景、インターンシップ、個人プロジェクト...",
    "シニアエンジニアの応募を評価。キャリア、大規模プロジェクト、技術リーダーシップ...",
    "専門エンジニアの応募を評価。ドメイン専門性、資格、論文、オープンソース貢献..."
]

# すべてのレベルに対応できる統合スキーマを生成
T_Model = extractor.extract_structure(prompts, use_high_reasoning=True)
```

#### 5. デュアルプロバイダー対応 (`examples/runner.py`)

例題レイヤーでは、OpenAIとGeminiの両方に対応：

```python
def run(llm_client: Any, model: OpenAIModel | GeminiModel, prompt: str, file_name: Optional[str] = None):
    # Step 1: スキーマ生成（OpenAI専用）
    extractor = StructureExtractor(llm_client=llm_client, model=model)
    T_Model = extractor.extract_structure([prompt])

    # Step 2: データ抽出（プロバイダー自動判定）
    if isinstance(llm_client, genai.Client):
        # Gemini用のスキーマ変換と実行
        gemini_schema = _convert_to_gemini_schema(T_Model)
        response = llm_client.models.generate_content(
            model=model,
            contents={"role": "user", "parts": [{"text": prompt}]},
            config={"response_mime_type": "application/json", "response_schema": gemini_schema}
        )
        data_dict = json.loads(response.text)
    else:
        # OpenAI実行
        response = llm_client.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=T_Model
        )
        data_dict = response.choices[0].message.parsed.model_dump()
```

**ポイント**:
- `isinstance(llm_client, genai.Client)`でプロバイダー判定
- GeminiにはPydantic→Geminiスキーマ変換が必要
- OpenAIは`response_format`に直接Pydanticモデルを指定可能

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.1.7
  - google-genai>=1.11.1
  - openai>=1.59.5
  - pydantic>=2.10.4
  - python-dotenv>=1.0.1
  - jsonschema>=4.23.0

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
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
# Geminiを使用して基本例を実行
python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -e example_1_simple_user_model

# OpenAIを使用して基本例を実行
python -m src.main -lp OPENAI -m GPT_4O -e example_1_simple_user_model

# 高推論例を実行（GPT-4o推奨）
python -m src.main -lp OPENAI -m GPT_4O -e example_1_customer_feedback_analysis
```

#### すべての例題の一覧表示

```bash
python -m src.main --help
```

**出力例**:
```
Options:
  -lp, --llm-provider [OPENAI|GEMINI]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5|GPT_4O|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|...]
                                  The model to use for the request.
                                  [required]
  -e, --example [example_1_simple_user_model|example_2_product_with_enum|...]
                                  The example to run.
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### カスタム出力ディレクトリの指定

```bash
# カスタム出力ディレクトリを指定
python -m src.main -lp OPENAI -m GPT_4O -e example_1_nested_objects -od ./my_outputs
```

#### Makefileを使った実行（開発用）

```bash
# 基本例の実行
make run-example-basic

# 応用例の実行
make run-example-advanced

# 高推論例の実行
make run-example-high-reasoning
```

### 出力例

#### 例1: シンプルなユーザーモデル

**実行コマンド**:
```bash
python -m src.main -lp OPENAI -m GPT_4O -e example_1_simple_user_model
```

**生成されたスキーマ** (`outputs/simple_user_model.json`):
```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "User's name"
    },
    "age": {
      "type": "integer",
      "description": "Age"
    },
    "email": {
      "type": "string",
      "description": "Email address"
    },
    "preferences": {
      "type": "object",
      "properties": {
        "theme": {
          "type": "string",
          "enum": ["light", "dark"],
          "description": "Theme preference"
        },
        "notifications_enabled": {
          "type": "boolean",
          "description": "Whether notifications are enabled"
        }
      },
      "required": ["theme", "notifications_enabled"]
    }
  },
  "required": ["name", "age", "email", "preferences"]
}
```

**実行ログ例**:
```
[2025-11-09 12:00:00] [INFO] [__main__] [main.py:121] [main] Executing example: example_1_simple_user_model

=== Example 1: Simple User Model ===
[2025-11-09 12:00:01] [INFO] [runner] [runner.py:80] [run] Generated model: DynamicModel
[2025-11-09 12:00:01] [INFO] [runner] [runner.py:81] [run] Fields: {...}

Generated data:
{'name': 'John Doe', 'age': 21, 'email': 'johndoe@example.com', 'preferences': {'theme': 'light', 'notifications_enabled': False}}
```

#### 例2: 高推論モード - 顧客フィードバック分析

**実行コマンド**:
```bash
python -m src.main -lp OPENAI -m GPT_4O -e example_1_customer_feedback_analysis
```

**生成されたスキーマの一部**:
```json
{
  "type": "object",
  "properties": {
    "product_quality_assessment": {
      "type": "object",
      "properties": {
        "overall_quality_rating": {
          "type": "number",
          "description": "Overall quality rating (1-5)"
        },
        "product_condition": {
          "type": "string"
        },
        "specific_products_mentioned": {
          "type": "array",
          "items": {"type": "string"}
        },
        "quality_issues": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "delivery_experience": {
      "type": "object",
      "properties": {
        "shipping_speed_rating": {"type": "number"},
        "packaging_quality": {"type": "string"},
        "delivery_accuracy": {"type": "boolean"},
        "met_promised_timeline": {"type": "boolean"}
      }
    },
    "customer_satisfaction_metrics": {
      "type": "object",
      "properties": {
        "overall_satisfaction": {"type": "number"},
        "likelihood_to_recommend": {"type": "number"},
        "likelihood_to_repurchase": {"type": "number"},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]}
      }
    },
    "actionable_recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "recommendation": {"type": "string"},
          "priority": {"type": "string", "enum": ["high", "medium", "low"]},
          "area": {"type": "string"}
        }
      }
    }
  }
}
```

**ポイント**:
- プロンプトには具体的なフィールド名の指定なし
- LLMが業務要件から最適な構造を推論
- 複数の観点を包括的にカバーする構造を自動生成

#### 例3: マルチプロンプト - 求人応募評価

**実行コマンド**:
```bash
python -m src.main -lp OPENAI -m GPT_4O -e example_4_job_application_evaluation
```

この例では、3つの異なるプロンプト（ジュニア、シニア、専門エンジニア）から、すべてのレベルに対応できる統合スキーマを生成します。

**生成されたスキーマの特徴**:
- ジュニア特有のフィールド（`internships`, `bootcamp_experience`）
- シニア特有のフィールド（`technical_leadership`, `system_scaling_experience`）
- 専門特有のフィールド（`certifications`, `publications`, `patents`）
- すべてのフィールドが適切にオプショナル化され、柔軟に対応可能

### テスト方法

#### 1. 基本例のテスト

```bash
# すべての基本例を順次実行
for example in example_1_simple_user_model example_2_product_with_enum example_3_optional_fields example_4_array_fields example_5_datetime_fields; do
    python -m src.main -lp OPENAI -m GPT_4O -e $example -od test_outputs
done
```

期待される動作：
- `test_outputs`ディレクトリにスキーマファイルが生成される
- 各ファイルが有効なJSON Schemaである
- ログにエラーが出力されない

#### 2. 応用例のテスト

```bash
# 複雑な構造の例をテスト
python -m src.main -lp OPENAI -m GPT_4O -e example_4_deep_nesting -od test_outputs
```

期待される動作：
- 深くネストされたスキーマが正しく生成される
- Pydanticモデルへの変換が成功する
- オブジェクト配列が正しく処理される

#### 3. 高推論モードのテスト

```bash
# 高推論例をテスト
python -m src.main -lp OPENAI -m GPT_4O -e example_1_customer_feedback_analysis -od test_outputs

# 生成されたスキーマを検証
cat test_outputs/customer_feedback_analysis.json | jq .
```

期待される動作：
- 曖昧なプロンプトから詳細なスキーマが生成される
- 業務ドメインに適した構造が推論される
- すべてのフィールドに適切な型と説明が付与される

#### 4. マルチプロンプトのテスト

```bash
# 複数プロンプトから統合スキーマを生成
python -m src.main -lp OPENAI -m GPT_4O -e example_4_job_application_evaluation -od test_outputs
```

期待される動作：
- 3つのプロンプトすべての要件をカバーするスキーマが生成される
- 共通フィールドは必須、特有フィールドはオプショナルになる
- スキーマが過度に複雑にならない

#### 5. プロバイダー互換性テスト

```bash
# OpenAIとGeminiで同じ例を実行し、結果を比較
python -m src.main -lp OPENAI -m GPT_4O -e example_1_nested_objects -od test_outputs/openai
python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -e example_1_nested_objects -od test_outputs/gemini

# スキーマを比較
diff test_outputs/openai/user_profile.json test_outputs/gemini/user_profile.json
```

#### 6. バリデーション機能のテスト

生成されたスキーマが正しく機能するか確認：

```bash
# Pythonで動的モデルのテスト
python << 'EOF'
from src.auto_structured_output import StructureExtractor
from src.client.llm_client import openai_client
import json

# スキーマ生成
extractor = StructureExtractor(llm_client=openai_client, model="gpt-4o")
T_Model = extractor.extract_structure([
    "Extract user with name, age (0-100), and email"
])

# スキーマ表示
print(json.dumps(T_Model.model_json_schema(), indent=2))

# バリデーションテスト
try:
    valid_user = T_Model(name="John", age=30, email="john@example.com")
    print(f"✓ Valid user: {valid_user}")
except Exception as e:
    print(f"✗ Validation error: {e}")

try:
    invalid_user = T_Model(name="Jane", age=150, email="invalid")  # 年齢が範囲外
    print(f"✗ Should have failed: {invalid_user}")
except Exception as e:
    print(f"✓ Correctly rejected: {e}")
EOF
```

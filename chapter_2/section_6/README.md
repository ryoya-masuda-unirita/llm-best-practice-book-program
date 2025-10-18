# Chapter 2 Section 6: プロンプトを構造的にテンプレート化する

## 概要

このプロジェクトは、**構造化されたテンプレート化プロンプト（Structured Template Prompting）** の実装を示すサンプルコードです。プロンプトをソースコードから分離し、YAML形式のテンプレートファイルとして管理することで、再利用性、保守性、可読性を飛躍的に向上させます。Jinja2テンプレートエンジンを活用して動的に変数を注入し、最終的なプロンプトを生成します。

キャラクター生成、商品説明文作成、メール文面生成といった複数のユースケースを通じて、プロンプトテンプレート化のベストプラクティスを学ぶことができます。

## 機能

- **テンプレートベースのプロンプト管理**: YAMLファイルでプロンプト構造を定義
- **動的変数注入**: Jinja2を使用した柔軟な変数置換とロジック（条件分岐、ループなど）
- **テンプレートバリデーション**: 必須変数の存在チェックによる実行時エラーの防止
- **複数テンプレートのサポート**: キャラクター生成、商品説明、メールなど多様なユースケース
- **変数ファイル管理**: テンプレートとデータを完全に分離した設計
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **型安全な構造化出力**: Pydanticモデルによる厳密な型検証
- **包括的なテストスイート**: TemplateEngineとプロンプト生成の網羅的テスト
- **CLIインターフェース**: 使いやすいコマンドラインツール
- **Makefileサポート**: 一般的なタスクを簡単に実行

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_6/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py       # LLM APIリクエスト処理
│       └── template_engine.py   # テンプレートエンジン実装
├── templates/                    # プロンプトテンプレートファイル
│   ├── character_generation.yaml # キャラクター生成テンプレート
│   ├── product_description.yaml  # 商品説明文テンプレート
│   ├── email_formal.yaml         # フォーマルメールテンプレート
│   └── email_casual.yaml         # カジュアルメールテンプレート
├── variables/                    # テンプレート変数定義ファイル
│   ├── character_artist.yaml     # 芸術家キャラクター変数
│   ├── character_detective.yaml  # 探偵キャラクター変数
│   ├── product_electronics.yaml  # 家電商品変数
│   ├── product_apparel.yaml      # アパレル商品変数
│   ├── email_campaign_summer.yaml # サマーキャンペーン変数
│   └── email_campaign_winter.yaml # ウィンターキャンペーン変数
├── tests/                        # テストファイル
│   ├── __init__.py
│   ├── conftest.py              # pytest設定とフィクスチャ
│   ├── test_template_engine.py  # TemplateEngineのテスト
│   └── test_prompt.py           # プロンプト生成のテスト
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # タスク自動化
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、テンプレート駆動型の4層アーキテクチャで構成されています：

```
┌───────────────────────────────────────────────┐
│         CLI Layer (main.py)                   │
│     - コマンドライン引数解析                   │
│     - 出力ディレクトリ管理                     │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│      Business Logic Layer                     │
│  - プロンプト生成 (prompt.py)                 │
│  - LLMリクエスト処理 (request_llm.py)         │
│  - データモデル (model.py)                    │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│      Template Layer                           │
│  - テンプレートエンジン (template_engine.py)  │
│  - YAMLテンプレート (templates/)              │
│  - 変数定義 (variables/)                      │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│      Infrastructure Layer                     │
│  - 設定管理 (config.py)                       │
│  - ログ管理 (logger.py)                       │
│  - 外部API (OpenAI, Gemini)                   │
└───────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. テンプレートエンジン (`src/service/template_engine.py`)

Jinja2を使用した構造化テンプレート管理の中核実装です：

```python
class TemplateEngine:
    """
    Template engine for loading and rendering YAML-based prompt templates.

    This class implements structured template prompting by:
    1. Loading YAML templates from a designated directory
    2. Rendering templates with dynamic variables using Jinja2
    3. Validating that all required variables are provided
    """

    def __init__(self, template_dir: str | Path = "templates"):
        """Initialize with template directory path."""
        self.template_dir = Path(template_dir)
        # Setup Jinja2 environment with proper settings
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
```

**主要機能**:

1. **`get_template_variables()`**: テンプレートで使用されている変数を抽出
2. **`validate_variables()`**: 必須変数が全て提供されているか検証
3. **`render_template()`**: テンプレートを変数でレンダリングしてYAMLをパース
4. **`render_prompt_messages()`**: LLM API形式のメッセージリストを生成

**ポイント**:
- `trim_blocks`と`lstrip_blocks`でYAMLインデントを適切に処理
- `meta.find_undeclared_variables()`で必須変数を自動検出
- テンプレート読み込み時のバリデーションで早期エラー検出

#### 2. YAMLテンプレート (`templates/character_generation.yaml`)

プロンプト構造をYAML形式で定義します：

```yaml
system_prompt: >-
  あなたは創造的なキャラクタージェネレーターです。

  あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。

  以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

  {{ response_schema | indent(2) }}

  以下を確認してください：
  1. 応答は有効なJSONであること
  2. すべてのフィールドが含まれていること
  3. 性別は指定された値であること
  4. 年齢は指定された値であること
  5. 正確に3つの性格特性が提供されていること

user_prompt: >-
  ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。

  性別は「{{ gender }}」、年齢は「{{ age }}」歳です。
{% if additional_instructions %}

  {{ additional_instructions }}
{% endif %}
```

**特徴**:
- `{{ variable }}`形式でプレースホルダーを定義
- `{% if %}...{% endif %}`で条件分岐
- `{{ variable | filter }}`でJinja2フィルタを適用（例: `indent(2)`）
- `>-`構文で複数行テキストを改行なしで結合

#### 3. 変数ファイル (`variables/character_artist.yaml`)

テンプレートに注入するデータを別ファイルで管理：

```yaml
# 芸術家キャラクター生成用変数設定
gender: "female"
age: 28
additional_instructions: "このキャラクターは画家で、感受性が豊かです。情熱的で自由奔放な性格ですが、繊細な一面も持っています。"
```

**メリット**:
- テンプレートとデータの完全な分離
- 同じテンプレートで異なるデータセットを簡単に切り替え
- 非エンジニアでも変数ファイルを編集可能

#### 4. プロンプト生成 (`src/prompt/prompt.py`)

テンプレートエンジンを使用してプロンプトを生成：

```python
# Initialize template engine with the templates directory
_template_dir = Path(__file__).parent.parent.parent / "templates"
_template_engine = TemplateEngine(template_dir=_template_dir)

def make_prompt(character_request: CharacterRequest) -> list:
    """
    Generate a structured prompt using template-based approach.

    This function demonstrates the structured template prompting practice by:
    1. Separating prompt logic from code (templates stored in YAML)
    2. Using Jinja2 for dynamic variable injection
    3. Validating that all required variables are provided
    """
    # Prepare the response schema for the template
    params = CharacterResponse.detailed_model()
    response_schema = json.dumps(params, indent=2, ensure_ascii=False)

    # Define variables to inject into the template
    template_variables = {
        "response_schema": response_schema,
        "gender": character_request.gender.value,
        "age": character_request.age,
        "additional_instructions": character_request.additional_instructions or "",
    }

    # Render the template with validation
    return _template_engine.render_prompt_messages(
        template_name="character_generation.yaml",
        variables=template_variables,
        validate=True,  # Ensure all required variables are provided
    )
```

**ポイント**:
- テンプレートエンジンをモジュールレベルで初期化（効率化）
- `validate=True`で必須変数の存在を保証
- スキーマ情報を動的に生成してテンプレートに注入

#### 5. データモデル (`src/model/model.py`)

リクエストとレスポンスのPydanticモデル：

```python
class CharacterRequest(BaseModel):
    """Request model for character generation."""
    gender: Gender = Field(..., description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    additional_instructions: Optional[str] = Field(
        ..., description="Additional instructions for character generation."
    )

class CharacterResponse(BaseModel):
    """Response model for generated character."""
    first_name: str = Field(..., description="The first name of the character.")
    last_name: str = Field(..., description="The last name of the character.")
    gender: Gender = Field(Gender.MALE, description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    personalities: list[CharacterPersonality] = Field(
        ..., description="The three most important personality traits of the character."
    )

    @staticmethod
    def detailed_model() -> dict:
        """Generate a detailed schema for prompt inclusion."""
        # Creates a human-readable schema representation for the prompt
        ...
```

**特徴**:
- `frozen=True`で不変オブジェクトを保証
- `validate_assignment=True`で代入時のバリデーション
- `detailed_model()`メソッドでプロンプト用のスキーマ説明を生成

#### 6. LLM APIリクエスト (`src/service/request_llm.py`)

OpenAIとGeminiの両方に対応したAPI呼び出し：

```python
async def request_openai(model: OpenAIModel) -> CharacterResponse:
    character_request = CharacterRequest(
        gender=Gender.MALE,
        age=25,
        additional_instructions="このキャラクターは冒険好きで、好奇心旺盛です。",
    )
    prompt = make_prompt(character_request)
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,  # Template-generated messages
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed

async def request_gemini(model: GeminiModel) -> CharacterResponse:
    character_request = CharacterRequest(
        gender=Gender.FEMALE,
        age=30,
        additional_instructions="このキャラクターは知的で、洞察力に優れています。",
    )
    prompt = make_prompt(character_request)
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,
            temperature=2.0,
        ),
    )
    return result.parsed
```

**ポイント**:
- テンプレート生成されたプロンプトをそのままAPI呼び出しに使用
- プロンプトロジックはテンプレートに集約され、コードは簡潔

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0 (CLIインターフェース)
  - google-genai>=1.45.0 (Gemini API)
  - jinja2>=3.1.6 (テンプレートエンジン)
  - openai>=2.4.0 (OpenAI API)
  - pydantic>=2.12.2 (データモデル)
  - python-dotenv>=1.1.1 (環境変数管理)
  - pyyaml>=6.0.3 (YAMLパーサー)

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# または make コマンド
make install

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用（デフォルト）
uv run python -m src.main --llm-provider gemini --model gemini-2.0-flash-exp

# OpenAI APIを使用
uv run python -m src.main --llm-provider openai --model gpt-4o

# Makefileを使用
make run-gemini
make run-openai
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp openai -m gpt-4o-mini -od ./custom_output

# 短縮オプション
uv run python -m src.main -lp gemini -m gemini-2.0-flash-exp -od ./my_characters
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [openai|gemini]
                                  The LLM provider to use.  [required]
  -m, --model TEXT                The model to use for the request.  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### Makefileコマンド一覧

```bash
# ヘルプを表示
make help

# テストを実行
make test               # 全テスト実行
make pytest             # ユニットテストのみ
make pytest-cov         # カバレッジレポート付き
make test-templates     # テンプレートテストのみ

# コード品質チェック
make lint               # リンター実行
make fmt                # コードフォーマット
make fix                # リントとフォーマットを両方実行
make mypy               # 型チェック

# LLM実行
make run-openai         # OpenAI APIで実行
make run-gemini         # Gemini APIで実行
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/openai_c5339cd3f7b240b3b6e7b113eeacd216.json`

```json
{
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 25,
    "personalities": [
        {
            "short_personality": "冒険心旺盛",
            "description": "新しい場所や経験を求め、常に未知への挑戦を楽しむ。好奇心が強く、リスクを恐れず行動する。"
        },
        {
            "short_personality": "社交的",
            "description": "初対面の人とも打ち解けやすく、会話を楽しむ。多様なバックグラウンドを持つ人々との交流を大切にする。"
        },
        {
            "short_personality": "楽観的",
            "description": "困難な状況でもポジティブな側面を見つけ、前向きに対処する。失敗を学びの機会と捉える。"
        }
    ]
}
```

**実行ログ例**:
```
[2025-01-18 10:30:45] [INFO] [__main__] [main.py:53] [main] LLM provider: openai
Model: gpt-4o
Output directory: outputs
[2025-01-18 10:30:47] [INFO] [__main__] [main.py:74] [main] File saved to outputs/openai_c5339cd3f7b240b3b6e7b113eeacd216.json
```

### テスト方法

このプロジェクトには包括的なテストスイートが含まれています。

#### 1. すべてのテストを実行

```bash
make test
# または
uv run pytest
```

期待される出力：
```
tests/test_prompt.py ....                                    [ 30%]
tests/test_template_engine.py .............................. [100%]

====== 32 passed in 0.45s ======
```

#### 2. カバレッジレポート付きテスト

```bash
make pytest-cov
```

期待される出力：
```
---------- coverage: platform darwin, python 3.13.2 ----------
Name                                Stmts   Miss  Cover   Missing
-----------------------------------------------------------------
src/__init__.py                         0      0   100%
src/service/template_engine.py         47      0   100%
src/prompt/prompt.py                   15      0   100%
-----------------------------------------------------------------
TOTAL                                  62      0   100%

HTML coverage report generated at htmlcov/index.html
```

#### 3. 特定のテストのみ実行

```bash
# TemplateEngineのテストのみ
uv run pytest tests/test_template_engine.py -v

# プロンプト生成のテストのみ
uv run pytest tests/test_prompt.py -v

# または Makefile
make pytest-unit
```

#### 4. テンプレートの手動テスト

```bash
# 基本的なテンプレートテスト
make test-basic

# すべてのテンプレート組み合わせをテスト
make test-all
```

#### 5. 失敗したテストのみ再実行

```bash
make pytest-failed
# または
uv run pytest --lf
```

#### テストの構成

テストスイートは以下のカテゴリで構成されています：

1. **TemplateEngineテスト** (`tests/test_template_engine.py`):
   - 初期化とディレクトリ検証
   - 変数抽出機能
   - 変数バリデーション
   - テンプレートレンダリング
   - メッセージフォーマット変換
   - エッジケース（特殊文字、None値、ネストされたデータ構造など）

2. **プロンプト生成テスト** (`tests/test_prompt.py`):
   - make_prompt()関数の動作検証
   - レンダリングされたメッセージ形式の確認
   - 変数注入の正確性

3. **フィクスチャ** (`tests/conftest.py`):
   - 一時テンプレートディレクトリの作成
   - サンプルテンプレートファイルの生成
   - 各テスト間での独立性確保

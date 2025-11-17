# Chapter 2 Section 1: 構造化出力を用いたLLM基本実装

## 概要

このプロジェクトは、**構造化出力（Structured Outputs）** を用いたLLM（大規模言語モデル）の基本実装を示すサンプルコードです。OpenAI GPTシリーズ（GPT-4o、GPT-5など）、Google Gemini 2.5シリーズ、Anthropic Claudeシリーズの3つのプロバイダーに対応し、複数のモデルから選択して利用できます。Pydanticモデルを活用して型安全なLLM応答を実現します。

フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、構造化出力の実践的な実装方法を学ぶことができます。

## 機能

- **構造化出力**: PydanticモデルをAPI応答形式として直接利用
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic Claudeの3つのAPIをサポート
- **モデル選択**: 各プロバイダーで複数のモデルから選択可能
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
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   └── prompt/
│       ├── __init__.py
│       └── prompt.py            # プロンプト生成ロジック
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────┐
│         CLI Layer (main.py)             │
│     - コマンドライン引数解析             │
│     - 出力ディレクトリ管理               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Business Logic Layer               │
│  - プロンプト生成 (prompt.py)           │
│  - LLMクライアント管理 (llm_client.py)  │
│  - データモデル (model.py)              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - 外部API (OpenAI, Gemini)             │
└─────────────────────────────────────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/model.py`)

Pydanticを使用して、厳密に型付けされたデータモデルを定義します：

```python
class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"

class CharacterPersonality(BaseModel):
    short_personality: str
    description: str

class CharacterResponse(BaseModel):
    first_name: str
    last_name: str
    gender: Gender
    age: int  # 0-100
    personalities: list[CharacterPersonality]  # 3つの性格特性
```

**ポイント**:
- `frozen=True`により不変オブジェクトを保証
- `validate_assignment=True`で代入時のバリデーションを有効化
- Fieldディスクリプタで詳細な制約を定義（`ge=0, le=100`など）

#### 2. LLMクライアント (`src/client/llm_client.py`)

OpenAI、Gemini、Anthropicの3つのクライアントを初期化し、利用可能なモデルを定義します：

```python
class LLMProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"

class OpenAIModel(StrEnum):
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

class AnthropicModel(StrEnum):
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4_1 = "claude-opus-4-1"

google_genai_client = genai.Client(api_key=config.gemini_api_key)
openai_client = AsyncOpenAI(api_key=config.openai_api_key)
anthropic_client = AsyncAnthropic(api_key=config.anthropic_api_key)
```

**ポイント**:
- 列挙型（`StrEnum`）でプロバイダーとモデルを型安全に管理
- 設定情報から安全にAPIキーを取得
- 各プロバイダーで利用可能なモデルを明示的に定義

**利用可能なモデル**:

OpenAI:
- `gpt-5`, `gpt-5-mini`, `gpt-5-nano`
- `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- `gpt-4o`, `gpt-4o-mini`

Gemini:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

Anthropic:
- `claude-sonnet-4-5`
- `claude-opus-4-1`

#### 3. プロンプト生成 (`src/prompt/prompt.py`)

スキーマ情報を埋め込んだプロンプトを動的に生成します：

```python
def make_prompt() -> list:
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return [
        {
            "role": "system",
            "content": f"""あなたは創造的なキャラクタージェネレーターです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}
..."""
        },
        ...
    ]
```

**ポイント**:
- モデルから自動的にスキーマ情報を抽出
- システムプロンプトにスキーマを埋め込むことで、出力の一貫性を確保

#### 4. API呼び出し (`src/main.py`)

##### OpenAI実装

```python
async def request_openai(model: OpenAIModel) -> CharacterResponse:
    prompt = make_prompt()
    result = await openai_client.beta.chat.completions.parse(
        model=model,  # モデルをパラメータとして受け取る
        messages=prompt,
        response_format=CharacterResponse,  # Pydanticモデルを直接指定
        temperature=1.0,
    )
    return result.choices[0].message.parsed
```

**特徴**:
- `beta.chat.completions.parse()`で構造化出力をサポート
- `response_format`パラメータにPydanticモデルを直接渡せる
- 返り値は自動的にPydanticモデルにパースされる
- モデルはCLI引数から動的に選択可能

##### Gemini実装

```python
async def request_gemini(model: GeminiModel) -> CharacterResponse:
    system_prompt, user_prompt = make_gemini_prompt()
    result = await google_genai_client.aio.models.generate_content(
        model=model,  # モデルをパラメータとして受け取る
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=CharacterResponse,  # Pydanticモデルを指定
        ),
    )
    return result.parsed
```

**特徴**:
- `response_schema`でPydanticモデルを指定
- `response_mime_type="application/json"`でJSON形式を強制
- system_instructionとcontentsを分離して指定
- モデルはCLI引数から動的に選択可能

##### Anthropic実装

```python
async def request_anthropic(model: AnthropicModel) -> CharacterResponse:
    prompt = make_anthropic_prompt()
    result = await anthropic_client.beta.messages.parse(
        model=model,  # モデルをパラメータとして受け取る
        max_tokens=1024,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=CharacterResponse,  # Pydanticモデルを指定
    )
    return result.parsed_output
```

**特徴**:
- `beta.messages.parse()`で構造化出力をサポート
- `output_format`パラメータにPydanticモデルを直接渡せる
- `betas`パラメータで構造化出力のベータ機能を有効化
- 返り値は自動的にPydanticモデルにパースされる
- モデルはCLI引数から動的に選択可能

#### 5. 設定管理 (`src/config.py`)

環境変数からAPIキーを安全に読み込みます：

```python
class Config(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    if os.path.exists(".envrc"):
        load_dotenv(".envrc")

    gemini_api_key: Secret[str] = Field(default=os.environ["GEMINI_API_KEY"])
    openai_api_key: Secret[str] = Field(default=os.environ["OPENAI_API_KEY"])
    anthropic_api_key: Secret[str] = Field(default=os.environ["ANTHROPIC_API_KEY"])
```

**ポイント**:
- `Secret[str]`型でAPIキーを保護（ログ出力時に自動マスキング）
- Pydanticの検証機能で環境変数の存在をチェック

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
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用（プロバイダーとモデルを指定）
uv run python -m src.main --llm-provider GEMINI --model GEMINI_2_5_FLASH --output-directory ./custom_output

# OpenAI APIを使用
uv run python -m src.main --llm-provider OPENAI --model GPT_5_MINI --output-directory ./custom_output

# Anthropic APIを使用
uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_SONNET_4_5 --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -lp openai -m gpt-4o -od ./custom_output
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
$ uv run python -m src.main --help                                       
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5|GPT_5_MINI|GPT_5_NANO|GPT_4_1|GPT_4_1_MINI|GPT_4_1_NANO|GPT_4O|GPT_4O_MINI|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_4_5|CLAUDE_OPUS_4_1]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/gemini_a1b2c3d4e5f6.json`

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

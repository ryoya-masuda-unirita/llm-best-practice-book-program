# Chapter and Section number with title: e.g. `Chapter 2 Section 1: 構造化出力を用いたLLM基本実装`

## 概要

## 機能

## プロジェクト構成

### ディレクトリ構成

### アーキテクチャ

### 実装の詳細

## 使い方

### 環境構成

### セットアップ

### 使用方法、実行方法

### 出力例

### テスト方法


<Example>
# Chapter 2 Section 1: 構造化出力を用いたLLM基本実装

## 概要

このプロジェクトは、**構造化出力（Structured Outputs）** を用いたLLM（大規模言語モデル）の基本実装を示すサンプルコードです。OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応し、Pydanticモデルを活用して型安全なLLM応答を実現します。

フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、構造化出力の実践的な実装方法を学ぶことができます。

## 機能

- **構造化出力**: PydanticモデルをAPI応答形式として直接利用
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
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
│   ├── llms.py                  # 互換性レイヤー
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

OpenAIとGeminiの両方のクライアントを初期化します：

```python
class LLMProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"

google_genai_client = genai.Client(api_key=config.gemini_api_key)
openai_client = AsyncOpenAI(api_key=config.openai_api_key)
```

**ポイント**:
- 列挙型（`StrEnum`）でプロバイダーを型安全に管理
- 設定情報から安全にAPIキーを取得

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
async def request_openai() -> CharacterResponse:
    prompt = make_prompt()
    result = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
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

##### Gemini実装

```python
async def request_gemini() -> CharacterResponse:
    prompt = make_prompt()
    result = await google_genai_client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,  # Pydanticモデルを指定
            temperature=2.0,
        ),
    )
    return result.parsed
```

**特徴**:
- `response_schema`でPydanticモデルを指定
- `response_mime_type="application/json"`でJSON形式を強制
- system_instructionとcontentsを分離して指定

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
```

**ポイント**:
- `Secret[str]`型でAPIキーを保護（ログ出力時に自動マスキング）
- Pydanticの検証機能で環境変数の存在をチェック

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
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
# Gemini APIを使用（デフォルト）
uv run python -m src.main

# OpenAI APIを使用
uv run python -m src.main --llm-provider openai

# 短縮オプション
uv run python -m src.main -lp openai
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -od ./my_characters
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
                                  The LLM provider to use.
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/gemini_a1b2c3d4e5f6.json`

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
[2025-10-17 10:30:45] [INFO] [__main__] [main.py:73] [main] LLM provider: gemini
Output directory: outputs
[2025-10-17 10:30:47] [INFO] [__main__] [main.py:88] [main] File saved to outputs/gemini_a1b2c3d4e5f6.json
```

### テスト方法

現在、このセクションにはユニットテストは含まれていません。手動テストは以下の方法で行います：

#### 1. OpenAI APIのテスト

```bash
uv run python -m src.main -lp openai -od test_outputs
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `openai_XXXXXXXX.json`形式のファイルが生成される
- JSONファイルが`CharacterResponse`スキーマに準拠している

#### 2. Gemini APIのテスト

```bash
uv run python -m src.main -lp gemini -od test_outputs
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `gemini_XXXXXXXX.json`形式のファイルが生成される
- JSONファイルが`CharacterResponse`スキーマに準拠している

#### 3. バリデーションの確認

生成されたJSONファイルが正しい構造を持っているか確認：

```bash
# jqを使用してJSONを検証
cat test_outputs/gemini_*.json | jq .

# Pythonで読み込みテスト
python -c "
from src.model.model import CharacterResponse
import json

with open('test_outputs/gemini_*.json') as f:
    data = json.load(f)
    character = CharacterResponse(**data)
    print(f'Valid! {character.first_name} {character.last_name}')
"
```

</Example>

# Chapter 2 Section 10: LLM APIのためのアダプターとファクトリーパターン

## 概要

このプロジェクトは、**AdapterパターンとFactoryパターン**を用いた複数LLMプロバイダの統一的な管理手法を示すサンプルコードです。OpenAIとGoogle Geminiの両方に対応し、各プロバイダのAPI仕様の違いを吸収しながら、共通のインターフェースを通じて柔軟にLLMを切り替えられる設計を実現しています。

フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、ベンダーロックインを回避し、保守性と拡張性を両立させるプラクティスを学ぶことができます。

## 機能

- **Adapterパターン**: 各LLMプロバイダの差異を吸収する統一インターフェース
- **Factoryパターン**: プロバイダとモデルに基づいたクライアント生成の一元管理
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **プロバイダー切り替え**: コマンドライン引数で簡単にプロバイダー/モデルを変更可能
- **構造化出力**: Pydanticモデルを活用した型安全なLLM応答
- **包括的なテスト**: 43個のユニットテストによる品質保証
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_10/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/                  # LLMクライアント関連
│   │   ├── __init__.py
│   │   ├── base.py              # 抽象基底クラス（LLMClient）
│   │   ├── adapters.py          # 具体的なAdapter実装
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
│   ├── test_adapters.py         # Adapterのテスト（17テスト）
│   └── test_factory.py          # Factoryのテスト（26テスト）
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

### 実装の詳細

#### 1. 抽象基底クラス (`src/client/base.py`)

すべてのLLMプロバイダが実装すべき共通インターフェースを定義します：

```python
class LLMClient(ABC):
    """LLMクライアントの共通インターフェース"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        """チャット完了を生成"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を取得"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """モデル名を取得"""
        pass
```

**ポイント**:
- すべてのプロバイダーで統一されたメソッドシグネチャ
- Pydantic BaseModelによる型安全な戻り値
- 非同期処理（async/await）をサポート

#### 2. Adapter実装 (`src/client/adapters.py`)

各プロバイダー固有のAPIを共通インターフェースに変換します：

##### OpenAIAdapter

```python
class OpenAIAdapter(LLMClient):
    """OpenAI API用のAdapter"""

    def __init__(self, model: str):
        self._client = AsyncOpenAI(api_key=config.openai_api_key)
        self._model = model

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        result = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=messages,
            response_format=response_format,
            **kwargs,
        )
        return result.choices[0].message.parsed
```

##### GeminiAdapter

```python
class GeminiAdapter(LLMClient):
    """Google Gemini API用のAdapter"""

    def __init__(self, model: str):
        self._client = genai.Client(api_key=config.gemini_api_key)
        self._model = model

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        # システムメッセージとユーザーメッセージを分離
        system_instruction = None
        user_content = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]

        # Gemini固有の設定
        config = GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=response_format,
        )

        result = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_content,
            config=config,
        )
        return result.parsed
```

**ポイント**:
- 各プロバイダーのAPI仕様の違いをAdapter内で吸収
- 共通インターフェースを通じて同じ方法で呼び出し可能
- プロバイダー固有の設定は各Adapter内で処理

#### 3. Factory実装 (`src/client/factory.py`)

プロバイダーとモデルに基づいて適切なAdapterインスタンスを生成します：

```python
class LLMClientFactory:
    """LLMクライアントを生成するFactory"""

    # プロバイダーとサポートモデルのマッピング
    PROVIDER_MODELS = {
        LLMProvider.OPENAI: OpenAIModel.list_str(),
        LLMProvider.GEMINI: GeminiModel.list_str(),
    }

    @staticmethod
    def create_client(
        provider: LLMProvider,
        model: OpenAIModel | GeminiModel,
    ) -> LLMClient:
        """プロバイダーとモデルに基づいてクライアントを生成"""
        provider_lower = provider.lower()

        # プロバイダーとモデルの組み合わせを検証
        if not LLMClientFactory.is_valid_combination(provider_lower, model):
            raise ValueError(f"Invalid combination: {provider} and {model}")

        # 適切なAdapterを生成
        if provider_lower == LLMProvider.OPENAI:
            return OpenAIAdapter(model=model)
        elif provider_lower == LLMProvider.GEMINI:
            return GeminiAdapter(model=model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @staticmethod
    def is_valid_combination(provider: str, model: str) -> bool:
        """プロバイダーとモデルの組み合わせが有効かチェック"""
        provider_lower = provider.lower()
        if provider_lower not in LLMClientFactory.PROVIDER_MODELS:
            return False
        return model in LLMClientFactory.PROVIDER_MODELS[provider_lower]
```

**ポイント**:
- プロバイダーとモデルの組み合わせを事前検証
- クライアント生成ロジックを一元管理
- ビジネスロジックから具体的なAdapter実装を隠蔽

#### 4. サービス層 (`src/service/request_llm.py`)

Factoryを使用して統一されたLLMリクエスト処理を提供します：

```python
async def request_llm(
    provider: LLMProvider,
    model: OpenAIModel | GeminiModel,
) -> CharacterResponse:
    """FactoryパターンでLLMリクエストを実行"""

    # Factoryを使用してクライアントを生成
    client: LLMClient = LLMClientFactory.create_client(
        provider=provider,
        model=model
    )

    # 共通インターフェースを通じてリクエスト
    result = await client.chat(
        messages=make_prompt(),
        response_format=CharacterResponse,
    )

    return result
```

**ポイント**:
- プロバイダーに依存しない統一されたインターフェース
- どのプロバイダーでも同じコードで処理可能
- 新しいプロバイダーの追加が容易

#### 5. データモデル (`src/model/model.py`)

Pydanticを使用して厳密に型付けされたデータモデルを定義します：

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

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
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
uv run python -m src.main -lp openai -m gpt-4o
uv run python -m src.main -lp openai -m gpt-4o-mini

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
  -lp, --llm-provider [openai|gemini]
                                  The LLM provider to use (openai or gemini).
  -m, --model [gpt-4o|gpt-4o-mini|gemini-2.5-pro|gemini-2.5-flash|...]
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

### テスト方法

このプロジェクトには、AdapterとFactoryパターンの実装を検証する包括的なテストスイートが含まれています。

#### テストの実行

```bash
# すべてのテストを実行
uv run python -m pytest tests/ -v

# 特定のテストファイルを実行
uv run python -m pytest tests/test_adapters.py -v
uv run python -m pytest tests/test_factory.py -v

# カバレッジレポート付きで実行
uv run python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

#### テストの構成

**1. Adapterテスト (`tests/test_adapters.py`) - 17テスト**

- OpenAIAdapterのテスト
  - インターフェース実装の検証
  - 初期化とモデル設定
  - チャット完了の成功ケース
  - 追加パラメータの処理
  - APIエラーハンドリング

- GeminiAdapterのテスト
  - インターフェース実装の検証
  - 初期化とモデル設定
  - システムメッセージ処理
  - マルチメッセージ処理
  - APIエラーハンドリング

- Adapter比較テスト
  - 両Adapterの一貫性検証
  - 共通インターフェース確認

**2. Factoryテスト (`tests/test_factory.py`) - 26テスト**

- サポートプロバイダー/モデルの取得
- プロバイダー・モデル組み合わせの検証
- クライアント生成の正常系
- エラーハンドリング（不正なプロバイダー、モデル）
- 大文字小文字の区別なし検証
- 統合テスト（実際のAdapter生成）
- PROVIDER_MODELSマッピングの検証

#### テスト実行例

```bash
$ uv run python -m pytest tests/ -v

============================= test session starts ==============================
platform darwin -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
collected 43 items

tests/test_adapters.py::TestOpenAIAdapter::test_implements_llm_client_interface PASSED
tests/test_adapters.py::TestOpenAIAdapter::test_initialization PASSED
tests/test_adapters.py::TestOpenAIAdapter::test_get_provider_name PASSED
tests/test_adapters.py::TestOpenAIAdapter::test_get_model_name PASSED
tests/test_adapters.py::TestOpenAIAdapter::test_chat_success PASSED
...
tests/test_factory.py::TestLLMClientFactory::test_get_supported_providers PASSED
tests/test_factory.py::TestLLMClientFactory::test_create_client_openai PASSED
...

============================== 43 passed in 4.35s ==============================
```

#### 手動テスト

実際のAPIを使用した統合テストも可能です：

```bash
# OpenAI APIのテスト
uv run python -m src.main -lp openai -m gpt-4o -od test_outputs

# Gemini APIのテスト
uv run python -m src.main -lp gemini -m gemini-2.5-flash -od test_outputs

# 生成されたJSONの検証
cat test_outputs/openai_*.json | jq .

# Pythonで読み込みテスト
python -c "
from src.model.model import CharacterResponse
import json
import glob

files = glob.glob('test_outputs/*.json')
for file_path in files:
    with open(file_path) as f:
        data = json.load(f)
        character = CharacterResponse(**data)
        print(f'Valid! {character.first_name} {character.last_name}, {character.age} years old')
"
```

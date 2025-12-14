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
        result = await self._client.responses.parse(
            model=self._model,
            input=messages,
            text_format=response_format,
            **kwargs,
        )
        return result.output_parsed

    async def aclose(self) -> None:
        await self._client.close()
```

##### AnthropicAdapter

```python
class AnthropicAdapter(LLMClient):
    """Anthropic Claude API用のAdapter"""

    def __init__(self, model: str):
        self._client = AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = model

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        result = await self._client.beta.messages.parse(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", 1024),
            betas=["structured-outputs-2025-11-13"],
            messages=messages,
            output_format=response_format,
            **{k: v for k, v in kwargs.items() if k != "max_tokens"},
        )
        return result.parsed_output

    async def aclose(self) -> None:
        await self._client.close()
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
        messages: list[dict[str, str]] | tuple[str, str],
        response_format: type,
        **kwargs: Any,
    ) -> BaseModel:
        # システムメッセージとユーザーメッセージを分離
        if isinstance(messages, tuple):
            system_instruction, user_content = messages
        else:
            system_instruction = None
            user_content = None
            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    user_content = msg["content"]

        # Gemini固有の設定
        config = GenerateContentConfig(response_mime_type="application/json")
        if system_instruction:
            config.system_instruction = system_instruction
        if response_format:
            config.response_schema = response_format

        result = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_content,
            config=config,
            **kwargs,
        )
        return result.parsed

    async def aclose(self) -> None:
        await self._client.aio.aclose()
```

**ポイント**:
- 各プロバイダーのAPI仕様の違いをAdapter内で吸収
- 共通インターフェースを通じて同じ方法で呼び出し可能
- プロバイダー固有の設定は各Adapter内で処理
- 各Adapterに`aclose()`メソッドを実装し、適切なリソース解放を実現
- OpenAIは最新の`responses.parse()`API、Anthropicはbeta版の`messages.parse()`、Geminiは`generate_content()`を使用

#### 3. Factory実装 (`src/client/factory.py`)

プロバイダーとモデルに基づいて適切なAdapterインスタンスを生成します：

```python
class LLMClientFactory:
    """LLMクライアントを生成するFactory"""

    # プロバイダーとサポートモデルのマッピング
    PROVIDER_MODELS = {
        LLMProvider.OPENAI: OpenAIModel.list_str(),
        LLMProvider.GEMINI: GeminiModel.list_str(),
        LLMProvider.ANTHROPIC: AnthropicModel.list_str(),
    }

    @staticmethod
    def create_client(
        provider: LLMProvider,
        model: OpenAIModel | GeminiModel | AnthropicModel,
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
        elif provider_lower == LLMProvider.ANTHROPIC:
            return AnthropicAdapter(model=model)
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
    client: LLMClient,
    model: str,
) -> CharacterResponse:
    """統一されたインターフェースでLLMリクエストを実行"""

    # プロンプトを生成
    prompt = make_prompt()

    # 共通インターフェースを通じてリクエスト
    result = await client.chat(
        messages=prompt,
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

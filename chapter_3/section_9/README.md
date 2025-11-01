# Chapter 3 Section 9: LLM SDKの薄いラッパーライブラリ

## 概要

このプロジェクトは、**LLM SDKの薄いラッパーライブラリ**の実装例を示すサンプルコードです。OpenAI APIとGoogle Gemini APIの公式SDKをラップし、透過的なログ記録、トークン使用量の追跡、処理時間の計測といった横断的関心事を一元化します。

公式SDKのインターフェースを可能な限り維持しながら、全てのAPI呼び出しを自動的にロギングする仕組みを実装しています。これにより、アプリケーションコードはビジネスロジックに集中でき、LLM連携部分の保守性、拡張性、観測可能性を飛躍的に向上させることができます。

## 機能

- **透過的なラッパー実装**: 公式SDKのインターフェースを維持しつつ、ログ機能を追加
- **自動ログ記録**: 全てのAPI呼び出しのリクエスト/レスポンスをJSON形式で保存
- **トークン使用量追跡**: プロンプトトークン数、補完トークン数、合計トークン数を記録
- **処理時間計測**: 各API呼び出しの実行時間をミリ秒単位で記録
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **非同期処理対応**: 同期/非同期の両方のクライアントをラップ
- **`__getattr__`による委譲**: ラップしていないメソッドは自動的に元のSDKに委譲
- **構造化出力**: Pydanticモデルを使用した型安全なLLM応答

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_9/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（APIキー、ログディレクトリ）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # ラッパークライアントの初期化
│   │   └── wrapper_client.py    # ラッパークラスの実装
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── request_llm.py       # LLMリクエスト処理
├── tests/
│   ├── __init__.py
│   └── test_wrapper_client.py   # ラッパーのテストコード
├── outputs/                      # 生成結果の保存先（自動作成）
├── usage_logs/                   # 使用ログの保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── .gitignore                    # Git除外設定
├── Makefile                      # 開発用コマンド
├── pyproject.toml                # プロジェクト依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト詳細ドキュメント
```

### アーキテクチャ

このプロジェクトは、ラッパーパターンを採用した3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────┐
│         CLI Layer (main.py)                     │
│     - コマンドライン引数解析                    │
│     - プロバイダー選択とモデル指定              │
│     - 出力ディレクトリ管理                      │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Business Logic Layer                       │
│  - プロンプト生成 (prompt.py)                   │
│  - LLMリクエスト処理 (request_llm.py)           │
│  - データモデル (model.py)                      │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Wrapper Layer (wrapper_client.py)          │
│  - OpenAIWrapperClient                          │
│  - AsyncOpenAIWrapperClient                     │
│  - GenAIWrapperClient                           │
│  - 自動ログ記録とトークン追跡                   │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Infrastructure Layer                       │
│  - 公式SDK (OpenAI, Google Gemini)              │
│  - 設定管理 (config.py)                         │
│  - ログ管理 (logger.py)                         │
└─────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. ラッパークライアントの設計原則 (`src/client/wrapper_client.py`)

このプロジェクトの中核となるラッパーライブラリは、以下の設計原則に従っています：

**原則1: 薄く保つ**
公式SDKのインターフェースを極力維持し、過剰な抽象化を避けます。

**原則2: 透過的な動作**
`__getattr__`メソッドを使用して、ラップしていないメソッド呼び出しを自動的に元のSDKに委譲します。

```python
def __getattr__(self, name):
    """Delegate other attributes to the original object."""
    return getattr(self._chat_completions, name)
```

**原則3: 横断的関心事の集約**
ログ記録、トークン追跡、処理時間計測といった共通処理をラッパーに集約します。

#### 2. OpenAIラッパーの実装

##### 同期版ラッパー (`OpenAIWrapperClient`)

```python
class OpenAIWrapperClient(OpenAI):
    """Thin wrapper for OpenAI client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._chat_wrapper = None
        self._responses_wrapper = None

    @property
    def chat(self):
        """Wrap chat object to add logging."""
        if self._chat_wrapper is None:
            self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=False)
        return self._chat_wrapper

    @property
    def responses(self):
        """Wrap responses object to add logging."""
        if self._responses_wrapper is None:
            self._responses_wrapper = ResponsesWrapper(super().responses, self._log_dir)
        return self._responses_wrapper
```

**ポイント**:
- `OpenAI`クラスを継承し、公式SDKのすべての機能を保持
- `chat`と`responses`プロパティのみをオーバーライドしてログ機能を追加
- 遅延初期化により、使用されない機能のオーバーヘッドを削減

##### 非同期版ラッパー (`AsyncOpenAIWrapperClient`)

```python
class AsyncOpenAIWrapperClient(AsyncOpenAI):
    """Thin wrapper for AsyncOpenAI client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._chat_wrapper = None
        self._responses_wrapper = None

    @property
    def chat(self):
        """Wrap chat object to add logging."""
        if self._chat_wrapper is None:
            self._chat_wrapper = ChatWrapper(super().chat, self._log_dir, is_async=True)
        return self._chat_wrapper

    @property
    def responses(self):
        """Wrap responses object to add logging."""
        if self._responses_wrapper is None:
            self._responses_wrapper = AsyncResponsesWrapper(super().responses, self._log_dir)
        return self._responses_wrapper
```

#### 3. ログ記録の実装

各メソッドラッパーは、API呼び出しの前後で処理時間を計測し、詳細な情報をJSON形式でファイルに保存します：

```python
def _log_usage(self, method: str, args: tuple, kwargs: dict, response: Any, start_time: datetime):
    """Log usage information to JSON file."""
    end_time = datetime.now()
    duration_ms = (end_time - start_time).total_seconds() * 1000

    log_data = {
        "timestamp": start_time.isoformat(),
        "method": method,
        "duration_ms": duration_ms,
        "request": {
            "model": kwargs.get("model"),
            "messages": kwargs.get("messages"),
            "temperature": kwargs.get("temperature"),
            # ... その他のパラメータ
        },
        "response": {
            "id": getattr(response, "id", None),
            "model": getattr(response, "model", None),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        },
    }

    log_filename = self._log_dir / f"openai_{start_time.strftime('%Y%m%d_%H%M%S_%f')}.json"
    with open(log_filename, "w") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
```

**ログの内容**:
- タイムスタンプ
- 呼び出されたメソッド名
- 処理時間（ミリ秒）
- リクエストパラメータ（モデル、プロンプト、温度など）
- レスポンス情報（ID、生成テキスト、トークン使用量）

#### 4. Google Geminiラッパーの実装

```python
class GenAIWrapperClient(genai.Client):
    """Thin wrapper for genai.Client with usage logging."""

    def __init__(self, *args, log_dir: str = config.usage_log_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_dir = log_dir
        self._models_wrapper = None
        self._aio_wrapper = None

    @property
    def models(self):
        """Wrap models object to add logging."""
        if self._models_wrapper is None:
            self._models_wrapper = ModelsWrapper(super().models, self._log_dir)
        return self._models_wrapper

    @property
    def aio(self):
        """Wrap aio object to add logging for async methods."""
        if self._aio_wrapper is None:
            self._aio_wrapper = AioWrapper(super().aio, self._log_dir)
        return self._aio_wrapper
```

**特徴**:
- `genai.Client`を継承し、OpenAIと同様のパターンでラップ
- 同期版（`models`）と非同期版（`aio.models`）の両方に対応
- プロバイダー固有のレスポンス構造（`usage_metadata`など）を適切に処理

#### 5. クライアントの初期化 (`src/client/llm_client.py`)

```python
from src.client.wrapper_client import AsyncOpenAIWrapperClient, GenAIWrapperClient
from src.config import config

openai_client = AsyncOpenAIWrapperClient(api_key=config.openai_api_key)
google_genai_client = GenAIWrapperClient(api_key=config.google_api_key)
```

**ポイント**:
- ラッパークライアントを公式SDKと同じ方法で初期化
- アプリケーションコードからは、公式SDKを直接使用する場合と同じインターフェースで利用可能
- APIキーは設定ファイルから安全に取得

#### 6. 設定管理 (`src/config.py`)

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

    google_api_key: Secret[str] = Field(
        default=os.environ.get("GOOGLE_API_KEY", ""),
        description="API key for Google GenAI"
    )
    openai_api_key: Secret[str] = Field(
        default=os.environ.get("OPENAI_API_KEY", ""),
        description="API key for OpenAI"
    )
    usage_log_directory: str = Field(
        default=os.environ.get("USAGE_LOG_DIRECTORY", "usage_logs"),
        description="Directory for logs"
    )
```

**ポイント**:
- `Secret[str]`型でAPIキーを保護（ログ出力時に自動マスキング）
- ログディレクトリを環境変数で設定可能
- Pydanticの検証機能で設定の健全性を確保

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - pytest>=8.4.2
  - pytest-asyncio>=1.2.0
  - pytest-mock>=3.15.1
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
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
uv run python -m src.main --llm-provider gemini --model gemini-2.5-flash

# OpenAI APIを使用
uv run python -m src.main --llm-provider openai --model gpt-4o-mini

# 短縮オプション
uv run python -m src.main -lp openai -m gpt-4o
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp gemini -m gemini-2.5-flash --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -lp openai -m gpt-4o-mini -od ./my_characters
```

#### 利用可能なモデル

**OpenAI**:
- gpt-5
- gpt-5-mini
- gpt-5-nano
- gpt-4.1
- gpt-4.1-mini
- gpt-4.1-nano
- gpt-4o
- gpt-4o-mini

**Google Gemini**:
- gemini-2.5-pro
- gemini-2.5-flash
- gemini-2.5-flash-lite

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

### 出力例

#### 生成されたキャラクター情報

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

#### 使用ログファイル

**ファイル名**: `usage_logs/async_genai_20251101_101739_694420.json`

```json
{
  "timestamp": "2025-11-01T10:17:39.694420",
  "method": "aio.models.generate_content",
  "duration_ms": 4290.696,
  "request": {
    "model": "gemini-2.5-flash",
    "contents": "ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。",
    "config": "GenerateContentConfig(...)",
    "parameters": {}
  },
  "response": {
    "text": "...",
    "candidates": [...],
    "usage_metadata": {
      "prompt_token_count": 156,
      "candidates_token_count": 243,
      "total_token_count": 399
    }
  }
}
```

**ログから得られる情報**:
- **コスト分析**: トークン使用量から費用を算出
- **パフォーマンス分析**: 処理時間の統計情報
- **デバッグ**: エラー発生時の詳細な情報
- **監査**: API使用履歴の完全な記録

#### 実行ログ例

```
[2025-11-01 10:17:39] [INFO] [__main__] [main.py:53] [main] LLM provider: gemini
Model: gemini-2.5-flash
Output directory: outputs
[2025-11-01 10:17:44] [INFO] [__main__] [main.py:74] [main] File saved to outputs/gemini_a1b2c3d4e5f6.json
```

### テスト方法

#### 1. ユニットテストの実行

```bash
# 全てのテストを実行
pytest

# 特定のテストファイルを実行
pytest tests/test_wrapper_client.py

# 詳細な出力を表示
pytest -v

# カバレッジレポートを生成
pytest --cov=src --cov-report=html
```

#### 2. OpenAI APIのテスト

```bash
uv run python -m src.main -lp openai -m gpt-4o-mini -od test_outputs
```

**期待される動作**:
- `test_outputs`ディレクトリが作成される
- `openai_XXXXXXXX.json`形式のファイルが生成される
- `usage_logs`ディレクトリに`async_openai_responses_XXXXXXXX.json`が生成される
- JSONファイルが`CharacterResponse`スキーマに準拠している

#### 3. Gemini APIのテスト

```bash
uv run python -m src.main -lp gemini -m gemini-2.5-flash -od test_outputs
```

**期待される動作**:
- `test_outputs`ディレクトリが作成される
- `gemini_XXXXXXXX.json`形式のファイルが生成される
- `usage_logs`ディレクトリに`async_genai_XXXXXXXX.json`が生成される
- JSONファイルが`CharacterResponse`スキーマに準拠している

#### 4. ログファイルの検証

```bash
# 最新のログファイルを確認
ls -lt usage_logs/ | head -5

# ログファイルの内容を確認（jq使用）
cat usage_logs/async_genai_*.json | jq .

# トークン使用量の集計（jq使用）
cat usage_logs/*.json | jq -s 'map(.response.usage_metadata.total_token_count // .response.usage.total_tokens) | add'
```

#### 5. コード品質チェック

```bash
# リンターの実行
make lint

# フォーマッターの実行
make fmt

# 型チェックの実行
make mypy

# 全てのチェックを実行
make fix && make mypy
```

#### 6. バリデーションの確認

生成されたJSONファイルが正しい構造を持っているか確認：

```bash
# Pythonで読み込みテスト
python -c "
from src.model.model import CharacterResponse
import json
import glob

for file in glob.glob('test_outputs/*.json'):
    with open(file) as f:
        data = json.load(f)
        character = CharacterResponse(**data)
        print(f'Valid! {character.first_name} {character.last_name}')
"
```

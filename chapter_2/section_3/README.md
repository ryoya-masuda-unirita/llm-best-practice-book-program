# Chapter 2 Section 3: LLMリクエストのリジリエンスとフォールバック戦略

## 概要

このプロジェクトは、**本番環境で求められるLLM APIリクエストの復元力（レジリエンス）とフォールバック戦略**を実装したサンプルコードです。プライマリLLMプロバイダーの障害やタイムアウトが発生した場合でも、サービスを継続的に提供するための多段階フォールバックシステムを実現します。

Section 1とSection 2で学んだ基本的なLLM実装をベースに、**プロダクションレディなエラーハンドリング、キャッシング、代替プロバイダー切り替え、テンプレート応答**などの実用的なパターンを追加しています。

フィクションのキャラクター情報生成を通じて、API障害時でも安定したサービス提供を実現する方法を学ぶことができます。

## 機能

### 1. 4段階フォールバックシステム

プライマリプロバイダーの障害時に自動的に代替手段へ切り替える多段階システム：

1. **プライマリプロバイダーリクエスト** - 設定されたタイムアウト内でリクエストを試行
2. **キャッシュルックアップ** - 過去の類似リクエストのキャッシュを検索
3. **代替プロバイダー** - 別のLLMプロバイダー（OpenAI ⇄ Gemini）に自動切り替え
4. **テンプレート応答** - 最終手段として事前定義されたキャラクターデータを返却

### 2. レスポンスキャッシング

- **SHA256ベースのキャッシュキー生成** - プロンプト、モデル、temperatureを元にハッシュ化
- **TTL（Time-To-Live）サポート** - キャッシュの有効期限管理（デフォルト: 1時間）
- **JSONファイルベースストレージ** - `.cache/` ディレクトリに保存
- **期限切れエントリの自動クリーンアップ** - 無効なキャッシュの自動削除

### 3. 設定可能なタイムアウト管理

- **デフォルトタイムアウト**: 10秒（環境変数またはCLIで設定可能）
- **リクエスト毎のタイムアウト上書き** - 柔軟な制御が可能
- **タイムアウト追跡** - 監視用の統計情報を記録

### 4. 統計情報とモニタリング

包括的なメトリクスの追跡：
- 総リクエスト数
- プライマリプロバイダー成功率
- キャッシュヒット率
- 代替プロバイダー使用率
- テンプレートフォールバック回数
- タイムアウトおよびエラーカウント

### 5. デュアルLLMプロバイダーサポート

- **OpenAI**: GPT-4o-miniによる構造化出力
- **Gemini**: Gemini-2.5-flashによるJSONスキーマ検証
- **クロスプロバイダーフォールバック**: OpenAI失敗時にGeminiへ、またはその逆

### 6. その他の機能

- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **詳細なログ出力**: 実行状況とフォールバック戦略の可視化
- **JSON出力**: 生成結果をJSON形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_3/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー、タイムアウト、TTL）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # LLMクライアント初期化（OpenAI/Gemini）
│   │   └── llm_request_wrapper.py  # フォールバックロジックを含むリクエストラッパー
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── cache_manager.py     # TTL付きレスポンスキャッシング
│       ├── fallback_coordinator.py  # フォールバック戦略の統括
│       └── template_response.py # テンプレート応答生成
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytestフィクスチャ
│   ├── test_cache_manager.py    # キャッシュマネージャーのテスト
│   ├── test_fallback_coordinator.py # フォールバックコーディネーターのテスト
│   └── test_template_response.py    # テンプレート応答のテスト
├── .cache/                      # キャッシュストレージ（.gitignore）
├── outputs/                     # 生成結果の保存先（自動作成）
├── .envrc.example               # 環境変数設定のサンプル
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
└── CLAUDE.md                    # プロジェクト状態レポート（英語）
```

### アーキテクチャ

このプロジェクトは、以下の4層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────┐
│         CLI Layer (main.py)                 │
│     - コマンドライン引数解析                 │
│     - 出力ディレクトリ管理                   │
│     - フォールバック有効/無効制御             │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Request Wrapper Layer                  │
│  - リクエストラッパー (llm_request_wrapper)  │
│  - OpenAI/Geminiリクエストの統一I/F         │
│  - 統計情報の管理                            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Fallback Coordination Layer            │
│  - フォールバック統括 (fallback_coordinator)│
│  - タイムアウト管理                          │
│  - 4段階フォールバック戦略実行               │
│  - 統計情報の追跡                            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Service Layer                          │
│  - キャッシュマネージャー (cache_manager)   │
│  - テンプレート生成 (template_response)     │
│  - プロンプト生成 (prompt.py)               │
│  - データモデル (model.py)                  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Infrastructure Layer                   │
│  - 設定管理 (config.py)                     │
│  - ログ管理 (logger.py)                     │
│  - 外部API (OpenAI, Gemini)                 │
│  - ファイルシステム（キャッシュ、出力）      │
└─────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. キャッシュマネージャー (`src/service/cache_manager.py`)

TTLサポートを備えたLLM応答のキャッシング機能を提供します。

**キャッシュキー生成**:
```python
def _generate_cache_key(self, prompt: list, model: str, temperature: float) -> str:
    cache_data = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
    }
    cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(cache_str.encode()).hexdigest()
```

**主要メソッド**:
- `get(prompt, model, temperature)` - キャッシュ済み応答を取得（TTLを考慮）
- `set(prompt, model, temperature, response)` - 応答をキャッシュに保存
- `clear_expired()` - 期限切れキャッシュエントリを削除
- `clear_all()` - すべてのキャッシュエントリを削除

**ポイント**:
- プロンプト、モデル、temperatureの組み合わせでユニークなキーを生成
- キャッシュファイルにタイムスタンプを保存し、TTL経過後は自動的に無効化
- 破損したキャッシュファイルは自動削除

#### 2. フォールバックコーディネーター (`src/service/fallback_coordinator.py`)

多段階フォールバック戦略を統括します。

**フォールバック戦略の列挙型**:
```python
class FallbackStrategy(StrEnum):
    CACHE = "cache"
    ALTERNATIVE_PROVIDER = "alternative_provider"
    TEMPLATE = "template"
```

**フォールバックフロー** (`request_with_fallback` メソッド):
```python
# 1. プライマリプロバイダーでリクエスト試行
try:
    response = await asyncio.wait_for(primary_request_func(), timeout=self.timeout)
    # 成功したらキャッシュに保存
    self.cache_manager.set(prompt, model, temperature, response)
    return response, None, None
except (asyncio.TimeoutError, Exception):
    # 失敗したらフォールバック開始
    pass

# 2. キャッシュをチェック
cached_response = self.cache_manager.get(prompt, model, temperature)
if cached_response:
    return cached_response, FallbackStrategy.CACHE, error_reason

# 3. 代替プロバイダーを試行
response = await asyncio.wait_for(alternative_request_func(), timeout=self.timeout)
return response, FallbackStrategy.ALTERNATIVE_PROVIDER, error_reason

# 4. テンプレート応答を返却（最終手段）
template_response = self.template_generator.generate(reason=error_reason)
return template_response, FallbackStrategy.TEMPLATE, error_reason
```

**統計情報の追跡**:
- 総リクエスト数、プライマリ成功数、キャッシュヒット数などを記録
- `get_stats()` で成功率やフォールバック率を計算
- `log_stats()` でフォーマット済み統計をログ出力

#### 3. テンプレート応答ジェネレーター (`src/service/template_response.py`)

すべてのフォールバック戦略が失敗した場合の最終手段として、事前定義されたキャラクターデータを提供します。

**事前定義テンプレート**:
```python
TEMPLATE_CHARACTERS = [
    {
        "first_name": "太郎",
        "last_name": "山田",
        "gender": Gender.MALE,
        "age": 30,
        "personalities": [
            CharacterPersonality(
                short_personality="誠実",
                description="常に正直で、約束を守る信頼できる人物。困っている人を見過ごせない性格。"
            ),
            # ... 他の性格特性
        ],
    },
    # ... 他のテンプレートキャラクター（計4種類）
]
```

**特徴**:
- 4種類の多様なキャラクタープロファイルを用意
- ランダム選択またはラウンドロビン選択をサポート
- エラー理由に応じたユーザーフレンドリーなメッセージを生成
- サービスが完全に停止することを防ぐ安全網の役割

**フォールバックメッセージ**:
```python
def get_fallback_message(self, reason: str) -> str:
    messages = {
        "timeout": "現在、AIによる応答が遅延しています。代替のキャラクターデータを提供いたします。",
        "error": "AIサービスでエラーが発生しました。代替のキャラクターデータを提供いたします。",
        "api_unavailable": "AIサービスが一時的に利用できません。代替のキャラクターデータを提供いたします。",
        "rate_limit": "リクエスト制限に達しました。代替のキャラクターデータを提供いたします。",
    }
    return messages.get(reason, "現在、標準のAI応答が利用できません。代替のキャラクターデータを提供いたします。")
```

#### 4. LLMリクエストラッパー (`src/client/llm_request_wrapper.py`)

フォールバック機能を統合した高レベルなLLMリクエストインターフェースを提供します。

**OpenAIリクエスト（Geminiフォールバック付き）**:
```python
async def request_openai(self, with_fallback: bool = True) -> tuple[CharacterResponse, Optional[FallbackStrategy], Optional[str]]:
    prompt = make_prompt()
    model = "gpt-4o-mini"
    temperature = 1.0

    async def primary_request():
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=temperature,
        )
        return result.choices[0].message.parsed

    if with_fallback:
        # Geminiを代替プロバイダーとして使用
        async def alternative_request():
            return await self._request_gemini_internal()

        return await self.coordinator.request_with_fallback(
            primary_provider=LLMProvider.OPENAI,
            primary_request_func=primary_request,
            alternative_request_func=alternative_request,
            prompt=prompt,
            model=model,
            temperature=temperature,
        )
    else:
        # フォールバックなしの直接リクエスト
        response = await primary_request()
        return response, None, None
```

**Geminiリクエスト（OpenAIフォールバック付き）**:
同様の構造で、プライマリとしてGeminiを使用し、代替としてOpenAIを使用します。

**ポイント**:
- `with_fallback=False` でフォールバック機能を無効化可能（デバッグ用）
- クロスプロバイダーフォールバックにより高可用性を実現
- 統一されたインターフェースで複雑さを隠蔽

#### 5. 設定管理 (`src/config.py`)

環境変数から設定を読み込み、タイムアウトとキャッシュTTLを管理します。

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

    # タイムアウト設定（秒単位）
    llm_request_timeout: float = Field(
        default=float(os.getenv("LLM_REQUEST_TIMEOUT", "10.0")),
        description="Timeout for LLM API requests in seconds"
    )
    # キャッシュTTL設定（秒単位）
    cache_ttl: int = Field(
        default=int(os.getenv("CACHE_TTL", "3600")),
        description="Cache time-to-live in seconds (default: 1 hour)"
    )
```

**ポイント**:
- `Secret[str]`型でAPIキーを保護（ログ出力時に自動マスキング）
- 環境変数が未設定の場合は適切なデフォルト値を使用
- Pydanticの検証機能で環境変数の存在をチェック

#### 6. メインエントリーポイント (`src/main.py`)

CLIインターフェースを提供し、フォールバック戦略を実行します。

```python
@click.command()
@click.option("--llm-provider", "-lp", type=click.Choice(LLMProvider), default=LLMProvider.GEMINI)
@click.option("--output-directory", "-od", type=click.Path(), default="outputs")
@click.option("--timeout", "-t", type=float, default=None)
@click.option("--disable-fallback", "-df", is_flag=True, default=False)
@async_cmd
async def main(llm_provider, output_directory, timeout, disable_fallback):
    # リクエストラッパーを初期化
    wrapper = LLMRequestWrapper(timeout=timeout)

    # フォールバックの有無でリクエスト実行
    result, strategy, error_reason = await wrapper.request_openai(
        with_fallback=not disable_fallback
    )

    # 結果を保存
    result.save_as_json(file_path)

    # 統計情報をログ出力
    wrapper.log_stats()
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - **コア**:
    - click>=8.3.0 - CLIフレームワーク
    - google-genai>=1.45.0 - Google Gemini APIクライアント
    - openai>=2.4.0 - OpenAI APIクライアント
    - pydantic>=2.12.2 - データ検証とスキーマ
    - python-dotenv>=1.1.1 - 環境変数管理
  - **開発**:
    - pytest>=8.4.2 - テストフレームワーク
    - pytest-asyncio>=1.2.0 - 非同期テストサポート
    - pytest-mock>=3.15.1 - モッキングサポート

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX

# オプション設定（デフォルト値で問題なければ省略可）
LLM_REQUEST_TIMEOUT=10.0    # リクエストタイムアウト（秒）
CACHE_TTL=3600              # キャッシュTTL（秒、デフォルト: 1時間）
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .

# 開発依存関係も含める場合
uv sync --all-extras
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用（デフォルト、フォールバック有効）
uv run python -m src.main

# OpenAI APIを使用（フォールバック有効）
uv run python -m src.main --llm-provider openai

# 短縮オプション
uv run python -m src.main -lp openai
```

#### タイムアウトの設定

```bash
# カスタムタイムアウトを指定（5秒）
uv run python -m src.main --timeout 5

# 短縮オプション
uv run python -m src.main -t 5

# 非常に短いタイムアウト（3秒）でフォールバック動作をテスト
uv run python -m src.main -t 3
```

#### フォールバックの制御

```bash
# フォールバックを無効化（プライマリプロバイダーのみ使用）
uv run python -m src.main --disable-fallback

# 短縮オプション
uv run python -m src.main -df

# デバッグ用: OpenAIのみ、フォールバックなし、短いタイムアウト
uv run python -m src.main -lp openai -df -t 5
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -od ./my_characters
```

#### 複合オプション

```bash
# すべてのオプションを組み合わせ
uv run python -m src.main -lp openai -od ./outputs -t 15 -df

# 本番環境向け設定例（長めのタイムアウト）
uv run python -m src.main -lp gemini -t 30

# 開発/テスト環境向け設定例（短いタイムアウトでフォールバックをテスト）
uv run python -m src.main -lp gemini -t 2
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**ヘルプ出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [openai|gemini]
                                  The LLM provider to use.
  -od, --output-directory PATH    The directory to save output files.
  -t, --timeout FLOAT             Request timeout in seconds (default:
                                  10.0s from config)
  -df, --disable-fallback         Disable fallback mechanisms (use only
                                  primary provider)
  --help                          Show this message and exit.
```

### 出力例

#### 正常実行時（プライマリプロバイダー成功）

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
[2025-10-17 10:30:45] [INFO] [__main__] [main.py:59] [main] LLM provider: gemini
Output directory: outputs
Timeout: 10.0s
Fallback enabled: True
[2025-10-17 10:30:45] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:96] [request_with_fallback] Attempting primary request with gemini (timeout: 10.0s)
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:103] [request_with_fallback] Primary request succeeded with gemini
[2025-10-17 10:30:47] [INFO] [__main__] [main.py:91] [main] File saved to outputs/gemini_a1b2c3d4e5f6.json
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:220] [log_stats] === Fallback Statistics ===
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:221] [log_stats] Total Requests: 1
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:222] [log_stats] Primary Success: 1 (100.0%)
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:226] [log_stats] Cache Hits: 0 (0.0%)
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:230] [log_stats] Alternative Provider: 0
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:233] [log_stats] Template Fallback: 0
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:234] [log_stats] Timeouts: 0
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:235] [log_stats] Errors: 0
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:236] [log_stats] Fallback Rate: 0.0%
[2025-10-17 10:30:47] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:237] [log_stats] ===========================
```

#### フォールバック実行時（キャッシュヒット）

**実行ログ例**:
```
[2025-10-17 10:32:10] [WARNING] [src.service.fallback_coordinator] [fallback_coordinator.py:118] [request_with_fallback] Primary request timed out after 3.0s. Initiating fallback strategies...
[2025-10-17 10:32:10] [INFO] [src.service.cache_manager] [cache_manager.py:95] [get] Cache hit: 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d (age: 120.5s)
[2025-10-17 10:32:10] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:133] [request_with_fallback] Fallback: Using cached response
[2025-10-17 10:32:10] [INFO] [__main__] [main.py:83] [main] Response obtained via fallback strategy: cache
[2025-10-17 10:32:10] [WARNING] [__main__] [main.py:85] [main] Primary provider failed due to: timeout
```

#### 代替プロバイダー使用時

**実行ログ例**:
```
[2025-10-17 10:35:22] [WARNING] [src.service.fallback_coordinator] [fallback_coordinator.py:125] [request_with_fallback] Primary request failed with error: Connection error
[2025-10-17 10:35:22] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:142] [request_with_fallback] Fallback: Attempting alternative provider (timeout: 10.0s)
[2025-10-17 10:35:24] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:149] [request_with_fallback] Fallback: Alternative provider succeeded
[2025-10-17 10:35:24] [INFO] [__main__] [main.py:83] [main] Response obtained via fallback strategy: alternative_provider
[2025-10-17 10:35:24] [WARNING] [__main__] [main.py:85] [main] Primary provider failed due to: error
```

#### テンプレート応答使用時（最終フォールバック）

**ファイル名**: `outputs/gemini_e7f8g9h0i1j2.json`

```json
{
    "first_name": "太郎",
    "last_name": "山田",
    "gender": "male",
    "age": 30,
    "personalities": [
        {
            "short_personality": "誠実",
            "description": "常に正直で、約束を守る信頼できる人物。困っている人を見過ごせない性格。"
        },
        {
            "short_personality": "勤勉",
            "description": "目標に向かって努力を惜しまず、計画的に物事を進めることができる。"
        },
        {
            "short_personality": "思慮深い",
            "description": "行動する前に慎重に考え、状況を分析してから判断を下す。"
        }
    ]
}
```

**実行ログ例**:
```
[2025-10-17 10:40:15] [WARNING] [src.service.fallback_coordinator] [fallback_coordinator.py:118] [request_with_fallback] Primary request timed out after 3.0s. Initiating fallback strategies...
[2025-10-17 10:40:15] [DEBUG] [src.service.cache_manager] [cache_manager.py:73] [get] Cache miss: 5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u
[2025-10-17 10:40:15] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:142] [request_with_fallback] Fallback: Attempting alternative provider (timeout: 3.0s)
[2025-10-17 10:40:18] [WARNING] [src.service.fallback_coordinator] [fallback_coordinator.py:166] [request_with_fallback] Alternative provider timed out after 3.0s
[2025-10-17 10:40:18] [WARNING] [src.service.fallback_coordinator] [fallback_coordinator.py:176] [request_with_fallback] Fallback: All strategies exhausted. Using template response.
[2025-10-17 10:40:18] [INFO] [src.service.template_response] [template_response.py:122] [generate] Generated random template response due to: timeout
[2025-10-17 10:40:18] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:180] [request_with_fallback] Fallback message: 現在、AIによる応答が遅延しています。代替のキャラクターデータを提供いたします。
[2025-10-17 10:40:18] [INFO] [__main__] [main.py:83] [main] Response obtained via fallback strategy: template
```

### テスト方法

#### 単体テストの実行

```bash
# すべてのテストを実行
uv run pytest

# 詳細な出力で実行
uv run pytest -v

# 特定のテストファイルのみ実行
uv run pytest tests/test_cache_manager.py
uv run pytest tests/test_fallback_coordinator.py
uv run pytest tests/test_template_response.py

# 特定のテストケースのみ実行
uv run pytest tests/test_cache_manager.py::test_cache_ttl -v
uv run pytest tests/test_fallback_coordinator.py::test_timeout_fallback -v

# カバレッジレポート付きで実行
uv run pytest --cov=src --cov-report=html
# カバレッジレポートは htmlcov/index.html で確認可能
```

#### 手動テスト

##### 1. 基本動作のテスト

```bash
# OpenAI APIのテスト（フォールバック有効）
uv run python -m src.main -lp openai -od test_outputs

# Gemini APIのテスト（フォールバック有効）
uv run python -m src.main -lp gemini -od test_outputs
```

**期待される動作**:
- `test_outputs`ディレクトリが作成される
- `{provider}_{uuid}.json`形式のファイルが生成される
- JSONファイルが`CharacterResponse`スキーマに準拠している
- 統計情報が表示され、`Primary Success: 1 (100.0%)`となる

##### 2. タイムアウトとフォールバックのテスト

```bash
# 非常に短いタイムアウトでタイムアウト動作を確認
uv run python -m src.main -t 0.1 -od test_outputs

# 同じ設定で2回実行し、キャッシュヒットを確認
uv run python -m src.main -t 0.1 -od test_outputs
uv run python -m src.main -t 0.1 -od test_outputs  # 2回目はキャッシュヒットのはず
```

**期待される動作**:
- 1回目: タイムアウトが発生し、キャッシュミス後に代替プロバイダーまたはテンプレート応答を使用
- 2回目: タイムアウト後にキャッシュヒットし、`Cache Hits: 1`と表示される

##### 3. フォールバック無効化のテスト

```bash
# フォールバックなしで実行（エラーの場合は即座に失敗）
uv run python -m src.main -df -od test_outputs
```

**期待される動作**:
- フォールバック戦略が使用されない
- プライマリプロバイダーが失敗した場合、例外が発生してプログラムが終了

##### 4. キャッシュの検証

```bash
# キャッシュディレクトリの確認
ls -la .cache/

# キャッシュファイルの内容を確認（jqを使用）
cat .cache/*.json | jq .

# Pythonでキャッシュデータを読み込みテスト
python -c "
from src.service.cache_manager import CacheManager
import json

cache = CacheManager()
cache_files = list(cache.cache_dir.glob('*.json'))
print(f'Found {len(cache_files)} cache files')

for cache_file in cache_files[:3]:  # 最初の3件を表示
    with open(cache_file) as f:
        data = json.load(f)
        print(f'Model: {data[\"model\"]}, Age: {data[\"timestamp\"]}')
"
```

##### 5. 生成結果の検証

```bash
# jqを使用してJSONの構造を検証
cat test_outputs/*.json | jq .

# 必須フィールドが存在するか確認
cat test_outputs/*.json | jq 'has("first_name", "last_name", "gender", "age", "personalities")'

# 性格特性が正確に3つあるか確認
cat test_outputs/*.json | jq '.personalities | length'

# Pythonで読み込みテスト
python -c "
from src.model.model import CharacterResponse
import json
import glob

for file in glob.glob('test_outputs/*.json'):
    with open(file) as f:
        data = json.load(f)
        character = CharacterResponse(**data)
        print(f'Valid! {character.first_name} {character.last_name} ({character.age}歳)')
"
```

##### 6. 統計情報のテスト

複数回実行して統計情報を確認：

```bash
# 5回実行してさまざまな統計を蓄積
for i in {1..5}; do
    echo "=== Run $i ==="
    uv run python -m src.main -od test_outputs
    sleep 2
done
```

**期待される動作**:
- 各実行後に統計情報が表示される
- キャッシュヒット率が徐々に上昇する可能性がある

# Chapter 3 Section 10: 外部サービス活用を用いたLLM実装

## 概要

このプロジェクトは、**外部サービス活用（External Service Integration）** を用いたLLMの実装を示すサンプルコードです。LLMの卓越した自然言語処理能力を司令塔として活かしつつ、リアルタイム情報の取得といった専門的なタスクを外部のAPIやツールに委譲する設計パターンを実践します。

具体的には、**MCP (Model Context Protocol)** を使用して、米国国立気象局（NWS）の天気予報APIから気象データを取得し、LLMがそのデータを解釈して適切な服装を提案するアプリケーションを構築します。OpenAI GPTシリーズとGoogle Gemini 2.5の両方に対応し、それぞれ異なるMCP統合パターンを示します。

## 機能

- **外部サービス連携**: MCP経由で米国国立気象局（NWS）の天気予報APIを呼び出し
- **構造化出力**: Pydanticモデルを活用した型安全な服装提案レスポンス
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **2つのMCP統合パターン**:
  - **OpenAI方式**: MCPツールを手動で呼び出し、結果をプロンプトに含める
  - **Gemini方式**: MCPセッションをネイティブにツールとして渡す
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果をJSON形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_10/
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
│       └── request_llm.py       # LLMリクエスト処理
├── tool_server/
│   ├── __init__.py
│   └── weather_server.py        # MCP天気予報サーバー
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # 開発用コマンド
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト設計ドキュメント
```

### アーキテクチャ

このプロジェクトは、LLMを中心に外部サービス（天気予報API）を連携させる4層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────┐
│         CLI Layer (main.py)             │
│     - コマンドライン引数解析             │
│     - 出力ディレクトリ管理               │
│     - 結果の表示とファイル保存           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Business Logic Layer               │
│  - リクエスト処理 (request_llm.py)      │
│  - プロンプト生成 (prompt.py)           │
│  - データモデル (model.py)              │
│  - LLMクライアント管理 (llm_client.py)  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      External Service Layer             │
│  - MCPサーバー (weather_server.py)      │
│  - 天気予報API統合                      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - 外部API (OpenAI, Gemini, NWS)        │
└─────────────────────────────────────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/model.py`)

3つのPydanticモデルで、天気情報と服装提案を型安全に管理します：

```python
class WeatherCondition(BaseModel):
    """天気予報の情報を格納するモデル"""
    period_name: str
    temperature: int
    temperature_unit: str
    wind_speed: str
    wind_direction: str
    forecast_summary: str

class ClothingRecommendation(BaseModel):
    """服装提案を格納するモデル"""
    clothing_type: str
    item_suggestion: str
    reason: str

class OutfitResponse(BaseModel):
    """天気に基づく服装提案のレスポンスモデル"""
    location: str
    weather_summary: str
    current_weather: WeatherCondition
    outfit_recommendations: list[ClothingRecommendation]  # 最低3つ
    additional_advice: str
```

**ポイント**:
- `frozen=True`により不変オブジェクトを保証
- `validate_assignment=True`で代入時のバリデーションを有効化
- `min_length=3`でoutfit_recommendationsの最小個数を強制

#### 2. MCPサーバー (`tool_server/weather_server.py`)

FastMCPを使用して、天気予報APIをMCPツールとして公開します：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # NWS APIから予報を取得
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    # 予報URLを取得
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    # フォーマットして返す
    periods = forecast_data["properties"]["periods"]
    # ... (フォーマット処理)
    return "\n---\n".join(forecasts)
```

**ポイント**:
- `@mcp.tool()`デコレータでツールとして登録
- 米国国立気象局（NWS）のAPIを使用（米国内の座標のみ対応）
- エラーハンドリングとタイムアウト処理を実装
- stdioトランスポートで通信（`mcp.run(transport="stdio")`）

#### 3. OpenAI実装 - 手動MCPツール呼び出し (`src/service/request_llm.py`)

OpenAI SDKはネイティブMCPサポートがないため、MCPツールを手動で呼び出し、結果をプロンプトに含めます：

```python
async def request_openai_outfit(model: OpenAIModel, latitude: float, longitude: float) -> OutfitResponse:
    """天気予報に基づいた服装提案（OpenAI + MCP）"""
    # MCPサーバーパラメータを設定
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "tool_server/weather_server.py"],
    )

    # MCPサーバーから天気予報を取得
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # get_forecast ツールを呼び出し
            result = await session.call_tool(
                "get_forecast",
                arguments={"latitude": latitude, "longitude": longitude}
            )

            # 結果を抽出
            weather_data = result.content[0].text

    # 天気データを使ってプロンプトを作成
    prompt = make_outfit_prompt(weather_data)

    # OpenAI APIで服装提案を生成
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=OutfitResponse,  # 構造化出力
    )
    return result.output_parsed
```

**特徴**:
- MCPツールを明示的に呼び出す（`session.call_tool()`）
- 取得した天気データをプロンプトに埋め込む
- `responses.parse()`で構造化出力を取得

#### 4. Gemini実装 - ネイティブMCP統合 (`src/service/request_llm.py`)

Gemini SDKはネイティブMCPサポートを持ち、MCPセッションを直接ツールとして渡せます：

```python
async def request_gemini_outfit(model: GeminiModel, latitude: float, longitude: float) -> OutfitResponse:
    """天気予報に基づいた服装提案（Gemini + MCP）"""
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "tool_server/weather_server.py"],
    )

    # MCPサーバーと接続
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # プロンプトを作成（天気データは含めず）
            system_instruction = """あなたは気象データを分析して、適切な服装を提案する
親切なファッションアドバイザーです。利用可能な天気予報ツールを使用して、
指定された場所の天気を取得し、それに基づいて服装を提案してください。"""

            user_prompt = f"""緯度{latitude}、経度{longitude}の地点の天気予報を取得して、
今日外出する際の最適な服装を提案してください。"""

            # Gemini APIにMCPセッションをツールとして渡す
            result = await google_genai_client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[session],  # MCPセッションを直接渡す
                ),
            )

            # レスポンスからJSONテキストを抽出してパース
            response_text = result.text
            # ... (JSON抽出とパース処理)
            return OutfitResponse(**outfit_data)
```

**特徴**:
- `tools=[session]`でMCPセッションをネイティブに統合
- LLMが自動的にツールを呼び出し判断
- ツール呼び出しと構造化出力（`response_mime_type`）は同時使用不可のため、テキストレスポンスをパース

#### 5. プロンプト生成 (`src/prompt/prompt.py`)

天気データとスキーマ情報を埋め込んだプロンプトを生成します：

```python
def make_outfit_prompt(weather_data: str) -> list:
    """天気予報に基づいた服装提案用のプロンプトを作成"""
    params = OutfitResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    return [
        {
            "role": "system",
            "content": f"""あなたは気象データを分析して、適切な服装を提案する
親切なファッションアドバイザーです。

天気予報データを分析し、以下の構造に厳密に従ったJSONオブジェクトで応答してください：

{param_dump}

ガイドライン：
1. 応答は有効なJSONであること
2. すべてのフィールドが必須項目として含まれていること
3. 気温、風速、天気の状況を総合的に考慮すること
4. outfit_recommendationsには最低3つのアイテムを含めること
..."""
        },
        {
            "role": "user",
            "content": f"""以下は今日の天気予報データです。このデータに基づいて、
今日外出する際の最適な服装を提案してください：

{weather_data}"""
        }
    ]
```

**ポイント**:
- モデルから自動的にスキーマ情報を抽出
- 天気データをユーザープロンプトに埋め込む
- 日本の気候と文化に適した提案を依頼

#### 6. エラーハンドリング

外部サービス連携では、堅牢なエラーハンドリングが不可欠です：

```python
# 天気データの取得失敗を検出
if "天気予報データの取得に失敗" in weather_data or "Unable to fetch" in weather_data:
    raise ValueError(
        "天気予報データの取得に失敗しました。\n"
        "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
        f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
        "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）"
    )
```

**ポイント**:
- 外部APIの制約（米国内のみ）を明確にユーザーに伝える
- 具体的な代替案を提示（例の座標を含む）
- JSON解析エラーも詳細にログ出力

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - fastapi>=0.119.0
  - google-genai>=1.45.0
  - httpx>=0.28.1
  - mcp[cli]>=1.20.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - redis>=7.0.0
  - uvicorn>=0.37.0

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
# Gemini APIを使用
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892

# OpenAI APIを使用
uv run python -m src.main -lp OPENAI -m GPT_5_MINI -lat 39.7456 -lon -97.0892

# 異なる座標で実行（例: カンザス州）
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.0119 -lon -95.6788
```

**重要**: このツールは米国国立気象局（NWS）のAPIを使用しているため、**米国内の座標のみ対応**しています。

#### パラメータ説明

- `-lp, --llm-provider`: LLMプロバイダー（`OPENAI` または `GEMINI`）【必須】
- `-m, --model`: 使用するモデル【必須】
  - OpenAI: `gpt-5`, `gpt-5-mini`, `gpt-4o`, `gpt-4o-mini` など
  - Gemini: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`
- `-lat, --latitude`: 緯度（例: 39.7456）【必須】
- `-lon, --longitude`: 経度（例: -97.0892）【必須】
- `-od, --output-directory`: 出力ディレクトリ（デフォルト: `outputs`）

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892 -od ./custom_output

# 短縮オプション
uv run python -m src.main -lp OPENAI -m gpt-4o-mini -lat 39.7456 -lon -97.0892 -od ./my_outfits
```

#### ヘルプの表示

```bash
$ python -m src.main --help
Usage: python -m src.main [OPTIONS]

  天気予報に基づいて服装を提案します

  Example:     python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456
  -lon -97.0892

Options:
  -lp, --llm-provider [OPENAI|GEMINI]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5|GPT_5_MINI|GPT_5_NANO|GPT_4_1|GPT_4_1_MINI|GPT_4_1_NANO|GPT_4O|GPT_4O_MINI|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The model to use for the request.
                                  [required]
  -lat, --latitude FLOAT          緯度 (例: 39.7456 for Kansas, USA)  [required]
  -lon, --longitude FLOAT         経度 (例: -97.0892 for Kansas, USA)  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### 米国の主要都市の座標例

```bash
# ニューヨーク市（マンハッタン）
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 40.7128 -lon -74.0060

# ロサンゼルス
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 34.0522 -lon -118.2437

# シカゴ
uv run python -m src.main -lp OPENAI -m GPT_5_MINI -lat 41.8781 -lon -87.6298

# シアトル
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 47.6062 -lon -122.3321
```

### 出力例

実行すると、以下のような構造化されたJSONファイルと詳細なログが生成されます：

**ファイル名**: `outputs/outfit_gemini_dd9eb6dd3ac748e9a79e64908ea0d413.json`

```json
{
    "location": "今日の予報地域",
    "weather_summary": "今日は一日を通して晴れ間が広がる見込みですが、最高気温は約8.9℃（48°F）と非常に肌寒い一日となるでしょう。風もやや強く吹くため、しっかりとした防寒対策が必要です。",
    "current_weather": {
        "period_name": "Saturday",
        "temperature": 48,
        "temperature_unit": "F",
        "wind_speed": "5 to 15 mph",
        "wind_direction": "Northwest",
        "forecast_summary": "Mostly sunny, with a high near 48. Northwest wind 5 to 15 mph."
    },
    "outfit_recommendations": [
        {
            "clothing_type": "アウター",
            "item_suggestion": "厚手のダウンジャケットまたはウールコート",
            "reason": "最高気温が約8.9℃と低く、風も強めに吹くため、体全体をしっかりと覆い、保温性の高いダウンジャケットやウールコートで寒さから身を守ることが必須です。"
        },
        {
            "clothing_type": "トップス",
            "item_suggestion": "厚手のセーターや裏起毛のスウェットシャツ",
            "reason": "アウターの下には、保温性の高い厚手のセーターや裏起毛のスウェットシャツを着用し、重ね着で体温を逃がさないようにしましょう。ヒートテックなどの機能性インナーもおすすめです。"
        },
        {
            "clothing_type": "ボトムス",
            "item_suggestion": "保温性の高いパンツ（例: コーデュロイパンツ、ウールパンツ、裏起毛パンツ）",
            "reason": "足元も冷えやすいので、保温効果のあるコーデュロイパンツやウールパンツ、または裏起毛のパンツを選び、下半身の冷えを防ぎましょう。"
        },
        {
            "clothing_type": "小物",
            "item_suggestion": "マフラー、手袋、ニット帽",
            "reason": "首元、手先、耳元は特に冷えやすいので、マフラー、手袋、ニット帽で徹底的に防寒対策をすることで、より快適に過ごせます。"
        }
    ],
    "additional_advice": "日中は晴れ間が広がりそうですが、気温は非常に低く、風も冷たく感じられるでしょう。外出時は最大限の防寒対策を心がけ、重ね着で調整できるように準備してください。暖かい飲み物を持ち歩くのも良いでしょう。"
}
```

**実行ログ例**:
```
[2025-11-01 10:30:45] [INFO] [__main__] [main.py:74] [main] LLM provider: gemini
Model: gemini-2.5-flash
Latitude: 39.7456
Longitude: -97.0892
Output directory: outputs
[2025-11-01 10:30:46] [INFO] [src.service.request_llm] [request_llm.py:84] [request_gemini_outfit] MCP session initialized for Gemini. Requesting outfit recommendation for lat=39.7456, lon=-97.0892
[2025-11-01 10:30:48] [INFO] [__main__] [main.py:101] [main] File saved to outputs/outfit_gemini_dd9eb6dd3ac748e9a79e64908ea0d413.json

=== 服装提案 ===
場所: 今日の予報地域
天気概要: 今日は一日を通して晴れ間が広がる見込みですが、最高気温は約8.9℃（48°F）と非常に肌寒い一日となるでしょう。風もやや強く吹くため、しっかりとした防寒対策が必要です。

現在の天気:
  期間: Saturday
  気温: 48°F
  風: 5 to 15 mph Northwest
  予報: Mostly sunny, with a high near 48. Northwest wind 5 to 15 mph.

推奨服装:
  1. アウター: 厚手のダウンジャケットまたはウールコート
     理由: 最高気温が約8.9℃と低く、風も強めに吹くため、体全体をしっかりと覆い、保温性の高いダウンジャケットやウールコートで寒さから身を守ることが必須です。
  2. トップス: 厚手のセーターや裏起毛のスウェットシャツ
     理由: アウターの下には、保温性の高い厚手のセーターや裏起毛のスウェットシャツを着用し、重ね着で体温を逃がさないようにしましょう。ヒートテックなどの機能性インナーもおすすめです。
  3. ボトムス: 保温性の高いパンツ（例: コーデュロイパンツ、ウールパンツ、裏起毛パンツ）
     理由: 足元も冷えやすいので、保温効果のあるコーデュロイパンツやウールパンツ、または裏起毛のパンツを選び、下半身の冷えを防ぎましょう。
  4. 小物: マフラー、手袋、ニット帽
     理由: 首元、手先、耳元は特に冷えやすいので、マフラー、手袋、ニット帽で徹底的に防寒対策をすることで、より快適に過ごせます。

追加アドバイス: 日中は晴れ間が広がりそうですが、気温は非常に低く、風も冷たく感じられるでしょう。外出時は最大限の防寒対策を心がけ、重ね着で調整できるように準備してください。暖かい飲み物を持ち歩くのも良いでしょう。
```

### テスト方法

現在、このセクションにはユニットテストは含まれていません。手動テストは以下の方法で行います：

#### 1. Gemini APIのテスト（ネイティブMCP統合）

```bash
uv run python -m src.main -lp GEMINI -m gemini-2.5-flash -lat 39.7456 -lon -97.0892 -od test_outputs
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `outfit_gemini_XXXXXXXX.json`形式のファイルが生成される
- JSONファイルが`OutfitResponse`スキーマに準拠している
- ログに「MCP session initialized for Gemini」が表示される
- LLMが自動的に`get_forecast`ツールを呼び出す

#### 2. OpenAI APIのテスト（手動MCPツール呼び出し）

```bash
uv run python -m src.main -lp OPENAI -m gpt-4o-mini -lat 39.7456 -lon -97.0892 -od test_outputs
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `outfit_openai_XXXXXXXX.json`形式のファイルが生成される
- JSONファイルが`OutfitResponse`スキーマに準拠している
- ログに「Calling get_forecast」が表示される
- 天気データがプロンプトに埋め込まれる

#### 3. MCPサーバーの単独テスト

MCPサーバーが正しく動作するか、別プロセスで確認：

```bash
# MCPサーバーを起動（別ターミナル）
make run_weather_mcp

# または
uv run python tool_server/weather_server.py
```

期待される動作：
- 「Starting Weather MCP Server...」が表示される
- stdioでの通信待機状態になる

#### 4. バリデーションの確認

生成されたJSONファイルが正しい構造を持っているか確認：

```bash
# jqを使用してJSONを検証
cat test_outputs/outfit_gemini_*.json | jq .

# outfit_recommendationsの個数を確認（最低3つ必要）
cat test_outputs/outfit_gemini_*.json | jq '.outfit_recommendations | length'

# Pythonで読み込みテスト
python -c "
from src.model.model import OutfitResponse
import json
import glob

files = glob.glob('test_outputs/outfit_*.json')
for file in files:
    with open(file) as f:
        data = json.load(f)
        outfit = OutfitResponse(**data)
        print(f'✓ Valid: {file}')
        print(f'  Location: {outfit.location}')
        print(f'  Temperature: {outfit.current_weather.temperature}°{outfit.current_weather.temperature_unit}')
        print(f'  Recommendations: {len(outfit.outfit_recommendations)} items')
"
```

#### 5. エラーハンドリングのテスト

米国外の座標で実行し、適切なエラーメッセージが表示されることを確認：

```bash
# 日本（東京）の座標でテスト - エラーが期待される
uv run python -m src.main -lp GEMINI -m gemini-2.5-flash -lat 35.6762 -lon 139.6503
```

期待される動作：
- 「天気予報データの取得に失敗しました」エラーメッセージが表示される
- 「米国内の座標のみ対応しています」という説明が表示される
- 例の座標（Kansas, USA）が提示される

#### 6. 異なるモデルの比較テスト

複数のモデルで同じ座標を試して、出力の違いを比較：

```bash
# 各モデルで実行
uv run python -m src.main -lp OPENAI -m GPT_5_MINI -lat 39.7456 -lon -97.0892 -od comparison
uv run python -m src.main -lp OPENAI -m GPT_5 -lat 39.7456 -lon -97.0892 -od comparison
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892 -od comparison
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_PRO -lat 39.7456 -lon -97.0892 -od comparison

# 結果を比較
ls -lh comparison/
cat comparison/outfit_*.json | jq '.outfit_recommendations[0]'
```

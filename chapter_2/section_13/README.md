# Chapter 2 Section 13: 外部サービス活用

## 概要

このプロジェクトは、**外部サービス活用** を用いたLLMの実装を示すサンプルコードです。LLMの卓越した自然言語処理能力を司令塔として活かしつつ、リアルタイム情報の取得といった専門的なタスクを外部のAPIやツールに委譲する設計パターンを実践します。

具体的には、**MCP (Model Context Protocol)** を使用して、米国国立気象局（NWS）の天気予報APIから気象データを取得し、LLMがそのデータを解釈して適切な服装を提案するアプリケーションを構築します。OpenAI、Google Gemini、Anthropic Claudeの3つのプロバイダーに対応し、それぞれ異なるMCP統合パターンを示します。

## 機能

- **外部サービス連携**: MCP経由で米国国立気象局（NWS）の天気予報APIを呼び出し
- **構造化出力**: Pydanticモデルを活用した型安全な服装提案レスポンス
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic Claudeの3つをサポート
- **2つのMCP統合パターン**:
  - **手動方式（OpenAI/Anthropic）**: MCPツールを手動で呼び出し、結果をプロンプトに含める
  - **ネイティブ方式（Gemini）**: MCPセッションをネイティブにツールとして渡す
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果をJSON形式でファイルに保存

## プロジェクト構成

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

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.74.1
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
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用する
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892 -od ./outputs

# OpenAI APIを使用
uv run python -m src.main -lp OPENAI -m GPT_5_MINI -lat 39.7456 -lon -97.0892 -od ./outputs

# 異なる座標で実行（例: カンザス州）
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.0119 -lon -95.6788 -od ./outputs
```

**重要**: このツールは米国国立気象局（NWS）のAPIを使用しているため、**米国内の座標のみ対応**しています。

#### パラメータ説明

- `-lp, --llm-provider`: LLMプロバイダー（`OPENAI` または `GEMINI`）【必須】
- `-m, --model`: 使用するモデル【必須】
  - OpenAI: `gpt-5`, `gpt-5-mini`, `gpt-5.4`, `gpt-5.4-mini` など
  - Gemini: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`
- `-lat, --latitude`: 緯度（例: 39.7456）【必須】
- `-lon, --longitude`: 経度（例: -97.0892）【必須】
- `-od, --output-directory`: 出力ディレクトリ（デフォルト: `outputs`）

#### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  天気予報に基づいて服装を提案します

  Example:     python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456
  -lon -97.0892

Options:
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_OPUS_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
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
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 40.7128 -lon -74.0060 -od ./outputs

# ロサンゼルス
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 34.0522 -lon -118.2437 -od ./outputs

# シカゴ
uv run python -m src.main -lp OPENAI -m GPT_5_MINI -lat 41.8781 -lon -87.6298 -od ./outputs

# シアトル
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 47.6062 -lon -122.3321 -od ./outputs
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
$ uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892
[2026-01-18 15:22:40,321] [INFO] [__main__] [main.py:73] [main] LLM provider: gemini
Model: gemini-2.5-flash
Latitude: 39.7456
Longitude: -97.0892
Output directory: outputs
[2026-01-18 15:22:40,951] [INFO] [src.service.request_llm] [request_llm.py:81] [request_gemini_outfit] MCP session initialized for Gemini. Requesting outfit recommendation for lat=39.7456, lon=-97.0892
[01/18/26 15:22:40] INFO     Processing request of type ListToolsRequest                                                                      server.py:674
[01/18/26 15:22:42] INFO     Processing request of type CallToolRequest                                                                       server.py:674
[01/18/26 15:22:43] INFO     HTTP Request: GET https://api.weather.gov/points/39.7456,-97.0892 "HTTP/1.1 200 OK"                            _client.py:1740
                    INFO     HTTP Request: GET https://api.weather.gov/gridpoints/TOP/32,81/forecast "HTTP/1.1 200 OK"                      _client.py:1740
[2026-01-18 15:22:51,347] [INFO] [src.service.request_llm] [request_llm.py:95] [request_gemini_outfit] Gemini response: sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""```json
{
  "location": "緯度39.7456、経度-97.0892の地点",
  "weather_summary": "今日は一日を通して晴れ間が広がりますが、強い風が吹き、体感温度は非常に低くなるでしょう。",
  "current_weather": {
    "period_name": "日中（日曜）",
    "temperature": 43,
    "temperature_unit": "F",
    "wind_speed": "15 to 20 mph",
    "wind_direction": "W",
    "forecast_summary": "ほとんど晴れ、最高気温は43°F付近。西風15～20mph、突風は35mphにも達するでしょう。"
  },
  "outfit_recommendations": [
    {
      "clothing_type": "アウター",
      "item_suggestion": "厚手のダウンコートまたはウールコート",
      "reason": "気温が低く、特に強い風が吹くため、体温をしっかりと保つ厚手のコートは必須です。風を通しにくい素材がおすすめです。"
    },
    {
      "clothing_type": "トップス",
      "item_suggestion": "厚手のセーターやフリース、または機能性インナー（ヒートテックなど）の上に重ね着",
      "reason": "コートの下にも保温性の高い衣類を重ね着することで、寒さから体を守ります。特に風が強い日は、重ね着で空気の層を作り体温を逃がさないことが重要です。"
    },
    {
      "clothing_type": "ボトムス",
      "item_suggestion": "裏起毛のパンツ、または保温性のある素材のスカートに厚手のタイツ",
      "reason": "下半身も冷えやすいため、保温性の高い素材を選びましょう。風を防ぐ素材のパンツも良いでしょう。"
    },
    {
      "clothing_type": "小物類",
      "item_suggestion": "マフラー、手袋、ニット帽",
      "reason": "風が強く、体感温度が非常に低くなるため、首、耳、手などの末端をしっかりと保護することが凍傷や体温低下を防ぎます。"
    }
  ],
  "additional_advice": "本日は非常に風が強く、体感温度が実際の気温よりもかなり低く感じられます。外出する際は、防寒対策を徹底し、特に露出する部分を冷やさな いように心がけてください。風で物が飛ばされないように注意し、不要な外出は控えることをお勧めします。"
}
```""",
        thought_signature=b'\n\xa5\x1b\x01r\xc8\xda|l\xef~\x9f!\xd3\x8a\xe5Jv\x1b\x00\r\xac\xb9d\xed1\xac\xe4\xf0\xdbP%\xe0\x1b^\xc0*\xb8X\xe8\xdf]A\xa6\x9af\x9bQ\xa3\x7f\xe0qR\x04Q\x14\x80\xd8\x0b\x1d\xb6\xb9Z\xeb\xc8\xf9\xd2\xb1\xc9\x9b\x8b\xb0\xf1\xc2\x94\xa8\xddx\xfd\xc5Q+x4M\xd9 \xb4\x0b7p\xd6\xc0\x1be\xf30...'
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='O3xsaaXuCoGr0-kPrfzg-QE' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=589,
  prompt_token_count=1373,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=1373
    ),
  ],
  thoughts_token_count=899,
  total_token_count=2861
) automatic_function_calling_history=[UserContent(
  parts=[
    Part(
      text="""緯度39.7456、経度-97.0892の地点の天気予報を取得して、
今日外出する際の最適な服装を提案してください。

以下の構造のJSONで回答してください：
{
  "location": "場所の説明",
  "weather_summary": "今日の天気の概要",
  "current_weather": {
    "period_name": "予報期間の名前",
    "temperature": 気温（数値）,
    "temperature_unit": "F",
    "wind_speed": "風速",
    "wind_direction": "風向き",
    "forecast_summary": "天気予報の要約"
  },
  "outfit_recommendations": [
    {
      "clothing_type": "服装の種類",
      "item_suggestion": "具体的なアイテムの提案",
      "reason": "その服装を提案する理由"
    }
  ],
  "additional_advice": "その他のアドバイス"
}

気温、風速、天気の状況を総合的に考慮して、日本の気候と文化に適した提案をしてください。
outfit_recommendationsには最低3つのアイテムを含めてください。"""
    ),
  ],
  role='user'
), Content(
  parts=[
    Part(
      function_call=FunctionCall(
        args={
          'latitude': 39.7456,
          'longitude': -97.0892
        },
        name='get_forecast'
      ),
      thought_signature=b'\n\xf8\x07\x01r\xc8\xda|\x1a\xf8\xbc\xa4lO\xcd/I>\xdd\xf0!I\x9f\x98\x97x\xf5\xc0z\x16\xe3*\xe9>\x86a\x96\rsb\xb7\x88j9\xe9\x9a#\xcbL.B(\\\xcc\xda\x87{\x19J\x0e\xd6\xc1I\x91\xc6\xa3\x80l\xb4\xc3\x0eU0\xf4#\x9c]\xa7\tf\xb8I\xce\xa8>~!)\xcc019t7\xa4@f...'
    ),
  ],
  role='model'
), Content(
  parts=[
    Part(
      function_response=FunctionResponse(
        name='get_forecast',
        response={
          'result': CallToolResult(
            content=[<... 1 item at Max depth ...>],
            isError=False,
            structuredContent={<... 1 item at Max depth ...>}
          )
        }
      )
    ),
  ],
  role='user'
)] parsed=None
Warning: there are non-text parts in the response: ['thought_signature'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:104] [main] File saved to outputs/outfit_gemini_1b0df08100614ec9b9b10287c3621824.json
[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:106] [main] 
=== 服装提案 ===
場所: 緯度39.7456、経度-97.0892の地点
天気概要: 今日は一日を通して晴れ間が広がりますが、強い風が吹き、体感温度は非常に低くなるでしょう。

現在の天気:
  期間: 日中（日曜）
  気温: 43°F
  風: 15 to 20 mph W
  予報: ほとんど晴れ、最高気温は43°F付近。西風15～20mph、突風は35mphにも達するでしょう。

推奨服装:

[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:120] [main]   1. アウター: 厚手のダウンコートまたはウールコート
     理由: 気温が低く、特に強い風が吹くため、体温をしっかりと保つ厚手のコートは必須です。風を通しにくい素材がおすすめです。
[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:120] [main]   2. トップス: 厚手のセーターやフリース、または機能性インナー（ヒートテックなど）の上に重 ね着
     理由: コートの下にも保温性の高い衣類を重ね着することで、寒さから体を守ります。特に風が強い日は、重ね着で空気の層を作り体温を逃がさないことが重要です。
[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:120] [main]   3. ボトムス: 裏起毛のパンツ、または保温性のある素材のスカートに厚手のタイツ
     理由: 下半身も冷えやすいため、保温性の高い素材を選びましょう。風を防ぐ素材のパンツも良いでしょう。
[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:120] [main]   4. 小物類: マフラー、手袋、ニット帽
     理由: 風が強く、体感温度が非常に低くなるため、首、耳、手などの末端をしっかりと保護することが凍傷や体温低下を防ぎます。
[2026-01-18 15:22:51,412] [INFO] [__main__] [main.py:123] [main] 
追加アドバイス: 本日は非常に風が強く、体感温度が実際の気温よりもかなり低く感じられます。外出する際は、防寒対策を徹底し、特に露出する部分を冷やさないように 心がけてください。風で物が飛ばされないように注意し、不要な外出は控えることをお勧めします。
```

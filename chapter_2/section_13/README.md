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

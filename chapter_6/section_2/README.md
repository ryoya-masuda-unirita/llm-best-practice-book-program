# Chapter 6 Section 2: LLM SDKの薄いラッパーライブラリ

## 概要

このプロジェクトは、**LLM SDKの薄いラッパーライブラリ**の実装例を示すサンプルコードです。OpenAI、Google Gemini、Anthropicの公式SDKをラップし、透過的なログ記録、トークン使用量の追跡、処理時間の計測といった横断的関心事を一元化します。

公式SDKのインターフェースを可能な限り維持しながら、全てのAPI呼び出しを自動的にロギングする仕組みを実装しています。これにより、アプリケーションコードはビジネスロジックに集中でき、LLM連携部分の保守性、拡張性、観測可能性を飛躍的に向上させることができます。

## 機能

- **透過的なラッパー実装**: 公式SDKのインターフェースを維持しつつ、ログ機能を追加
- **自動ログ記録**: 全てのAPI呼び出しのリクエスト/レスポンスをJSON形式で保存
- **トークン使用量追跡**: プロンプトトークン数、補完トークン数、合計トークン数を記録
- **処理時間計測**: 各API呼び出しの実行時間をミリ秒単位で記録
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic APIをサポート
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
│   │   ├── llm_client.py            # ラッパークライアントの初期化
│   │   ├── openai_wrapper_client.py     # OpenAIラッパー実装
│   │   ├── gemini_wrapper_client.py     # Geminiラッパー実装
│   │   └── anthropic_wrapper_client.py  # Anthropicラッパー実装
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
│      Wrapper Layer                              │
│  - OpenAIWrapperClient                          │
│  - GenAIWrapperClient                           │
│  - AnthropicWrapperClient                       │
│  - 自動ログ記録とトークン追跡                   │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Infrastructure Layer                       │
│  - 公式SDK (OpenAI, Google Gemini, Anthropic)   │
│  - 設定管理 (config.py)                         │
│  - ログ管理 (logger.py)                         │
└─────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.74.1
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
cp .envrc.example .envrc

# .envrcを編集してAPIキーを設定
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用
uv run python -m src.main --llm-provider GEMINI --model GEMINI_2_5_FLASH

# OpenAI APIを使用
uv run python -m src.main --llm-provider OPENAI --model GPT_5_MINI

# Anthropic APIを使用
uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_HAIKU_4_5
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH --output-directory ./custom_output
```

#### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_2|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_OPUS_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

#### 生成されたキャラクター情報

**ファイル名**: `outputs/gemini_a1b2c3d4e5f6.json`

```json
{
    "first_name": "アオイ",
    "last_name": "田中",
    "gender": "female",
    "age": 28,
    "personalities": [
        {
            "short_personality": "直感的",
            "description": "彼女は人々の感情や状況の背後にある隠れた意味を素早く察知する能力を持っています。論理よりも直感を信じ、しばしば正しい結論に達します。"
        },
        {
            "short_personality": "観察力がある",
            "description": "彼女は周囲の細部に非常に注意を払います。人々の行動、表情、周囲の環境のわずかな変化も見逃さず、それが彼女の直感を裏付ける根拠となることがあります。"
        },
        {
            "short_personality": "冷静沈着",
            "description": "予期せぬ困難やストレスの多い状況に直面しても、彼女は感情的になることなく、常に冷静さを保ちます。この特性により、客観的な判断を下し、効率的な解決策を見つけることができます。"
        }
    ]
}
```

#### 使用ログファイル

**ファイル名**: `usage_logs/async_genai_20251101_101739_694420.json`

```json
{
  "timestamp": "2026-02-08T09:09:34.577627",
  "method": "aio.models.generate_content",
  "duration_ms": 3655.6670000000004,
  "request": {
    "model": "gemini-2.5-flash",
    "contents": "ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。",
    "config": "http_options=None should_return_http_response=None system_instruction='あなたは創造的なキャラクタージェネレーターです。\\nあなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。\\n以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：\\n\\n{\\n  \"first_name\": \"string; The first name of the character.\",\\n  \"last_name\": \"string; The last name of the character.\",\\n  \"gender\": \"enum; The gender of the character.; [\\'female\\', \\'male\\']\",\\n  \"age\": \"number; The age of the character.; 0-100\",\\n  \"personalities\": [\\n    {\\n      \"short_personality\": \"string; The three most important personality traits of the character. (personality 1)\",\\n      \"description\": \"string; The three most important personality traits of the character. (detailed description for personality 1)\"\\n    },\\n    {\\n      \"short_personality\": \"string; The three most important personality traits of the character. (personality 2)\",\\n      \"description\": \"string; The three most important personality traits of the character. (detailed description for personality 2)\"\\n    },\\n    {\\n      \"short_personality\": \"string; The three most important personality traits of the character. (personality 3)\",\\n      \"description\": \"string; The three most important personality traits of the character. (detailed description for personality 3)\"\\n    }\\n  ]\\n}\\n\\n以下を確認してください：\\n1. 応答は有効なJSONであること\\n2. すべてのフィールドが含まれていること\\n3. 性別は「female」または「male」のいずれかであること\\n4. 年齢は0から100の間であること\\n5. 正確に3つの性格特性が提供されていること\\n6. JSON構造の外に説明や追加のテキストを含めないこと\\n' temperature=None top_p=None top_k=None candidate_count=None max_output_tokens=None stop_sequences=None response_logprobs=None logprobs=None presence_penalty=None frequency_penalty=None seed=None response_mime_type='application/json' response_schema=<class 'src.model.model.CharacterResponse'> response_json_schema=None routing_config=None model_selection_config=None safety_settings=None tools=None tool_config=None labels=None cached_content=None response_modalities=None media_resolution=None speech_config=None audio_timestamp=None automatic_function_calling=None thinking_config=None image_config=None",
    "parameters": {}
  },
  "response": {
    "text": "{\n  \"first_name\": \"アオイ\",\n  \"last_name\": \"田中\",\n  \"gender\": \"female\",\n  \"age\": 28,\n  \"personalities\": [\n    {\n      \"short_personality\": \"直感的\",\n      \"description\": \"彼女は人々の感情や状況の背後にある隠れた意味を素早く察知する能力を持っています。論理よりも直感を信じ、しばしば正しい結論に達します。\"\n    },\n    {\n      \"short_personality\": \"観察力がある\",\n      \"description\": \"彼女は周囲の細部に非常に注意を払います。人々の行動、表情、周囲の環境のわずかな変化も見逃さず、それが彼女の直感を裏付ける根拠となることがあります。\"\n    },\n    {\n      \"short_personality\": \"冷静沈着\",\n      \"description\": \"予期せぬ困難やストレスの多い状況に直面しても、彼女は感情的になることなく、常に冷静さを保ちます。この特性により、客観的な判断を下し、効率的な解決策を見つけることができます。\"\n    }\n  ]\n}",
    "candidates": [
      {
        "content": {
          "parts": [
            {
              "text": "{\n  \"first_name\": \"アオイ\",\n  \"last_name\": \"田中\",\n  \"gender\": \"female\",\n  \"age\": 28,\n  \"personalities\": [\n    {\n      \"short_personality\": \"直感的\",\n      \"description\": \"彼女は人々の感情や状況の背後にある隠れた意味を素早く察知する能力を持っています。論理よりも直感を信じ、しばしば正しい結論に達します。\"\n    },\n    {\n      \"short_personality\": \"観察力がある\",\n      \"description\": \"彼女は周囲の細部に非常に注意を払います。人々の行動、表情、周囲の環境のわずかな変化も見逃さず、それが彼女の直感を裏付ける根拠となることがあります。\"\n    },\n    {\n      \"short_personality\": \"冷静沈着\",\n      \"description\": \"予期せぬ困難やストレスの多い状況に直面しても、彼女は感情的になることなく、常に冷静さを保ちます。この特性により、客観的な判断を下し、効率的な解決策を見つけることができます。\"\n    }\n  ]\n}"
            }
          ],
          "role": "model"
        },
        "finish_reason": "STOP",
        "safety_ratings": null
      }
    ],
    "usage_metadata": {
      "prompt_token_count": 411,
      "candidates_token_count": 253,
      "total_token_count": 993
    }
  }
}
```

#### 実行ログ

```bash
$ uv run python -m src.main --llm-provider GEMINI --model GEMINI_2_5_FLASH

[2026-02-08 09:09:34,576] [INFO] [__main__] [main.py:52] [main] LLM provider: gemini
Model: gemini-2.5-flash
Output directory: outputs
[2026-02-08 09:09:38,233] [INFO] [src.service.request_llm] [request_llm.py:38] [request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""{
  "first_name": "アオイ",
  "last_name": "田中",
  "gender": "female",
  "age": 28,
  "personalities": [
    {
      "short_personality": "直感的",
      "description": "彼女は人々の感情や状況の背後にある隠れた意味を素早く察知する能力を持っています。論理よりも直感を信じ、しばしば正しい結論に達します。"
    },
    {
      "short_personality": "観察力がある",
      "description": "彼女は周囲の細部に非常に注意を払います。人々の行動、表情、周囲の環境のわずかな変化も見逃さず、それが彼女の直感を裏付ける根拠となることがあります。"
    },
    {
      "short_personality": "冷静沈着",
      "description": "予期せぬ困難やストレスの多い状況に直面しても、彼女は感情的になることなく、常に冷静さを保ちます。この特性により、客観的な判断を下し、効率的な解決策を見つけることができます。"
    }
  ]
}"""
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='QtSHaZz3Av3k2roPlv_BkA4' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=253,
  prompt_token_count=411,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=411
    ),
  ],
  thoughts_token_count=329,
  total_token_count=993
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='アオイ', last_name='田中', gender=<Gender.FEMALE: 'female'>, age=28, personalities=[CharacterPersonality(short_personality='直感的', description='彼女は人々の感情や状況の背後にある隠れた意味を素早く察知する能力を持 っています。論理よりも直感を信じ、しばしば正しい結論に達します。'), CharacterPersonality(short_personality='観察力がある', description='彼女は周囲の細部に非常に注意を払います。人々の行動、表情、周囲の環境のわずかな変化も見逃さず、それが彼女の直感を裏付ける根拠となることがあります。'), CharacterPersonality(short_personality='冷静沈着', description='予期せぬ困難やストレスの多い状況に直面しても、彼女は感情的になることなく、常に冷静さを保ちます。この特性により、客観的な判断を下し、効率的な解決策を見つけることができます。')])
[2026-02-08 09:09:38,280] [INFO] [__main__] [main.py:77] [main] File saved to outputs/gemini_20f0ba4d70514b06b40a067f911e18c1.json
```

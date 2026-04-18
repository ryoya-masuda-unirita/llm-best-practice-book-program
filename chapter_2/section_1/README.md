# Chapter 2 Section 1: LLMの出力を構造化する

## 概要

このプロジェクトは、**構造化出力（Structured Outputs）** を用いたLLM（大規模言語モデル）の基本実装を示すサンプルコードです。OpenAI、Google Gemini、Anthropic Claudeの3つのLLMプロバイダーに対応し、Pydanticモデルを活用して型安全なLLM応答を実現します。

フィクションのキャラクター情報（名前、性別、年齢、性格特性）を生成するユースケースを通じて、構造化出力の実践的な実装方法を学ぶことができます。各プロバイダー固有のStructured Outputs APIを活用し、LLMからの応答を確実にPydanticモデルにパースします。

## 機能

- **構造化出力**: PydanticモデルをAPI応答形式として直接利用し、型安全なLLM出力を実現
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic Claude APIの3プロバイダーをサポート
- **複数モデル選択**: 各プロバイダーで複数のモデルから選択可能（全17モデル対応）
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果をJSON形式でファイルに保存

## プロジェクト構成

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────┐
│              CLI Layer (main.py)                    │
│         - コマンドライン引数解析                     │
│         - プロバイダー・モデル選択                   │
│         - 出力ディレクトリ管理                       │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│           Service Layer (service/)                  │
│    - request_llm.py: LLMリクエスト処理              │
│    - 各プロバイダー固有のAPI呼び出しロジック          │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│          Business Logic Layer                       │
│    - prompt/prompt.py: プロンプト生成               │
│    - client/llm_client.py: クライアント管理          │
│    - model/model.py: データモデル定義                │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│          Infrastructure Layer                       │
│    - config.py: 設定管理                            │
│    - logger.py: ログ管理                            │
│    - 外部API (OpenAI, Gemini, Anthropic)            │
└─────────────────────────────────────────────────────┘
```

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
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. **依存関係のインストール**

```bash
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Geminiで実行（モデルを指定）
uv run python -m src.main --llm-provider GEMINI --model GEMINI_2_5_FLASH --output-directory outputs/

# OpenAIで実行
uv run python -m src.main --llm-provider OPENAI --model GPT_5_MINI --output-directory outputs/

# Anthropicで実行
uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_SONNET_4_6 --output-directory outputs/

# 短縮オプションで実行
uv run python -m src.main -lp OPENAI -m GPT_5_MINI -od outputs/
```

#### 利用可能なモデル

| プロバイダー | モデル |
|-------------|--------|
| OpenAI | GPT_5_4, GPT_5_4_MINI, GPT_5_4_NANO, GPT_5_2, GPT_5_1, GPT_5, GPT_5_MINI, GPT_5_NANO |
| Gemini | GEMINI_2_5_PRO, GEMINI_2_5_FLASH, GEMINI_2_5_FLASH_LITE |
| Anthropic | CLAUDE_OPUS_4_6, CLAUDE_SONNET_4_6, CLAUDE_HAIKU_4_5 |

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
  -m, --model [GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_OPUS_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/gemini_27ea9c6863a640fdb60d60d2d34f6991.json`

```json
{
    "first_name": "Akira",
    "last_name": "Sato",
    "gender": "male",
    "age": 28,
    "personalities": [
        {
            "short_personality": "Observant",
            "description": "He rarely misses a detail, whether it's a subtle change in someone's tone of voice or a small discrepancy in a complex system. This makes him an excellent problem-solver and a quiet, insightful presence in any group."
        },
        {
            "short_personality": "Pragmatic",
            "description": "Akira prefers practical solutions over idealistic ones. He assesses situations based on facts and likely outcomes, always aiming for the most efficient and sensible path forward, even if it's not the most popular."
        },
        {
            "short_personality": "Reserved",
            "description": "He keeps to himself, not out of shyness, but due to a natural inclination towards introspection. Akira doesn't initiate small talk often and expresses his thoughts concisely, preferring action and observation to lengthy discourse."
        }
    ]
}
```

**実行ログ例**:
```
$ uv run python -m src.main -lp OPENAI -m GPT_5_MINI

[2026-01-17 16:01:25,696] [INFO] [__main__] [main.py:52] [main] LLM provider: openai
Model: gpt-5-mini
Output directory: outputs
[2026-01-17 16:01:39,120] [INFO] [src.service.request_llm] [request_llm.py:24] [request_openai] ParsedResponse[CharacterResponse](id='resp_0051941f89c5ee9a00696b33c61fb8819e84241a8a2471f0a3', created_at=1768633286.0, error=None, incomplete_details=None, instructions=None, metadata={}, model='gpt-5-mini-2025-08-07', object='response', output=[ResponseReasoningItem(id='rs_0051941f89c5ee9a00696b33c679c4819ebb7f59c248651a97', summary=[], type='reasoning', content=None, encrypted_content=None, status=None), ParsedResponseOutputMessage[CharacterResponse](id='msg_0051941f89c5ee9a00696b33ccf224819e9ebc6d698d5b652a', content=[ParsedResponseOutputText[CharacterResponse](annotations=[], text='{\n  "first_name": "Aiko",\n  "last_name": "Sazanami",\n  "gender": "female",\n  "age": 32,\n  "personalities": [\n    {\n      "short_personality": "好奇心旺盛",\n      "description": "見知らぬものや忘れられた場所に強く惹かれる探究心の持 ち主。古い地図や異国の小物に目がなく、些細な手がかりから物語を組み立てるのが得意。好奇心が行動の原動力であり、常識や危険をいったん置いておいてでも真実を確 かめに行くことが多い。"\n    },\n    {\n      "short_personality": "不屈の執着心",\n      "description": "一度決めたことには粘り強く取り組み、困難があって も手を緩めない。計画は綿密で、失敗を細かく分析して次に活かす。周囲からは冷静で頼りになる人物と見なされるが、時に目標に対して融通が利かず人間関係を犠牲にす ることもある。"\n    },\n    {\n      "short_personality": "いたずら好きで共感的",\n      "description": "人の感情に敏感で、場の空気を読むのが得意。その感 覚を利用してユーモアや小さないたずらで緊張を解きほぐすことを好む。表情や言葉で相手の弱さを見抜く一方、深いところでは誰かを守りたいという強い思いがある。自 分の弱さは滅多に見せないため、思いやりと軽やかな皮肉を同時に使うことが多い。"\n    }\n  ]\n}', type='output_text', logprobs=[], parsed=CharacterResponse(first_name='Aiko', last_name='Sazanami', gender=<Gender.FEMALE: 'female'>, age=32, personalities=[CharacterPersonality(short_personality='好奇心旺盛', description='見知らぬものや忘れられた場所に強く惹かれる探究心の持ち主。古い地図や異国の小物に目がなく、些細な手がかりから物語を組み立てるのが得意。好奇心が行動の原動力であり、常識や危険をいったん置いておいてでも真実を確かめに行くことが多い。'), CharacterPersonality(short_personality='不屈の執着心', description='一 度決めたことには粘り強く取り組み、困難があっても手を緩めない。計画は綿密で、失敗を細かく分析して次に活かす。周囲からは冷静で頼りになる人物と見なされるが、 時に目標に対して融通が利かず人間関係を犠牲にすることもある。'), CharacterPersonality(short_personality='いたずら好きで共感的', description='人の感情に敏感 で、場の空気を読むのが得意。その感覚を利用してユーモアや小さないたずらで緊張を解きほぐすことを好む。表情や言葉で相手の弱さを見抜く一方、深いところでは誰か を守りたいという強い思いがある。自分の弱さは滅多に見せないため、思いやりと軽やかな皮肉を同時に使うことが多い。')]))], role='assistant', status='completed', type='message')], parallel_tool_calls=True, temperature=1.0, tool_choice='auto', tools=[], top_p=1.0, background=False, conversation=None, max_output_tokens=None, max_tool_calls=None, previous_response_id=None, prompt=None, prompt_cache_key=None, reasoning=Reasoning(effort='medium', generate_summary=None, summary=None), safety_identifier=None, service_tier='default', status='completed', text=ResponseTextConfig(format=ResponseFormatTextJSONSchemaConfig(name='CharacterResponse', schema_={'$defs': {'CharacterPersonality': {'properties': {'short_personality': {'description': "A short description of the character's personality.", 'title': 'Short Personality', 'type': 'string'}, 'description': {'description': "A description of the character's personality traits and behaviors.", 'title': 'Description', 'type': 'string'}}, 'required': ['short_personality', 'description'], 'title': 'CharacterPersonality', 'type': 'object', 'additionalProperties': False}, 'Gender': {'enum': ['female', 'male'], 'title': 'Gender', 'type': 'string'}}, 'properties': {'first_name': {'description': 'The first name of the character.', 'title': 'First Name', 'type': 'string'}, 'last_name': {'description': 'The last name of the character.', 'title': 'Last Name', 'type': 'string'}, 'gender': {'default': 'male', 'description': 'The gender of the character.', 'enum': ['female', 'male'], 'title': 'Gender', 'type': 'string'}, 'age': {'description': 'The age of the character.', 'maximum': 100, 'minimum': 0, 'title': 'Age', 'type': 'integer'}, 'personalities': {'description': 'The three most important personality traits of the character.', 'items': {'$ref': '#/$defs/CharacterPersonality'}, 'title': 'Personalities', 'type': 'array'}}, 'required': ['first_name', 'last_name', 'gender', 'age', 'personalities'], 'title': 'CharacterResponse', 'type': 'object', 'additionalProperties': False}, type='json_schema', description=None, strict=True), verbosity='medium'), top_logprobs=0, truncation='disabled', usage=ResponseUsage(input_tokens=690, input_tokens_details=InputTokensDetails(cached_tokens=0), output_tokens=898, output_tokens_details=OutputTokensDetails(reasoning_tokens=448), total_tokens=1588), user=None, billing={'payer': 'developer'}, completed_at=1768633298, frequency_penalty=0.0, presence_penalty=0.0, prompt_cache_retention=None, store=True)
[2026-01-17 16:01:39,121] [INFO] [__main__] [main.py:77] [main] File saved to outputs/openai_6e52740ae6e94f51baf1bf0f949ae21b.json
```

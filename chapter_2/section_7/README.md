# Chapter 2 Section 7: LLMでLLMを評価する（LLM-as-a-Judge）

## 概要

このプロジェクトは、**LLM-as-a-Judge**（LLMを審査員として活用する設計手法）の実装を示すサンプルコードです。LLMが生成したコンテンツを別のLLMが自動的に評価することで、品質管理の自動化と効率化を実現します。

OpenAI、Google Gemini、Anthropic Claudeの3つのプロバイダーに対応し、**クロスプロバイダー評価**（異なるプロバイダーで生成と評価を行う）もサポートしています。キャラクター生成という具体的なユースケースを通じて、LLM-as-a-Judgeの実践的な実装方法を学ぶことができます。

## 機能

### 基本機能
- **自動品質評価**: 生成されたすべてのキャラクターを自動的に評価
- **構造化評価結果**: JSON形式で詳細な評価結果を出力
- **3つの評価軸**: 正確性（accuracy）、網羅性（comprehensiveness）、明瞭さ（clarity）
- **スコアリング**: 1-5点の5段階評価と総合スコア算出
- **品質閾値チェック**: 設定した閾値（デフォルト3.0/5.0）を下回る場合に警告

### 高度な機能
- **クロスプロバイダー評価**: 異なるLLMプロバイダーで生成と評価を実行
- **リクエストパラメータ評価**: 生成されたキャラクターが元のリクエスト要件（性別、年齢、追加指示）を満たしているかを自動検証
- **カスタム評価基準**: プログラマティックAPIでドメイン固有の評価基準を定義可能
- **温度パラメータ制御**: 評価の一貫性を高めるため低温度（0.0）で実行
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic Claude APIの3つをサポート
- **プロバイダー別プロンプト**: 各LLMプロバイダーの特性に最適化されたプロンプト形式を自動選択
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し

### システム機能
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果と評価結果をそれぞれJSON形式でファイルに保存

## プロジェクト構成

### アーキテクチャ

このプロジェクトは、以下の多層アーキテクチャで構成されています：

```
┌────────────────────────────────────────────────┐
│         CLI Layer (main.py)                    │
│  - コマンドライン引数解析                       │
│  - 生成と評価の統合ワークフロー                 │
│  - 出力ディレクトリ管理                         │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│      Business Logic Layer                      │
│  ┌──────────────────────────────────────────┐  │
│  │  生成サービス (request_llm.py)           │  │
│  │  - request_openai()                      │  │
│  │  - request_gemini()                      │  │
│  │  - request_with_judge() ★統合機能       │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  評価サービス (llm_as_a_judge.py)        │  │
│  │  - judge_with_openai()                   │  │
│  │  - judge_with_gemini()                   │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  プロンプト生成                           │  │
│  │  - make_prompt() (キャラクター生成)      │  │
│  │  - make_judge_prompt() (評価)            │  │
│  │  - make_custom_judge_prompt() (カスタム) │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  データモデル                             │  │
│  │  - CharacterRequest/Response             │  │
│  │  - JudgeRequest/Response                 │  │
│  │  - EvaluationCriterion                   │  │
│  └──────────────────────────────────────────┘  │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│      Infrastructure Layer                      │
│  - 設定管理 (config.py)                        │
│  - ログ管理 (logger.py)                        │
│  - LLMクライアント (llm_client.py)             │
│  - 外部API (OpenAI, Gemini)                    │
└────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.42.0
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
AWS_REGION=us-east-1
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方（同じプロバイダーで生成と評価）

```bash
# Geminiで生成し、Geminiで評価
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5

# OpenAIで生成し、OpenAIで評価
uv run python -m src.main -g FEMALE -a 25 -lp OPENAI -m GPT_5_4

# Anthropicで生成し、Anthropicで評価
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_SONNET_4_6
```

#### クロスプロバイダー評価（推奨）

異なるプロバイダーで生成と評価を行うことで、より客観的な評価が可能になります：

```bash
# Geminiで生成、OpenAIで評価
uv run python -m src.main \
  -g FEMALE -a 25 \
  -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -jp OPENAI -jm GPT_5_4

# OpenAIで生成、Anthropicで評価
uv run python -m src.main \
  -g MALE -a 40 \
  -lp OPENAI -m GPT_5_4 \
  -jp ANTHROPIC -jm CLAUDE_SONNET_4_6

# Anthropicで生成、Geminiで評価
uv run python -m src.main \
  -g FEMALE -a 30 \
  -lp ANTHROPIC -m CLAUDE_SONNET_4_6 \
  -jp ANTHROPIC -jm CLAUDE_SONNET_4_6
```

#### 追加指示の指定

```bash
uv run python -m src.main \
  -g FEMALE -a 30 \
  -ai "mysterious artist" \
  -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -jp OPENAI -jm GPT_5_4
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```bash
$ uv run python -m src.main --help                                              
Usage: python -m src.main [OPTIONS]

Options:
  -g, --gender [FEMALE|MALE]      The gender of the character to generate.
                                  [required]
  -a, --age INTEGER RANGE         The age of the character to generate.
                                  [0<=x<=100; required]
  -ai, --additional-instructions TEXT
                                  Additional instructions for character
                                  generation.
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_5|GPT_5_4|CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -jp, --judge-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use for judgment
                                  (defaults to same as generation provider).
  -jm, --judge-model [GPT_5_5|GPT_5_4|CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for judgment (defaults to
                                  same as generation model).
  --help                          Show this message and exit.
```

### 出力例

実行すると、2つのJSONファイルが生成されます：

#### 1. キャラクターファイル

**ファイル名**: `outputs/gemini_character_a1b2c3d4e5f6.json`

```json
{
    "first_name": "Mika",
    "last_name": "Nekomura",
    "gender": "female",
    "age": 20,
    "personalities": [
        {
            "short_personality": "執拗な好奇心",
            "description": "糸の端を見ると放っておけない猫のように、謎や矛盾を見つけると夜更けまで追い続ける。細部に触れる指先が鋭く、痕跡から物語を復元するのが得意。質問は静かだが核心を突き、沈黙の間に相手の本心を引き出す。薄明の時間に最も冴え、街の路地という迷路を自分の縄張りのように歩く。"
        },
        {
            "short_personality": "自立としなやかさ",
            "description": "群れにも孤独にも居心地を見つけられる、猫背の自由主義者。締め付けられると音もなく距離を取り、必要な時だけ柔らかく寄り添う。計画が崩れても体の向きを変えるように素早く切り替え、失敗を静かに糧にする。誰にも馴れないわけではないが、首輪は自分で選ぶタイプ。"
        },
        {
            "short_personality": "温かな警戒心",
            "description": "初対面には警戒線を引くが、一度心を許した相手にはひざ掛けのような温もりを惜しまない。弱者や迷子にはすぐ気づき、さりげない手助けを置き土産のように残す。一方で境界線を越えられると、爪のように鋭い言葉で静かに距離を戻す。優しさと自己防衛のバランスを本能的に保てる。"
        }
    ]
}
```

#### 2. 評価ファイル

**ファイル名**: `outputs/openai_judge_a1b2c3d4e5f6.json`（クロスプロバイダー評価の場合）

```json
{
    "evaluations": [
        {
            "reasoning": "パラメータ（Gender: female, Age: 20）に忠実で、猫の要素も性格描写に一貫して反映。事実関係の矛盾や不正確さはなく、架空キャラ生成という要件に適合している。",
            "criterion_name": "accuracy",
            "score": 5
        },
        {
            "reasoning": "名前と年齢、性別に加え、3つの側面から具体的かつ豊かな性格描写があり、行動傾向や対人スタイルまで掘り下げている。背景設定はないが、質問は性格の詳細を主眼としており十分に満たしている。",
            "criterion_name": "comprehensiveness",
            "score": 5
        },
        {
            "reasoning": "日本語の表現は明快でイメージが湧きやすく、比喩も過剰ではない。JSON構造で整理され可読性が高い。",
            "criterion_name": "clarity",
            "score": 5
        }
    ],
    "overall_score": 5.0,
    "summary": "要件を正確に満たし、詳細で魅力的な性格描写が明瞭に提示されている優れた回答です。大きな改善点は見当たりません。"
}
```

#### 実行ログ例

```bash
$ uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5

[2026-01-17 17:04:18,436] [INFO] [__main__] [main.py:99] [main] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: 

Generation LLM: gemini / global.anthropic.claude-haiku-4-5-20251001-v1:0
Judge LLM: gemini / global.anthropic.claude-haiku-4-5-20251001-v1:0
Output directory: outputs
[2026-01-17 17:04:18,436] [INFO] [src.service.request_llm] [request_llm.py:66] [request_with_judge] Generating prompt...
[2026-01-17 17:04:18,437] [INFO] [src.service.request_llm] [request_llm.py:69] [request_with_judge] Generating character...
[2026-01-17 17:04:22,542] [INFO] [src.service.request_llm] [request_llm.py:42] [request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""{
  "first_name": "Akira",
  "last_name": "Yamada",
  "gender": "female",
  "age": 25,
  "personalities": [
    {
      "short_personality": "好奇心旺盛",
      "description": "アキラは常に新しい知識や経験を求めています。見慣れない場所や物事には特に興味を示し、納得がいくまで探求しようとします。"
    },
    {
      "short_personality": "観察力がある",
      "description": "周囲の環境や人々の微細な変化にもすぐに気づきます。会話の少ないときでも、人や状況を詳細に分析していることが多いです。"
    },
    {
      "short_personality": "内向的だが芯が強い",
      "description": "初対面の人や大人数の場では控えめですが、自分の信念や大切なものを守るためには断固とした態度を取ります。困難な状況でも冷静さを保ち、解 決策を見つけ出そうと努力するタイプです。"
    }
  ]
}"""
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='global.anthropic.claude-haiku-4-5-20251001-v1:0' prompt_feedback=None response_id='hkJraffyFrue1e8P3OvHoAs' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=246,
  prompt_token_count=388,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=388
    ),
  ],
  thoughts_token_count=404,
  total_token_count=1038
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='Akira', last_name='Yamada', gender=<Gender.FEMALE: 'female'>, age=25, personalities=[CharacterPersonality(short_personality='好奇心旺盛', description='アキラは常に新しい知識や経験を求めています。見慣れない場所や物事には特に興味を示し、納得がいくまで探求しようとします。'), CharacterPersonality(short_personality='観察力がある', description='周囲の環境や人々の微細な変化にもすぐに気づきま す。会話の少ないときでも、人や状況を詳細に分析していることが多いです。'), CharacterPersonality(short_personality='内向的だが芯が強い', description='初対面 の人や大人数の場では控えめですが、自分の信念や大切なものを守るためには断固とした態度を取ります。困難な状況でも冷静さを保ち、解決策を見つけ出そうと努力する タイプです。')])
[2026-01-17 17:04:22,543] [INFO] [src.service.request_llm] [request_llm.py:79] [request_with_judge] Character generation completed.
[2026-01-17 17:04:22,543] [INFO] [src.service.request_llm] [request_llm.py:81] [request_with_judge] Evaluating character with LLM-as-a-Judge...
[2026-01-17 17:04:22,543] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:47] [judge_with_gemini] Requesting judgment from Gemini model: global.anthropic.claude-haiku-4-5-20251001-v1:0
[2026-01-17 17:04:28,273] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:61] [judge_with_gemini] Judgment completed. Overall score: 5.00/5.0
[2026-01-17 17:04:28,273] [INFO] [src.service.request_llm] [request_llm.py:115] [request_with_judge] Evaluation completed. Overall score: 5.00/5.0
[2026-01-17 17:04:28,275] [INFO] [__main__] [main.py:140] [main] Character file saved to outputs/765f1492a4a34acdb86e7066dd161f42_gemini_character.json
[2026-01-17 17:04:28,275] [INFO] [__main__] [main.py:145] [main] Judge evaluation saved to outputs/765f1492a4a34acdb86e7066dd161f42_gemini_judge.json
[2026-01-17 17:04:28,275] [INFO] [__main__] [main.py:146] [main] Overall evaluation score: 5.00/5.0
```

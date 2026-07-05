# Chapter 6 Section 3: 複数推論と候補評価（Best-of-N with LLM-as-a-Judge）

## 概要

LLMの出力プロセスは確率的であり、同一のプロンプトを与えても品質や内容にばらつきが生じます。本プロジェクトでは、1回のリクエストで複数の出力候補を並列生成し、LLM自身を評価者として活用する「LLM-as-a-Judge」パターンで各候補をスコアリングし、最も優れた候補を自動選択する仕組みを実装しています。

このアーキテクチャにより、人手を介さずに出力の安定性と品質を高めることができます。すべての候補が品質閾値を下回った場合は自動的に再生成を行い、最大リトライ回数に達した場合はフォールバックとして最高スコアの候補を返却します。

## 機能

- **Best-of-N 候補生成**: 指定した数（1〜10）の候補を並列に生成
- **LLM-as-a-Judge 評価**: 生成された各候補を「正確性」「網羅性」「明瞭さ」の3軸で自動評価
- **品質閾値による選別**: 設定した閾値（1.0〜5.0）を超えた候補のみを採用
- **自動リトライ**: すべての候補が閾値未満の場合、自動的に再生成
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic の3つのLLMプロバイダーに対応
- **生成・評価の分離**: 生成用LLMと評価用LLMを別々に指定可能

## プロジェクト構成

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI (main.py)                                 │
│   --num-candidates, --quality-threshold, --max-retries                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    request_with_best_of_n()                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              Parallel Candidate Generation                       │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐      ┌──────────┐   │   │
│  │   │Candidate │  │Candidate │  │Candidate │ ...  │Candidate │   │   │
│  │   │    1     │  │    2     │  │    3     │      │    N     │   │   │
│  │   └────┬─────┘  └────┬─────┘  └────┬─────┘      └────┬─────┘   │   │
│  └────────│─────────────│─────────────│─────────────────│─────────┘   │
│           │             │             │                 │              │
│           ▼             ▼             ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              LLM-as-a-Judge Evaluation (Parallel)                │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐      ┌──────────┐   │   │
│  │   │ Score:   │  │ Score:   │  │ Score:   │ ...  │ Score:   │   │   │
│  │   │  4.2/5   │  │  3.1/5   │  │  4.8/5   │      │  2.5/5   │   │   │
│  │   └──────────┘  └──────────┘  └──────────┘      └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Threshold Check                               │   │
│  │   passing_candidates = [c for c if score >= threshold]          │   │
│  │                                                                  │   │
│  │   if passing_candidates:                                         │   │
│  │       return max(passing_candidates, key=score)  ─────────────▶ │   │
│  │   else:                                                          │   │
│  │       retry (up to max_retries) or fallback                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   Best Candidate +    │
                        │   Judge Evaluation    │
                        │   (JSON output)       │
                        └───────────────────────┘
```

### 評価軸（LLM-as-a-Judge）

| 評価軸 | 説明 |
|--------|------|
| **正確性 (accuracy)** | 回答が質問に対して正確かつ事実として正しいか |
| **網羅性 (comprehensiveness)** | 質問に対して必要な情報が十分に含まれているか |
| **明瞭さ (clarity)** | 回答が理解しやすく、適切な表現で書かれているか |

各評価軸は1〜5点でスコアリングされ、`overall_score` は各軸の平均値となります。

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - `click` - CLIフレームワーク
  - `pydantic` - データバリデーション
  - `openai` - OpenAI API クライアント
  - `google-genai` - Google Gemini API クライアント
  - `anthropic` - Anthropic API クライアント
  - `python-dotenv` - 環境変数管理

### セットアップ

1. **環境変数ファイルを作成**

```bash
cp .envrc.example .envrc
```

2. **`.envrc` にAPIキーを設定**

```bash
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

3. **依存ライブラリをインストール**

```bash
uv sync
```

### 使用方法、実行方法

#### 基本的な実行

```bash
uv run python -m src.main \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH
```

#### Best-of-N パラメータを指定

```bash
uv run python -m src.main \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --num-candidates 5 \
  --quality-threshold 4.0 \
  --max-retries 3
```

#### 生成と評価で異なるモデルを使用

```bash
uv run python -m src.main \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --judge-provider OPENAI \
  --judge-model GPT_5_2
```

### CLIオプション一覧

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
  -m, --model [GPT_5_2|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_5|CLAUDE_OPUS_4_8|CLAUDE_OPUS_4_7|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -jp, --judge-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use for judgment
                                  (defaults to same as generation provider).
  -jm, --judge-model [GPT_5_2|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_5|CLAUDE_OPUS_4_8|CLAUDE_OPUS_4_7|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for judgment (defaults to
                                  same as generation model).
  -n, --num-candidates INTEGER RANGE
                                  Number of candidates to generate for Best-
                                  of-N selection.  [1<=x<=10]
  -qt, --quality-threshold FLOAT RANGE
                                  Minimum quality threshold for accepting a
                                  candidate (1.0-5.0).  [1.0<=x<=5.0]
  -mr, --max-retries INTEGER RANGE
                                  Maximum retry attempts when all candidates
                                  fail threshold.  [1<=x<=10]
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 説明 | デフォルト |
|------------|--------|------|------------|
| `--gender` | `-g` | キャラクターの性別 (female/male) | female |
| `--age` | `-a` | キャラクターの年齢 (0-100) | 25 |
| `--additional-instructions` | `-ai` | 追加の生成指示 | "" |
| `--llm-provider` | `-lp` | 生成用LLMプロバイダー (openai/gemini/anthropic) | gemini |
| `--model` | `-m` | 生成用モデル名 | (必須) |
| `--output-directory` | `-od` | 出力ディレクトリ | outputs |
| `--judge-provider` | `-jp` | 評価用LLMプロバイダー | (生成と同じ) |
| `--judge-model` | `-jm` | 評価用モデル名 | (生成と同じ) |
| `--num-candidates` | `-n` | 生成する候補数 (1-10) | 3 |
| `--quality-threshold` | `-qt` | 品質閾値 (1.0-5.0) | 3.0 |
| `--max-retries` | `-mr` | 最大リトライ回数 (1-10) | 3 |

### 出力例

#### キャラクター出力 (character.json)

```json
{
    "first_name": "アヤカ",
    "last_name": "サクラバ",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "好奇心旺盛",
            "description": "常に新しい知識や経験を求めており、特に忘れ去られた歴史や珍しい文化に強い関心を持つ。どんな小さな手がかりも見逃さず、疑問に感じたことは徹底的に調べ上げようとする。この特性が彼女を様々な冒険へと駆り立てる原動力となっている。"
        },
        {
            "short_personality": "鋭い観察力",
            "description": "周囲の環境や人々の行動を注意深く観察する習慣がある。細かい変化や隠された意味に気づくことができ、多くの場合、誰もが見過ごしてしまうような手がかりから真実を見抜く。この能力は、彼女が未解明な謎を解き明かす上で非常に役立っている。"
        },
        {
            "short_personality": "独立心が強く、自律的",
            "description": "自分の意見や信念に基づいて行動し、他人に頼ることをあまりしない。困難な状況に直面しても、まずは自分の力で解決策を見つけようと努める。ただし、それが頑固さとして受け取られることもあるが、彼女の自律的な姿勢は周りに良い影響を与えることもある。"
        }
    ]
}
```

#### 評価出力 (judge.json)

```json
{
    "evaluations": [
        {
            "reasoning": "リクエストパラメータのGender: female、Age: 25を満たしており、内容にも矛盾はありません。事実性を問うタイプの質問ではないため、ハルシネーションの問題も特に見当たりません。",
            "criterion_name": "accuracy",
            "score": 5
        },
        {
            "reasoning": "性別・年齢に加え、複数の性格特性と詳細な説明が提示されており「詳細な性格」という要件は概ね満たしています。一方で、質問の「ユニークで興味深い」に対しては、背景設定（世界観、職業、目的、弱点、葛藤、口調や癖など）の情報が少なく、キャラクターとしての独自性を強く印象づける要素がやや不足しています。",
            "criterion_name": "comprehensiveness",
            "score": 4
        },
        {
            "reasoning": "JSON形式で整理され、性格ごとに短いラベルと説明が分かれていて読みやすいです。表現も自然で、過度な専門用語はなく理解しやすい一方、フィクションキャラクターとしてのフックが文章上で明確に打ち出されているとは言い切れません。",
            "criterion_name": "clarity",
            "score": 4
        }
    ],
    "overall_score": 4.3,
    "summary": "指定された性別・年齢に正確に合致し、性格の記述も明瞭です。より「ユニークで興味深い」キャラクターにするには、背景や動機、弱点などの追加情報があると網羅性がさらに高まります。"
}
```

#### 実行ログ

```bash
$ uv run python -m src.main \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --judge-provider OPENAI \
  --judge-model GPT_5_2

[2026-02-08 09:37:40,067] [INFO] [__main__] [main.py:124] [main] Character Generation Request (Best-of-3):
Gender: female
Age: 25
Additional Instructions: 

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: openai / gpt-5.2
Quality Threshold: 3.0/5.0
Max Retries: 3
Output directory: outputs
[2026-02-08 09:37:40,068] [INFO] [src.service.request_llm] [request_llm.py:175] [request_with_best_of_n] Starting Best-of-3 generation with threshold 3.0
[2026-02-08 09:37:40,068] [INFO] [src.service.request_llm] [request_llm.py:176] [request_with_best_of_n] Generation: gemini/gemini-2.5-flash, Judge: openai/gpt-5.2
[2026-02-08 09:37:40,068] [INFO] [src.service.request_llm] [request_llm.py:80] [generate_single_candidate] Generating candidate 1...
[2026-02-08 09:37:40,103] [INFO] [src.service.request_llm] [request_llm.py:80] [generate_single_candidate] Generating candidate 2...
[2026-02-08 09:37:40,104] [INFO] [src.service.request_llm] [request_llm.py:80] [generate_single_candidate] Generating candidate 3...
[2026-02-08 09:37:43,131] [INFO] [src.service.request_llm] [request_llm.py:57] [request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text='{"first_name": "Akari", "last_name": "Miyazaki", "gender": "female", "age": 25, "personalities": [{"short_personality": "Insightful", "description": "Akari possesses a deep sense of perception, often noticing details and underlying emotions that others miss. She can quickly grasp complex situations and offer well-reasoned perspectives, making her a trusted advisor among her friends."}, {"short_personality": "Determined", "description": "Once Akari sets her mind on a goal, she exhibits remarkable perseverance. She\'s not easily swayed by setbacks or difficulties and will put in the necessary effort and time to achieve her objectives, often inspiring others with her tenacity."}, {"short_personality": "Gentle", "description": "Despite her determination, Akari has a very gentle and compassionate nature. She approaches interactions with kindness and empathy, always mindful of others\' feelings, and often seeks to create harmonious environments for those around her."}]}'
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='1tqHaduZPNmwvr0PlK7viQ8' usage_metadata=GenerateContentResponseUsageMetadata(
  cache_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=341
    ),
  ],
  cached_content_token_count=341,
  candidates_token_count=205,
  prompt_token_count=388,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=388
    ),
  ],
  thoughts_token_count=177,
  total_token_count=770
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='Akari', last_name='Miyazaki', gender=<Gender.FEMALE: 'female'>, age=25, personalities=[CharacterPersonality(short_personality='Insightful', description='Akari possesses a deep sense of perception, often noticing details and underlying emotions that others miss. She can quickly grasp complex situations and offer well-reasoned perspectives, making her a trusted advisor among her friends.'), CharacterPersonality(short_personality='Determined', description="Once Akari sets her mind on a goal, she exhibits remarkable perseverance. She's not easily swayed by setbacks or difficulties and will put in the necessary effort and time to achieve her objectives, often inspiring others with her tenacity."), CharacterPersonality(short_personality='Gentle', description="Despite her determination, Akari has a very gentle and compassionate nature. She approaches interactions with kindness and empathy, always mindful of others' feelings, and often seeks to create harmonious environments for those around her.")])
[2026-02-08 09:37:43,132] [INFO] [src.service.request_llm] [request_llm.py:100] [evaluate_candidate] Evaluating candidate 2 with LLM-as-a-Judge...
[2026-02-08 09:37:43,132] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:27] [judge_with_openai] Requesting judgment from OpenAI model: gpt-5.2
[2026-02-08 09:37:45,321] [INFO] [src.service.request_llm] [request_llm.py:57] [request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""{
  "first_name": "アヤカ",
  "last_name": "サクラバ",
  "gender": "female",
  "age": 25,
  "personalities": [
    {
      "short_personality": "好奇心旺盛",
      "description": "常に新しい知識や経験を求めており、特に忘れ去られた歴史や珍しい文化に強い関心を持つ。どんな小さな手がかりも見逃さず、疑問に感じたことは徹底的に調べ上げようとする。この特性が彼女を様々な冒険へと駆り立てる原動力となっている。"
    },
    {
      "short_personality": "鋭い観察力",
      "description": "周囲の環境や人々の行動を注意深く観察する習慣がある。細かい変化や隠された意味に気づくことができ、多くの場合、誰もが見過ごしてしまうような手がかりから真実を見抜く。この能力は、彼女が未解明な謎を解き明かす上で非常に役立っている。"
    },
    {
      "short_personality": "独立心が強く、自律的",
      "description": "自分の意見や信念に基づいて行動し、他人に頼ることをあまりしない。困難な状況に直面しても、まずは自分の力で解決策を見つけようと努める。ただし、それが頑固さとして受け取られることもあるが、彼女の自律的な姿勢は周りに良い影響を与えることもある。"
    }
  ]
}"""
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='2dqHaYXeCL-l0-kPlu2EqQI' usage_metadata=GenerateContentResponseUsageMetadata(
  cache_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=341
    ),
  ],
  cached_content_token_count=341,
  candidates_token_count=325,
  prompt_token_count=388,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=388
    ),
  ],
  thoughts_token_count=500,
  total_token_count=1213
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='アヤカ', last_name='サクラバ', gender=<Gender.FEMALE: 'female'>, age=25, personalities=[CharacterPersonality(short_personality='好奇心旺盛', description='常に新しい知識や経験を求めており、特に忘れ去られた歴史や珍し い文化に強い関心を持つ。どんな小さな手がかりも見逃さず、疑問に感じたことは徹底的に調べ上げようとする。この特性が彼女を様々な冒険へと駆り立てる原動力となっている。'), CharacterPersonality(short_personality='鋭い観察力', description='周囲の環境や人々の行動を注意深く観察する習慣がある。細かい変化や隠された意味に気づくことができ、多くの場合、誰もが見過ごしてしまうような手がかりから真実を見抜く。この能力は、彼女が未解明な謎を解き明かす上で非常に役立っている。'), CharacterPersonality(short_personality='独立心が強く、自律的', description='自分の意見や信念に基づいて行動し、他人に頼ることをあまりしない。困難な状況に直面しても、まずは自分の力で解決策を見つけようと努める。ただし、それが頑固さとして受け取られることもあるが、彼女の自律的な姿勢は周りに良い影響を与えることもある。')])
[2026-02-08 09:37:45,321] [INFO] [src.service.request_llm] [request_llm.py:100] [evaluate_candidate] Evaluating candidate 1 with LLM-as-a-Judge...
[2026-02-08 09:37:45,322] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:27] [judge_with_openai] Requesting judgment from OpenAI model: gpt-5.2
[2026-02-08 09:37:45,323] [INFO] [src.service.request_llm] [request_llm.py:57] [request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""{
  "first_name": "アキラ",
  "last_name": "ミズキ",
  "gender": "female",
  "age": 25,
  "personalities": [
    {
      "short_personality": "止まらない好奇心",
      "description": "アキラは常に新しい知識や経験を追い求め、疑問に思ったことは徹底的に調べないと気が済まない。周りの世界や人々に深く興味を持ち、表面的な事柄だけでなく、その裏に隠された真実や動機を探ろうとする。この飽くなき探求心は、時に大胆な行動へと繋がることもある。"
    },
    {
      "short_personality": "不屈の楽観主義",
      "description": "どんな困難な状況に直面しても、アキラは常に明るい面を見つけ出し、前向きに物事を捉えることができる。失敗を恐れず、むしろそれを成長の機会と捉える傾向があるため、周囲の人々にも希望と活力を与える存在である。しかし、時に現実を少し甘く見過ぎる傾向がある。"
    },
    {
      "short_personality": "自立した精神",
      "description": "アキラは自分の意見や価値観を強く持ち、他者の影響を受けにくい。物事を一人で解決しようとする傾向があり、チームワークよりも単独行動を好むこともある。自身の判断力と能力を信頼しており、困難な状況でも他者に頼ることなく、自身の力で切り開いていく強さを持っている。"
    }
  ]
}"""
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='2dqHabr2B9OJ1e8PmJzKwAc' usage_metadata=GenerateContentResponseUsageMetadata(
  cache_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=341
    ),
  ],
  cached_content_token_count=341,
  candidates_token_count=347,
  prompt_token_count=388,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=388
    ),
  ],
  thoughts_token_count=549,
  total_token_count=1284
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='アキラ', last_name='ミズキ', gender=<Gender.FEMALE: 'female'>, age=25, personalities=[CharacterPersonality(short_personality='止まらない好奇心', description='アキラは常に新しい知識や経験を追い求め、疑問に思ったこと は徹底的に調べないと気が済まない。周りの世界や人々に深く興味を持ち、表面的な事柄だけでなく、その裏に隠された真実や動機を探ろうとする。この飽くなき探求心は、時に大胆な行動へと繋がることもある。'), CharacterPersonality(short_personality='不屈の楽観主義', description='どんな困難な状況に直面しても、アキラは常に明るい面を見つけ出し、前向きに物事を捉えることができる。失敗を恐れず、むしろそれを成長の機会と捉える傾向があるため、周囲の人々にも希望と活力を与える存在である。しかし、時に現実を少し甘く見過ぎる傾向がある。'), CharacterPersonality(short_personality='自立した精神', description='アキラは自分の意見や価値観を強く持ち、他者の影響を受けにくい。物事を一人で解決しようとする傾向があり、チームワークよりも単独行動を好むこともある。自身の判断力と能力を信頼しており、困難な状況でも他者に頼ることなく、自身の力で切り開いていく強さを持っている。')])
[2026-02-08 09:37:45,324] [INFO] [src.service.request_llm] [request_llm.py:100] [evaluate_candidate] Evaluating candidate 3 with LLM-as-a-Judge...
[2026-02-08 09:37:45,324] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:27] [judge_with_openai] Requesting judgment from OpenAI model: gpt-5.2
[2026-02-08 09:37:52,381] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:36] [judge_with_openai] Judgment completed. Overall score: 3.70/5.0
[2026-02-08 09:37:52,381] [INFO] [src.service.request_llm] [request_llm.py:129] [evaluate_candidate] Candidate 2 score: 3.70/5.0
[2026-02-08 09:37:52,716] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:36] [judge_with_openai] Judgment completed. Overall score: 4.30/5.0
[2026-02-08 09:37:52,716] [INFO] [src.service.request_llm] [request_llm.py:129] [evaluate_candidate] Candidate 1 score: 4.30/5.0
[2026-02-08 09:37:54,215] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:36] [judge_with_openai] Judgment completed. Overall score: 3.67/5.0
[2026-02-08 09:37:54,215] [INFO] [src.service.request_llm] [request_llm.py:129] [evaluate_candidate] Candidate 3 score: 3.67/5.0
[2026-02-08 09:37:54,215] [INFO] [src.service.request_llm] [request_llm.py:203] [request_with_best_of_n] Selected candidate 1 with score 4.30/5.0
[2026-02-08 09:37:54,216] [INFO] [__main__] [main.py:170] [main] Character file saved to outputs/5bcaaab304e84f1fba944b67b1dbb161_gemini_character.json
[2026-02-08 09:37:54,216] [INFO] [__main__] [main.py:175] [main] Judge evaluation saved to outputs/5bcaaab304e84f1fba944b67b1dbb161_openai_judge.json
[2026-02-08 09:37:54,216] [INFO] [__main__] [main.py:176] [main] Overall evaluation score: 4.30/5.0
```

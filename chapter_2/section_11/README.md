# Chapter 2 Section 11: プロンプトパフォーマンスのプロファイリング

## 概要

本プロジェクトは、LLMへのプロンプト実行を定量的に計測・分析し、品質、コスト、応答速度の最適化を科学的に実現するプロファイリングシステムの実装例です。

従来の「勘と経験」に頼った感覚的なプロンプト調整から脱却し、データドリブンな改善サイクルを確立することで、プロンプトエンジニアリングを工学的な営みへと昇華させます。各プロンプトの実行に伴うメトリクス（レイテンシ、トークン使用量、コスト、品質スコア）を収集し、時系列分析や比較評価を通じてボトルネックの特定と継続的な最適化を可能にします。

本実装では、キャラクター生成タスクを題材に、3層アーキテクチャ（収集層・分析層・可視化層）によるプロファイリングシステムを構築しています。生成されたキャラクターはLLM-as-a-Judgeによって品質評価され、その結果もプロファイリングデータとして統合されます。

## 機能

- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic の3つのLLMプロバイダーをサポート
- **パフォーマンスプロファイリング**: リクエストごとのレイテンシ、トークン使用量、推定コストを自動計測
- **LLM-as-a-Judge統合**: 生成結果の品質を自動評価し、品質スコアをメトリクスに統合
- **異常検出とアラート**: 設定可能な閾値に基づく警告・クリティカルアラートの自動生成
- **多角的分析**: プロンプト別、モデル別、プロバイダー別、時系列での集計と比較
- **複数形式でのレポート出力**: JSON、HTML、テキスト形式でのレポート生成

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_8/
├── CLAUDE.md                 # プロジェクト仕様書
├── README.md                 # 本ファイル
├── pyproject.toml            # 依存関係定義
├── .envrc.example            # 環境変数テンプレート
├── Makefile                  # ビルドコマンド
├── src/
│   ├── __init__.py
│   ├── main.py               # CLIエントリーポイント
│   ├── config.py             # 設定管理
│   ├── logger.py             # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py     # LLMクライアント定義
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py          # キャラクターモデル
│   │   ├── llm_as_a_judge_model.py  # 評価モデル
│   │   └── profiler_metrics.py      # プロファイラーメトリクスモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── prompt.py         # キャラクター生成プロンプト
│   │   └── llm_as_a_judge_prompt.py  # 評価プロンプト
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py    # 標準LLMリクエスト
│       ├── llm_as_a_judge.py # 評価サービス
│       ├── prompt_profiler.py      # 収集層
│       ├── metrics_analyzer.py     # 分析層
│       ├── profiler_reporter.py    # 可視化層
│       └── profiled_request_llm.py # プロファイリング付きリクエスト
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_prompt_profiler.py
    ├── test_metrics_analyzer.py
    └── test_profiler_reporter.py
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIエントリーポイント                           │
│                              (src/main.py)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
        ┌─────────────────────┐             ┌─────────────────────┐
        │   標準リクエスト     │             │  プロファイリング付き │
        │  (request_llm.py)   │             │ (profiled_request_  │
        │                     │             │      llm.py)        │
        └─────────────────────┘             └─────────────────────┘
                    │                                   │
                    │                       ┌───────────┴───────────┐
                    │                       ▼                       ▼
                    │           ┌─────────────────────┐   ┌─────────────────┐
                    │           │   【収集層】         │   │                 │
                    │           │  PromptProfiler     │   │  LLM-as-a-Judge │
                    │           │ (prompt_profiler.py)│   │                 │
                    │           └─────────────────────┘   └─────────────────┘
                    │                       │
                    │                       ▼
                    │           ┌─────────────────────┐
                    │           │   【分析層】         │
                    │           │  MetricsAnalyzer    │
                    │           │(metrics_analyzer.py)│
                    │           └─────────────────────┘
                    │                       │
                    │                       ▼
                    │           ┌─────────────────────┐
                    │           │   【可視化層】       │
                    │           │  ProfilerReporter   │
                    │           │(profiler_reporter.py)│
                    │           └─────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │                         LLMクライアント                              │
        │                      (llm_client.py)                                │
        │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐   │
        │  │   OpenAI    │   │   Gemini    │   │       Anthropic         │   │
        │  └─────────────┘   └─────────────┘   └─────────────────────────┘   │
        └─────────────────────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - `anthropic>=0.74.1`
  - `click>=8.3.0`
  - `google-genai>=1.45.0`
  - `openai>=2.4.0`
  - `pydantic>=2.12.2`
  - `python-dotenv>=1.1.1`

### セットアップ

1. 環境変数を設定:

```bash
cp .envrc.example .envrc
```

`.envrc` を編集し、各LLMプロバイダーのAPIキーを設定:

```bash
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. 依存関係のインストール:

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini でキャラクター生成（プロファイリングなし）
uv run python -m src.main \
  --gender FEMALE \
  --age 25 \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH

# OpenAI でキャラクター生成（プロファイリング有効）
uv run python -m src.main \
  --gender MALE \
  --age 30 \
  --llm-provider OPENAI \
  --model GPT_5_4_MINI \
  --enable-profiling

# 異なるプロバイダーで生成と評価を分離
uv run python -m src.main \
  --gender FEMALE \
  --age 22 \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --judge-provider ANTHROPIC \
  --judge-model CLAUDE_SONNET_4_6 \
  --enable-profiling \
  --profiler-report-format html
```

#### CLIオプション一覧

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
  -m, --model [GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_OPUS_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -jp, --judge-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use for judgment
                                  (defaults to same as generation provider).
  -jm, --judge-model [GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_OPUS_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
                                  The model to use for judgment (defaults to
                                  same as generation model).
  -p, --enable-profiling          Enable performance profiling for the
                                  request.
  -prf, --profiler-report-format [json|html|txt]
                                  Format for the profiler report.
  --help                          Show this message and exit.
```

### 出力例

#### プロファイリングサマリー（ターミナル出力）

```bash
$ uv run python -m src.main \
  --gender FEMALE \
  --age 22 \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --judge-provider ANTHROPIC \
  --judge-model CLAUDE_SONNET_4_6 \
  --enable-profiling \
  --profiler-report-format html
[2026-01-18 14:22:21,221] [INFO] [__main__] [main.py:126] [main] Character Generation Request:
Gender: female
Age: 22
Additional Instructions: 

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: anthropic / claude-sonnet-4-6
Output directory: outputs
[2026-01-18 14:22:21,221] [INFO] [__main__] [main.py:155] [main] Performance profiling is enabled.
[2026-01-18 14:22:21,221] [INFO] [src.service.profiled_request_llm] [profiled_request_llm.py:146] [profiled_request_with_judge] Generating prompt...
[2026-01-18 14:22:21,221] [INFO] [src.service.profiled_request_llm] [profiled_request_llm.py:149] [profiled_request_with_judge] Generating character...
[2026-01-18 14:22:23,881] [INFO] [src.service.profiled_request_llm] [profiled_request_llm.py:94] [profiled_request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""{
  "first_name": "Akari",
  "last_name": "Sato",
  "gender": "female",
  "age": 22,
  "personalities": [
    {
      "short_personality": "Curious",
      "description": "Akari possesses an insatiable curiosity, always questioning the 'how' and 'why' of the world around her. This drives her to constantly seek out new information, learn diverse skills, and explore unfamiliar places, often getting lost in research or fascinating documentaries."
    },
    {
      "short_personality": "Resourceful",
      "description": "When faced with a challenge, Akari rarely gives up. She's incredibly resourceful, capable of improvising solutions with whatever tools are at hand and thinking outside the box. This trait makes her an excellent problem-solver in both mundane and extraordinary situations."
    },
    {
      "short_personality": "Reserved",
      "description": "Despite her adventurous spirit, Akari tends to be reserved and somewhat introspective, especially in new social settings. She prefers to observe and listen before contributing, and while she values deep connections, she's not one to easily open up to just anyone. Her emotional world often runs deeper than she lets on."
    }
  ]
}"""
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='D25saZXnLc6k0-kPj-LVuAg' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=285,
  prompt_token_count=388,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=388
    ),
  ],
  thoughts_token_count=47,
  total_token_count=720
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='Akari', last_name='Sato', gender=<Gender.FEMALE: 'female'>, age=22, personalities=[CharacterPersonality(short_personality='Curious', description="Akari possesses an insatiable curiosity, always questioning the 'how' and 'why' of the world around her. This drives her to constantly seek out new information, learn diverse skills, and explore unfamiliar places, often getting lost in research or fascinating documentaries."), CharacterPersonality(short_personality='Resourceful', description="When faced with a challenge, Akari rarely gives up. She's incredibly resourceful, capable of improvising solutions with whatever tools are at hand and thinking outside the box. This trait makes her an excellent problem-solver in both mundane and extraordinary situations."), CharacterPersonality(short_personality='Reserved', description="Despite her adventurous spirit, Akari tends to be reserved and somewhat introspective, especially in new social settings. She prefers to observe and listen before contributing, and while she values deep connections, she's not one to easily open up to just anyone. Her emotional world often runs deeper than she lets on.")])
[2026-01-18 14:22:23,881] [INFO] [src.service.prompt_profiler] [prompt_profiler.py:222] [profile] Profiled request 6291bdc3-fe8f-4b2e-9a78-6f3e72fa56a0: prompt=character_generation_gemini, model=gemini-2.5-flash, latency=2660.23ms, tokens=673 (in=388, out=285), status=success
[2026-01-18 14:22:23,881] [INFO] [src.service.profiled_request_llm] [profiled_request_llm.py:176] [profiled_request_with_judge] Character generation completed.
[2026-01-18 14:22:23,881] [INFO] [src.service.profiled_request_llm] [profiled_request_llm.py:178] [profiled_request_with_judge] Evaluating character with LLM-as-a-Judge...
[2026-01-18 14:22:23,882] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:77] [judge_with_anthropic] Requesting judgment from Anthropic model: claude-sonnet-4-6
[2026-01-18 14:22:38,478] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:88] [judge_with_anthropic] Judgment completed. Overall score: 5.00/5.0
[2026-01-18 14:22:38,479] [INFO] [src.service.prompt_profiler] [prompt_profiler.py:222] [profile] Profiled request b952c227-24ac-4a4b-b65d-64277f1c3833: prompt=llm_as_a_judge_anthropic, model=claude-sonnet-4-6, latency=14597.65ms, tokens=517 (in=311, out=206), status=success
[2026-01-18 14:22:38,480] [INFO] [src.service.profiled_request_llm] [profiled_request_llm.py:230] [profiled_request_with_judge] Evaluation completed. Overall score: 5.00/5.0
[2026-01-18 14:22:38,480] [INFO] [__main__] [main.py:180] [main] Character file saved to outputs/8779952a32fb430486c8263df4f2baec_gemini_character.json
[2026-01-18 14:22:38,480] [INFO] [__main__] [main.py:185] [main] Judge evaluation saved to outputs/8779952a32fb430486c8263df4f2baec_anthropic_judge.json
[2026-01-18 14:22:38,480] [INFO] [__main__] [main.py:186] [main] Overall evaluation score: 5.00/5.0
[2026-01-18 14:22:38,684] [INFO] [src.service.profiler_reporter] [profiler_reporter.py:515] [save_report] Report saved to: outputs/8779952a32fb430486c8263df4f2baec_profiler_report.html
[2026-01-18 14:22:38,685] [INFO] [__main__] [main.py:209] [main] Profiler report saved to outputs/8779952a32fb430486c8263df4f2baec_profiler_report.html

============================================================
PERFORMANCE PROFILING SUMMARY
============================================================
Prompt Performance Summary
==========================

Report Generated: 2026-01-18T05:22:38.685756+00:00
Sample Count: 3
Time Range: 2026-01-18T05:22:23.881766+00:00 to 2026-01-18T05:22:38.480099+00:00

LATENCY
----------------------------------------
  Mean:    6,639.37 ms
  Median:  2,660.23 ms
  P95:     14,597.65 ms
  P99:     14,597.65 ms
  Min:     2,660.23 ms
  Max:     14,597.65 ms
  Std Dev: 6,892.07 ms

TOKEN USAGE
----------------------------------------
  Total Input:   1,087
  Total Output:  776
  Total:         1,863
  Avg Input:     362.3
  Avg Output:    258.7

SUCCESS RATE
----------------------------------------
  Successful:  3
  Failed:      0
  Rate:        100.0%

QUALITY SCORES
----------------------------------------
  Average: 5.00 / 5.0
  Min:     5.00 / 5.0
  Max:     5.00 / 5.0

COST ESTIMATE
----------------------------------------
  Total: $0.0043
  Avg:   $0.0014 per request

Performance Alerts
==================

Report Generated: 2026-01-18T05:22:38.685903+00:00
Total Alerts: 1

CRITICAL ALERTS
----------------------------------------
  [2026-01-18T05:22:38] Critical latency detected: 14597.65ms exceeds 10000.0ms threshold
```

#### 生成されたキャラクター（JSON）

```json
{
    "first_name": "エミ",
    "last_name": "田中",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "好奇心旺盛",
            "description": "常に新しい知識や経験を求めています。見知らぬ場所を探索したり、未読の本を読み漁ったり、異文化に触れることに深い喜びを感じます。その探求心は彼女を常に動かし続けます。"
        },
        {
            "short_personality": "共感的",
            "description": "他人の感情や視点に深く共感し、理解しようと努めます。困っている人を見ると放っておけず、常に思いやりを持って接します。そのため、周囲からは頼れる相談相手として慕われています。"
        },
        {
            "short_personality": "決断力がある",
            "description": "一度決めた目標に向かって、迷うことなく行動できます。困難な状況に直面しても、冷静に判断し、迅速かつ効果的な解決策を見出すことができます。この特性は、彼女を頼りになるリーダーにしています。"
        }
    ]
}
```

#### 評価結果（JSON）

```json
{
    "evaluations": [
        {
            "reasoning": "リクエストパラメータ（Gender: female, Age: 25）に忠実に従っており、質問内容に沿ったキャラクター情報が正確に生成されています。誤った情報やハルシネーションは含まれていません。",
            "criterion_name": "accuracy",
            "score": 5
        },
        {
            "reasoning": "質問で求められている「詳細な性格」が3つの異なる特性として具体的に記述されており、ユーザーの要求を完全に満たしています。リクエストパラメータもすべて網羅されています。",
            "criterion_name": "comprehensiveness",
            "score": 5
        },
        {
            "reasoning": "JSON形式で構造化されており、非常に読みやすいです。各性格の説明も簡潔かつ明瞭で、専門用語もなく理解しやすい表現が使われています。",
            "criterion_name": "clarity",
            "score": 5
        }
    ],
    "overall_score": 5.0,
    "summary": "質問とリクエストパラメータに完全に合致し、詳細かつ明瞭なキャラクター情報が生成されています。非常に質の高い回答です。"
}
```

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

### 実装の詳細

#### 1. 収集層: PromptProfiler (`src/service/prompt_profiler.py`)

LLM API呼び出しをラップし、パフォーマンスメトリクスを透過的に収集します。

**ポイント**: 非同期コンテキストマネージャを使用し、メインの処理フローへの影響を最小限に抑えています。

```python
async with profiler.profile(
    prompt_id="character_generation",
    model="gpt-4o-mini",
    provider="openai",
) as ctx:
    response = await llm_client.generate(...)
    ctx["input_tokens"] = response.usage.input_tokens
    ctx["output_tokens"] = response.usage.output_tokens
```

収集されるメトリクス:
- `latency_ms`: リクエストの実行時間（ミリ秒）
- `input_tokens`: 入力トークン数
- `output_tokens`: 出力トークン数
- `estimated_cost_usd`: 推定コスト（USD）
- `quality_score`: LLM-as-a-Judgeによる品質スコア（1.0-5.0）

#### 2. 分析層: MetricsAnalyzer (`src/service/metrics_analyzer.py`)

収集したメトリクスを多次元で解析し、異常検出とアラート生成を行います。

```python
analyzer = MetricsAnalyzer()

# プロンプト別に集計
by_prompt = analyzer.aggregate_by_prompt(metrics)

# 時系列分析
time_series = analyzer.aggregate_by_time_bucket(metrics, bucket_minutes=60)
trend = analyzer.detect_trend(time_series, "latency_mean_ms")

# 異常検出とアラート生成
alerts = analyzer.generate_alerts(metric)
```

分析機能:
- 統計的集計（平均、中央値、P95、P99、標準偏差）
- プロンプト/モデル/プロバイダー別グループ化
- 時系列バケット化とトレンド検出
- 閾値ベースの異常検出
- アラート生成

#### 3. 可視化層: ProfilerReporter (`src/service/profiler_reporter.py`)

分析結果を様々な形式でレポート出力します。

```python
reporter = ProfilerReporter(analyzer)

# テキストサマリー
reporter.print_summary(metrics)

# JSON/HTML/テキストファイル出力
reporter.save_report(metrics, "report.json", format="json")
reporter.save_report(metrics, "report.html", format="html")
```

レポート形式:
- **テキスト形式**: ターミナル出力向けのフォーマット
- **JSON形式**: プログラマティックな消費やGrafana/Kibana連携用
- **HTML形式**: ビジュアルダッシュボード

#### 4. メトリクスモデル (`src/model/profiler_metrics.py`)

プロファイリングデータの構造を定義します。

```python
class ProfilerMetrics(BaseModel):
    prompt_id: str           # プロンプト識別子
    request_id: str          # リクエスト識別子
    timestamp: str           # ISO 8601タイムスタンプ
    latency_ms: float        # レイテンシ（ミリ秒）
    input_tokens: int        # 入力トークン数
    output_tokens: int       # 出力トークン数
    total_tokens: int        # 合計トークン数
    model: str               # モデル名
    provider: str            # プロバイダー名
    status: MetricStatus     # ステータス（success/error/timeout）
    quality_score: float     # 品質スコア（1.0-5.0）
    estimated_cost_usd: float  # 推定コスト（USD）
```

アラート閾値の設定:

```python
class AlertThreshold(BaseModel):
    latency_warning_ms: float = 5000.0    # レイテンシ警告閾値
    latency_critical_ms: float = 10000.0  # レイテンシクリティカル閾値
    token_warning: int = 8000             # トークン警告閾値
    token_critical: int = 16000           # トークンクリティカル閾値
    quality_warning: float = 3.0          # 品質警告閾値
    quality_critical: float = 2.0         # 品質クリティカル閾値
    cost_warning_usd: float = 0.1         # コスト警告閾値
    cost_critical_usd: float = 0.5        # コストクリティカル閾値
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
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini でキャラクター生成（プロファイリングなし）
python -m src.main \
  --gender FEMALE \
  --age 25 \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH

# OpenAI でキャラクター生成（プロファイリング有効）
python -m src.main \
  --gender MALE \
  --age 30 \
  --llm-provider OPENAI \
  --model GPT_4O_MINI \
  --enable-profiling

# 異なるプロバイダーで生成と評価を分離
python -m src.main \
  --gender FEMALE \
  --age 22 \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --judge-provider ANTHROPIC \
  --judge-model CLAUDE_SONNET_4_5 \
  --enable-profiling \
  --profiler-report-format html
```

#### CLIオプション一覧

| オプション | 短縮形 | 説明 | 必須 | デフォルト |
|-----------|--------|------|------|-----------|
| `--gender` | `-g` | キャラクターの性別 (`FEMALE`, `MALE`) | Yes | `FEMALE` |
| `--age` | `-a` | キャラクターの年齢 (0-100) | Yes | `25` |
| `--additional-instructions` | `-ai` | 追加の生成指示 | No | - |
| `--llm-provider` | `-lp` | LLMプロバイダー (`OPENAI`, `GEMINI`, `ANTHROPIC`) | Yes | `GEMINI` |
| `--model` | `-m` | 使用するモデル | Yes | - |
| `--output-directory` | `-od` | 出力ディレクトリ | No | `outputs` |
| `--judge-provider` | `-jp` | 評価用LLMプロバイダー | No | 生成と同じ |
| `--judge-model` | `-jm` | 評価用モデル | No | 生成と同じ |
| `--enable-profiling` | `-p` | プロファイリングを有効化 | No | `False` |
| `--profiler-report-format` | `-prf` | レポート形式 (`json`, `html`, `txt`) | No | `json` |

### 出力例

#### プロファイリングサマリー（ターミナル出力）

```
============================================================
PERFORMANCE PROFILING SUMMARY
============================================================
Prompt Performance Summary
==========================

Report Generated: 2025-01-15T10:30:45.123456+00:00
Sample Count: 3
Time Range: 2025-01-15T10:30:40.000000+00:00 to 2025-01-15T10:30:45.000000+00:00

LATENCY
----------------------------------------
  Mean:    2,543.21 ms
  Median:  2,345.67 ms
  P95:     3,456.78 ms
  P99:     3,456.78 ms
  Min:     1,234.56 ms
  Max:     3,456.78 ms
  Std Dev: 567.89 ms

TOKEN USAGE
----------------------------------------
  Total Input:   1,234
  Total Output:  567
  Total:         1,801
  Avg Input:     411.3
  Avg Output:    189.0

SUCCESS RATE
----------------------------------------
  Successful:  3
  Failed:      0
  Rate:        100.0%

QUALITY SCORES
----------------------------------------
  Average: 4.25 / 5.0
  Min:     3.80 / 5.0
  Max:     4.70 / 5.0

COST ESTIMATE
----------------------------------------
  Total: $0.0045
  Avg:   $0.0015 per request
```

#### 生成されたキャラクター（JSON）

```json
{
    "first_name": "美咲",
    "last_name": "桜井",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "好奇心旺盛",
            "description": "新しいことへの興味が尽きず、常に学びの機会を探している。"
        },
        {
            "short_personality": "思いやりがある",
            "description": "周囲の人々の気持ちに敏感で、困っている人を放っておけない性格。"
        },
        {
            "short_personality": "芯が強い",
            "description": "一度決めたことは最後までやり遂げる強い意志を持っている。"
        }
    ]
}
```

#### 評価結果（JSON）

```json
{
    "evaluations": [
        {
            "reasoning": "指定された性別と年齢に一致しており、名前も適切。",
            "criterion_name": "accuracy",
            "score": 5
        },
        {
            "reasoning": "3つの性格特性が詳細に記述されており、十分な情報量がある。",
            "criterion_name": "comprehensiveness",
            "score": 4
        },
        {
            "reasoning": "各性格特性の説明が明確で理解しやすい。",
            "criterion_name": "clarity",
            "score": 4
        }
    ],
    "overall_score": 4.33,
    "summary": "リクエストに忠実なキャラクター生成が行われており、全体的に高品質な出力。"
}
```

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

### ディレクトリ構成

```
chapter_6/section_3/
├── .envrc.example       # 環境変数テンプレート
├── pyproject.toml       # プロジェクト設定
├── README.md            # このファイル
├── Makefile             # 実行用Makefile
└── src/
    ├── __init__.py
    ├── main.py          # CLIエントリーポイント
    ├── config.py        # 設定管理
    ├── logger.py        # ロガー設定
    ├── client/
    │   ├── __init__.py
    │   └── llm_client.py    # LLMクライアント定義
    ├── model/
    │   ├── __init__.py
    │   ├── model.py             # キャラクター生成モデル
    │   └── llm_as_a_judge_model.py  # 評価モデル
    ├── prompt/
    │   ├── __init__.py
    │   ├── prompt.py                # 生成用プロンプト
    │   └── llm_as_a_judge_prompt.py # 評価用プロンプト
    └── service/
        ├── __init__.py
        ├── request_llm.py       # Best-of-N生成ロジック
        └── llm_as_a_judge.py    # 評価実行ロジック
```

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
  --llm-provider gemini \
  --model gemini-2.5-flash
```

#### Best-of-N パラメータを指定

```bash
uv run python -m src.main \
  --llm-provider gemini \
  --model gemini-2.5-flash \
  --num-candidates 5 \
  --quality-threshold 4.0 \
  --max-retries 3
```

#### 生成と評価で異なるモデルを使用

```bash
uv run python -m src.main \
  --llm-provider gemini \
  --model gemini-2.5-flash \
  --judge-provider openai \
  --judge-model gpt-4o
```

### CLIオプション一覧

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

### 対応モデル

| プロバイダー | モデル |
|--------------|--------|
| OpenAI | gpt-5, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-4o, gpt-4o-mini |
| Gemini | gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite |
| Anthropic | claude-sonnet-4-5, claude-opus-4-1 |

### 出力例

#### 実行ログ

```
[2024-01-15 10:30:00] [INFO] Character Generation Request (Best-of-5):
Gender: female
Age: 25
Additional Instructions:

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: gemini / gemini-2.5-flash
Quality Threshold: 4.0/5.0
Max Retries: 3
Output directory: outputs

[2024-01-15 10:30:01] [INFO] Starting Best-of-5 generation with threshold 4.0
[2024-01-15 10:30:01] [INFO] Generating candidate 1...
[2024-01-15 10:30:01] [INFO] Generating candidate 2...
[2024-01-15 10:30:01] [INFO] Generating candidate 3...
[2024-01-15 10:30:01] [INFO] Generating candidate 4...
[2024-01-15 10:30:01] [INFO] Generating candidate 5...
[2024-01-15 10:30:03] [INFO] Evaluating candidate 1 with LLM-as-a-Judge...
[2024-01-15 10:30:03] [INFO] Candidate 1 score: 4.33/5.0
[2024-01-15 10:30:04] [INFO] Candidate 2 score: 3.67/5.0
[2024-01-15 10:30:04] [INFO] Candidate 3 score: 4.67/5.0
[2024-01-15 10:30:04] [INFO] Candidate 4 score: 4.00/5.0
[2024-01-15 10:30:05] [INFO] Candidate 5 score: 3.33/5.0
[2024-01-15 10:30:05] [INFO] Selected candidate 3 with score 4.67/5.0
[2024-01-15 10:30:05] [INFO] Character file saved to outputs/abc123_gemini_character.json
[2024-01-15 10:30:05] [INFO] Judge evaluation saved to outputs/abc123_gemini_judge.json
[2024-01-15 10:30:05] [INFO] Overall evaluation score: 4.67/5.0
```

#### キャラクター出力 (character.json)

```json
{
    "first_name": "美咲",
    "last_name": "高橋",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "好奇心旺盛",
            "description": "新しいことに対して常に興味を持ち、積極的に挑戦する性格。未知の分野でも臆せず飛び込んでいく。"
        },
        {
            "short_personality": "思いやり深い",
            "description": "周囲の人々の気持ちに敏感で、困っている人を見ると放っておけない。自然と人が集まってくる温かさを持つ。"
        },
        {
            "short_personality": "芯が強い",
            "description": "一度決めたことは最後までやり遂げる意志の強さを持つ。困難に直面しても諦めずに前に進む。"
        }
    ]
}
```

#### 評価出力 (judge.json)

```json
{
    "evaluations": [
        {
            "criterion_name": "accuracy",
            "score": 5,
            "reasoning": "リクエストパラメータ（女性、25歳）に完全に一致しており、キャラクター設定に矛盾がない。"
        },
        {
            "criterion_name": "comprehensiveness",
            "score": 4,
            "reasoning": "3つの性格特性が詳細に記述されているが、背景情報があるとより良い。"
        },
        {
            "criterion_name": "clarity",
            "score": 5,
            "reasoning": "各性格特性の説明が明確で理解しやすい。専門用語も適切に避けられている。"
        }
    ],
    "overall_score": 4.67,
    "summary": "リクエスト要件を満たす高品質なキャラクター生成。性格描写が具体的で魅力的。"
}
```

### 実装の詳細

#### 並列処理による効率化

```python
tasks = [
    generate_and_evaluate_candidate(...)
    for i in range(num_candidates)
]
results: list[CandidateResult] = await asyncio.gather(*tasks)
```

`asyncio.gather()` を使用して候補生成と評価を並列実行することで、直列処理と比較してレイテンシを大幅に削減しています。

#### 閾値によるフィルタリングとフォールバック

```python
passing_candidates = [r for r in results if r.judge_result.is_passing(threshold=quality_threshold)]

if passing_candidates:
    best_candidate = max(passing_candidates, key=lambda r: r.judge_result.overall_score)
    return best_candidate.candidate, best_candidate.judge_result

# リトライまたはフォールバック
```

品質閾値を超えた候補のみを採用対象とし、すべて閾値未満の場合は再生成を試みます。最大リトライ回数に達した場合は、最もスコアの高い候補をフォールバックとして返却します。

#### 生成・評価の分離

生成用と評価用で異なるLLMを指定できるため、以下のような柔軟な運用が可能です：

- **コスト最適化**: 生成は高速・安価なモデル、評価は高精度モデル
- **バイアス軽減**: 異なるプロバイダーのモデルで評価することで偏りを軽減

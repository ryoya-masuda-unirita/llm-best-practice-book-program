# Chapter 6 Section 6: 関数呼び出しのエンジニアリング

## 概要

LLMからTool call（関数呼び出し）を行う際、出力されたデータをそのままコンテキストに含めると、トークン制限の逼迫やレイテンシの増大を招きます。本プロジェクトでは、関数実行結果を外部ストレージに保存し、IDでコンテキストに参照を残す設計手法（**ID参照パターン**）と、単一の目的を達成するために複数の処理を統合した**統合関数（Composite Function）**の設計を実演します。

このアプローチにより、トークン効率の向上、コスト削減、LLMの文脈理解の改善を同時に実現できます。従来のソフトウェア工学における関数設計の原則とは異なる視点が求められる領域であり、実用的なLLMエージェント開発における重要なプラクティスの一つです。

本プロジェクトは、学校データ（生徒情報、テストスコア、成績レポート、カリキュラム）を分析するLLMアシスタントをGemini APIとFunction Callingを使って実装しています。

## 機能

- **ID参照パターン**: Tool callの結果を外部ストレージ（`SessionResultCache`）に保存し、コンテキストには要約とIDのみを渡す
- **統合関数（Composite Function）**: 複数の処理を1回のTool callで完了できる高凝集な関数設計
- **学校データ分析**: 生徒の成績分析、クラス別パフォーマンス分析、生徒間比較
- **フィルタリング機能**: クラス、生徒、四半期でデータを柔軟にフィルタリング
- **Pull型データ取得**: LLMが必要なタイミングで`get_result_details`を使って詳細データを取得

## プロジェクト構成

### ディレクトリ構成

```
section_6/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLIエントリーポイント
│   ├── config.py                  # 設定管理（API Key等）
│   ├── logger.py                  # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py          # Gemini APIクライアント
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py               # Pydanticモデル（ToolResult等）
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py              # システムプロンプト・ツール定義
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py         # LLMリクエスト処理・セッションキャッシュ
│       └── tools/
│           ├── __init__.py
│           ├── data_tools.py      # 統合関数（Composite Functions）
│           └── functions/
│               ├── __init__.py
│               ├── loaders.py     # データ読み込み
│               ├── validators.py  # 入力検証
│               ├── analyzers.py   # データ分析（Polars使用）
│               └── formatters.py  # 結果フォーマット
├── data/
│   ├── students.json              # 生徒マスタ（5名）
│   ├── 1st_quarter_test_score.json
│   ├── 2nd_quarter_test_score.json
│   ├── 3rd_quarter_test_score.json
│   ├── 4th_quarter_test_score.json
│   ├── 1st_quarter_grade_report.json
│   ├── 2nd_quarter_grade_report.json
│   ├── 3rd_quarter_grade_report.json
│   ├── 4th_quarter_grade_report.json
│   ├── 1st_quarter_curriculum.json
│   ├── 2nd_quarter_curriculum.json
│   ├── 3rd_quarter_curriculum.json
│   └── 4th_quarter_curriculum.json
├── pyproject.toml
├── .envrc.example
├── Makefile
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI (main.py)                                  │
│  • click によるコマンドライン引数処理                                      │
│  • セッション管理とログ出力                                               │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    request_llm.py                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  SessionResultCache                                               │   │
│  │  • Tool call結果を保存                                            │   │
│  │  • result_id でデータ参照                                         │   │
│  │  • max_size による容量管理                                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  process_with_function_calling()                                  │   │
│  │  • Gemini API呼び出し                                             │   │
│  │  • Function call検出・実行                                        │   │
│  │  • detailed_data をキャッシュに保存                               │   │
│  │  • 要約 + result_id のみをLLMコンテキストに返却                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 data_tools.py (統合関数)                                 │
│                                                                          │
│  ┌────────────────────────┐  ┌────────────────────────┐                 │
│  │ analyze_student_       │  │ analyze_class_         │                 │
│  │ performance()          │  │ performance()          │                 │
│  │ • 全四半期のスコア取得 │  │ • 全生徒のスコア取得   │                 │
│  │ • 成績傾向分析         │  │ • カリキュラム完了率   │                 │
│  │ • 強み/弱み特定        │  │ • トップパフォーマー   │                 │
│  └────────────────────────┘  └────────────────────────┘                 │
│                                                                          │
│  ┌────────────────────────┐  ┌────────────────────────┐                 │
│  │ compare_students()     │  │ get_result_details()   │                 │
│  │ • 2生徒の比較分析      │  │ • result_id で詳細取得 │                 │
│  │ • 科目別勝敗判定       │  │ • Pull型データ取得     │                 │
│  └────────────────────────┘  └────────────────────────┘                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 functions/ (小さな再利用可能関数)                        │
│                                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │   loaders    │ │  validators  │ │  analyzers   │ │  formatters  │   │
│  │ • JSON読込   │ │ • 入力検証   │ │ • Polars統計 │ │ • ID生成     │   │
│  │ • ファイル   │ │ • クラス名   │ │ • 平均/標準  │ │ • 要約生成   │   │
│  │   一覧取得   │ │ • 四半期     │ │   偏差計算   │ │ • エラー応答 │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**ポイント: 二層構造の設計**

統合関数（`data_tools.py`）の内部では、従来どおり小さな関数（`functions/`配下）に分割しています。この二層構造により：
- **LLMからは**: 高凝集な統合関数として1回のTool callで複数処理を完了
- **コードとしては**: 小さな関数単位でテスト・保守が可能

### ID参照パターンのデータフロー

```
┌──────────┐    Tool call     ┌────────────────┐
│   LLM    │ ───────────────▶ │  統合関数       │
│          │                  │  (data_tools)   │
└──────────┘                  └────────────────┘
     ▲                               │
     │                               │ 詳細データ
     │                               ▼
     │  要約 + result_id      ┌────────────────┐
     │ ◀────────────────────  │ SessionResult  │
     │                        │ Cache          │
     │                        │ ┌────────────┐ │
     │                        │ │result_id_1 │ │
     │                        │ │  → data    │ │
     │                        │ │result_id_2 │ │
     │                        │ │  → data    │ │
     │                        │ └────────────┘ │
     │                        └────────────────┘
     │                               ▲
     │  get_result_details()         │
     └───────────────────────────────┘
         (必要時にPull取得)
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - `polars>=1.36.1` (データ分析)
  - `google-genai` (Gemini API)
  - `click` (CLI)
  - `pydantic` (データモデル)
  - `python-dotenv` (環境変数)

### セットアップ

1. **環境変数の設定**

```bash
cp .envrc.example .envrc
# .envrc を編集してGEMINI_API_KEYを設定
```

`.envrc` の内容:
```bash
GEMINI_API_KEY=<your_gemini_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

```bash
# 基本的な使い方
python -m src.main --query "全生徒の成績を分析してください"

# モデルを指定
python -m src.main --model GEMINI_2_5_FLASH --query "数学の成績を分析してください"

# 結果をファイルに保存
python -m src.main --query "生徒a1b2c3d4の成績分析" --output-directory ./output
```

**CLIオプション**:
```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Data analysis assistant powered by Gemini.

  Analyzes school data including student records, test scores, grade reports,
  and curriculum information.

Options:
  -m, --model [GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The Gemini model to use for analysis.
  -q, --query TEXT                The query to analyze.  [required]
  -od, --output-directory PATH    Directory to save session log (JSON) and
                                  result (Markdown). Files are named with UUID
                                  prefix.
  --help                          Show this message and exit.
```

### 出力例

```bash
$ python -m src.main -q "数学の成績を分析してください"
```

**出力**:
```markdown
**数学の成績分析レポート**

**1. 概要**
数学クラスの全体的な成績は非常に良好で、平均スコアは87.75点でした。カリキュラムの達成度も96.2%と高く、生徒たちが積極的に学習に取り組んでいることが示されています。

**2. データ分析**
*   **平均スコア**: 数学クラスの平均スコアは87.75点でした。これは、クラス全体の学力水準が高いことを示しています。
*   **最高成績者**: 生徒UUID「e5f6a7b8......」が99.5点と最高成績を収めました。
*   **カリキュラム完了率**: カリキュラムの完了率は96.2%であり、ほとんどの単元が計画通りに学習されたことを示しています。

**3. 強み**
*   クラス全体の数学の平均スコアが非常に高いです。
*   カリキュラムの完了率が高く、学習計画が効果的に実行されていることを示しています。
*   突出した成績の生徒が存在し、クラス内の学習意欲を刺激している可能性があります。

**4. 改善点**
*   現在の要約情報からは具体的な改善点は特定できませんが、平均値が高い中でも個別の生徒の成績差については詳細な分析が必要です。

**5. 提案**
*   現在の高い学習水準を維持するための継続的な指導を推奨します。
*   最高成績者である生徒の学習方法を参考に、他の生徒への指導に活用することを検討してください。
*   平均スコアを下回る生徒がいる場合、個別の学習サポートや補習を検討し、全体的な底上げを図ることを推奨します。

**6. データソース**
*   class_analysis_math_20260208_094944
```

**実行ログ**:
```bash
$ python -m src.main -q "数学の成績を分析してください"
[2026-02-08 09:49:43,389] [INFO] [__main__] [main.py:140] [main] Session ID: 1a3985a3-6939-4047-bdda-091f39664f9a
[2026-02-08 09:49:43,389] [INFO] [__main__] [main.py:141] [main] Starting data analysis with model: gemini-2.5-flash
[2026-02-08 09:49:43,389] [INFO] [__main__] [main.py:142] [main] Query: 数学の成績を分析してください
[2026-02-08 09:49:44,625] [INFO] [src.service.request_llm] [request_llm.py:151] [process_with_function_calling] Initial response: sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        function_call=FunctionCall(
          args={
            'class_name': 'math'
          },
          name='analyze_class_performance'
        ),
        thought_signature=b'\n\xe6\x01\x01\xbe>\xf6\xfbJ^\x89\xf3!\xd9\x9f>oa\xe5\x9dd\xbc\xee\\\xc9\xd8\xf3EzbgI~\x90\xf9\x0b\x89\xe7\xd2\xf0\xcc\x868\xb5\xc7\x1e\xbe\x87\xb1\xbf\xdd\xae6\xbc\rU\xb8;HJ\'j\nl\xab\xa1!i7"{4\xf3F%V\xcdlU\x8b\xd4v\x05\x02\xf3\x82Y\xa0\x17\xdb$7\x89\x19\xb3\x1e\x1c...'
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='qN2HaYPSGpOM0-kP6J_esAE' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=19,
  prompt_token_count=1838,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=1838
    ),
  ],
  thoughts_token_count=46,
  total_token_count=1903
) automatic_function_calling_history=[] parsed=None
[2026-02-08 09:49:44,626] [INFO] [src.service.request_llm] [request_llm.py:96] [execute_function_call] Executing function: analyze_class_performance with args: {'class_name': 'math'}
[2026-02-08 09:49:44,626] [INFO] [src.service.tools.data_tools] [data_tools.py:309] [analyze_class_performance] Analyzing class performance for math
[2026-02-08 09:49:44,642] [INFO] [src.service.request_llm] [request_llm.py:103] [execute_function_call] Function result (before caching): {'tool_name': 'analyze_class_performance', 'result_id': 'class_analysis_math_20260208_094944', 'result_summary': 'Math class analysis: Average score 87.75, Top performer: e5f6a7b8...... (99.5). Curriculum completion: 96.2%', 'status': 'success'}
[2026-02-08 09:49:44,642] [INFO] [src.service.request_llm] [request_llm.py:110] [execute_function_call] Context-safe result for LLM: {'tool_name': 'analyze_class_performance', 'result_id': 'class_analysis_math_20260208_094944', 'result_summary': 'Math class analysis: Average score 87.75, Top performer: e5f6a7b8...... (99.5). Curriculum completion: 96.2%', 'status': 'success'}
[2026-02-08 09:49:48,733] [INFO] [src.service.request_llm] [request_llm.py:198] [process_with_function_calling] Response after function execution: sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""**数学の成績分析レポート**

**1. 概要**
数学クラスの全体的な成績は非常に良好で、平均スコアは87.75点でした。カリキュラムの達成度も96.2%と高く、生徒たちが積極的に学習に取り組んでいることが示されています。

**2. データ分析**
*   **平均スコア**: 数学クラスの平均スコアは87.75点でした。これは、クラス全体の学力水準が高いことを示しています。
*   **最高成績者**: 生徒UUID「e5f6a7b8......」が99.5点と最高成績を収めました。
*   **カリキュラム完了率**: カリキュラムの完了率は96.2%であり、ほとんどの単元が計画通りに学習されたことを示しています。

**3. 強み**
*   クラス全体の数学の平均スコアが非常に高いです。
*   カリキュラムの完了率が高く、学習計画が効果的に実行されていることを示しています。
*   突出した成績の生徒が存在し、クラス内の学習意欲を刺激している可能性があります。

**4. 改善点**
*   現在の要約情報からは具体的な改善点は特定できませんが、平均値が高い中でも個別の生徒の成績差については詳細な分析が必要です。

**5. 提案**
*   現在の高い学習水準を維持するための継続的な指導を推奨します。
*   最高成績者である生徒の学習方法を参考に、他の生徒への指導に活用することを検討してください。
*   平均スコアを下回る生徒がいる場合、個別の学習サポートや補習を検討し、全体的な底上げを図ることを推奨します。

**6. データソース**
*   class_analysis_math_20260208_094944""",
        thought_signature=b"\n\xf3\n\x01\xbe>\xf6\xfb_\xeb(Y(2aM\x113\xe9\xc5\xbeH\x02@:\xe1~]%\x08]\xf2\x8c{t\xeb+o\x0f\xbbh\xcc/\xc5r\x80\x80\x9c%z\xd7x\xc4\xfchj\xcd\xe5\xd4T\x9f)\xf6\xf2F\x8c\xb92\xc4\x1c\xd8\xa5\x8b\x9d&1?N\rbr\xec\xbf3\xd01'm\x8f\xd6\x1b|f\x1c\xcf\xfb\x8e...'
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='rN2HaYXJIOmZ0-kPx5OZgQg' usage_metadata=GenerateContentResponseUsageMetadata(
  cache_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=1644
    ),
  ],
  cached_content_token_count=1644,
  candidates_token_count=400,
  prompt_token_count=1964,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=1964
    ),
  ],
  thoughts_token_count=277,
  total_token_count=2641
) automatic_function_calling_history=[] parsed=None
**数学の成績分析レポート**

**1. 概要**
数学クラスの全体的な成績は非常に良好で、平均スコアは87.75点でした。カリキュラムの達成度も96.2%と高く、生徒たちが積極的に学習に取り組んでいることが示されています。

**2. データ分析**
*   **平均スコア**: 数学クラスの平均スコアは87.75点でした。これは、クラス全体の学力水準が高いことを示しています。
*   **最高成績者**: 生徒UUID「e5f6a7b8......」が99.5点と最高成績を収めました。
*   **カリキュラム完了率**: カリキュラムの完了率は96.2%であり、ほとんどの単元が計画通りに学習されたことを示しています。

**3. 強み**
*   クラス全体の数学の平均スコアが非常に高いです。
*   カリキュラムの完了率が高く、学習計画が効果的に実行されていることを示しています。
*   突出した成績の生徒が存在し、クラス内の学習意欲を刺激している可能性があります。

**4. 改善点**
*   現在の要約情報からは具体的な改善点は特定できませんが、平均値が高い中でも個別の生徒の成績差については詳細な分析が必要です。

**5. 提案**
*   現在の高い学習水準を維持するための継続的な指導を推奨します。
*   最高成績者である生徒の学習方法を参考に、他の生徒への指導に活用することを検討してください。
*   平均スコアを下回る生徒がいる場合、個別の学習サポートや補習を検討し、全体的な底上げを図ることを推奨します。

**6. データソース**
*   class_analysis_math_20260208_094944
```

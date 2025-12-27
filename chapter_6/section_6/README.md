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
# uvを使用する場合
uv sync

# または pip を使用
pip install -e .
```

### 使用方法、実行方法

```bash
# 基本的な使い方
python -m src.main --query "全生徒の成績を分析してください"

# モデルを指定
python -m src.main --model gemini-2.5-flash --query "数学の成績を分析してください"

# 結果をファイルに保存
python -m src.main --query "生徒a1b2c3d4の成績分析" --output-directory ./output
```

**CLIオプション**:
```
Usage: python -m src.main [OPTIONS]

  Data analysis assistant powered by Gemini.

  Analyzes school data including student records, test scores,
  grade reports, and curriculum information.

Options:
  -m, --model [gemini-2.5-pro|gemini-2.5-flash|gemini-2.5-flash-lite]
                                  The Gemini model to use for analysis.
  -q, --query TEXT                The query to analyze.  [required]
  -od, --output-directory PATH    Directory to save session log (JSON) and
                                  result (Markdown). Files are named with
                                  UUID prefix.
  --help                          Show this message and exit.
```

### 出力例

```bash
$ python -m src.main -q "数学の成績を分析してください"
```

**出力**:
```markdown
## 概要

数学クラスの全4四半期にわたる成績分析を完了しました。5名の生徒のデータを基に、
クラス全体のパフォーマンスとトップパフォーマーを特定しました。

## データ分析

### クラス平均スコア
- 全体平均: 87.8点
- 四半期別: Q1=87.8, Q2=88.2, Q3=88.6, Q4=89.0

### トップパフォーマー
- 生徒ID: e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8a9b
- 平均スコア: 100.0点

### カリキュラム完了率
- 平均完了率: 92.5%

## 強み

- クラス全体で高い平均スコア（87.8点）を維持
- 四半期ごとに着実な成績向上が見られる
- カリキュラム完了率も高水準

## 改善点

- 一部生徒に成績のばらつきが見られる
- Q1での初期スコアが相対的に低い

## 提案

1. **優先度高**: 成績下位の生徒への個別指導
2. **優先度中**: Q1開始時の復習プログラム導入
3. **優先度低**: トップパフォーマーへの発展課題提供

## データソース

- class_analysis_math_20251227_123456
```

`--output-directory` を指定した場合、セッションログ（JSON）と結果（Markdown）が保存されます:

```
output/
├── <session-uuid>_session_log.json   # 会話履歴、Tool call履歴、キャッシュ内容
└── <session-uuid>_result.md          # 最終レスポンス
```

## 利用可能なツール

| ツール名 | 説明 | 統合関数 |
|----------|------|----------|
| `list_available_data` | 利用可能なデータファイルを一覧表示 | - |
| `get_students` | 全生徒のリストを取得 | - |
| `get_test_scores` | 指定四半期のテストスコアを取得 | - |
| `get_grade_report` | 指定四半期の成績レポートを取得 | - |
| `get_curriculum` | 指定四半期のカリキュラム情報を取得 | - |
| `analyze_student_performance` | 生徒の全四半期パフォーマンス分析 | ✓ |
| `analyze_class_performance` | クラス全体のパフォーマンス分析 | ✓ |
| `compare_students` | 2生徒の成績比較 | ✓ |
| `filter_scores` | 条件でテストスコアをフィルタリング | - |
| `filter_grades` | 条件で成績をフィルタリング | - |
| `filter_curriculum` | 条件でカリキュラムをフィルタリング | - |
| `get_result_details` | result_idで詳細データを取得（Pull型） | - |

**ポイント: 統合関数の設計**

`analyze_student_performance` は内部で以下の処理を統合しています:
1. 全4四半期のスコアデータ読み込み
2. 全4四半期の成績レポート読み込み
3. 科目別平均の計算
4. 成績傾向（トレンド）の分析
5. 強み/弱みの科目特定

これにより、LLMは1回のTool callで包括的な分析結果を取得できます。

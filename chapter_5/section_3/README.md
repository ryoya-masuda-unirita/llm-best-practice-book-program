# Chapter 5 Section 3: 多層型AIエージェント

## 概要

このプロジェクトは、**階層型マルチエージェント（Hierarchical Multi-Layer Agent）** パターンを用いたパーソナライズ学習プラットフォームの実装です。4層アーキテクチャにより、学習者の目標と制約に基づいてカスタマイズされた学習プランを自律的に作成します。

階層型アプローチは、組織構造と同様に異なる抽象レベルで関心事を分離します：

- **戦略層（Strategy Layer）**: 学習目標とロードマップを定義
- **戦術層（Tactics Layer）**: 週次・日次カリキュラムを設計
- **実行層（Execution Layer）**: コンテンツとクイズを生成
- **省察層（Reflection Layer）**: 品質と目標整合性を評価

LangGraphによるステートマシンを活用し、各層のエージェントが連携して動作します。

## 機能

- **4層階層型エージェント**: 戦略・戦術・実行・省察の4層構造で学習プランを生成
- **パーソナライズ学習**: 学習者のゴール、既存知識、利用可能時間に応じたカスタマイズ
- **構造化出力**: Pydanticモデルによる型安全なLLM応答処理
- **ステートマシン制御**: LangGraphによる複雑なエージェントワークフローの管理
- **進捗評価**: 省察層による品質監査と改善提案
- **マークダウン出力**: 生成された学習プランをマークダウン形式でエクスポート
- **CLIインターフェース**: Clickによる柔軟なコマンドラインオプション

## プロジェクト構成

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Layer (main.py)                       │
│                - コマンドライン引数解析                       │
│                - プロファイル読み込み・検証                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────┴────────────────────────────────┐
│              LangGraph State Machine (service.py)            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
          ┌─────────────────────────────────┐
          │    1. STRATEGY LAYER            │
          │    (戦略・プランニング層)        │
          │    - ゴール解釈                 │
          │    - ロードマップ作成           │
          │    - 下位層への設計図提供       │
          └──────────────┬──────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────┐
          │    2. TACTICS LAYER             │
          │    (戦術・マネジメント層)        │
          │    - タスク分解                 │
          │    - 週次・日次計画             │
          │    - タスク割り当て             │
          └──────────────┬──────────────────┘
                         │
                         ▼
          ┌─────────────────────────────────┐
          │    3. EXECUTION LAYER           │◄───┐
          │    (実行層)                      │    │
          │    - コンテンツ生成             │    │ ループ
          │    - クイズ作成                 │    │
          └──────────────┬──────────────────┘    │
                         │                       │
                         ▼                       │
                  ┌──────┴──────┐                │
                  │ タスク残り? │────────────────┘
                  └──────┬──────┘
                         │ No
                         ▼
          ┌─────────────────────────────────┐
          │    4. REFLECTION LAYER          │
          │    (自己評価・省察層)            │
          │    - 品質評価                   │
          │    - 目標整合性チェック         │
          │    - 改善提案                   │
          └──────────────┬──────────────────┘
                         │
                         ▼
                       [END]
```

### 実装の詳細

#### 4層エージェントアーキテクチャ

| 層 | モジュール | 責任 |
|---|---|---|
| 戦略層 | `layer/strategy.py` | ゴール分析、学習ロードマップ作成（設計図） |
| 戦術層 | `layer/tactics.py` | 週次・日次カリキュラム設計、タスク割り当て |
| 実行層 | `layer/execution.py` | コンテンツ・クイズ生成（ContentAgent, QuizAgent） |
| 省察層 | `layer/reflection.py` | 品質評価、目標整合性確認、調整提案 |

#### 各層の責任

**戦略層（Strategy Layer）**
- 曖昧なユーザー目標を解釈
- 全体アーキテクチャと方向性を設定
- 下位層への設計図（ブループリント）を作成
- 実装詳細には関与しない

**戦術層（Tactics Layer）**
- 戦略を実行可能なサブタスクに変換
- 実行層へのToDoリスト作成
- 進捗集約を管理
- 中間管理職的な橋渡し役

**実行層（Execution Layer）**
- 具体的なタスクを忠実に遂行
- 外部ツール操作（コンテンツ生成用LLM）
- 専門家：ContentAgent、QuizAgent
- 戦略的判断は行わない

**省察層（Reflection Layer）**
- 独立した品質監査役
- 実行層の成果物を監視
- 目標整合性を評価
- 必要に応じて計画修正を要求

#### データモデル

```python
# 戦略層モデル
class StrategyOutput(FrozenModel):
    learning_domain: str          # 学習ドメイン
    roadmap: LearningRoadmap      # 学習ロードマップ
    recommended_study_hours_per_week: int
    learning_style_notes: str

# 戦術層モデル
class TacticsOutput(FrozenModel):
    curriculum_summary: str       # カリキュラム概要
    weekly_plans: list[WeeklyPlan]  # 週次計画
    assessment_strategy: str
    adaptation_notes: str

# 実行層モデル
class LearningSession(FrozenModel):
    session_id: str
    task_id: str
    content: LearningContent      # 学習コンテンツ
    quiz: Quiz                    # クイズ
    feedback: LearnerFeedback | None

# 省察層モデル
class ProgressReport(FrozenModel):
    report_id: str
    metrics: ProgressMetrics      # 進捗メトリクス
    progress_summary: str
    recommendations: list[str]    # 改善提案
    curriculum_adjustment_needed: bool
```

#### ステートマシンフロー

```
strategy → tactics → execution (loop) → reflection → END
```

**ポイント**: 実行層はタスクが残っている限りループし、最大5セッションを生成後に省察層へ移行します。

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - langchain-openai>=1.1.0
  - langgraph>=1.0.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - click>=8.3.0
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=<your_openai_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# 学習ゴールを指定して実行
uv run python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12

# プロファイルJSONファイルを使用
uv run python -m src.main -p example/learner_profile_data_analysis.json

# 現在の知識を指定
uv run python -m src.main -g "データ分析を学びたい" -k "Excel基礎,統計基礎"

# 特定のモデルを指定
uv run python -m src.main -g "SQLを学びたい" -m GPT_5_2
```

#### CLIオプション

| オプション | 短縮形 | 説明 | デフォルト |
|---|---|---|---|
| --model | -m | 使用するOpenAIモデル | gpt-5-mini |
| --output-directory | -od | 出力ファイルのディレクトリ | outputs |
| --profile-file | -p | 学習者プロファイルJSONファイル | None |
| --goal | -g | 学習ゴールの説明 | None |
| --hours-per-week | -h | 週あたりの学習時間 | 10 |
| --duration-weeks | -d | 目標期間（週） | 12 |
| --current-knowledge | -k | 現在のスキル（カンマ区切り） | "" |

#### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Personalized Learning Platform - A Hierarchical AI Agent System

  This system creates personalized learning plans using a hierarchical multi-
  agent architecture with three layers:

  1. Strategy Layer: Creates learning roadmap and sets objectives
  2. Tactics Layer: Designs weekly/daily curriculum
  3. Execution Layer: Generates content and quizzes

  You can provide a learner profile via JSON file or command-line options.

  Examples:

      # Using command-line options
      python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12

      # Using a profile file     python -m src.main -p
      example/learner_profile.json

      # With current knowledge     python -m src.main -g "データ分析を学びたい" -k
      "Excel基礎,統計基礎"

Options:
  -m, --model [GPT_5_2|GPT_5|GPT_5_MINI|GPT_5_NANO]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  -p, --profile-file PATH         Path to a JSON file containing the learner
                                  profile.
  -g, --goal TEXT                 Learning goal (e.g.,
                                  '3ヶ月でデータ分析ができるようになりたい').
  -h, --hours-per-week INTEGER    Available study hours per week.
  -d, --duration-weeks INTEGER    Target duration in weeks.
  -k, --current-knowledge TEXT    Current knowledge/skills (comma-separated).
  --help                          Show this message and exit.```

#### 学習者プロファイルJSONの例

```json
{
  "learner_id": "learner_001",
  "learning_goal": "3ヶ月でデータ分析ができるようになりたい。SQLでデータを抽出し、Pythonで分析・可視化ができるレベルを目指す。",
  "current_knowledge": [
    "Excelでの基本的な表計算",
    "基礎的な統計知識（平均、標準偏差など）"
  ],
  "available_hours_per_week": 10,
  "preferred_content_types": [
    "article",
    "exercise",
    "interactive"
  ],
  "target_duration_weeks": 12
}
```

### 出力例

実行すると、`outputs/`ディレクトリにマークダウン形式の学習プランが生成されます。

**ファイル名**: `outputs/learning_plan_a1b2c3d4.md`

```markdown
# パーソナライズ学習プラン

## 学習者プロフィール
- **学習目標**: SQLを学びたい
- **週あたり学習時間**: 10時間
- **目標期間**: 12週間

## 戦略概要
- **学習ドメイン**: SQL（リレーショナルデータベースとデータ分析クエリ）
- **現在レベル**: beginner
- **目標レベル**: intermediate
- **推奨学習時間**: 週10時間

## 学習ロードマップ

### ゴールサマリー
12週間でSQLの基礎〜実務で頻出する集計・結合・サブクエリ・ウィンドウ関数・簡単なパフォーマンス基礎を習得し、データ抽出・分析用クエリを独力で書けるようになる。

### マイルストーン
1. Week2: SELECT/WHERE/ORDER BY/LIMITとNULL処理で基本抽出ができる
2. Week4: GROUP BY/HAVINGとJOINを使い、複数テーブルからKPI集計ができる
3. Week6: サブクエリ/CTEで複雑な要件を段階的に書ける
4. Week8: ウィンドウ関数でランキング・時系列分析（累積/移動平均）ができる
5. Week10: DDL/DMLと制約・トランザクションの基礎を理解し、安全に操作できる
6. Week12: 実データ想定の課題を、性能も意識して一通り解ける（プロジェクト成果物完成）

## 学習モジュール
### mod_001: SQL/DBの全体像と環境構築
- **カテゴリ**: fundamentals
- **説明**: リレーショナルDBの概念（テーブル/行/列、主キー、外部キー）とSQLの役割を理解し、学習用環境（PostgreSQLまたはSQLite）を用意する。
- **推定時間**: 5時間
- **習得スキル**: RDB/SQLの基本用語を説明できる, 学習用DBに接続してクエリを実行できる

### mod_002: SELECT基礎（絞り込み・並べ替え・NULL）
- **カテゴリ**: fundamentals
- **説明**: SELECT/FROM/WHERE、比較演算、LIKE、IN、BETWEEN、ORDER BY、LIMIT、NULLの扱い（IS NULL）を学ぶ。
- **推定時間**: 12時間
- **習得スキル**: 基本的な抽出条件を書ける, NULLを考慮したフィルタリングができる

### mod_003: 集計（GROUP BY/HAVING）と集計関数
- **カテゴリ**: fundamentals
- **説明**: COUNT/SUM/AVG/MIN/MAX、GROUP BY、HAVING、DISTINCT、集計時の注意点を学ぶ。
- **推定時間**: 12時間
- **習得スキル**: 目的に応じた集計クエリを書ける, HAVINGで集計後条件を扱える

### mod_004: 結合（JOIN）とリレーション設計の基礎
- **カテゴリ**: theory
- **説明**: INNER/LEFT JOIN、結合キー、1対多、参照整合性の概念、結合による行数増加（多対多の罠）を理解する。
- **推定時間**: 14時間
- **習得スキル**: 適切なJOINを選べる, 結合で結果が増える理由を説明できる

### mod_005: サブクエリとCTE（WITH）
- **カテゴリ**: practical
- **説明**: スカラー/相関/IN/EXISTSサブクエリ、CTEでの段階的クエリ構築、可読性の高い書き方を学ぶ。
- **推定時間**: 12時間
- **習得スキル**: サブクエリで条件・集計を分離できる, CTEで複雑なクエリを分解できる

### mod_006: ウィンドウ関数（分析関数）入門
- **カテゴリ**: practical
- **説明**: OVER(PARTITION BY/ORDER BY)、ROW_NUMBER/RANK、移動平均、累積和など分析で頻出のパターンを学ぶ。
- **推定時間**: 12時間
- **習得スキル**: 順位付け・時系列集計をウィンドウ関数で書ける, GROUP BYとの使い分けができる

### mod_007: データ操作（INSERT/UPDATE/DELETE）とトランザクション基礎
- **カテゴリ**: fundamentals
- **説明**: INSERT/UPDATE/DELETE、トランザクション、ロールバック、制約違反の考え方を学ぶ（分析中心でも最低限）。
- **推定時間**: 8時間
- **習得スキル**: 基本的なDMLを安全に実行できる, トランザクションの意義を説明できる

### mod_008: スキーマ定義（DDL）と正規化のさわり
- **カテゴリ**: theory
- **説明**: CREATE TABLE、型、PRIMARY KEY/FOREIGN KEY/UNIQUE/CHECK、インデックス概念、正規化の目的を理解する。
- **推定時間**: 8時間
- **習得スキル**: 簡単なテーブル定義を書ける, 制約とインデックスの役割を説明できる

### mod_009: パフォーマンス基礎とEXPLAIN
- **カテゴリ**: advanced_topics
- **説明**: インデックスが効く/効かない条件、実行計画（EXPLAIN）の読み方の入口、JOIN/WHEREの基本最適化を学ぶ。
- **推定時間**: 8時間
- **習得スキル**: 遅いクエリの典型原因を挙げられる, EXPLAINでボトルネックの当たりを付けられる

### mod_010: 総合演習プロジェクト（分析レポート用クエリ作成）
- **カテゴリ**: project
- **説明**: 架空EC/サブスク等のデータセットで、KPI集計・コホート・ランキング・異常検知（簡易）などの問いに対して一連のSQLを作成し、再利用可能な形に整理する。
- **推定時間**: 25時間
- **習得スキル**: 要件からSQLを設計し段階的に実装できる, 可読性・再現性の高いクエリを納品できる, 結果の妥当性を検算できる

## カリキュラム詳細

### カリキュラム概要
12週間でSQL基礎〜実務で頻出する集計・結合・サブクエリ・ウィンドウ関数・パフォーマンス基礎を習得し、分析用クエリを独力で書ける状態を目指す。週10時間（インプット3h→ドリル5h→復習2h）を基本配分とし、毎週末にSQLリファクタと軽い性能意識（読みやすさ/再利用性/実行時間）を組み込む。

### 評価戦略
毎週：①日次ドリルの正答率/実行結果の検算ログ ②週末ミニテスト（またはチェックリスト）③リファクタ提出（可読性・再利用性・実行時間を簡易評価）。隔週：過去モジュールの復習セット（混合問題）を実施。Week12：総合プロジェクト（要件定義→クエリ群→簡易性能確認EXPLAIN→README）で最終評価。

### 第1週: SQL/DBの全体像と学習環境の構築（PostgreSQL想定）
**学習目標**:
- RDB/SQLの役割（スキーマ・テーブル・行/列・主キー/外部キー）を説明できる
- ローカルまたはクラウドでSQL実行環境を用意し、サンプルDBをロードできる
- SELECTの最小構文を実行し、結果を読み取れる
- クエリにコメントを付け、実行→検算→別解の学習手順を開始できる

**日別タスク**:

**週次評価**: チェックリスト評価：①DBに接続しSQLを実行できる ②サンプルデータを3テーブル以上確認できる ③簡単なSELECTを5本（列選択/式/エイリアス/ORDER BY）書ける ④各クエリに意図コメントがある。加えて10分の自己口頭説明（RDBの用語5つ）。

### 第2週: SELECT基礎：WHERE/ORDER BY/LIMITとNULL処理で基本抽出
**学習目標**:
- SELECT/FROM/WHERE/ORDER BY/LIMITの基本形を迷わず書ける
- 比較・範囲・集合（IN/BETWEEN）・パターン（LIKE）で絞り込みできる
- NULLの挙動（= NULLが偽）を理解し、IS NULL/COALESCE/NULLIFを使える
- 実データ想定の問い合わせを『要件→SQL→検算』で解ける

**日別タスク**:

**週次評価**: ミニテスト（60分）：20問（各3分目安）— 条件抽出/並べ替え/NULL処理/文字列パターン。合格基準：正答16/20以上。加えてリファクタ課題：過去クエリ2本をCTEなしで読みやすく整形（エイリアス/コメント/条件順）。

## 今週の学習セッション
## 進捗レポート
- **進捗状況**: 12週間のSQL（中級）学習計画の第1週開始時点。現時点では学習セッション/タスク未実施のため、進捗は0%。今週の着手がないため現状は計画から遅れていますが、週1の立ち上げ行動で取り戻し可能です。
- **トラック状況**: 調整が必要

### 推奨事項
- 今週中に最低1セッション（60〜90分）を確保し、環境準備（SQL実行環境/データセット）と基礎復習（SELECT/JOIN/GROUP BY）を行う
- 学習ログを開始し、各セッションで『学んだこと3点』『詰まった点1点』『次回やること1点』を記録して継続しやすくする
- 第1週の到達目標を具体化：例）結合＋集計のクエリを3本作成し、意図を説明できる状態にする
```

**実行ログ例**:

```bash
$ uv run python -m src.main -g "SQLを学びたい" -m GPT_5_2

[2026-02-07 09:13:59,348] [INFO] [__main__] [main.py:64] [_create_profile_from_options] Creating learner profile from command-line options
[2026-02-07 09:13:59,348] [INFO] [__main__] [main.py:83] [_log_startup_info] Personalized Learning Platform
Model: gpt-5.2
Learning Goal: SQLを学びたい
Hours/Week: 10
Duration: 12 weeks
Output directory: outputs
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:119] [run_personalized_learning] ================================================================================
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:120] [run_personalized_learning] HIERARCHICAL PERSONALIZED LEARNING PLATFORM
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:121] [run_personalized_learning] 4-Layer Architecture: Strategy -> Tactics -> Execution -> Reflection
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:122] [run_personalized_learning] ================================================================================
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:123] [run_personalized_learning] Learner goal: SQLを学びたい
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:124] [run_personalized_learning] Available hours/week: 10
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:125] [run_personalized_learning] Target duration: 12 weeks
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:126] [run_personalized_learning] Model: gpt-5.2
[2026-02-07 09:13:59,348] [INFO] [src.service.service] [service.py:52] [create_learning_platform_graph] Creating hierarchical learning platform graph...
[2026-02-07 09:13:59,349] [INFO] [src.service.service] [service.py:71] [create_learning_platform_graph] Learning platform graph created successfully
[2026-02-07 09:13:59,372] [INFO] [STRATEGY.StrategyAgent] [base.py:51] [_log_layer_start] ============================================================
[2026-02-07 09:13:59,372] [INFO] [STRATEGY.StrategyAgent] [base.py:52] [_log_layer_start] STRATEGY LAYER - StrategyAgent: Creating learning roadmap (blueprint)
[2026-02-07 09:13:59,372] [INFO] [STRATEGY.StrategyAgent] [base.py:53] [_log_layer_start] ============================================================
[2026-02-07 09:14:30,855] [INFO] [STRATEGY.StrategyAgent] [base.py:72] [_invoke_with_structured_output] Received structured response from LLM
[2026-02-07 09:14:30,855] [INFO] [STRATEGY.StrategyAgent] [strategy.py:42] [execute] Learning domain: SQL（リレーショナルデータベースとデータ分析 クエリ）
[2026-02-07 09:14:30,855] [INFO] [STRATEGY.StrategyAgent] [strategy.py:43] [execute] Modules created: 10
[2026-02-07 09:14:30,855] [INFO] [STRATEGY.StrategyAgent] [strategy.py:44] [execute] Level progression: beginner -> intermediate
[2026-02-07 09:14:30,856] [INFO] [TACTICS.TacticsAgent] [base.py:51] [_log_layer_start] ============================================================
[2026-02-07 09:14:30,856] [INFO] [TACTICS.TacticsAgent] [base.py:52] [_log_layer_start] TACTICS LAYER - TacticsAgent: Designing curriculum (sub-task assignment)
[2026-02-07 09:14:30,856] [INFO] [TACTICS.TacticsAgent] [base.py:53] [_log_layer_start] ============================================================
[2026-02-07 09:14:47,929] [INFO] [TACTICS.TacticsAgent] [base.py:72] [_invoke_with_structured_output] Received structured response from LLM
[2026-02-07 09:14:47,929] [INFO] [TACTICS.TacticsAgent] [tactics.py:59] [execute] Weekly plans created: 2
[2026-02-07 09:14:47,929] [INFO] [EXECUTION.Coordinator] [execution.py:193] [execute] No more tasks for day1
[2026-02-07 09:14:47,930] [INFO] [src.service.service] [service.py:46] [should_continue_execution] Moving to Reflection Layer for evaluation
[2026-02-07 09:14:47,930] [INFO] [REFLECTION.ReflectionAgent] [base.py:51] [_log_layer_start] ============================================================
[2026-02-07 09:14:47,930] [INFO] [REFLECTION.ReflectionAgent] [base.py:52] [_log_layer_start] REFLECTION LAYER - ReflectionAgent: Evaluating execution outputs
[2026-02-07 09:14:47,930] [INFO] [REFLECTION.ReflectionAgent] [base.py:53] [_log_layer_start] ============================================================
[2026-02-07 09:14:54,948] [INFO] [REFLECTION.ReflectionAgent] [base.py:72] [_invoke_with_structured_output] Received structured response from LLM
[2026-02-07 09:14:54,948] [INFO] [REFLECTION.ReflectionAgent] [reflection.py:60] [execute] Progress report created: sql-intermediate-w01-r01
[2026-02-07 09:14:54,948] [INFO] [REFLECTION.ReflectionAgent] [reflection.py:61] [execute] On track: False
[2026-02-07 09:14:54,948] [INFO] [REFLECTION.ReflectionAgent] [reflection.py:66] [execute] Execution aligned with strategic goals
[2026-02-07 09:14:54,949] [INFO] [src.service.service] [service.py:136] [run_personalized_learning] ================================================================================
[2026-02-07 09:14:54,949] [INFO] [src.service.service] [service.py:137] [run_personalized_learning] LEARNING PLAN CREATED SUCCESSFULLY
[2026-02-07 09:14:54,949] [INFO] [src.service.service] [service.py:138] [run_personalized_learning] All layers completed: Strategy -> Tactics -> Execution -> Reflection
[2026-02-07 09:14:54,949] [INFO] [src.service.service] [service.py:139] [run_personalized_learning] ================================================================================
[2026-02-07 09:14:54,949] [INFO] [__main__] [main.py:211] [main] Plan saved: outputs/learning_plan_25d9aba4d6a64bf4ac4585d1e0e4c978.md
```

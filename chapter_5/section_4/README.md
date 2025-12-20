# Chapter 5 Section 4: 階層型マルチエージェント - パーソナライズ学習プラットフォーム

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

### ディレクトリ構成

```
chapter_5/section_4/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（APIキー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # CLIエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # OpenAIモデル定義
│   ├── layer/                   # 4層エージェント実装
│   │   ├── __init__.py
│   │   ├── base.py              # BaseAgent抽象クラス
│   │   ├── strategy.py          # 戦略層エージェント
│   │   ├── tactics.py           # 戦術層エージェント
│   │   ├── execution.py         # 実行層エージェント
│   │   └── reflection.py        # 省察層エージェント
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # 各層のプロンプト定義
│   └── service/
│       ├── __init__.py
│       └── service.py           # LangGraphオーケストレーション
├── example/                     # サンプル学習者プロファイル
│   ├── learner_profile_data_analysis.json
│   ├── learner_profile_python.json
│   └── learner_profile_management.json
├── outputs/                     # 生成された学習プラン
├── .envrc.example               # 環境変数テンプレート
├── pyproject.toml               # プロジェクト依存関係
├── Makefile                     # 開発コマンド
└── README.md                    # このファイル
```

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
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
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
uv run python -m src.main -g "SQLを学びたい" -m gpt-4o-mini
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
uv run python -m src.main --help
```

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
  "preferred_content_types": ["article", "exercise", "interactive"],
  "target_duration_weeks": 12
}
```

### 出力例

実行すると、`outputs/`ディレクトリにマークダウン形式の学習プランが生成されます。

**ファイル名**: `outputs/learning_plan_a1b2c3d4.md`

```markdown
# パーソナライズ学習プラン

## 学習者プロフィール
- **学習目標**: 3ヶ月でデータ分析ができるようになりたい
- **週あたり学習時間**: 10時間
- **目標期間**: 12週間

## 戦略概要
- **学習ドメイン**: データ分析（SQL + Python）
- **現在レベル**: elementary
- **目標レベル**: intermediate
- **推奨学習時間**: 週10時間

## 学習ロードマップ

### ゴールサマリー
SQLとPythonを使ったデータ分析スキルを3ヶ月で習得する...

### マイルストーン
1. SQL基礎構文の習得（2週目）
2. Python基礎の完了（4週目）
...

## 学習モジュール
### mod_001: SQL基礎
- **カテゴリ**: fundamentals
- **説明**: SQLの基本的なクエリ構文を学習
- **推定時間**: 8時間
- **習得スキル**: SELECT文, WHERE句, JOIN操作
...

## 今週の学習セッション

### セッション1: SELECT文の基礎
- **コンテンツタイプ**: article
- **キーコンセプト**: SELECT, FROM, WHERE

**クイズ**: SELECT文理解度チェック (3問)
...

## 進捗レポート
- **進捗状況**: 初週のセッションを完了
- **トラック状況**: 順調

### 推奨事項
- 演習問題を繰り返し解くことで定着を図る
- 次週はJOIN操作の理解に注力する
```

**実行ログ例**:

```
[2025-12-20 10:30:45] [INFO] [src.service.service] ================================================================================
[2025-12-20 10:30:45] [INFO] [src.service.service] HIERARCHICAL PERSONALIZED LEARNING PLATFORM
[2025-12-20 10:30:45] [INFO] [src.service.service] 4-Layer Architecture: Strategy -> Tactics -> Execution -> Reflection
[2025-12-20 10:30:45] [INFO] [src.service.service] ================================================================================
[2025-12-20 10:30:45] [INFO] [STRATEGY.StrategyAgent] ============================================================
[2025-12-20 10:30:45] [INFO] [STRATEGY.StrategyAgent] STRATEGY LAYER - StrategyAgent: Creating learning roadmap (blueprint)
[2025-12-20 10:30:45] [INFO] [STRATEGY.StrategyAgent] ============================================================
[2025-12-20 10:31:20] [INFO] [STRATEGY.StrategyAgent] Learning domain: データ分析（SQL + Python）
[2025-12-20 10:31:20] [INFO] [STRATEGY.StrategyAgent] Modules created: 11
[2025-12-20 10:31:20] [INFO] [STRATEGY.StrategyAgent] Level progression: elementary -> intermediate
[2025-12-20 10:31:20] [INFO] [TACTICS.TacticsAgent] ============================================================
[2025-12-20 10:31:20] [INFO] [TACTICS.TacticsAgent] TACTICS LAYER - TacticsAgent: Designing curriculum (sub-task assignment)
...
[2025-12-20 10:35:00] [INFO] [src.service.service] LEARNING PLAN CREATED SUCCESSFULLY
[2025-12-20 10:35:00] [INFO] [__main__] Plan saved: outputs/learning_plan_a1b2c3d4.md
```

### 開発コマンド

```bash
make lint    # ruffによるリント（自動修正）
make fmt     # ruffによるフォーマット
make fix     # lint + fmt
make mypy    # mypyによる型チェック
```

## 設計上のポイント

### 構造化出力の活用

各層のエージェントは`with_structured_output()`を使用して、PydanticモデルへのLLM応答を直接取得します：

```python
def _invoke_with_structured_output(
    self,
    config: RunnableConfig,
    system_prompt: str,
    user_prompt: str,
    output_type: type[T],
) -> T:
    model = self._create_chat_model(config)
    structured_model = model.with_structured_output(output_type, method="function_calling")
    messages = self._build_messages(system_prompt, user_prompt)
    return structured_model.invoke(messages, config)
```

### 層間の明確なインターフェース

各層は構造化されたPydanticモデルを介して通信し、自然言語ではなく型安全なデータ構造を使用します。

### 独立した省察層

省察層は実行層から独立して動作し、戦略との整合性を客観的に評価します。必要に応じてカリキュラム調整を提案できます。

## トレードオフと考慮事項

- **レイテンシ**: 多層処理により応答時間が増加
- **複雑性**: 層インターフェースと状態管理の設計複雑性
- **硬直性リスク**: 上位層の決定が実行層の有益な洞察を上書きする可能性
- **エラー伝播**: 戦略層のミスが全ての下位層に影響

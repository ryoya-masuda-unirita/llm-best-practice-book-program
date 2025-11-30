# Chapter 4 Section 5: 学習型AIエージェント

## 概要

このプロジェクトは、**学習型AIエージェント（Learning AI Agent）** の実装例です。システムは環境からのフィードバックや過去の対話履歴といった経験を蓄積し、それに基づいて自身の振る舞いや出力の品質を継続的に改善していきます。

LangGraphを使用した階層型マルチエージェントアーキテクチャを採用し、パーソナライズされた学習プランを生成します。さらに、ユーザーフィードバックを収集・分析する学習フィードバックループを実装することで、運用を通じて自律的に成長するシステムを実現しています。

従来の静的なプロンプトベースのシステムとは異なり、本システムは過去の経験からパターンを学習し、そのパターンを各エージェントのプロンプトに注入することで、より高品質な出力を生成できるようになります。

## 機能

- **階層型マルチエージェント**: Strategy → Tactics → Execution → Progress の4層アーキテクチャ
- **学習フィードバックループ**: ユーザーフィードバックを収集し、システム改善に活用
- **経験ストア**: 過去の入力・出力・フィードバックを蓄積するデータストア
- **パターン学習**: 蓄積された経験から成功/失敗パターンを自動抽出
- **プロンプト注入**: 学習したパターンを各エージェントのプロンプトに動的に注入
- **LangGraph統合**: 状態管理と条件付きエッジによる柔軟なワークフロー制御
- **パーソナライズ学習プラン**: 学習者のプロファイルに基づいた個別化されたカリキュラム生成
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_5/
├── src/
│   ├── __init__.py               # パッケージ初期化
│   ├── config.py                 # 設定管理（APIキー読み込み）
│   ├── logger.py                 # ロギング設定
│   ├── main.py                   # CLIエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py         # OpenAIモデル定義
│   ├── model/
│   │   ├── __init__.py
│   │   └── llm_pipeline_model.py # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── llm_pipeline_prompt.py # プロンプトテンプレート
│   └── service/
│       ├── __init__.py
│       └── llm_pipeline_service.py # ビジネスロジック・エージェント実装
├── example/
│   ├── learner_profile.json      # 学習者プロファイル例
│   └── experience_store.json     # 経験ストア例
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # ビルド・実行コマンド
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト概念説明
```

### アーキテクチャ

このプロジェクトは、学習フィードバックループを持つ階層型マルチエージェントアーキテクチャで構成されています：

```
┌──────────────────────────────────────────────────────────────────┐
│                    Learning Agent                                │
│              （過去の経験を分析しパターンを抽出）                  │
└─────────────────────────┬────────────────────────────────────────┘
                          │ 学習したパターンを注入
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌─────────┐ │
│  │  Strategy  │──▶│  Tactics   │──▶│ Execution  │──▶│Progress │ │
│  │   Agent    │   │   Agent    │   │   Agent    │   │ Agent   │ │
│  │(学習戦略)  │   │(カリキュラ │   │(コンテンツ │   │(進捗    │ │
│  │            │   │   ム設計)  │   │  ・クイズ) │   │ 監視)   │ │
│  └────────────┘   └────────────┘   └─────┬──────┘   └─────────┘ │
│                                          │ループ                  │
│                                          ▼                       │
│                                    ┌──────────┐                  │
│                                    │ 次のタスク│                  │
│                                    │  へ移行  │                  │
│                                    └──────────┘                  │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Experience Store                              │
│      （経験を蓄積・学習パターンを保存・フィードバック集計）        │
└──────────────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. 経験モデル (`src/model/llm_pipeline_model.py`)

学習フィードバックループの中核となる経験関連のモデルを定義します：

```python
class FeedbackRating(StrEnum):
    """ユーザーフィードバックの評価レベル"""
    VERY_HELPFUL = "very_helpful"
    HELPFUL = "helpful"
    NEUTRAL = "neutral"
    NOT_HELPFUL = "not_helpful"
    VERY_POOR = "very_poor"

class ExperienceRecord(FrozenModel):
    """エージェントの経験を記録するモデル"""
    experience_id: str
    learner_id: str
    agent_type: str  # strategy, tactics, content, quiz, progress
    input_context: dict
    output_generated: dict
    user_feedback: UserFeedback | None
    learning_domain: str

class ExperiencePattern(FrozenModel):
    """複数の経験から学習したパターン"""
    pattern_id: str
    agent_type: str
    pattern_description: str
    positive_examples: list[str]  # 成功例
    negative_examples: list[str]  # 失敗例
    confidence_score: float  # 信頼度（0-1）
    source_experience_count: int
```

**ポイント**:
- `ExperienceRecord`は入力・出力・フィードバックの3要素を記録
- `ExperiencePattern`は複数の経験から抽出された一般化されたルール
- `confidence_score`でパターンの信頼性を数値化

#### 2. 経験ストア (`src/model/llm_pipeline_model.py`)

経験を蓄積し、学習パターンを管理するストア：

```python
class ExperienceStore(BaseModel):
    """経験と学習パターンを蓄積するストア"""
    store_id: str
    experiences: list[ExperienceRecord]
    learned_patterns: list[ExperiencePattern]
    total_positive_feedback: int
    total_negative_feedback: int

    def add_experience(self, experience: ExperienceRecord) -> None:
        """新しい経験を追加"""
        self.experiences.append(experience)
        # フィードバック統計を更新
        if experience.user_feedback:
            if experience.user_feedback.rating in [FeedbackRating.VERY_HELPFUL, FeedbackRating.HELPFUL]:
                self.total_positive_feedback += 1
            elif experience.user_feedback.rating in [FeedbackRating.NOT_HELPFUL, FeedbackRating.VERY_POOR]:
                self.total_negative_feedback += 1

    def get_positive_experiences(self, agent_type: str | None = None) -> list[ExperienceRecord]:
        """ポジティブフィードバックの経験を取得"""
        ...

    def get_patterns_for_agent(self, agent_type: str) -> list[ExperiencePattern]:
        """特定エージェント向けのパターンを取得"""
        ...
```

**ポイント**:
- ミュータブルモデルとして経験を継続的に蓄積
- エージェントタイプ別、ドメイン別の経験取得をサポート
- JSON形式でのシリアライズ/デシリアライズに対応

#### 3. 学習エージェント (`src/service/llm_pipeline_service.py`)

過去の経験を分析し、パターンを抽出するエージェント：

```python
def learning_agent(
    experience_store: ExperienceStore,
    agent_type: str,
    config: RunnableConfig,
) -> tuple[list[ExperiencePattern], list[LearningInsight], list[str]]:
    """経験を分析しパターンを抽出"""
    positive_experiences = experience_store.get_positive_experiences(agent_type)
    negative_experiences = experience_store.get_negative_experiences(agent_type)

    # 十分な経験がない場合はスキップ
    if total_experiences < 3:
        return [], [], []

    # LLMを使用してパターンを抽出
    user_prompt = make_learning_user_prompt(
        agent_type=agent_type,
        positive_experiences=positive_exp_str,
        negative_experiences=negative_exp_str,
        ...
    )
    response = invoke_with_retry(model, messages, config, "Learning Agent")

    patterns = _parse_learning_patterns(result)
    insights = _parse_learning_insights(result)
    return patterns, insights, prompt_adjustments
```

**ポイント**:
- ポジティブ/ネガティブ経験を分離して分析
- 最低3件の経験がないと学習をスキップ（過学習防止）
- パターン、洞察、プロンプト調整の3種類の出力を生成

#### 4. パターン注入 (`src/prompt/llm_pipeline_prompt.py`)

学習したパターンを各エージェントのプロンプトに注入：

```python
LEARNED_PATTERNS_INJECTION_TEMPLATE = """
## 過去の学習から得られた知見

以下は過去のユーザーフィードバックから学習したパターンです。
これらを参考にして出力を生成してください。

### 成功パターン（これらを取り入れてください）
{positive_patterns}

### 注意パターン（これらは避けてください）
{negative_patterns}

### 具体的な改善点
{improvement_notes}
"""

def make_strategy_system_prompt(learned_context: str = "") -> str:
    """学習コンテキストを注入したシステムプロンプトを生成"""
    base_prompt = STRATEGY_AGENT_SYSTEM_PROMPT
    if learned_context:
        return base_prompt + "\n" + learned_context
    return base_prompt
```

**ポイント**:
- 成功パターン、失敗パターン、改善点の3カテゴリで注入
- 各エージェントのシステムプロンプトに動的に追加
- 学習コンテキストがない場合は元のプロンプトをそのまま使用

#### 5. LangGraphワークフロー (`src/service/llm_pipeline_service.py`)

状態管理と条件付きエッジを使用したワークフロー定義：

```python
def create_learning_platform_graph() -> StateGraph:
    """階層型学習プラットフォームのグラフを作成"""
    graph = StateGraph(HierarchicalAgentState)

    # ノード追加: Strategy -> Tactics -> Execution (ループ) -> Progress
    graph.add_node("strategy", strategy_agent)
    graph.add_node("tactics", tactics_agent)
    graph.add_node("execution", execution_agent)
    graph.add_node("progress", progress_agent)

    # フロー定義
    graph.set_entry_point("strategy")
    graph.add_edge("strategy", "tactics")
    graph.add_edge("tactics", "execution")
    graph.add_conditional_edges(
        "execution",
        should_continue_execution,
        {"execute": "execution", "progress": "progress"},
    )
    graph.add_edge("progress", END)

    return graph.compile()
```

**ポイント**:
- `StateGraph`で状態を管理しながらエージェント間を遷移
- `add_conditional_edges`で条件に応じた分岐を実現
- Executionノードは最大5セッションまでループ

#### 6. 状態管理 (`src/model/llm_pipeline_model.py`)

LangGraphの状態を定義するTypedDict：

```python
class HierarchicalAgentState(TypedDict):
    """階層型エージェントシステムの状態"""
    # 入力
    learner_profile: LearnerProfile

    # 各レイヤーの出力
    strategy_output: StrategyOutput | None
    tactics_output: TacticsOutput | None
    learning_sessions: list[LearningSession]
    progress_report: ProgressReport | None

    # 実行コンテキスト
    current_week: int
    current_day: str
    current_task_index: int

    # 経験と学習
    experience_store: ExperienceStore | None
    learned_patterns_context: str  # プロンプト注入用

    # メッセージ
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

**ポイント**:
- 各レイヤーの出力を明確に型付け
- `experience_store`で学習データを保持
- `learned_patterns_context`で注入用の文字列を保持

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
# コマンドラインオプションで実行
uv run python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12

# プロファイルファイルを使用
uv run python -m src.main -p example/learner_profile.json
```

#### 経験ベースの学習

```bash
# 過去の経験を読み込んで学習サイクルを実行
uv run python -m src.main -p example/learner_profile.json -e example/experience_store.json

# 経験を保存して将来の学習に使用
uv run python -m src.main -p example/learner_profile.json -se outputs/experience_store.json

# 学習サイクルをスキップ
uv run python -m src.main -p example/learner_profile.json -e example/experience_store.json --skip-learning
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

  Personalized Learning Platform - A Learning AI Agent System

  This system creates personalized learning plans using a hierarchical multi-
  agent architecture with learning capabilities.

Options:
  -m, --model [GPT_5|GPT_5_MINI|GPT_5_NANO|GPT_4_1|GPT_4_1_MINI|GPT_4_1_NANO|GPT_4O|GPT_4O_MINI]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  -p, --profile-file PATH         Path to a JSON file containing the learner profile.
  -g, --goal TEXT                 Learning goal.
  -h, --hours-per-week INTEGER    Available study hours per week.
  -d, --duration-weeks INTEGER    Target duration in weeks.
  -k, --current-knowledge TEXT    Current knowledge/skills (comma-separated).
  -e, --experience-store PATH     Path to a JSON file containing past experiences.
  -se, --save-experience-store PATH
                                  Path to save the updated experience store.
  --skip-learning / --with-learning
                                  Skip the learning cycle.
  --help                          Show this message and exit.
```

### 出力例

#### 学習者プロファイル例 (`example/learner_profile.json`)

```json
{
  "learner_id": "learner_demo_001",
  "learning_goal": "3ヶ月でPythonプログラミングの基礎を習得し、データ分析ができるようになりたい",
  "current_knowledge": [
    "Excel基礎操作",
    "基本的なPC操作",
    "統計の基礎知識"
  ],
  "available_hours_per_week": 10,
  "preferred_content_types": ["article", "exercise", "interactive"],
  "target_duration_weeks": 12
}
```

#### 経験ストア例 (`example/experience_store.json`)

```json
{
  "store_id": "store_demo_001",
  "experiences": [
    {
      "experience_id": "exp_001",
      "agent_type": "content",
      "input_context": {"task_id": "task_w1d1_01", "title": "Python環境のセットアップ"},
      "output_generated": {"title": "Python環境構築ガイド"},
      "user_feedback": {
        "rating": "very_helpful",
        "helpful_aspects": ["手順が明確で分かりやすかった"],
        "improvement_suggestions": ["Macの手順も追加してほしい"]
      }
    }
  ],
  "learned_patterns": [
    {
      "pattern_id": "pattern_001",
      "agent_type": "content",
      "pattern_description": "コンテンツには具体的なコード例を多く含めると学習者の理解が深まる",
      "positive_examples": ["実行可能なサンプルコードを含める"],
      "negative_examples": ["抽象的な説明のみで具体例がない"],
      "confidence_score": 0.8
    }
  ],
  "total_positive_feedback": 3,
  "total_negative_feedback": 1
}
```

#### 実行ログ例

```
[2025-11-30 17:00:00] [INFO] Loading experience store from: example/experience_store.json
[2025-11-30 17:00:00] [INFO] Loaded 4 experiences, 2 patterns
[2025-11-30 17:00:01] [INFO] ============================================================
[2025-11-30 17:00:01] [INFO] HIERARCHICAL PERSONALIZED LEARNING PLATFORM (WITH LEARNING)
[2025-11-30 17:00:01] [INFO] ============================================================
[2025-11-30 17:00:01] [INFO] Running learning cycle to extract patterns from past experiences...
[2025-11-30 17:00:05] [INFO] Learning cycle complete: 3 new patterns
[2025-11-30 17:00:05] [INFO] ============================================================
[2025-11-30 17:00:05] [INFO] STRATEGY LAYER: Creating learning roadmap
[2025-11-30 17:00:10] [INFO] Strategy output: domain=Pythonプログラミング
[2025-11-30 17:00:10] [INFO] ============================================================
[2025-11-30 17:00:10] [INFO] TACTICS LAYER: Designing curriculum
...
[2025-11-30 17:00:30] [INFO] LEARNING PLAN CREATED SUCCESSFULLY
[2025-11-30 17:00:30] [INFO] Plan saved: outputs/learning_plan_abc123.md
```

# Chapter 5 Section 4: 多層型（階層型）AIエージェント

## 概要

本プロジェクトは、**多層型（階層型）AIエージェント**パターンを用いたパーソナライズ学習プラットフォームを実装しています。複雑なタスクを自律的に遂行するために、エージェントの機能を抽象度の異なる4つの「層（レイヤー）」に分割して配置するアーキテクチャを採用しています。

このアーキテクチャは、人間の組織における「経営層（戦略）・管理職（戦術）・現場（実行）・監査役（評価）」の役割分担を模倣しています。上位レイヤーが大局的な戦略や計画を立案し、下位レイヤーが具体的なタスクを実行し、独立したレイヤーが結果を客観的に評価・修正します。

学習者の目標（例：「3ヶ月でデータ分析ができるようになりたい」）を入力すると、システムは以下を自動生成します：
- 学習ロードマップ（戦略層）
- 週次・日次カリキュラム（戦術層）
- 学習コンテンツとクイズ（実行層）
- 進捗レポートと改善提案（自己評価層）

## 機能

- **戦略的学習計画生成**: 学習者の目標と制約から最適な学習ロードマップを自動設計
- **詳細カリキュラム作成**: 週次テーマと日次タスクへの分解
- **コンテンツ・クイズ自動生成**: 各タスクに対応した学習教材と評価問題を作成
- **品質評価・改善提案**: 生成物の品質チェックと目標整合性の確認
- **マークダウン出力**: 学習プラン全体を見やすいマークダウン形式で出力

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_4/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定（APIキー）
│   ├── logger.py                # ログユーティリティ
│   ├── main.py                  # CLIエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # OpenAIクライアント設定
│   ├── layer/                   # 4層エージェント実装
│   │   ├── __init__.py          # レイヤーパッケージエクスポート
│   │   ├── base.py              # BaseAgent抽象クラス
│   │   ├── strategy.py          # 戦略層（戦略・プランニング層）
│   │   ├── tactics.py           # 戦術層（戦術・マネジメント層）
│   │   ├── execution.py         # 実行層
│   │   └── reflection.py        # 自己評価層（自己評価・省察層）
│   ├── model/
│   │   ├── __init__.py
│   │   └── llm_pipeline_model.py  # Pydanticデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── llm_pipeline_prompt.py # 各層のプロンプト定義
│   └── service/
│       ├── __init__.py
│       └── llm_pipeline_service.py  # LangGraphオーケストレーション
├── example/                     # サンプルプロファイル
├── outputs/                     # 生成された学習プラン
├── .envrc.example               # 環境変数テンプレート
├── pyproject.toml               # プロジェクト依存関係
├── Makefile                     # 開発コマンド
├── REFERENCE.md                 # アーキテクチャ原則リファレンス
└── CLAUDE.md                    # プロジェクトガイド
```

### アーキテクチャ

```
┌──────────────────────────────────────────────────────────────┐
│                     CLI Layer (main.py)                      │
│                - コマンドライン引数解析                        │
│                - プロファイル読み込みと検証                     │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────┴────────────────────────────────────┐
│               LangGraph State Machine                        │
│                  (llm_pipeline_service.py)                   │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────────┐
          │     1. STRATEGY LAYER             │
          │     (戦略・プランニング層)           │
          │     - 目標解釈                      │
          │     - ロードマップ作成               │
          │     - 下位層へのブループリント提供     │
          └───────────────┬───────────────────┘
                          │
                          ▼
          ┌───────────────────────────────────┐
          │     2. TACTICS LAYER              │
          │     (戦術・マネジメント層)           │
          │     - タスク分解                    │
          │     - 週次/日次計画                 │
          │     - タスク割り当て                │
          └───────────────┬───────────────────┘
                          │
                          ▼
          ┌───────────────────────────────────┐
          │     3. EXECUTION LAYER            │◄────┐
          │     (実行層)                        │     │
          │     - コンテンツ生成                 │     │ ループ
          │     - クイズ作成                    │     │
          └───────────────┬───────────────────┘     │
                          │                         │
                          ▼                         │
                   ┌──────┴──────┐                  │
                   │ タスク残り?  │─────────────────┘
                   └──────┬──────┘
                          │ No
                          ▼
          ┌───────────────────────────────────┐
          │     4. REFLECTION LAYER           │
          │     (自己評価・省察層)              │
          │     - 品質評価                     │
          │     - 目標整合性チェック             │
          │     - 改善提案                     │
          └───────────────┬───────────────────┘
                          │
                          ▼
                       [END]
```

### 実装の詳細

#### 1. BaseAgent (`src/layer/base.py`)

全レイヤーエージェントの基底クラス。LLM呼び出し、JSON解析、リトライロジックを共通化しています。

```python
class BaseAgent(ABC):
    """
    全階層エージェントの抽象基底クラス。
    LLM呼び出し、ログ出力、JSON解析、エラーハンドリングの共通機能を提供。
    """

    def __init__(self, layer_name: str, agent_name: str):
        self.layer_name = layer_name
        self.agent_name = agent_name
        self.logger = make_logger(f"{layer_name}.{agent_name}")

    def _invoke_and_parse(
        self,
        config: RunnableConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """
        共通ワークフロー: メッセージ構築 → LLM呼び出し（リトライ付き） → JSON解析
        """
        model = self._create_chat_model(config)
        messages = self._build_messages(system_prompt, user_prompt)
        response_content = self._invoke_with_retry(model, messages, config)
        return extract_json_from_response(response_content)

    @abstractmethod
    def execute(self, state: dict, config: RunnableConfig) -> dict:
        """レイヤー固有のロジックを実装"""
        pass
```

**ポイント**: テンプレートメソッドパターンにより、各レイヤーのエージェントは`execute`メソッドのみを実装すれば良く、重複コードを排除しています。

#### 2. Strategy Layer (`src/layer/strategy.py`)

最上位層として、学習者の曖昧な目標を解釈し、学習ロードマップを作成します。

```python
class StrategyAgent(BaseAgent):
    """
    戦略層エージェント（戦略エージェント）
    学習者の目標を分析し、下位層へのブループリントとなる
    包括的な学習ロードマップを作成。
    """

    def __init__(self):
        super().__init__(layer_name="STRATEGY", agent_name="StrategyAgent")

    def execute(self, state: HierarchicalAgentState, config: RunnableConfig) -> dict:
        """戦略層を実行して学習ロードマップを作成"""
        self._log_layer_start("Creating learning roadmap (blueprint)")

        learner = state["learner_profile"]
        user_prompt = make_strategy_user_prompt(
            learning_goal=learner.learning_goal,
            current_knowledge=learner.current_knowledge,
            # ...
        )

        result = self._invoke_and_parse(config, make_strategy_system_prompt(), user_prompt)
        strategy_output = self._parse_strategy_output(result)

        return {"strategy_output": strategy_output}
```

**ポイント**: 戦略層は細部の実装には関与せず、全体ゴールの設定とアーキテクチャの決定に専念します。

#### 3. LangGraph State Machine (`src/service/llm_pipeline_service.py`)

4層の階層的フローをLangGraphで実装しています。

```python
def create_learning_platform_graph() -> StateGraph:
    """階層型学習プラットフォームグラフを作成"""
    graph = StateGraph(HierarchicalAgentState)

    # レイヤーノードを追加
    graph.add_node("strategy", strategy_agent_node)    # 層1: 戦略
    graph.add_node("tactics", tactics_agent_node)      # 層2: 戦術
    graph.add_node("execution", execution_agent_node)  # 層3: 実行
    graph.add_node("reflection", reflection_agent_node)# 層4: 自己評価

    # 階層的フローを定義
    graph.set_entry_point("strategy")
    graph.add_edge("strategy", "tactics")
    graph.add_edge("tactics", "execution")

    # 実行ループと自己評価層への遷移
    graph.add_conditional_edges(
        "execution",
        should_continue_execution,
        {"execute": "execution", "reflect": "reflection"},
    )
    graph.add_edge("reflection", END)

    return graph.compile()
```

**ポイント**: `add_conditional_edges`により、実行層はタスクが残っている間ループし、完了後に自己評価層へ遷移します。

#### 4. データモデル (`src/model/llm_pipeline_model.py`)

各層の入出力を型安全なPydanticモデルで定義しています。

```python
# 戦略層モデル
class StrategyOutput(FrozenModel):
    learning_domain: str
    roadmap: LearningRoadmap
    recommended_study_hours_per_week: int
    learning_style_notes: str

# 戦術層モデル
class TacticsOutput(FrozenModel):
    curriculum_summary: str
    weekly_plans: list[WeeklyPlan]
    assessment_strategy: str
    adaptation_notes: str

# 自己評価層モデル
class ProgressReport(FrozenModel):
    metrics: ProgressMetrics
    progress_summary: str
    recommendations: list[str]
    curriculum_adjustment_needed: bool  # 上位層への修正要求フラグ
```

**ポイント**: `curriculum_adjustment_needed`フラグにより、自己評価層は上位層に計画修正を要求できます。

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要依存ライブラリ:
  - `langchain-openai`: OpenAI連携
  - `langgraph`: エージェントワークフロー
  - `pydantic`: データ検証
  - `click`: CLIフレームワーク

### セットアップ

1. 環境変数ファイルを作成:

```bash
cp .envrc.example .envrc
```

2. APIキーを設定:

```bash
# .envrc を編集
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

3. 依存関係をインストール:

```bash
uv sync
```

### 使用方法、実行方法

#### コマンドラインオプションで実行

```bash
# 基本的な使用法
uv run python -m src.main -g "3ヶ月でPythonプログラミングを習得したい" -h 10 -d 12

# 現在の知識を指定
uv run python -m src.main -g "データ分析を学びたい" -k "Excel基礎,統計基礎"

# モデルを指定
uv run python -m src.main -g "SQLを学びたい" -m gpt-4o-mini
```

#### プロファイルJSONで実行

```bash
uv run python -m src.main -p example/learner_profile_data_analysis.json
```

#### CLIオプション一覧

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| `--model` | `-m` | 使用するOpenAIモデル | gpt-4o-mini |
| `--output-directory` | `-od` | 出力ディレクトリ | outputs |
| `--profile-file` | `-p` | 学習者プロファイルJSONファイル | None |
| `--goal` | `-g` | 学習目標 | None |
| `--hours-per-week` | `-h` | 週あたり学習時間 | 10 |
| `--duration-weeks` | `-d` | 目標期間（週） | 12 |
| `--current-knowledge` | `-k` | 現在のスキル（カンマ区切り） | "" |

#### プロファイルJSONの例

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

実行すると`outputs/`ディレクトリにマークダウンファイルが生成されます：

```markdown
# パーソナライズ学習プラン

## 学習者プロフィール
- **学習目標**: 3ヶ月でデータ分析ができるようになりたい。SQLでデータを抽出し、Pythonで分析・可視化ができるレベルを目指す。
- **週あたり学習時間**: 10時間
- **目標期間**: 12週間

## 戦略概要
- **学習ドメイン**: データ分析（SQL + Python）
- **現在レベル**: elementary
- **目標レベル**: intermediate
- **推奨学習時間**: 週10時間

## 学習ロードマップ

### ゴールサマリー
12週間でSQLを用いてデータを抽出し、Python（pandas, matplotlib/seabornなど）で分析・可視化できるレベルになる。

### マイルストーン
1. Week 3: 基礎の習得完了（mod_001完了）
2. Week 6: SQLとPython基礎の習得（mod_002, mod_003完了）
3. Week 9: データ整形と可視化の実務力（mod_004, mod_005, mod_006完了）
4. Week 12: 実務レベルの統合（mod_007, mod_008完了）

## 学習モジュール
### mod_001: データ分析の基本と統計リフレッシュ
- **カテゴリ**: fundamentals
- **説明**: データ分析のワークフロー、基本的な統計の復習
- **推定時間**: 8時間
- **習得スキル**: データ分析プロセスの理解, 基礎統計指標の計算と解釈

...

## 進捗レポート
- **進捗状況**: 第1週目として予定された5セッションがすべて完了
- **トラック状況**: 順調

### 推奨事項
- クイズの個別スコアを毎回記録し、週次で平均スコアを算出
- 第2週に短いSQL入門セッションを組み込むこと推奨
```

## 開発コマンド

```bash
make lint    # ruffでリント（自動修正）
make fmt     # ruffでフォーマット
make fix     # lint + fmt
make mypy    # 型チェック
```

## 設計原則（REFERENCE.mdより）

### 関心の分離
各層は明確に異なる抽象度と責任を持ちます：
- **戦略層**: 何を達成するか（What）
- **戦術層**: どう分解するか（How to break down）
- **実行層**: 具体的に実行（Do）
- **自己評価層**: 品質を監査（Audit）

### 明確なインターフェース
層間のやり取りは自然言語ではなく、構造化されたJSONデータで定義しています。これにより各層がコンテキストを共有し、整合性を保てます。

### 独立した監査
自己評価層は実行層から独立して動作し、客観的な品質評価を行います。`curriculum_adjustment_needed`フラグにより、上位層への計画修正要求が可能です。

## トレードオフと考慮事項

- **レイテンシ**: 多層処理により応答時間が増加します
- **複雑性**: 層間インターフェースと状態管理により設計が複雑化します
- **硬直性リスク**: 上位層の決定が実行層の有益な洞察を無視する可能性があります
- **エラー伝播**: 戦略層のミスは全ての下流層に影響します

# Chapter 4 Section 4: 階層型AIエージェント - パーソナライズ学習プラットフォーム

## 概要

本プロジェクトは、階層型AIエージェントアーキテクチャを用いたパーソナライズ学習プラットフォームの実装です。階層型AIエージェントは、複数のAIエージェントを階層構造に配置する設計パターンで、人間の組織におけるマネジメント層と実行部隊の関係を模しています。

このシステムでは、「3ヶ月でデータ分析ができるようになりたい」「新任マネージャーがマネジメントスキルを身につけたい」といった漠然とした学習ゴールを入力すると、以下のプロセスを自律的に実行します：

1. **学習ゴールの明確化・レベル定義**
2. **カリキュラム設計（どの分野をどの順番で学ぶか）**
3. **日々の学習プランと教材提示**
4. **テスト・フィードバック・進捗レポートの生成**

LangGraphを用いたステートマシンにより、戦略→戦術→実行の3層構造でエージェントを連携させ、一貫性のある学習プランを生成します。

## 機能

- **学習戦略の自動生成**: 学習者の目標と現在レベルから最適な学習ロードマップを設計
- **カリキュラムの自動設計**: 週単位・日単位の具体的な学習タスクを自動生成
- **学習コンテンツの生成**: 各タスクに対応した学習教材を動的に生成
- **クイズの自動生成**: 理解度確認用のクイズを自動作成
- **進捗レポートの作成**: 学習進捗を分析し、推奨事項を提示
- **Markdown形式での出力**: 生成された学習プランをMarkdownファイルとして保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_4/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLIエントリーポイント
│   ├── config.py                  # 設定管理
│   ├── logger.py                  # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py          # OpenAI クライアント設定
│   ├── model/
│   │   ├── __init__.py
│   │   └── llm_pipeline_model.py  # Pydanticデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── llm_pipeline_prompt.py # 各エージェント用プロンプト
│   └── service/
│       ├── __init__.py
│       └── llm_pipeline_service.py # 階層型エージェントサービス
├── example/
│   ├── learner_profile_data_analysis.json
│   ├── learner_profile_python.json
│   └── learner_profile_management.json
├── outputs/                        # 生成された学習プランの出力先
├── pyproject.toml
├── .envrc.example
├── CLAUDE.md
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Hierarchical Agent System                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Strategy Layer（戦略層）                    │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │            Learning Strategy Agent                       │  │  │
│  │  │  • 学習ドメインの特定                                     │  │  │
│  │  │  • 現在/目標スキルレベルの評価                            │  │  │
│  │  │  • 学習モジュールの設計                                   │  │  │
│  │  │  • マイルストーンの定義                                   │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Tactics Layer（戦術層）                     │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │           Curriculum Design Agent                        │  │  │
│  │  │  • 週次計画の作成                                         │  │  │
│  │  │  • 日次タスクの設計                                       │  │  │
│  │  │  • 評価戦略の設計                                         │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   Execution Layer（実行層）                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │  │
│  │  │   Content   │  │    Quiz     │  │      Progress       │  │  │
│  │  │    Agent    │  │    Agent    │  │       Agent         │  │  │
│  │  │  • 教材生成  │  │  • クイズ   │  │  • 進捗メトリクス   │  │  │
│  │  │  • キー     │  │    生成     │  │  • 達成事項記録     │  │  │
│  │  │    概念抽出 │  │  • 正解解説 │  │  • 推奨事項提供     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### LangGraphによる処理フロー

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                         ▼
                ┌────────────────┐
                │ Strategy Agent │
                │  (戦略策定)    │
                └────────┬───────┘
                         │
                         ▼
                ┌────────────────┐
                │ Tactics Agent  │
                │ (カリキュラム)  │
                └────────┬───────┘
                         │
                         ▼
             ┌───────────────────────┐
             │   Execution Agent     │◄──────┐
             │ (Content + Quiz生成)  │       │
             └───────────┬───────────┘       │
                         │                   │
                         ▼                   │
            ┌────────────────────────┐       │
            │ should_continue_exec?  │───────┘
            │  (セッション < 5?)     │  yes
            └────────────┬───────────┘
                         │ no
                         ▼
                ┌────────────────┐
                │ Progress Agent │
                │  (進捗報告)    │
                └────────┬───────┘
                         │
                         ▼
                    ┌─────────┐
                    │   END   │
                    └─────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/llm_pipeline_model.py`)

階層型エージェントの状態管理と出力を定義するPydanticモデル群です。

**主要なモデル:**

```python
class HierarchicalAgentState(TypedDict):
    """階層型エージェントシステムの状態"""
    learner_profile: LearnerProfile       # 学習者プロフィール
    strategy_output: StrategyOutput | None # 戦略層の出力
    tactics_output: TacticsOutput | None   # 戦術層の出力
    learning_sessions: list[LearningSession] # 実行層の出力
    progress_report: ProgressReport | None # 進捗レポート
    current_week: int                      # 現在の週
    current_day: str                       # 現在の日
    current_task_index: int                # 現在のタスクインデックス
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

**スキルレベルの定義:**

```python
class SkillLevel(StrEnum):
    BEGINNER = "beginner"           # 全くの初心者
    ELEMENTARY = "elementary"       # 基礎的な概念は理解
    INTERMEDIATE = "intermediate"   # 基本的な作業を独力で行える
    UPPER_INTERMEDIATE = "upper_intermediate" # 複雑な作業も対応可能
    ADVANCED = "advanced"           # 専門家レベル
```

> **ポイント**: TypedDictを使用することで、LangGraphの状態管理と型安全性を両立しています。

#### 2. プロンプト定義 (`src/prompt/llm_pipeline_prompt.py`)

各エージェント用のシステムプロンプトとユーザープロンプトを定義しています。

**戦略エージェントのプロンプト例:**

```python
STRATEGY_AGENT_SYSTEM_PROMPT = """あなたは学習戦略エージェントです。
あなたの役割は、学習者の目標と現在のレベルを分析し、
最終到達像を定義して、学習ロードマップを作成することです。

## あなたの責任
1. **学習ドメインの特定**: 学習者の目標から学習領域を特定します
2. **現在レベルの評価**: 学習者の既存知識から現在のスキルレベルを評価します
3. **目標レベルの設定**: 達成すべきスキルレベルを設定します
4. **学習モジュールの設計**: 必要な学習モジュールを順序立てて設計します
5. **マイルストーンの定義**: 進捗を確認するためのマイルストーンを設定します
...
"""
```

> **ポイント**: 各エージェントに明確な責任と出力形式（JSON）を指定することで、構造化された応答を得られます。

#### 3. 階層型エージェントサービス (`src/service/llm_pipeline_service.py`)

LangGraphを用いた階層型エージェントシステムの中核実装です。

**グラフの構築:**

```python
def create_learning_platform_graph() -> StateGraph:
    """階層型学習プラットフォームグラフを作成"""
    graph = StateGraph(HierarchicalAgentState)

    # ノードの追加（各層のエージェント）
    graph.add_node("strategy", strategy_agent)
    graph.add_node("tactics", tactics_agent)
    graph.add_node("execution", execution_agent)
    graph.add_node("progress", progress_agent)

    # エントリーポイントの設定
    graph.set_entry_point("strategy")

    # エッジの定義（処理フロー）
    graph.add_edge("strategy", "tactics")
    graph.add_edge("tactics", "execution")

    # 条件付きエッジ（実行ループ）
    graph.add_conditional_edges(
        "execution",
        should_continue_execution,
        {"execute": "execution", "progress": "progress"},
    )
    graph.add_edge("progress", END)

    return graph.compile()
```

**戦略エージェントの実装:**

```python
def strategy_agent(state: HierarchicalAgentState, config: RunnableConfig) -> dict:
    """戦略層エージェント - 学習ロードマップを作成"""
    learner = state["learner_profile"]
    model = ChatOpenAI(model=model_name, temperature=0.7)

    # プロンプトの構築
    system_prompt = make_strategy_system_prompt()
    user_prompt = make_strategy_user_prompt(
        learning_goal=learner.learning_goal,
        current_knowledge=learner.current_knowledge,
        available_hours_per_week=learner.available_hours_per_week,
        target_duration_weeks=learner.target_duration_weeks,
    )

    # LLM呼び出しとJSON解析
    response_content = invoke_with_retry(model, messages, config, "Strategy Agent")
    result = extract_json_from_response(response_content)

    # StrategyOutputの構築
    strategy_output = StrategyOutput(...)
    return {"strategy_output": strategy_output}
```

> **ポイント**: `invoke_with_retry`関数により、LLMのレート制限や一時的な障害に対してリトライ機能を実装しています。

#### 4. CLIインターフェース (`src/main.py`)

Clickを使用したコマンドラインインターフェースです。

```python
@click.command()
@click.option("--model", "-m", type=click.Choice(OpenAIModel.list_str()), default=OpenAIModel.GPT_4O)
@click.option("--output-directory", "-od", type=click.Path(), default="outputs")
@click.option("--profile-file", "-p", type=click.Path(exists=True))
@click.option("--goal", "-g", type=str, help="Learning goal")
@click.option("--hours-per-week", "-h", type=int, default=10)
@click.option("--duration-weeks", "-d", type=int, default=12)
@click.option("--current-knowledge", "-k", type=str)
@async_cmd
async def main(...):
    """Personalized Learning Platform - A Hierarchical AI Agent System"""
    # 学習者プロファイルの読み込みまたは作成
    # 階層型エージェントシステムの実行
    # 結果の保存と出力
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - `langchain-anthropic>=1.2.0`
  - `langgraph>=1.0.0`
  - `langchain-openai` (内部で使用)
  - `openai>=2.4.0`
  - `pydantic>=2.12.2`
  - `click>=8.3.0`
  - `python-dotenv>=1.1.1`

### セットアップ

1. **環境変数の設定**

```bash
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定
```

`.envrc`の内容:
```
OPENAI_API_KEY=<your_openai_api_key_here>
```

2. **依存関係のインストール**

```bash
uv sync
```

### 使用方法、実行方法

#### CLIオプション

```
Usage: python -m src.main [OPTIONS]

Options:
  -m, --model [GPT_5|GPT_5_MINI|GPT_5_NANO|GPT_4_1|GPT_4_1_MINI|GPT_4_1_NANO|GPT_4O|GPT_4O_MINI]
                                  使用するモデル（デフォルト: GPT_4O）
  -od, --output-directory PATH    出力ディレクトリ（デフォルト: outputs）
  -p, --profile-file PATH         学習者プロファイルJSONファイルのパス
  -g, --goal TEXT                 学習目標
  -h, --hours-per-week INTEGER    週あたりの学習可能時間（デフォルト: 10）
  -d, --duration-weeks INTEGER    目標期間（週）（デフォルト: 12）
  -k, --current-knowledge TEXT    現在の知識・スキル（カンマ区切り）
  --help                          ヘルプを表示
```

#### 実行例

**1. コマンドラインオプションを使用:**

```bash
python -m src.main \
  -g "3ヶ月でPythonプログラミングを習得したい" \
  -h 10 \
  -d 12 \
  -k "PCの基本操作はできる"
```

**2. プロファイルファイルを使用:**

```bash
python -m src.main -p example/learner_profile_data_analysis.json
```

**3. 詳細なオプション指定:**

```bash
python -m src.main \
  -m GPT_4_1_MINI \
  -od outputs/ \
  -p example/learner_profile_management.json
```

#### 学習者プロファイルJSONの形式

```json
{
  "learner_id": "learner_001",
  "learning_goal": "3ヶ月でデータ分析ができるようになりたい。SQLでデータを抽出し、Pythonで分析・可視化ができるレベルを目指す。",
  "current_knowledge": [
    "Excel基礎",
    "簡単な数式は使える"
  ],
  "available_hours_per_week": 10,
  "preferred_content_types": [
    "video",
    "article",
    "exercise"
  ],
  "target_duration_weeks": 12
}
```

### 出力例

実行後、`outputs/`ディレクトリに以下のようなMarkdownファイルが生成されます:

```
============================================================
PERSONALIZED LEARNING PLAN CREATED
============================================================

Learning Domain: 新任マネージャーのピープルマネジメント
Current Level: elementary
Target Level: intermediate
Duration: 8 weeks
Modules: 8
First Week Sessions: 5

Plan saved to: outputs/learning_plan_f92b525fa1c34a23a1d4060f441926c9.md

============================================================
```

**生成されるMarkdownの例:**

```markdown
# パーソナライズ学習プラン

## 学習者プロフィール
- **学習目標**: 新任マネージャーとしてマネジメントスキルを身につけたい...
- **週あたり学習時間**: 5時間
- **目標期間**: 8週間

## 戦略概要
- **学習ドメイン**: 新任マネージャーのピープルマネジメント
- **現在レベル**: elementary
- **目標レベル**: intermediate
- **推奨学習時間**: 週5時間

## 学習ロードマップ

### ゴールサマリー
新任マネージャーとして、週次1on1を効果的に実施し...

### マイルストーン
1. Week 2: mod_001 と mod_002 を完了し、模擬1on1を実施
2. Week 4: mod_003 を完了し、5名分のSMART目標を作成
...

## 学習モジュール
### mod_001: マネージャーの役割と移行（IC→Manager）
- **カテゴリ**: fundamentals
- **説明**: マネージャーの基本的責務、権限と責任の違い...
- **推定時間**: 4時間
- **習得スキル**: マネージャーとしての役割理解, 期待値と優先順位設定
...

## カリキュラム詳細

### 第1週: マネージャーへの移行：役割理解と基礎
**学習目標**:
- マネージャーとしての主要な責務と期待を理解する
...

**日別タスク**:
  - **day1**: 記事：マネージャーの役割, 動画：役割移行の心理的側面
  - **day2**: 記事：権限委譲と意思決定, 演習：委任ケースワーク
...

## 今週の学習セッション

### 記事：マネージャーの役割（概要）
- **コンテンツタイプ**: article
- **キーコンセプト**: マネージャーの役割, 期待値設定...

**クイズ**: マネージャーの役割理解チェック (4問)
...

## 進捗レポート
- **進捗状況**: 学習開始週として、予定されていた5つのセッションを完了...
- **トラック状況**: 順調

### 推奨事項
- 今後のモジュールに向けて、学習時間の記録を開始しましょう
- クイズのスコアを記録し、理解度の定期的な評価を行うことを推奨します
```

## 設計のポイント

### 階層間のインターフェース

上位から下位への指示、下位から上位への報告は、すべてJSON形式の構造化データで行われます。これにより：
- 各エージェントの入出力が明確
- パース可能で検証しやすい
- システム全体の安定性が向上

### エラーハンドリング

```python
def extract_json_from_response(response: str) -> dict:
    """LLM応答からJSONを抽出（複数の戦略を試行）"""
    # Strategy 1: 応答が'{' で始まる場合、そのままJSON
    # Strategy 2: ```json コードブロックから抽出
    # Strategy 3: 最初の'{' から最後の'}' を抽出
    # Strategy 4: 切り詰められたJSONの修復を試行
```

### リトライ機能

```python
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

def invoke_with_retry(model, messages, config, agent_name) -> str:
    """LLM呼び出しにリトライロジックを適用"""
    for attempt in range(MAX_RETRIES):
        try:
            response = model.invoke(messages, config)
            if response.content and response.content.strip():
                return response.content
        except Exception as e:
            logger.warning(f"{agent_name}: Error on attempt {attempt + 1}: {e}")
        time.sleep(RETRY_DELAY_SECONDS)
    raise ValueError(f"{agent_name} failed after {MAX_RETRIES} attempts")
```

## 注意点とトレードオフ

1. **応答速度**: 階層が深くなるほど、処理に時間がかかります（1回の実行で5-10分程度）
2. **コスト**: 複数のLLM呼び出しが発生するため、APIコストに注意が必要です
3. **柔軟性**: 上位エージェントの判断が固定的な場合、下位エージェントの柔軟な対応が制限される可能性があります

## ライセンス

このプロジェクトはLLMベストプラクティスブックのサンプルコードとして提供されています。

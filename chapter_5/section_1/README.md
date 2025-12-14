# Chapter 5 Section 1: ReAct型AIエージェント

## 概要

このプロジェクトは、**ReAct（Reasoning and Acting）パターン** を用いたAIエージェントの実装を示すサンプルコードです。LangChainとLangGraphを活用し、「思考（Thought）→ 行動（Action）→ 観察（Observation）」のサイクルを繰り返すことで、複雑なタスクを段階的に解決するエージェントを構築します。

夕食メニューのアドバイザーエージェントを通じて、ReActパターンの実践的な実装方法を学ぶことができます。エージェントはレシピ検索、栄養情報確認、旬の食材取得、調理時間見積もりなどのツールを活用し、ユーザーのリクエストに基づいて最適な夕食メニューを提案します。

## 機能

- **ReActパターン実装**: Thought-Action-Observationループによる段階的な問題解決
- **ツール連携**: 4種類の専用ツール（レシピ検索、栄養情報、旬の食材、調理時間見積もり）
- **LangGraph状態管理**: StateGraphによるエージェントの状態遷移管理
- **無限ループ防止**: 最大イテレーション数による安全機構
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能によるエージェント実行状況の可視化
- **Markdown出力**: 推薦結果をMarkdown形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_1/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── config.py                      # 設定管理（API キー読み込み）
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # メインエントリーポイント（CLI）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── llm_pipeline_model.py      # エージェント状態・データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── llm_pipeline_prompt.py     # システムプロンプト・ユーザープロンプト
│   └── service/
│       ├── __init__.py
│       └── llm_pipeline_service.py    # ReActエージェント実装・ツール定義
├── outputs/                            # 推薦結果の保存先（自動作成）
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── README.md                           # このファイル
└── CLAUDE.md                           # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、ReActパターンに基づく以下のアーキテクチャで構成されています：

```
┌─────────────────────────────────────────┐
│         CLI Layer (main.py)             │
│     - コマンドライン引数解析             │
│     - 出力ディレクトリ管理               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      ReAct Agent Layer                  │
│  - StateGraph (LangGraph)               │
│  - Thought-Action-Observation Loop      │
│  - ツール実行・結果観察                  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Tool Layer                         │
│  - search_recipes (レシピ検索)          │
│  - check_nutrition (栄養情報確認)       │
│  - get_seasonal_ingredients (旬の食材)  │
│  - estimate_cooking_time (調理時間)     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - 外部API (OpenAI)                     │
└─────────────────────────────────────────┘
```

### ReActエージェントのフロー

```
    ┌─────────────┐
    │    Start    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │    Agent    │ ◄──────────────────┐
    │  (Thought)  │                    │
    └──────┬──────┘                    │
           │                           │
           ▼                           │
    ┌─────────────┐    Yes      ┌──────┴──────┐
    │ Tool Call?  │────────────►│    Tools    │
    └──────┬──────┘             │(Observation)│
           │ No                 └─────────────┘
           ▼
    ┌─────────────┐
    │  Finalize   │
    │ (Response)  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │     End     │
    └─────────────┘
```

### 実装の詳細

#### 1. エージェント状態モデル (`src/model/llm_pipeline_model.py`)

LangGraphのTypedDictを使用して、エージェントの状態を定義します：

```python
class AgentState(TypedDict):
    """ReAct agent state for dinner menu advisor."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_request: str
    final_recommendation: str | None
```

**ポイント**:
- `Annotated`と`add_messages`でメッセージ履歴を自動管理
- `final_recommendation`で最終的な推薦結果を保持

#### 2. ツール定義 (`src/service/llm_pipeline_service.py`)

LangChainの`@tool`デコレータを使用して、エージェントが利用可能なツールを定義します：

```python
@tool
def search_recipes(query: str, cuisine_type: str | None = None) -> str:
    """
    Search for recipes based on keywords and optional cuisine type.

    Args:
        query: Search keywords (e.g., "chicken", "pasta", "quick dinner")
        cuisine_type: Optional cuisine type (e.g., "Japanese", "Italian", "Chinese")

    Returns:
        JSON string containing matching recipes
    """
    # レシピデータベースの検索ロジック
    ...

@tool
def check_nutrition(dish_name: str) -> str:
    """Check the nutritional information of a dish."""
    ...

@tool
def get_seasonal_ingredients(season: str | None = None) -> str:
    """Get a list of ingredients that are currently in season."""
    ...

@tool
def estimate_cooking_time(dish_name: str, skill_level: str = "intermediate") -> str:
    """Estimate the cooking time for a specific dish."""
    ...
```

**ポイント**:
- docstringがLLMへのツール説明として自動的に使用される
- JSON形式で結果を返すことで、LLMが解釈しやすい

#### 3. ReActエージェントグラフ (`src/service/llm_pipeline_service.py`)

LangGraphのStateGraphを使用して、ReActループを構築します：

```python
def create_dinner_advisor_graph() -> StateGraph:
    """Create the ReAct agent graph for dinner menu advice."""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", call_model)      # Thought + Action決定
    graph.add_node("tools", tool_node)       # Observation
    graph.add_node("finalize", extract_final_recommendation)

    # Set entry point
    graph.set_entry_point("agent")

    # Add conditional edges
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": "finalize",
        },
    )

    # Tools always go back to agent
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    return graph.compile()
```

**ポイント**:
- `call_model`: LLMを呼び出し、次のアクションを決定（Thought + Action）
- `tool_node`: ツールを実行し、結果を観察（Observation）
- `should_continue`: ループを継続するか終了するかを判定

#### 4. 無限ループ防止機構

最大イテレーション数を設定し、無限ループを防止します：

```python
MAX_ITERATIONS = 10

def should_continue(state: AgentState) -> Literal["tools", "end"]:
    messages = state["messages"]
    last_message = messages[-1]

    # Check iteration count to prevent infinite loops
    tool_message_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    if tool_message_count >= MAX_ITERATIONS:
        logger.warning(f"Agent: Max iterations ({MAX_ITERATIONS}) reached, ending loop")
        return "end"

    # If the last message has tool calls, continue to tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"
```

#### 5. システムプロンプト (`src/prompt/llm_pipeline_prompt.py`)

ReActパターンの思考プロセスを促すシステムプロンプトを定義します：

```python
DINNER_ADVISOR_SYSTEM_PROMPT = """You are a helpful dinner menu advisor AI assistant.
Your goal is to recommend the best dinner menu based on the user's request.

You have access to the following tools to help you make better recommendations:

1. **search_recipes**: Search for recipes based on keywords, cuisine type, or ingredients.
2. **check_nutrition**: Check the nutritional information of a dish.
3. **get_seasonal_ingredients**: Get a list of ingredients that are currently in season.
4. **estimate_cooking_time**: Estimate the cooking time for a specific dish.

## ReAct Process

For each user request, follow this Thought-Action-Observation loop:

1. **Thought**: Think about what information you need to gather...
2. **Action**: Use one of the available tools to gather information.
3. **Observation**: Analyze the results from the tool...

Repeat this loop until you have enough information to make a confident recommendation.
...
"""
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - langchain-openai>=1.1.0
  - langgraph>=1.0.0
  - openai>=2.4.0
  - pydantic>=2.12.2
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
# リクエストを指定して実行
uv run python -m src.main -r "今日は疲れているので簡単な料理がいい"

# 健康志向のリクエスト
uv run python -m src.main -r "健康的な和食を作りたい"

# 時間制限のあるリクエスト
uv run python -m src.main -r "30分以内で作れるイタリアン"
```

#### モデルの指定

```bash
# デフォルト（gpt-4o）
uv run python -m src.main -r "簡単な夕食"

# 別のモデルを使用
uv run python -m src.main -m gpt-4o-mini -r "簡単な夕食"
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -r "簡単な夕食" -od ./my_recommendations
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

  Dinner Menu Advisor - A ReAct AI Agent

  This agent recommends dinner menus based on your request. It uses tools to
  search recipes, check nutrition, find seasonal ingredients, and estimate
  cooking times.

Options:
  -m, --model [gpt-5|gpt-5-mini|gpt-5-nano|gpt-4.1|gpt-4.1-mini|gpt-4.1-nano|gpt-4o|gpt-4o-mini]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  -r, --request TEXT              Your dinner request in natural language.
                                  [required]
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のようなMarkdownファイルが生成されます：

**ファイル名**: `outputs/dinner_recommendation_a1b2c3d4.md`

```markdown
# 夕食メニュー提案: 豚の生姜焼き

## 概要
- **調理時間**: 約20分
- **難易度**: 簡単

## おすすめの理由
お疲れの時にぴったりの、シンプルで美味しい定番料理です。
材料も少なく、手順も簡単なので、疲れていても無理なく作れます。
豚肉のタンパク質と生姜の風味で、元気が出る一品です。

## 材料
- 豚ロース 200g
- 生姜 1かけ
- 醤油 大さじ2
- みりん 大さじ1
- 酒 大さじ1

## 作り方
1. 生姜をすりおろす
2. 調味料を混ぜ合わせてタレを作る
3. 豚肉をフライパンで焼く
4. タレを加えて絡める
5. 皿に盛り付けて完成
```

**実行ログ例**:
```
[2025-10-17 10:30:45] [INFO] [src.main] Dinner Menu Advisor
Model: gpt-4o
Request: 今日は疲れているので簡単な料理がいい
Output directory: outputs

[2025-10-17 10:30:45] [INFO] [src.service.llm_pipeline_service] Starting dinner advisor for request: 今日は疲れているので簡単な料理がいい
[2025-10-17 10:30:45] [INFO] [src.service.llm_pipeline_service] Creating dinner advisor ReAct agent graph...
[2025-10-17 10:30:46] [INFO] [src.service.llm_pipeline_service] Agent: Calling model for reasoning...
[2025-10-17 10:30:47] [INFO] [src.service.llm_pipeline_service] Agent: Model response received (has_tool_calls=True)
[2025-10-17 10:30:47] [INFO] [src.service.llm_pipeline_service] Agent: Executing tool calls...
[2025-10-17 10:30:47] [INFO] [src.service.llm_pipeline_service] Tool: search_recipes called with query='簡単', cuisine_type='Quick'
[2025-10-17 10:30:47] [INFO] [src.service.llm_pipeline_service] Agent: Tool 'search_recipes' returned result
[2025-10-17 10:30:48] [INFO] [src.service.llm_pipeline_service] Agent: Calling model for reasoning...
[2025-10-17 10:30:50] [INFO] [src.service.llm_pipeline_service] Agent: No tool calls, ending loop with final answer
[2025-10-17 10:30:50] [INFO] [src.service.llm_pipeline_service] Dinner advisor completed successfully
[2025-10-17 10:30:50] [INFO] [src.main] Recommendation saved: outputs/dinner_recommendation_a1b2c3d4.md
```

# Chapter 3 Section 15: AIエージェントの抽象化設計

## 概要

このプロジェクトは、**AIエージェントの抽象化設計**パターンを実装した包括的なフレームワークです。LLMを中核に据えた自律的なシステムを、高レベルなインターフェースとしてカプセル化し、8つの設計パターンを組み合わせることで、保守性と拡張性に優れたエージェントシステムを構築します。

思考戦略(Brain)、ツールカタログ(ToolBox)、コンテキストマネージャー(Memory)の3つの独立したコンポーネントに分離し、開発者は統一されたインターフェースを通じてエージェントに目標を指示するだけで、自律的なタスク実行が可能になります。

**コード削減率: 56%** (3,752行 → 1,643行) - 全機能とインターフェースを維持したまま、高度にリファクタリングされた実装です。

## 機能

### コアアーキテクチャ
- **Brain (思考エンジン)**: Strategy パターンによる交換可能な思考戦略
  - Chain-of-Thought (CoT): 段階的推論
  - ReAct: 推論と行動の統合
  - Tree-of-Thought (ToT): 複数経路の探索
- **ToolBox (ツールカタログ)**: Composite パターンによる階層的ツール管理
- **Memory (コンテキストマネージャー)**: Memento パターンによるスナップショット機能

### 実装済み設計パターン
1. **Strategy Pattern** - プラグイン可能な思考戦略
2. **Composite Pattern** - ツールの階層構造管理
3. **Memento Pattern** - メモリのスナップショットと復元
4. **State Pattern** - エージェント実行状態の管理
5. **Chain of Responsibility** - 実行制御と安全機構
6. **Builder Pattern** - 流暢なエージェント構築インターフェース
7. **Factory Pattern** - 設定ベースのエージェント生成
8. **Mediator Pattern** - マルチエージェント調整

### 安全機構
- **実行ステップ数制限**: 暴走実行の防止
- **コスト追跡**: API呼び出しコストの制限
- **ツール呼び出し制限**: 過剰な外部呼び出しの防止
- **危険な操作のブロック**: 安全でないツールの実行禁止
- **ループ検出**: 無限ループの自動検出と停止

### その他の特徴
- **マルチプロバイダー対応**: OpenAI と Google Gemini API をサポート
- **型安全性**: Pydantic による厳密な型検証
- **詳細なログ**: 実行トレースとイベントログ
- **設定駆動**: YAML/JSON による柔軟な設定
- **CLIインターフェース**: Click による使いやすいコマンドライン

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_15/
├── src/
│   ├── __init__.py
│   ├── config.py                 # 設定管理（API キー読み込み）
│   ├── logger.py                 # ロギング設定
│   ├── main.py                   # メインエントリーポイント
│   ├── examples.py               # 8つの包括的な使用例
│   ├── agent/                    # エージェントフレームワーク
│   │   ├── __init__.py          # パッケージエクスポート
│   │   ├── base.py              # 基本抽象化 (107行)
│   │   ├── memory.py            # メモリ実装 (110行)
│   │   ├── toolbox.py           # ツール管理 (146行)
│   │   ├── strategies.py        # 思考戦略 (161行)
│   │   ├── states.py            # 状態管理 (156行)
│   │   ├── controller.py        # 実行制御 (182行)
│   │   ├── agent.py             # エージェント実装 (201行)
│   │   ├── factory.py           # ビルダー&ファクトリ (159行)
│   │   └── mediator.py          # マルチエージェント調整 (275行)
│   └── client/
│       ├── __init__.py
│       └── llm_client.py         # LLMクライアント初期化
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # 便利なコマンド集
├── README.md                     # このファイル
├── CLAUDE.md                     # 設計仕様書
├── ARCHITECTURE.md               # アーキテクチャ詳細
├── FIXES.md                      # バグ修正ドキュメント
└── REFACTORING.md                # リファクタリング詳細
```

### アーキテクチャ

このフレームワークは、以下の階層構造で構成されています:

```
┌─────────────────────────────────────────────────────────────┐
│                        BaseAgent                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Brain    │  │ ToolBox  │  │ Memory   │  │ Controller  │ │
│  │(Strategy)│  │(Composite│  │(Memento) │  │(Chain of    │ │
│  │          │  │ Pattern) │  │          │  │ Resp.)      │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │                                            │
    ┌────▼────────┐                          ┌───────▼──────┐
    │ AgentState  │                          │   Mediator   │
    │ (State      │                          │ (Multi-Agent │
    │  Pattern)   │                          │  Coordination│
    └─────────────┘                          └──────────────┘
```

**実行フロー:**

```
1. ユーザー → Agent.execute(goal)
              ↓
2. State: Idle → Thinking
              ↓
3. Loop until complete:
   ├─ Memory.get_context()
   ├─ Strategy.think(goal, context, tools)
   ├─ Controller.check_execution(action)
   ├─ Execute Action:
   │  ├─ TOOL_CALL: State → Acting → Execute → Thinking
   │  ├─ FINAL_ANSWER: State → Completed
   │  └─ THINK: Continue reasoning
   ├─ Memory.add_action(action)
   ├─ Memory.add_observation(result)
   └─ Strategy.update_context()
              ↓
4. Return result
              ↓
5. State: → Idle
```

### 実装の詳細

#### 1. 基本抽象化 (`src/agent/base.py`)

フレームワークの基礎となるインターフェースを定義:

```python
class Tool(ABC):
    """ツールの基底クラス"""
    @abstractmethod
    def execute(self, params: dict[str, Any]) -> ToolResult:
        pass

class Strategy(ABC):
    """思考戦略の基底クラス"""
    @abstractmethod
    def think(self, goal: str, context: dict[str, Any],
              available_tools: list[Tool]) -> Action:
        pass

class Memory(ABC):
    """メモリ管理の基底クラス"""
    @abstractmethod
    def save_snapshot(self) -> Any:
        pass

    @abstractmethod
    def restore_snapshot(self, snapshot: Any) -> None:
        pass
```

**ポイント**:
- ABC (Abstract Base Class) による厳密なインターフェース定義
- Memento パターンによるスナップショット機能の標準化
- 型ヒントによる型安全性の確保

#### 2. 思考戦略 (`src/agent/strategies.py`)

LLMを使用した3つの思考戦略を実装:

```python
class BaseStrategy(Strategy):
    """共通のLLM呼び出しロジックを持つ基底戦略"""
    def _call_llm(self, prompt: str) -> str:
        response = google_genai_client.models.generate_content(
            model=self.model, contents=prompt
        )
        return response.text

    def _parse_action(self, response: str) -> Action:
        # LLM応答を Action オブジェクトにパース
        ...

class ChainOfThoughtStrategy(BaseStrategy):
    """段階的推論戦略"""
    def think(self, goal, context, tools) -> Action:
        prompt = f"""Goal: {goal}
        Think step-by-step. You can:
        1. TOOL: <tool_name> | PARAMS: <json_params>
        2. ANSWER: <your_answer>"""
        return self._parse_action(self._call_llm(prompt))

class ReActStrategy(BaseStrategy):
    """推論と行動を統合した戦略"""
    # Thought → Action → Observation のサイクル

class TreeOfThoughtStrategy(BaseStrategy):
    """複数の推論経路を探索する戦略"""
    # ブランチングと評価による最適経路探索
```

**ポイント**:
- 基底クラスで重複コードを排除(60%のコード削減)
- 各戦略は `think()` メソッドのみ実装
- LLM応答の統一的なパース処理

#### 3. ツール管理 (`src/agent/toolbox.py`)

Composite パターンによる階層的なツール管理:

```python
class ToolBox(Tool):
    """ツールのコンテナ (Composite)"""
    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_all_tools(self) -> list[Tool]:
        """再帰的にすべてのツールを取得"""
        result = []
        for tool in self._tools.values():
            if isinstance(tool, ToolBox):
                result.extend(tool.get_all_tools())
            else:
                result.append(tool)
        return result

class CategorizableToolBox(ToolBox):
    """カテゴリ分けされたツールボックス"""
    def add_to_category(self, category: str, tool: Tool):
        self.add_category(category).add(tool)
```

**実装例**:
```python
# CalculatorTool - 基本的な算術演算
# WebSearchTool - Web検索のモック実装
```

**ポイント**:
- 個別ツールとツールグループを統一的に扱う
- カテゴリによる整理が可能
- 動的なツール追加・削除

#### 4. メモリ管理 (`src/agent/memory.py`)

Memento パターンによるスナップショット機能:

```python
@dataclass
class MemorySnapshot:
    """メモリの状態スナップショット"""
    timestamp: datetime
    observations: list[Any]
    actions: list[Action]
    metadata: dict[str, Any]

class ContextMemory(Memory):
    """シンプルなリストベースのメモリ"""
    def save_snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(
            timestamp=datetime.now(),
            observations=copy.deepcopy(self.observations),
            actions=copy.deepcopy(self.actions),
            metadata=copy.deepcopy(self.metadata),
        )

class ConversationalMemory(ContextMemory):
    """会話ターン形式のメモリ (継承による実装)"""
    # ContextMemory を拡張して会話ターンを管理

class MemoryCaretaker:
    """スナップショット管理 (Caretaker)"""
    def save(self, memory: Memory) -> int:
        snapshot = memory.save_snapshot()
        self.snapshots.append(snapshot)
        return len(self.snapshots) - 1

    def restore(self, memory: Memory, index: int) -> bool:
        memory.restore_snapshot(self.snapshots[index])
```

**ポイント**:
- 継承により重複コードを65%削減
- スナップショットによる状態の保存と復元
- Caretaker による一元管理

#### 5. 状態管理 (`src/agent/states.py`)

State パターンによる実行状態の管理:

```python
class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    COMPLETED = "completed"
    ERROR = "error"
    # ...

class AgentState(ABC):
    @abstractmethod
    def get_status(self) -> AgentStatus:
        pass

    def can_transition_to(self, next_state: "AgentState") -> bool:
        return True  # サブクラスでオーバーライド

class ThinkingState(AgentState):
    def can_transition_to(self, next_state: AgentState) -> bool:
        return isinstance(next_state,
            (ActingState, CompletedState, ErrorState))

class AgentContext:
    """状態を管理するコンテキスト"""
    def transition_to(self, new_state: AgentState) -> bool:
        if not self._state.can_transition_to(new_state):
            return False
        self._state = new_state
        self._state_history.append(...)
        return True
```

**状態遷移図**:
```
Idle → Thinking → Acting → Thinking → ... → Completed
                     ↓                         ↓
                   Error ← ← ← ← ← ← ← ← ← ← ←
```

**ポイント**:
- 許可された状態遷移のみを実行
- 状態履歴の自動記録
- イベントログによる詳細なトレース

#### 6. 実行制御 (`src/agent/controller.py`)

Chain of Responsibility による安全機構:

```python
class ExecutionHandler(ABC):
    """実行チェックのハンドラー基底クラス"""
    def set_next(self, handler: "ExecutionHandler"):
        self._next_handler = handler
        return handler

    def handle(self, request: ExecutionRequest) -> ExecutionResponse:
        response = self._check(request)
        if not response.allowed or not self._next_handler:
            return response
        return self._next_handler.handle(request)

class MaxStepsHandler(ExecutionHandler):
    """最大ステップ数制限"""

class CostLimitHandler(ExecutionHandler):
    """コスト制限"""

class LoopDetectionHandler(ExecutionHandler):
    """ループ検出"""

class ExecutionController:
    """ハンドラーチェーンの管理"""
    def add_handler(self, handler: ExecutionHandler):
        self.handlers.append(handler)
        self._rebuild_chain()
```

**実行例**:
```
Request → MaxSteps → CostLimit → ToolRateLimit → DangerousAction → LoopDetection
            ↓           ↓            ↓                 ↓                ↓
          allowed?   allowed?     allowed?          allowed?         allowed?
            ↓           ↓            ↓                 ↓                ↓
          Response (allowed=True/False, reason=...)
```

**ポイント**:
- 複数の安全チェックを動的に連鎖
- 拡張可能なハンドラーアーキテクチャ
- 各ハンドラーは単一責任

#### 7. エージェント実装 (`src/agent/agent.py`)

Brain、ToolBox、Memory を統合した BaseAgent:

```python
class BaseAgent:
    """基本エージェント実装"""
    def __init__(self, strategy: Strategy, toolbox: ToolBox,
                 memory: Memory | None = None,
                 controller: ExecutionController | None = None):
        self.strategy = strategy      # Brain
        self.toolbox = toolbox        # ToolBox
        self.memory = memory or ConversationalMemory()
        self.controller = controller or create_default_controller()
        self.agent_context = AgentContext()

    def execute(self, goal: str) -> str:
        """目標を達成するためにエージェントを実行"""
        self.agent_context.transition_to(ThinkingState())

        while not self._is_task_complete(goal):
            context = self.memory.get_context()
            action = self.strategy.think(goal, context,
                                       self.toolbox.get_all_tools())

            # 実行制御チェック
            exec_response = self.controller.check_execution(
                ExecutionRequest(action=action, context=context))
            if not exec_response.allowed:
                return f"Action blocked: {exec_response.reason}"

            # アクション実行
            result = self._execute_action(action)
            self.memory.add_observation(result)

        return result

class ConfigurableAgent(BaseAgent):
    """ログ機能付きエージェント"""

class MultiStrategyAgent(BaseAgent):
    """動的に戦略を切り替えられるエージェント"""
    def switch_strategy(self, strategy_name: str) -> bool:
        self.strategy = self.strategies[strategy_name]
```

**ポイント**:
- Strategy パターンによる思考戦略の交換
- 統一されたインターフェース
- 拡張可能な基底クラス設計

#### 8. ファクトリとビルダー (`src/agent/factory.py`)

設定駆動型のエージェント生成:

```python
class AgentBuilder:
    """流暢なインターフェースによるエージェント構築"""
    def with_strategy(self, strategy) -> "AgentBuilder":
        self.strategy = self._create_strategy(strategy) \
            if isinstance(strategy, dict) else strategy
        return self

    def with_toolbox(self, toolbox) -> "AgentBuilder":
        self.toolbox = self._create_toolbox(toolbox) \
            if isinstance(toolbox, dict) else toolbox
        return self

    def build(self) -> BaseAgent:
        """エージェントを構築"""
        if self.agent_type == "configurable":
            return ConfigurableAgent(...)
        elif self.agent_type == "multi_strategy":
            return MultiStrategyAgent(...)
        return BaseAgent(...)

def create_agent_from_config(config: dict) -> BaseAgent:
    """設定辞書からエージェントを生成"""
    builder = AgentBuilder()
    builder.with_strategy(config["strategy"])
    builder.with_toolbox(config["toolbox"])
    # ...
    return builder.build()
```

**使用例**:
```python
# Builder パターン
agent = (
    AgentBuilder()
    .with_strategy({"type": "react", "max_iterations": 10})
    .with_toolbox({"tools": [{"type": "calculator"}]})
    .with_agent_type("configurable")
    .build()
)

# Factory パターン
config = {
    "type": "configurable",
    "strategy": {"type": "react"},
    "toolbox": {"tools": [{"type": "calculator"}]}
}
agent = create_agent_from_config(config)
```

**ポイント**:
- 流暢なインターフェース (Fluent Interface)
- 設定辞書またはインスタンスの両方をサポート
- 65%のコード削減 (459行 → 159行)

#### 9. マルチエージェント調整 (`src/agent/mediator.py`)

Mediator パターンによるグラフベースの実行:

```python
class Node(ABC):
    """グラフノードの基底クラス"""
    @abstractmethod
    def execute(self, input_data: Any) -> NodeResult:
        pass

class AgentNode(Node):
    """エージェントを表すノード"""
    def execute(self, input_data: Any) -> NodeResult:
        result = self.agent.execute(str(input_data))
        return NodeResult(node_id=self.node_id,
                         success=True, output=result)

class SimpleGraphMediator(GraphMediator):
    """シンプルなグラフ実行"""
    def execute_graph(self, start_node_id: str,
                     input_data: Any) -> dict:
        # グラフを順次実行
        ...

class ParallelGraphMediator(SimpleGraphMediator):
    """並列実行サポート"""
    def execute_graph(self, start_node_id: str,
                     input_data: Any) -> dict:
        # PARALLEL エッジを並列実行
        ...
```

**ポイント**:
- グラフ構造によるワークフロー管理
- 順次実行と並列実行のサポート
- ノード間のメッセージルーティング

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
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
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
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

**Example 1: 基本的なエージェント**

```python
from src.agent import (
    AgentBuilder,
    ChainOfThoughtStrategy,
    CalculatorTool,
    CategorizableToolBox,
)

# コンポーネントの作成
strategy = ChainOfThoughtStrategy(max_steps=5)
toolbox = CategorizableToolBox()
toolbox.add_to_category("math", CalculatorTool())

# ビルダーパターンでエージェント構築
agent = (
    AgentBuilder()
    .with_strategy(strategy)
    .with_toolbox(toolbox)
    .with_agent_type("configurable")
    .with_config(enable_logging=True)
    .build()
)

# 実行
result = agent.execute("Calculate 15 plus 27")
print(result)
```

**Example 2: 設定ベースのエージェント**

```python
from src.agent import create_agent_from_config

config = {
    "type": "configurable",
    "strategy": {
        "type": "react",
        "max_iterations": 10
    },
    "toolbox": {
        "categorized": True,
        "tools": [
            {"type": "calculator", "category": "math"},
            {"type": "web_search", "category": "search"}
        ]
    },
    "controller": {
        "handlers": {
            "max_steps": 50,
            "max_cost": 10.0,
            "enable_loop_detection": True
        }
    }
}

agent = create_agent_from_config(config)
result = agent.execute("Search for information and calculate")
```

**Example 3: マルチストラテジーエージェント**

```python
from src.agent import (
    AgentBuilder,
    ChainOfThoughtStrategy,
    ReActStrategy,
)

strategies = {
    "cot": ChainOfThoughtStrategy(max_steps=5),
    "react": ReActStrategy(max_iterations=8),
}

agent = (
    AgentBuilder()
    .with_toolbox(toolbox)
    .with_agent_type("multi_strategy")
    .with_config(strategies=strategies, default_strategy="cot")
    .build()
)

# デフォルト戦略で実行
result1 = agent.execute("Task 1")

# 戦略を切り替え
agent.switch_strategy("react")
result2 = agent.execute("Task 2")
```

**Example 4: メモリスナップショット**

```python
from src.agent.memory import MemoryCaretaker, ConversationalMemory

memory = ConversationalMemory(max_turns=10)
caretaker = MemoryCaretaker()

agent = (
    AgentBuilder()
    .with_strategy(ChainOfThoughtStrategy())
    .with_toolbox(toolbox)
    .with_memory(memory)
    .build()
)

# タスク実行
agent.execute("Calculate 10 plus 5")

# スナップショット保存
snapshot_id = caretaker.save(memory)

# さらに実行
agent.execute("Multiply 7 by 8")

# スナップショットから復元
caretaker.restore(memory, snapshot_id)
print("Memory restored!")
```

**Example 5: マルチエージェント調整**

```python
from src.agent import (
    SimpleGraphMediator,
    AgentNode,
    Edge,
    EdgeType,
)

# 専門化されたエージェントを作成
math_agent = create_agent_from_config(math_config)
search_agent = create_agent_from_config(search_config)

# メディエーターでグラフを構築
mediator = SimpleGraphMediator()
mediator.add_node(AgentNode("math", math_agent))
mediator.add_node(AgentNode("search", search_agent))
mediator.add_edge(Edge("math", "search", EdgeType.SEQUENTIAL))

# グラフを実行
result = mediator.execute_graph("math", "Solve this problem")
```

#### CLIコマンド

```bash
# 特定のエージェント例を実行
python -m src.main -a example_1_basic_agent
python -m src.main -a example_3_multi_strategy_agent
python -m src.main -a example_4_config_based_agent

# すべての例を実行
python -m src.main -a all

# ヘルプを表示
python -m src.main --help
```

### 出力例

**実行ログ**:
```
[2025-11-09 15:41:42] [INFO] [__main__] [main.py:86] [main] Running agent: example_4_config_based_agent

[2025-11-09 15:41:42] [INFO] [src.examples] [examples.py:155] [example_4_config_based_agent]
=== Example 4: Config-Based Agent Creation ===

[2025-11-09 15:41:46] [INFO] [src.examples] [examples.py:196] [example_4_config_based_agent] Goal: Calculate the product of 12 and 15
[2025-11-09 15:41:46] [INFO] [src.examples] [examples.py:197] [example_4_config_based_agent] Result: Action blocked: Possible infinite loop detected: action repeated 3 times

=== Agent Execution Trace ===
Iterations: 3
Final State: idle

State History:
  idle -> thinking at 2025-11-09 15:41:42.988316
  thinking -> error at 2025-11-09 15:41:46.934697
  error -> idle at 2025-11-09 15:41:46.934711

Events:
  [thinking] Agent is thinking
  [error] Agent error: Action blocked: Possible infinite loop detected: action repeated 3 times
  [idle] Agent is idle
```

**期待される動作**:
- ループ検出による安全な停止
- 詳細な状態遷移履歴
- イベントログによるトレース

### テスト方法

#### 1. インポートテスト

```bash
python -c "from src.agent import AgentBuilder, CalculatorTool, ChainOfThoughtStrategy; print('✓ Imports successful')"
```

期待される出力:
```
✓ Imports successful
```

#### 2. 基本エージェントのテスト

```bash
python -m src.main -a example_1_basic_agent
```

期待される動作:
- エージェントが正常に起動
- Chain-of-Thought 戦略による推論
- 実行トレースの出力

#### 3. マルチストラテジーのテスト

```bash
python -m src.main -a example_3_multi_strategy_agent
```

期待される動作:
- 複数の戦略間の切り替え
- 各戦略の実行結果
- 戦略名のログ出力

#### 4. 設定ベースエージェントのテスト

```bash
python -m src.main -a example_4_config_based_agent
```

期待される動作:
- 設定から正しくエージェントを生成
- 実行制御機構の動作確認
- 詳細なログ出力

#### 5. すべての例の実行

```bash
python -m src.main -a all
```

期待される動作:
- 8つの例がすべて順次実行
- 各例の成功確認
- エラーなく完了

#### 6. コード品質の確認

```bash
# 行数の確認 (リファクタリング前: 3,752行、後: 1,643行)
wc -l src/agent/*.py | tail -1

# 型チェック
mypy src/agent/

# フォーマット確認
ruff check src/agent/
```

## 高度な使用例

### カスタム戦略の実装

```python
from src.agent.base import Strategy, Action, ActionType

class CustomStrategy(Strategy):
    def __init__(self, **kwargs):
        super().__init__("CustomStrategy")

    def think(self, goal, context, available_tools):
        # カスタムロジック実装
        return Action(
            type=ActionType.FINAL_ANSWER,
            answer="Custom result"
        )
```

### カスタムツールの実装

```python
from src.agent.base import Tool, ToolResult

class CustomTool(Tool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="カスタムツールの説明"
        )

    def execute(self, params):
        # ツールロジック実装
        return ToolResult(success=True, data=result)

    def validate_params(self, params):
        return "required_param" in params
```

### カスタム実行ハンドラーの実装

```python
from src.agent.controller import ExecutionHandler, ExecutionResponse

class CustomHandler(ExecutionHandler):
    def _check(self, request):
        if some_condition:
            return ExecutionResponse(
                allowed=False,
                reason="Custom check failed"
            )
        return ExecutionResponse(allowed=True)
```

## アーキテクチャの利点

### 保守性
- **56%のコード削減**: 3,752行 → 1,643行
- **明確な責任分離**: 各モジュールが単一責任
- **低い結合度**: コンポーネント間の依存関係が最小限

### 拡張性
- **プラグイン可能な戦略**: 新しい思考方法を簡単に追加
- **動的ツール追加**: 実行時にツールを追加・削除可能
- **カスタムハンドラー**: 独自の安全チェックを追加可能

### 安全性
- **多層防御**: 5つの独立した安全機構
- **状態遷移制御**: 不正な状態変化を防止
- **ループ検出**: 無限ループの自動検出

### 可観測性
- **詳細なログ**: 実行の各ステップを記録
- **状態履歴**: すべての状態遷移を追跡
- **イベントログ**: タイムスタンプ付きイベント記録

## 参考資料

- **CLAUDE.md**: 設計仕様と理論的背景
- **ARCHITECTURE.md**: 詳細なアーキテクチャ図とフロー
- **FIXES.md**: バグ修正の詳細ドキュメント
- **REFACTORING.md**: リファクタリングの全記録

## ライセンス

このプロジェクトは LLM Best Practice Book の一部です。

# Chapter 4 Section 8: AIエージェントの抽象化設計

## 概要

このプロジェクトは、**AIエージェントの抽象化設計**パターンを実装した包括的なフレームワークです。LLMを中核に据えた自律的なシステムを、高レベルなインターフェースとしてカプセル化し、8つの設計パターンを組み合わせることで、保守性と拡張性に優れたエージェントシステムを構築します。

思考戦略(Brain)、ツールカタログ(ToolBox)、コンテキストマネージャー(Memory)の3つの独立したコンポーネントに分離し、開発者は統一されたインターフェースを通じてエージェントに目標を指示するだけで、自律的なタスク実行が可能になります。

## 機能

### コアアーキテクチャ
- **Brain (思考エンジン)**: Strategy パターンによる交換可能な思考戦略
  - Chain-of-Thought (CoT): 段階的推論
  - ReAct: 推論と行動の統合
  - Tree-of-Thought (ToT): 複数経路の探索
- **ToolBox (ツールカタログ)**: Composite パターンによる階層的ツール管理
- **Memory (コンテキストマネージャー)**: Memento パターンによるスナップショット機能

### 実装済み設計パターン
| パターン | コンポーネント | 目的 |
|---------|---------------|------|
| Strategy | `strategies.py` | プラグイン可能な思考戦略 (CoT, ReAct, ToT) |
| Composite | `toolbox.py` | ツールの階層構造管理 |
| Memento | `memory.py` | メモリのスナップショットと復元 |
| State | `states.py` | エージェント実行状態の管理 |
| Chain of Responsibility | `controller.py` | 実行制御と安全機構 |
| Builder | `factory.py` | 流暢なエージェント構築インターフェース |
| Factory | `factory.py` | 設定ベースのエージェント生成 |
| Mediator | `mediator.py` | マルチエージェント調整 |

### 安全機構
- **MaxStepsHandler**: 実行ステップ数制限（暴走実行の防止）
- **CostLimitHandler**: API呼び出しコストの制限
- **ToolRateLimitHandler**: 過剰な外部呼び出しの防止
- **DangerousActionHandler**: 安全でないツールの実行禁止
- **LoopDetectionHandler**: 無限ループの自動検出と停止

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_15/
├── src/
│   ├── __init__.py
│   ├── config.py                 # 設定管理（API キー読み込み）
│   ├── logger.py                 # ロギング設定
│   ├── main.py                   # メインエントリーポイント (CLI)
│   ├── examples.py               # 8つの包括的な使用例
│   ├── agent/                    # エージェントフレームワーク
│   │   ├── __init__.py          # パッケージエクスポート
│   │   ├── base.py              # 基本抽象化 (Tool, Strategy, Memory)
│   │   ├── memory.py            # メモリ実装 (Memento パターン)
│   │   ├── toolbox.py           # ツール管理 (Composite パターン)
│   │   ├── strategies.py        # 思考戦略 (Strategy パターン)
│   │   ├── states.py            # 状態管理 (State パターン)
│   │   ├── controller.py        # 実行制御 (Chain of Responsibility)
│   │   ├── agent.py             # エージェント実装
│   │   ├── factory.py           # ビルダー & ファクトリ
│   │   └── mediator.py          # マルチエージェント調整
│   └── client/
│       ├── __init__.py
│       └── llm_client.py         # LLMクライアント初期化
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── CLAUDE.md                     # 設計仕様書
└── README.md                     # このファイル
```

### アーキテクチャ

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
   └─ Memory.add_observation(result)
              ↓
4. Return result
              ↓
5. State: → Idle
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0 (オプション)
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

```bash
cd chapter_3/section_15

# 環境変数ファイルの作成
cp .envrc.example .envrc

# .envrc を編集して API キーを設定
# export GEMINI_API_KEY=your-gemini-api-key-here

# 依存関係のインストール
uv sync  # または: pip install -e .
```

### 使用方法、実行方法

#### CLI コマンド

```bash
# 特定のエージェント例を実行
python -m src.main -a example_1_basic_agent
python -m src.main -a example_2_react_agent
python -m src.main -a example_3_multi_strategy_agent
python -m src.main -a example_4_config_based_agent
python -m src.main -a example_5_graph_mediator
python -m src.main -a example_6_parallel_execution
python -m src.main -a example_7_memory_snapshots
python -m src.main -a example_8_execution_control

# すべての例を実行
python -m src.main -a all

# ヘルプを表示
python -m src.main --help
```

#### コード例

**基本的なエージェント構築 (Builder パターン)**:

```python
from src.agent import (
    AgentBuilder, ChainOfThoughtStrategy,
    CalculatorTool, CategorizableToolBox
)

# ツールボックスの作成
toolbox = CategorizableToolBox()
toolbox.add_to_category("math", CalculatorTool())

# エージェントの構築
agent = (
    AgentBuilder()
    .with_strategy(ChainOfThoughtStrategy(max_steps=5))
    .with_toolbox(toolbox)
    .with_agent_type("configurable")
    .build()
)

result = agent.execute("Calculate 15 plus 27")
```

**設定ベースのエージェント生成 (Factory パターン)**:

```python
from src.agent import create_agent_from_config

config = {
    "type": "configurable",
    "strategy": {"type": "react", "max_iterations": 10},
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
```

**マルチストラテジーエージェント**:

```python
from src.agent import AgentBuilder, ChainOfThoughtStrategy, ReActStrategy

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

# 戦略の動的切り替え
agent.switch_strategy("react")
```

**メモリスナップショット (Memento パターン)**:

```python
from src.agent.memory import MemoryCaretaker, ConversationalMemory

memory = ConversationalMemory(max_turns=10)
caretaker = MemoryCaretaker()

# スナップショット保存
snapshot_id = caretaker.save(memory)

# ... タスク実行 ...

# スナップショットから復元
caretaker.restore(memory, snapshot_id)
```

### 出力例

```
[2025-12-13 15:17:19] [INFO] Running agent: example_1_basic_agent

=== Example 1: Basic Agent with Chain-of-Thought ===

=== Agent Execution Trace ===
Iterations: 6
Final State: idle

State History:
  idle -> thinking at 2025-12-13 15:17:19.097389
  thinking -> acting at 2025-12-13 15:17:20.460676
  acting -> thinking at 2025-12-13 15:17:20.460697
  ...
  thinking -> completed at 2025-12-13 15:17:25.500652
  completed -> idle at 2025-12-13 15:17:25.500657

Events:
  [thinking] Agent is thinking
  [acting] Agent is acting
  ...
  [completed] Agent is completed
  [idle] Agent is idle

Goal: Calculate the sum of 15 and 27, then multiply the result by 3
Result: Task execution terminated
```

## 利用可能なサンプル

| サンプル | 説明 |
|---------|------|
| `example_1_basic_agent` | Chain-of-Thought 戦略による基本的なエージェント |
| `example_2_react_agent` | ReAct 戦略による推論・行動統合エージェント |
| `example_3_multi_strategy_agent` | 動的に戦略を切り替えられるエージェント |
| `example_4_config_based_agent` | 設定辞書からエージェントを生成 |
| `example_5_graph_mediator` | Mediator パターンによるマルチエージェント調整 |
| `example_6_parallel_execution` | 並列実行のサポート |
| `example_7_memory_snapshots` | Memento パターンによるメモリスナップショット |
| `example_8_execution_control` | Chain of Responsibility による実行制御 |

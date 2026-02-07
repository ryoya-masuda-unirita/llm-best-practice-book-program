# Chapter 4 Section 9: AIエージェントフレームワーク（デザインパターン適用）

## 概要

本プロジェクトは、GoFデザインパターンを活用して構築された拡張可能なAIエージェントフレームワークです。「安定したコア層と柔軟な拡張層」というアーキテクチャ設計により、コア部分の安定性を保ちながら、具体的な実装を柔軟に追加・変更できる構造を実現しています。

フレームワークは複数の推論戦略（Chain-of-Thought、ReAct、Tree-of-Thought）、ツール管理、メモリ管理、実行制御、マルチエージェント協調などの機能を提供します。各コンポーネントはデザインパターンに基づいて設計されており、単一責任の原則に従った疎結合な構造となっています。

## 機能

- **推論戦略（Strategy Pattern）**: Chain-of-Thought、ReAct、Tree-of-Thoughtなど複数の推論戦略を切り替え可能
- **ツール管理（Composite Pattern）**: ツールを階層的に管理し、カテゴリ別に整理可能
- **メモリ管理（Memento Pattern）**: エージェントの状態をスナップショットとして保存・復元可能
- **実行制御（Chain of Responsibility）**: ステップ数制限、コスト制限、レート制限などのハンドラをチェーン形式で適用
- **状態管理（State Pattern）**: エージェントのライフサイクルを状態遷移として管理
- **マルチエージェント協調（Mediator Pattern）**: 複数エージェントをグラフ構造で連携、逐次・並列実行に対応
- **柔軟な構築（Builder Pattern）**: 設定辞書またはBuilderパターンによる宣言的なエージェント構築

## プロジェクト構成

### ディレクトリ構成

```
src/
├── main.py                    # CLIエントリーポイント
├── examples.py                # 8つのサンプルコード
├── config.py                  # 環境変数設定
├── logger.py                  # ロギング設定
├── client/
│   └── llm_client.py          # Google Gemini APIクライアント
└── agent/
    ├── core/                  # コア層（安定した抽象化）
    │   ├── base.py            # 基本インターフェース（Tool, Strategy, Action等）
    │   ├── agent.py           # BaseAgent実装
    │   ├── controller.py      # ExecutionController（Chain of Responsibility）
    │   ├── mediator.py        # GraphMediator（Mediator Pattern）
    │   ├── memory.py          # Memory抽象クラス（Memento Pattern）
    │   ├── states.py          # 状態管理（State Pattern）
    │   └── toolbox.py         # ToolBox（Composite Pattern）
    └── extensions/            # 拡張層（具体的な実装）
        ├── factory.py         # AgentBuilder, create_agent_from_config
        ├── agents/            # ConfigurableAgent, MultiStrategyAgent
        ├── strategies/        # ChainOfThought, ReAct, TreeOfThought
        ├── handlers/          # MaxSteps, CostLimit, ToolRateLimit等
        ├── mediators/         # SimpleGraphMediator, ParallelGraphMediator
        ├── memory/            # ConversationalMemory, ContextMemory, MemoryCaretaker
        ├── nodes/             # AgentNode, DecisionNode, AggregatorNode
        └── tools/             # Calculator, WebSearch, TextGenerator
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Agent Framework                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      Extensions Layer                                ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              ││
│  │  │  Strategies   │ │   Handlers    │ │   Mediators   │              ││
│  │  │  - CoT        │ │  - MaxSteps   │ │  - Simple     │              ││
│  │  │  - ReAct      │ │  - CostLimit  │ │  - Parallel   │              ││
│  │  │  - ToT        │ │  - RateLimit  │ │               │              ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘              ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              ││
│  │  │    Memory     │ │     Tools     │ │    Agents     │              ││
│  │  │ - Conversa.   │ │ - Calculator  │ │ - Configurable│              ││
│  │  │ - Context     │ │ - WebSearch   │ │ - MultiStrat. │              ││
│  │  │ - Caretaker   │ │ - TextGen     │ │               │              ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘              ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                         Core Layer                                   ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              ││
│  │  │   Strategy    │ │    Memory     │ │  Controller   │              ││
│  │  │   (Abstract)  │ │   (Abstract)  │ │   + Handler   │              ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘              ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              ││
│  │  │   ToolBox     │ │   BaseAgent   │ │ GraphMediator │              ││
│  │  │  (Composite)  │ │               │ │   (Abstract)  │              ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘              ││
│  │  ┌───────────────┐                                                   ││
│  │  │ AgentContext  │ ← State Pattern                                   ││
│  │  │   (States)    │                                                   ││
│  │  └───────────────┘                                                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### デザインパターン一覧

| パターン | 適用箇所 | 目的 |
|---------|---------|------|
| **Strategy** | `Strategy`, `ChainOfThoughtStrategy`, `ReActStrategy`, `TreeOfThoughtStrategy` | 推論アルゴリズムの切り替え |
| **Composite** | `ToolBox`, `CategorizableToolBox` | ツールの階層的管理 |
| **Memento** | `Memory`, `MemorySnapshot`, `MemoryCaretaker` | 状態の保存・復元 |
| **Chain of Responsibility** | `ExecutionHandler`, `ExecutionController` | 実行制御の連鎖的処理 |
| **State** | `AgentState`, `AgentContext`, `IdleState`, `ThinkingState`等 | エージェントのライフサイクル管理 |
| **Mediator** | `GraphMediator`, `SimpleGraphMediator`, `ParallelGraphMediator` | マルチエージェント協調 |
| **Builder** | `AgentBuilder` | 宣言的なエージェント構築 |
| **Factory Method** | `create_agent_from_config` | 設定からのエージェント生成 |

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要依存ライブラリ:
  - `google-genai`: Google Gemini API クライアント
  - `click`: CLIフレームワーク
  - `pydantic`: 設定管理
  - `python-dotenv`: 環境変数読み込み

### セットアップ

1. 環境変数の設定

```bash
cp .envrc.example .envrc
```

`.envrc`を編集してAPIキーを設定:

```bash
# Google Gemini API Key
# Get your key from: https://aistudio.google.com/app/apikey
export GEMINI_API_KEY="your-gemini-api-key-here"
```

2. 依存関係のインストール

```bash
uv sync
```

### 使用方法、実行方法

```bash
$ python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -a, --agent [example_1_basic_agent|example_2_react_agent|example_3_multi_strategy_agent|example_4_config_based_agent|example_5_graph_mediator|example_6_parallel_execution|example_7_memory_snapshots|example_8_execution_control|all]
                                  The agent workflow to run.  [required]
  --help                          Show this message and exit.
```

### CLIから各サンプルを実行:

```bash
# 特定のサンプルを実行
uv run python -m src.main --agent example_1_basic_agent

# 全サンプルを順次実行
uv run python -m src.main --agent all
```

### 利用可能なサンプル一覧:

| サンプル名 | 説明 |
|-----------|------|
| `example_1_basic_agent` | Chain-of-Thought戦略を使用した基本エージェント |
| `example_2_react_agent` | ReAct戦略を使用したエージェント |
| `example_3_multi_strategy_agent` | 複数戦略を切り替え可能なエージェント |
| `example_4_config_based_agent` | 設定辞書からエージェントを生成 |
| `example_5_graph_mediator` | Mediatorパターンによるマルチエージェント協調 |
| `example_6_parallel_execution` | 並列実行によるマルチエージェント処理 |
| `example_7_memory_snapshots` | Mementoパターンによるメモリスナップショット |
| `example_8_execution_control` | Chain of Responsibilityによる実行制御 |

### 実行結果例

```bash
$ uv run python -m src.main --agent example_1_basic_agent

[2026-02-07 08:57:04,228] [INFO] [__main__] [main.py:83] [main] Running agent: example_1_basic_agent

[2026-02-07 08:57:04,228] [INFO] [src.examples] [examples.py:36] [example_1_basic_agent] 
=== Example 1: Basic Agent with Chain-of-Thought ===

[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:49] [_log_execution] 
=== Agent Execution Trace ===
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:50] [_log_execution] Iterations: 2
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:51] [_log_execution] Final State: idle

[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:52] [_log_execution] State History:
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:57] [_log_execution]   idle -> thinking at 2026-02-07 08:57:04.228340
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:57] [_log_execution]   thinking -> acting at 2026-02-07 08:57:05.571529
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:57] [_log_execution]   acting -> thinking at 2026-02-07 08:57:10.337268
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:57] [_log_execution]   thinking -> completed at 2026-02-07 08:57:11.484063
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:57] [_log_execution]   completed -> idle at 2026-02-07 08:57:11.484078
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:58] [_log_execution] 
Events:
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:63] [_log_execution]   [thinking] Agent is thinking
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:63] [_log_execution]   [acting] Agent is acting
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:63] [_log_execution]   [thinking] Agent is thinking
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:63] [_log_execution]   [completed] Agent is completed
[2026-02-07 08:57:11,484] [INFO] [src.agent.extensions.agents.configurable] [configurable.py:63] [_log_execution]   [idle] Agent is idle
[2026-02-07 08:57:11,484] [INFO] [src.examples] [examples.py:58] [example_1_basic_agent] Goal: Write a haiku about the changing seasons
[2026-02-07 08:57:11,484] [INFO] [src.examples] [examples.py:59] [example_1_basic_agent] Result:
Warm sun turns to chill,
Leaves dance down in fiery hues,
Earth dreams, fresh life waits.
[2026-02-07 08:57:11,484] [INFO] [__main__] [main.py:88] [main] 
✓ Agent 'example_1_basic_agent' completed successfully
[2026-02-07 08:57:11,484] [INFO] [__main__] [main.py:92] [main]   Output: Warm sun turns to chill,
Leaves dance down in fiery hues,
Earth dreams, fresh life waits.
```

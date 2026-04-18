# Chapter 4 Section 8: AIエージェントの抽象化設計

## 概要

本プロジェクトは、LLMを活用した自律型AIエージェントシステムを構築するための**抽象化設計パターン**を実装しています。AIエージェントの責務を「思考エンジン（Brain/Strategy）」「ツールカタログ（ToolBox）」「コンテキストマネージャー（Memory）」の3つの独立したコンポーネントに分離し、交換可能で拡張性の高いアーキテクチャを実現します。

この設計により、新しい思考戦略（Chain-of-Thought、ReAct、Tree-of-Thoughtなど）やツールの追加が、システムの他の部分に影響を与えることなく容易に行えます。また、実行制御機構（ExecutionController）により、無限ループやコスト超過といったリスクを防止する安全機構を組み込んでいます。

本実装では以下の8つのデザインパターンを活用しています：
- **Strategy**: 思考アルゴリズムの交換
- **Composite**: ツールの階層的管理
- **Memento**: メモリのスナップショット/復元
- **State**: エージェント実行状態の管理
- **Chain of Responsibility**: 安全ハンドラの連鎖
- **Builder**: エージェントの段階的構築
- **Factory**: 設定ベースのエージェント生成
- **Mediator**: マルチエージェント連携

## 機能

- **思考戦略の交換**: Chain-of-Thought、ReAct、Tree-of-Thoughtを実行時に切り替え可能
- **ツール管理**: Compositeパターンによる階層的なツール管理とカテゴリ分類
- **メモリ管理**: 会話履歴の管理とスナップショット/ロールバック機能
- **実行制御**: 最大ステップ数、コスト上限、ループ検出などの安全機構
- **マルチエージェント**: グラフベースのエージェント連携と並列実行
- **設定ベース構築**: JSON/辞書形式の設定からエージェントを動的生成

## プロジェクト構成

### アーキテクチャ

```
+---------------------------------------------------------------+
|                         BaseAgent                              |
|  +----------+  +----------+  +----------+  +---------------+  |
|  | Brain    |  | ToolBox  |  | Memory   |  | Controller    |  |
|  |(Strategy)|  |(Composite)|  |(Memento) |  |(Chain of Resp)|  |
|  +----------+  +----------+  +----------+  +---------------+  |
+---------------------------------------------------------------+
        |                                           |
   +----v--------+                         +--------v-------+
   | AgentState  |                         |    Mediator    |
   | (State      |                         | (Multi-Agent   |
   |  Pattern)   |                         |  Coordination) |
   +-------------+                         +----------------+
```

### 実行フロー

```
1. User -> Agent.execute(goal)
              |
              v
2. State: Idle -> Thinking
              |
              v
3. Loop until complete:
   +-- Memory.get_context()
   +-- Strategy.think(goal, context, tools)
   +-- Controller.check_execution(action)
   +-- Execute Action:
   |   +-- TOOL_CALL: State -> Acting -> Execute -> Thinking
   |   +-- FINAL_ANSWER: State -> Completed
   |   +-- THINK: Continue reasoning
   +-- Memory.add_action(action)
   +-- Memory.add_observation(result)
              |
              v
4. Return result -> State: Idle
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| google-genai | >=1.45.0 | Gemini APIクライアント |
| openai | >=2.4.0 | OpenAI APIクライアント（オプション） |
| pydantic | >=2.12.2 | 設定とデータバリデーション |
| click | >=8.3.0 | CLIインターフェース |
| python-dotenv | >=1.1.1 | 環境変数読み込み |

### セットアップ

```bash
cd chapter_4/section_8

# 環境変数設定
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定:
GEMINI_API_KEY=<your_gemini_api_key_here>

# 依存関係インストール
uv sync  # または: pip install -e .
```

### 実行方法

```bash
# 全サンプルを実行
uv run python -m src.main -a all

# 特定のサンプルを実行
uv run python -m src.main -a example_1_basic_agent
uv run python -m src.main -a example_2_react_agent
uv run python -m src.main -a example_3_multi_strategy_agent
uv run python -m src.main -a example_4_config_based_agent
uv run python -m src.main -a example_5_graph_mediator
uv run python -m src.main -a example_6_parallel_execution
uv run python -m src.main -a example_7_memory_snapshots
uv run python -m src.main -a example_8_execution_control

# ヘルプ表示
uv run python -m src.main --help
```

### CLIオプション

```shell
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -a, --agent [example_1_basic_agent|example_2_react_agent|example_3_multi_strategy_agent|example_4_config_based_agent|example_5_graph_mediator|example_6_parallel_execution|example_7_memory_snapshots|example_8_execution_control|all]
                                  The agent workflow to run.  [required]
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--agent` | `-a` | 実行するエージェントワークフロー（必須） |
| `--help` | | ヘルプメッセージを表示 |

**利用可能なエージェント:**

| エージェント名 | 説明 |
|---------------|------|
| `example_1_basic_agent` | Chain-of-Thought戦略の基本エージェント |
| `example_2_react_agent` | ReAct戦略によるエージェント |
| `example_3_multi_strategy_agent` | 動的な戦略切り替え |
| `example_4_config_based_agent` | Factoryパターンでの生成 |
| `example_5_graph_mediator` | マルチエージェント連携 |
| `example_6_parallel_execution` | 並列エージェント実行 |
| `example_7_memory_snapshots` | Mementoパターンのデモ |
| `example_8_execution_control` | 安全ハンドラチェーン |
| `all` | 全サンプルを実行 |

### 出力例

```bash
$ uv run python -m src.main -a example_1_basic_agent

[2026-02-07 08:54:06,213] [INFO] [__main__] [main.py:84] [main] Running agent: example_1_basic_agent

[2026-02-07 08:54:06,213] [INFO] [src.examples] [examples.py:33] [example_1_basic_agent] 
=== Example 1: Basic Agent with Chain-of-Thought ===

[2026-02-07 08:54:07,769] [INFO] [src.agent.agent] [agent.py:172] [_log_execution] 
=== Agent Execution Trace ===
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:173] [_log_execution] Iterations: 1
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:174] [_log_execution] Final State: idle

[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:175] [_log_execution] State History:
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   idle -> thinking at 2026-02-07 08:54:06.213214
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   thinking -> completed at 2026-02-07 08:54:07.769916
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   completed -> idle at 2026-02-07 08:54:07.769933
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:181] [_log_execution] 
Events:
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [thinking] Agent is thinking
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [completed] Agent is completed
[2026-02-07 08:54:07,770] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [idle] Agent is idle
[2026-02-07 08:54:07,770] [INFO] [src.examples] [examples.py:58] [example_1_basic_agent] Goal: Write a haiku about the changing seasons
[2026-02-07 08:54:07,770] [INFO] [src.examples] [examples.py:59] [example_1_basic_agent] Result:
Green fades to gold now,
Winter's breath will chill the air,
Life turns, new cycle.
[2026-02-07 08:54:07,770] [INFO] [__main__] [main.py:89] [main] 
✓ Agent 'example_1_basic_agent' completed successfully
[2026-02-07 08:54:07,770] [INFO] [__main__] [main.py:93] [main]   Output: Green fades to gold now,
Winter's breath will chill the air,
Life turns, new cycle.
```

```bash
$ uv run python -m src.main -a example_2_react_agent      
[2026-02-07 08:55:18,581] [INFO] [__main__] [main.py:84] [main] Running agent: example_2_react_agent

[2026-02-07 08:55:18,581] [INFO] [src.examples] [examples.py:66] [example_2_react_agent] 
=== Example 2: Agent with ReAct Strategy ===

[2026-02-07 08:55:28,847] [INFO] [src.agent.agent] [agent.py:172] [_log_execution] 
=== Agent Execution Trace ===
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:173] [_log_execution] Iterations: 4
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:174] [_log_execution] Final State: idle

[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:175] [_log_execution] State History:
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   idle -> thinking at 2026-02-07 08:55:18.581284
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   thinking -> acting at 2026-02-07 08:55:19.614846
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   acting -> thinking at 2026-02-07 08:55:19.614895
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   thinking -> acting at 2026-02-07 08:55:23.555026
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   acting -> thinking at 2026-02-07 08:55:23.555046
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   thinking -> completed at 2026-02-07 08:55:28.847894
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:180] [_log_execution]   completed -> idle at 2026-02-07 08:55:28.847913
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:181] [_log_execution] 
Events:
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [thinking] Agent is thinking
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [acting] Agent is acting
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [thinking] Agent is thinking
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [acting] Agent is acting
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [thinking] Agent is thinking
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [completed] Agent is completed
[2026-02-07 08:55:28,848] [INFO] [src.agent.agent] [agent.py:186] [_log_execution]   [idle] Agent is idle
[2026-02-07 08:55:28,848] [INFO] [src.examples] [examples.py:107] [example_2_react_agent] Goal: Search for information about the Eiffel Tower, then write a short poem inspired by what you learned
[2026-02-07 08:55:28,848] [INFO] [src.examples] [examples.py:108] [example_2_react_agent] Result:
A structure of iron, a skyward climb,
Parisian sentinel, defying time.
From latticework forged, a towering might,
An iconic beacon, bathed in city light.
A metallic marvel, a symbol grand and bold,
A Parisian story, in steel forever told.
[2026-02-07 08:55:28,848] [INFO] [__main__] [main.py:89] [main] 
✓ Agent 'example_2_react_agent' completed successfully
[2026-02-07 08:55:28,848] [INFO] [__main__] [main.py:93] [main]   Output: A structure of iron, a skyward climb,
Parisian sentinel, defying time.
From latticework forged, a towering might,
An iconic beacon, bathed in city light.
A metallic marvel, a symbol grand and bold,
A Parisian story, in steel forever told.
```


## 主要コンポーネント

### 思考戦略（Strategy）

| 戦略 | 説明 | 用途 |
|------|------|------|
| `ChainOfThoughtStrategy` | 逐次的なステップバイステップ推論 | 数学、論理問題 |
| `ReActStrategy` | 思考-行動-観察のインターリーブ | 調査、情報収集 |
| `TreeOfThoughtStrategy` | 複数パスの探索とスコアリング | 創造的問題解決 |

### 安全ハンドラ

| ハンドラ | 説明 | デフォルト値 |
|---------|------|-------------|
| `MaxStepsHandler` | 実行ステップ数の上限 | 50ステップ |
| `CostLimitHandler` | APIコストの上限 | $10.0 |
| `ToolRateLimitHandler` | ツールごとの呼び出し回数制限 | 10回/ツール |
| `DangerousActionHandler` | 危険な操作のブロック | delete, destroy, remove_all |
| `LoopDetectionHandler` | 無限ループの検出 | 5アクション中3回の繰り返し |

### 状態遷移

```
有効な遷移:
  Idle -> Thinking
  Thinking -> Acting, Completed, Error
  Acting -> Thinking, Completed, Error
  Completed -> Idle
  Error -> Idle
```

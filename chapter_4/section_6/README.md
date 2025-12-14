# Chapter 4 Section 6: LLMワークフローのためのオーケストレーション

## 概要

本プロジェクトは、LLMを含む複雑な処理フローを効率的に管理・実行するための**ワークフローオーケストレーションエンジン**を実装しています。

LLMを組み込んだソフトウェアでは、単一のLLM呼び出しで完結することは稀です。多くの場合、データの前処理、複数のLLM呼び出し、外部APIとの連携、条件分岐といった複数のステップから構成される複雑なワークフローとなります。本実装では、これらの処理フローをDAG（有向非巡回グラフ）として宣言的に定義し、処理の順序、依存関係、エラーハンドリング、チェックポイント/リカバリを自動で管理します。

主要なデザインパターン（Builder、Strategy、Memento、State）を活用し、堅牢で拡張性の高いアーキテクチャを実現しています。

## 機能

- **宣言的なワークフロー定義**: Builderパターンによる流暢なインターフェースでDAGを構築
- **多様なノードタイプ**: Start、End、Prompt（LLM）、IfElse（条件分岐）、Loop、Script
- **自動リトライ**: 指数バックオフによる失敗時の自動再試行
- **チェックポイント/リカバリ**: 状態永続化と障害復旧
- **状態追跡**: 詳細な実行状況監視
- **Gemini対応**: Google Gemini APIによるLLM実行

## プロジェクト構成

### ディレクトリ構成

```
section_12/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLIエントリポイント
│   ├── config.py            # 設定管理
│   ├── logger.py            # ロギング設定
│   ├── client.py            # Geminiクライアント・エグゼキュータ
│   ├── examples.py          # ワークフロー実行例
│   └── workflow/
│       ├── __init__.py
│       ├── models.py        # 基底クラス（Node, Edge, ExecutionContext, WorkflowState）
│       ├── nodes.py         # ノード実装（Start, End, Prompt, IfElse等）
│       ├── workflow.py      # Workflowクラス（DAG構造）
│       ├── builder.py       # WorkflowBuilder（Builderパターン）
│       ├── engine.py        # WorkflowEngine（実行エンジン）
│       └── checkpoint.py    # チェックポイント管理
├── checkpoints/             # チェックポイント保存先
├── pyproject.toml
├── .envrc.example
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        WorkflowBuilder                          │
│  (Builderパターン: 流暢なインターフェースでDAGを構築)            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Workflow                               │
│  (DAG構造: ノードとエッジの集合)                                │
│  ┌─────┐    ┌─────────┐    ┌──────────┐    ┌─────┐             │
│  │Start│───▶│PromptLLM│───▶│IfElseNode│───▶│ End │             │
│  └─────┘    └─────────┘    └──────────┘    └─────┘             │
│                                 │ true         │ false          │
│                                 ▼              ▼                │
│                            ┌────────┐    ┌────────┐             │
│                            │ Accept │    │ Refine │             │
│                            └────────┘    └────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       WorkflowEngine                            │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ CheckpointManager   │  │    Retry Logic      │              │
│  │ (状態永続化)        │  │ (指数バックオフ)   │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                 │
│  • DAG走査・ノード実行                                          │
│  • 指数バックオフリトライ                                        │
│  • チェックポイント作成/復元                                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Gemini Executor                          │
│  (Strategyパターン: Gemini LLMプロバイダ実行)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. WorkflowBuilder (`src/workflow/builder.py`)

Builderパターンにより、流暢なインターフェースでワークフローを宣言的に定義します。

```python
class WorkflowBuilder:
    def __init__(self, workflow_id: str, name: str | None = None):
        self._workflow = Workflow(workflow_id, name)

    def add_start_node(self, node_id: str, initial_data: dict | None = None) -> "WorkflowBuilder":
        node = StartNode(node_id, initial_data=initial_data)
        self._workflow.add_node(node)
        self._workflow.set_start_node(node_id)
        return self

    def add_prompt_node(self, node_id: str, prompt_template: str, llm_executor) -> "WorkflowBuilder":
        node = PromptNode(node_id, prompt_template=prompt_template, llm_executor=llm_executor)
        self._workflow.add_node(node)
        return self

    def add_edge(self, from_node_id: str, to_node_id: str) -> "WorkflowBuilder":
        self._workflow.add_edge(Edge(from_node_id=from_node_id, to_node_id=to_node_id))
        return self

    def build(self) -> Workflow:
        self._workflow.validate()  # DAG検証（サイクル検出等）
        return self._workflow
```

**ポイント**: メソッドチェーンで直感的にワークフローを構築でき、`build()`時にDAGの整合性を自動検証します。

#### 2. WorkflowEngine (`src/workflow/engine.py`)

ワークフローを実行し、リトライとチェックポイントを管理します。

```python
class WorkflowEngine:
    def __init__(self, enable_checkpointing: bool = True, max_retries: int = 3):
        self.max_retries = max_retries
        self.checkpoint_manager = CheckpointManager() if enable_checkpointing else None

    async def execute(self, workflow: Workflow) -> dict:
        context = ExecutionContext(workflow_id=workflow.workflow_id)
        current_node_id = workflow.start_node_id

        while current_node_id:
            node = workflow.get_node(current_node_id)
            output = await self._execute_with_retry(node, context)
            context.set_node_output(current_node_id, output)

            if current_node_id in workflow.end_node_ids:
                break
            current_node_id = self._get_next_node(workflow, node, output, context)

        return {"status": "completed", "outputs": context.node_outputs}

    async def _execute_with_retry(self, node, context) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                return await node.execute(context)
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # 指数バックオフ
                else:
                    raise
```

**ポイント**: 各ノードを指数バックオフ付きでリトライし、一定間隔でチェックポイントを自動作成します。

#### 3. ノード実装 (`src/workflow/nodes.py`)

様々な処理を担うノードクラス群を提供します。

```python
class PromptNode(Node):
    """LLMプロンプト実行ノード"""
    def __init__(self, node_id: str, prompt_template: str, llm_executor):
        super().__init__(node_id)
        self.prompt_template = prompt_template
        self.llm_executor = llm_executor

    async def execute(self, context: ExecutionContext) -> Any:
        prompt = self.prompt_template.format(**context.variables)
        result = await self.llm_executor(prompt, context)
        context.set_variable(f"{self.node_id}_output", result)
        return result

class IfElseNode(Node):
    """条件分岐ノード"""
    def __init__(self, node_id: str, condition: Callable[[ExecutionContext], bool]):
        super().__init__(node_id)
        self.condition = condition
        self.true_branch: str | None = None
        self.false_branch: str | None = None

    async def execute(self, context: ExecutionContext) -> dict:
        condition_result = self.condition(context)
        return {
            "condition_result": condition_result,
            "next_branch": self.true_branch if condition_result else self.false_branch,
        }
```

**ポイント**: 各ノードは単一の責務を持ち、`execute()`メソッドで処理を実行します。

#### 4. チェックポイント管理 (`src/workflow/checkpoint.py`)

ワークフロー状態を永続化し、障害からの復旧を可能にします。

```python
class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(self, workflow_id: str, state, context) -> Checkpoint:
        return Checkpoint(
            workflow_id=workflow_id,
            checkpoint_id=uuid4().hex,
            workflow_state=state.model_dump(),
            execution_context=context.model_dump(),
        )

    def save_checkpoint(self, checkpoint: Checkpoint) -> Path:
        path = self.checkpoint_dir / f"{checkpoint.workflow_id}_{checkpoint.checkpoint_id}.json"
        path.write_text(checkpoint.to_json(), encoding="utf-8")
        return path

    def restore_from_checkpoint(self, checkpoint: Checkpoint):
        return (
            WorkflowState(**checkpoint.workflow_state),
            ExecutionContext(**checkpoint.execution_context),
        )
```

**ポイント**: チェックポイントをJSON形式で永続化し、障害時に任意のポイントから再開可能です。

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - click >= 8.3.0
  - google-genai >= 1.45.0
  - pydantic >= 2.12.2
  - python-dotenv >= 1.1.1

### セットアップ

1. 環境変数の設定

```bash
# .envrc.exampleをコピーして編集
cp .envrc.example .envrc

# Gemini APIキーを設定
# https://aistudio.google.com/app/apikey から取得
export GEMINI_API_KEY="your-gemini-api-key-here"
```

2. 依存関係のインストール

```bash
# uvを使用する場合
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

```bash
# 利用可能なオプションを表示
python -m src.main --help

# シンプルなGeminiワークフローを実行
python -m src.main -w example_gemini_simple

# 条件分岐ワークフローを実行
python -m src.main -w example_conditional_workflow

# ループワークフローを実行
python -m src.main -w example_loop_workflow

# チェックポイント/リカバリのデモ
python -m src.main -w example_checkpoint_recovery

# 複雑なコンテンツ生成パイプライン
python -m src.main -w example_complex_content_pipeline

# 複雑なリサーチワークフロー
python -m src.main -w example_complex_research_workflow

# すべてのワークフローを実行
python -m src.main -w all
```

### CLIオプション

```
Usage: python -m src.main [OPTIONS]

  Run workflow orchestration examples.

Options:
  -w, --workflow [example_gemini_simple|example_checkpoint_recovery|example_loop_workflow|example_conditional_workflow|example_complex_content_pipeline|example_complex_research_workflow|all]
                                  Workflow to run. Use 'all' to run all
                                  workflows.
  --help                          Show this message and exit.
```

### 出力例

```
$ python -m src.main -w example_conditional_workflow

[2025-01-15 10:30:00] [INFO] Running: example_conditional_workflow
[2025-01-15 10:30:00] [INFO] ============================================================
[2025-01-15 10:30:00] [INFO] Example: Conditional Workflow
[2025-01-15 10:30:00] [INFO] ============================================================
[2025-01-15 10:30:00] [INFO] Starting workflow: conditional
[2025-01-15 10:30:00] [INFO] Workflow conditional validated
[2025-01-15 10:30:00] [INFO] Executing: start (Start)
[2025-01-15 10:30:00] [INFO] Starting workflow: conditional
[2025-01-15 10:30:00] [INFO] Executing: age_check (Check Age)
[2025-01-15 10:30:00] [INFO] Evaluating condition: Check Age
[2025-01-15 10:30:00] [INFO] Condition result: True
[2025-01-15 10:30:00] [INFO] Executing: adult (Adult Path)
[2025-01-15 10:30:00] [INFO] Executing script: Adult Path
[2025-01-15 10:30:00] [INFO] Executing: end (End)
[2025-01-15 10:30:00] [INFO] Ending workflow: conditional
[2025-01-15 10:30:00] [INFO] Reached end: end
[2025-01-15 10:30:00] [INFO] Workflow conditional completed
[2025-01-15 10:30:00] [INFO] Completed: completed (4 nodes)
```

### プログラムからの使用例

```python
from src.client import GeminiModel, create_executor
from src.workflow import ExecutionContext, WorkflowBuilder, WorkflowEngine

async def run_review_pipeline():
    # Gemini Executorを作成
    executor = create_executor(
        model=GeminiModel.GEMINI_2_5_FLASH,
        system_instruction="You are a helpful assistant."
    )

    # 条件判定関数
    def check_quality(ctx: ExecutionContext) -> bool:
        return ctx.get_variable("quality_score", 0) >= 7

    # ワークフローを定義
    workflow = (
        WorkflowBuilder("review_pipeline", "Review Processing")
        .add_start_node("start", initial_data={"review": "素晴らしい商品です！"})
        .add_prompt_node(
            "analyze",
            prompt_template="以下のレビューを分析してください: {review}",
            llm_executor=executor
        )
        .add_if_else_node("quality_check", condition=check_quality)
        .add_script_node("accept", func=lambda ctx: {"status": "accepted"})
        .add_script_node("refine", func=lambda ctx: {"status": "needs_review"})
        .add_end_node("end")
        .add_edge("start", "analyze")
        .add_edge("analyze", "quality_check")
        .set_if_else_branches("quality_check", "accept", "refine")
        .add_edge("accept", "end")
        .add_edge("refine", "end")
        .build()
    )

    # ワークフローを実行
    engine = WorkflowEngine(enable_checkpointing=True, max_retries=3)
    result = await engine.execute(workflow)

    print(f"Status: {result['status']}")
    print(f"Nodes executed: {result['nodes_executed']}")
    return result
```

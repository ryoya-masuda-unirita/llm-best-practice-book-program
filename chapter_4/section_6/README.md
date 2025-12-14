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

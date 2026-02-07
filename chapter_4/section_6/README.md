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
# uvを使用
uv sync
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
$ python -m src.main --help
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
$ python -m src.main -w example_gemini_simple

[2026-02-07 08:43:48,295] [INFO] [__main__] [main.py:64] [main] Running: example_gemini_simple
[2026-02-07 08:43:48,295] [INFO] [src.examples] [examples.py:94] [example_gemini_simple] ============================================================
[2026-02-07 08:43:48,296] [INFO] [src.examples] [examples.py:95] [example_gemini_simple] Example: Gemini Simple
[2026-02-07 08:43:48,296] [INFO] [src.examples] [examples.py:96] [example_gemini_simple] ============================================================
[2026-02-07 08:43:48,296] [INFO] [src.workflow.workflow] [workflow.py:65] [validate] Workflow gemini_simple validated
[2026-02-07 08:43:48,296] [INFO] [src.workflow.engine] [engine.py:35] [execute] Starting workflow: gemini_simple
[2026-02-07 08:43:48,296] [INFO] [src.workflow.workflow] [workflow.py:65] [validate] Workflow gemini_simple validated
[2026-02-07 08:43:48,296] [INFO] [src.workflow.engine] [engine.py:77] [_run] Executing: start (Start)
[2026-02-07 08:43:48,296] [INFO] [src.workflow.nodes] [nodes.py:20] [execute] Starting workflow: gemini_simple
[2026-02-07 08:43:48,296] [INFO] [src.workflow.engine] [engine.py:77] [_run] Executing: generate (Generate)
[2026-02-07 08:43:48,296] [INFO] [src.workflow.nodes] [nodes.py:54] [execute] Executing prompt node: Generate
[2026-02-07 08:43:50,367] [INFO] [src.workflow.engine] [engine.py:77] [_run] Executing: display (Display)
[2026-02-07 08:43:50,367] [INFO] [src.workflow.nodes] [nodes.py:158] [execute] Executing script: Display
[2026-02-07 08:43:50,367] [INFO] [src.workflow.engine] [engine.py:77] [_run] Executing: end (End)
[2026-02-07 08:43:50,367] [INFO] [src.workflow.nodes] [nodes.py:33] [execute] Ending workflow: gemini_simple
[2026-02-07 08:43:50,367] [INFO] [src.workflow.engine] [engine.py:89] [_run] Reached end: end
[2026-02-07 08:43:50,367] [INFO] [src.workflow.engine] [engine.py:54] [execute] Workflow gemini_simple completed
[2026-02-07 08:43:50,367] [INFO] [src.examples] [examples.py:115] [example_gemini_simple] Response: Artificial intelligence (AI) is a field of computer science dedicated to creating machines that can perform tasks traditionally requiring human intelligence. This involves developing systems capable of learning, problem-solving, decision-making, perception, and understanding language, ultimately aiming to enable computers to think and act like humans.
[2026-02-07 08:43:50,367] [INFO] [__main__] [main.py:66] [main] Completed: completed (4 nodes)
```

# Chapter 4 Section 6: LLMパイプラインのための依存性注入

## 概要

このプロジェクトは、**依存性注入（Dependency Injection, DI）** を用いたLLMワークフローシステムの実装を示すサンプルコードです。プロンプト構築、モデル呼び出し、応答処理という各処理を独立したコンポーネントとして設計し、それらを疎結合に組み合わせることで、テスト容易性、保守性、拡張性に優れたシステムを実現します。

ワークフローエンジン、ノード実装、DI��ンテナという3つの主要コンポーネントを通じて、エンタープライズグレードのLLMアプリケーション設計手法を学ぶことができます。

## 機能

- **依存性注入パターン**: プロンプトビルダー、LLMクライアント、レスポンスパーサーを独立したコンポーネントとして実装
- **軽量DIコンテナ**: Singleton、Transient、Scopedの3つのサービスライフタイムをサポート
- **マルチプロバイダー対応**: OpenAI、Gemini、Mockクライアントを統一インターフェースで利用可能
- **ワークフローエンジン**: DAG（有向非巡回グラフ）ベースの柔軟なワークフロー実行
- **チェックポイント機能**: ワークフロー実行の中断・再開をサポート
- **デザインパターン**: Builder、Mediator、Memento、Strategyパターンの実装
- **テスト容易性**: MockLLMClientによる高速なユニットテスト

## プロジェクト構成

### アーキテクチャ

このプロジェクトは、以下の階層型アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────┐
│         Application Layer (main.py, examples.py)    │
│     - CLIインターフェース                            │
│     - ワークフロー定義と実行                         │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│         Workflow Orchestration Layer                │
│  - WorkflowEngine: ワークフロー実行エンジン          │
│  - WorkflowBuilder: ワークフロー構築                 │
│  - Nodes: 各種ノード実装（Prompt、IfElse、Loop等）  │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│      Dependency Injection Layer (di.py)             │
│  - DIContainer: サービスコンテナ                     │
│  - IPromptBuilder: プロンプト構築インターフェース     │
│  - ILLMClient: LLMクライアントインターフェース        │
│  - IResponseParser: レスポンス解析インターフェース    │
│  - 具体実装: OpenAI、Gemini、Mock各クライアント      │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│         Infrastructure Layer                        │
│  - State管理: WorkflowState、ExecutionState         │
│  - Mediator: ノード間通信                            │
│  - Memento: チェックポイント管理                     │
│  - Logger: ログ出力                                  │
└─────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - click>=8.3.0
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
``

### 使用方法、実行方法

```shell
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Run Dependency Injection workflow examples.

  This command allows you to run different workflow examples that demonstrate
  the LLM workflow orchestration engine with Dependency Injection patterns.

  Examples:     # Run example 1 (manual DI)     python -m src.main --workflow
  example_1_manual_di

      # Run example 4 (multi-stage pipeline)     python -m src.main --workflow
      example_4_multi_stage_pipeline

      # Run all workflows     python -m src.main --workflow all

Options:
  -lp, --llm-provider [OPENAI|GEMINI]
                                  The LLM provider to use.
  -w, --workflow [example_1_manual_di|example_2_di_container_singleton|example_3_swapping_providers|example_4_multi_stage_pipeline|example_5_structured_output|example_6_testing_pattern|all]
                                  The workflow example to run. Use 'all' to
                                  run all workflows.
  --help                          Show this message and exit.
```

#### 基本的な使い方

```bash
# すべてのサンプルを実行
uv run python -m src.main --workflow all

# 特定のサンプルを実行
uv run python -m src.main --workflow example_1_manual_di

# 直接実行
uv run python -m src.examples
```

#### Example 1: 手動依存性注入

最もシンプルなDIの例：

```bash
uv run python -m src.main --workflow example_1_manual_di
```

**実装コード**:
```python
# 依存関係を手動で作成
prompt_builder = TemplatePromptBuilder(template="Translate '{text}' to {target_language}")
llm_client = MockLLMClient(mock_response="Bonjour le monde")
response_parser = TextResponseParser()

# ワークフローにインジェクト
workflow = (
    WorkflowBuilder("translation-workflow", "Translation Example")
    .add_start_node(initial_data={"text": "Hello world", "target_language": "French"})
    .add_prompt_node(
        "translate",
        injected_prompt_builder=prompt_builder,
        injected_llm_client=llm_client,
        injected_response_parser=response_parser,
    )
    .add_end_node()
    .add_edge("start", "translate").add_edge("translate", "end")
    .build()
)
```

#### Example 2: DIコンテナの使用

サービスコンテナによる依存関係管理：

```bash
uv run python -m src.main --workflow example_2_di_container_singleton
```

**実装コード**:
```python
# DIコンテナを作成
container = DIContainer()

# サービスを登録
container.register_singleton(ILLMClient, lambda: MockLLMClient(mock_response="Analyzed content"))
container.register_singleton(IResponseParser, TextResponseParser)
container.register_transient(IPromptBuilder, lambda: TemplatePromptBuilder(template="Analyze: {content}"))

# サービスを解決
llm_client = container.resolve(ILLMClient)
response_parser = container.resolve(IResponseParser)
prompt_builder = container.resolve(IPromptBuilder)

# ワークフローで使用
workflow = build_workflow(llm_client, response_parser, prompt_builder)
```

#### Example 3: プロバイダー切り替え（A/Bテスト）

異なるLLMプロバイダーを簡単に切り替え：

```bash
uv run python -m src.main --workflow example_3_swapping_providers
```

**実装コード**:
```python
# 同じワークフロー定義で異なるクライアントを使用
providers = [
    ("Provider A", MockLLMClient(mock_response="Summary from provider A")),
    ("Provider B", MockLLMClient(mock_response="Summary from provider B")),
]

for provider_name, llm_client in providers:
    workflow = build_workflow(llm_client)
    result = await engine.execute(workflow)
    # 結果を比較...
```

### 出力例

#### Example 1: 手動DI

```
$ uv run python -m src.main --workflow example_1_manual_di 

[2026-02-07 08:49:38,563] [INFO] [__main__] [main.py:111] [main] Running workflow: example_1_manual_di

[2026-02-07 08:49:38,563] [INFO] [src.examples] [examples.py:50] [example_1_manual_di] ============================================================
[2026-02-07 08:49:38,563] [INFO] [src.examples] [examples.py:51] [example_1_manual_di] Example 1: Manual Dependency Injection
[2026-02-07 08:49:38,563] [INFO] [src.examples] [examples.py:52] [example_1_manual_di] ============================================================
[2026-02-07 08:49:38,563] [INFO] [src.workflow.workflow] [workflow.py:83] [validate] Workflow translation-workflow validated successfully
[2026-02-07 08:49:38,563] [INFO] [src.workflow.engine] [engine.py:33] [__init__] Engine initialized (checkpointing: False, DI: False)
[2026-02-07 08:49:38,563] [INFO] [src.workflow.engine] [engine.py:39] [execute] Starting workflow: translation-workflow
[2026-02-07 08:49:38,563] [INFO] [src.workflow.workflow] [workflow.py:83] [validate] Workflow translation-workflow validated successfully
[2026-02-07 08:49:38,563] [DEBUG] [src.workflow.engine] [engine.py:147] [_setup_mediator] Mediator setup complete
[2026-02-07 08:49:38,563] [DEBUG] [src.workflow.engine] [engine.py:148] [_setup_mediator] end -> translate
translate -> start
[2026-02-07 08:49:38,563] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: start (Start)
[2026-02-07 08:49:38,563] [INFO] [src.workflow.nodes] [nodes.py:20] [execute] Starting workflow: translation-workflow
[2026-02-07 08:49:38,564] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: translate (Translate Text)
[2026-02-07 08:49:38,564] [INFO] [src.workflow.nodes] [nodes.py:65] [execute] Executing prompt node: Translate Text
[2026-02-07 08:49:38,564] [INFO] [src.workflow.nodes] [nodes.py:77] [execute] Prompt: Translate 'Hello world' to French...
[2026-02-07 08:49:38,564] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: end (End)
[2026-02-07 08:49:38,564] [INFO] [src.workflow.nodes] [nodes.py:36] [execute] Ending workflow: translation-workflow
[2026-02-07 08:49:38,564] [INFO] [src.workflow.engine] [engine.py:57] [execute] Workflow translation-workflow completed
[2026-02-07 08:49:38,564] [INFO] [src.examples] [examples.py:80] [example_1_manual_di] Translation result: Bonjour le monde
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:116] [main] 
✓ Workflow completed successfully
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:117] [main]   Status: completed
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:118] [main]   Nodes executed: 3
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:121] [main] 
  Final outputs:
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:123] [main]     start: {'status': 'started', 'initial_data': {'text': 'Hello world', 'target_language': 'French'}}...
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:123] [main]     translate: Bonjour le monde...
[2026-02-07 08:49:38,564] [INFO] [__main__] [main.py:123] [main]     end: {'status': 'completed', 'workflow_id': 'translation-workflow'}...
```

#### Example 4: 多段階パイプライン

```
$ uv run python -m src.main --workflow example_4_multi_stage_pipeline

[2026-02-07 08:50:14,665] [INFO] [__main__] [main.py:111] [main] Running workflow: example_4_multi_stage_pipeline

[2026-02-07 08:50:14,665] [INFO] [src.examples] [examples.py:191] [example_4_multi_stage_pipeline] ============================================================
[2026-02-07 08:50:14,665] [INFO] [src.examples] [examples.py:192] [example_4_multi_stage_pipeline] Example 4: Multi-Stage Pipeline with DI
[2026-02-07 08:50:14,665] [INFO] [src.examples] [examples.py:193] [example_4_multi_stage_pipeline] ============================================================
[2026-02-07 08:50:14,666] [INFO] [src.workflow.workflow] [workflow.py:83] [validate] Workflow multi-stage-workflow validated successfully
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:33] [__init__] Engine initialized (checkpointing: False, DI: False)
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:39] [execute] Starting workflow: multi-stage-workflow
[2026-02-07 08:50:14,666] [INFO] [src.workflow.workflow] [workflow.py:83] [validate] Workflow multi-stage-workflow validated successfully
[2026-02-07 08:50:14,666] [DEBUG] [src.workflow.engine] [engine.py:147] [_setup_mediator] Mediator setup complete
[2026-02-07 08:50:14,666] [DEBUG] [src.workflow.engine] [engine.py:148] [_setup_mediator] end -> format
extract -> start
format -> summarize
summarize -> extract
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: start (Start)
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:20] [execute] Starting workflow: multi-stage-workflow
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: extract (Extract Key Points)
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:65] [execute] Executing prompt node: Extract Key Points
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:77] [execute] Prompt: Extract key points from: Long technical document......
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: summarize (Generate Summary)
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:65] [execute] Executing prompt node: Generate Summary
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:77] [execute] Prompt: 2 messages...
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: format (Format Output)
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:211] [execute] Executing script: Format Output
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:226] [execute] Script result: ## Key Points
Key points: A, B, C

## Summary
Professional summary of key points
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:87] [_run] Executing: end (End)
[2026-02-07 08:50:14,666] [INFO] [src.workflow.nodes] [nodes.py:36] [execute] Ending workflow: multi-stage-workflow
[2026-02-07 08:50:14,666] [INFO] [src.workflow.engine] [engine.py:57] [execute] Workflow multi-stage-workflow completed
[2026-02-07 08:50:14,666] [INFO] [src.examples] [examples.py:243] [example_4_multi_stage_pipeline] 
Final formatted output:
[2026-02-07 08:50:14,666] [INFO] [src.examples] [examples.py:244] [example_4_multi_stage_pipeline] ## Key Points
Key points: A, B, C

## Summary
Professional summary of key points
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:116] [main] 
✓ Workflow completed successfully
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:117] [main]   Status: completed
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:118] [main]   Nodes executed: 5
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:121] [main] 
  Final outputs:
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:123] [main]     start: {'status': 'started', 'initial_data': {'document': 'Long technical document...', 'prompt': 'temp'}}...
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:123] [main]     extract: Key points: A, B, C...
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:123] [main]     summarize: Professional summary of key points...
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:123] [main]     format: ## Key Points
Key points: A, B, C

## Summary
Professional summary of key points...
[2026-02-07 08:50:14,666] [INFO] [__main__] [main.py:123] [main]     end: {'status': 'completed', 'workflow_id': 'multi-stage-workflow'}...
```

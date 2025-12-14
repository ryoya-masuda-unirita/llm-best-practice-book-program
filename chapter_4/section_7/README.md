# Chapter 4 Section 7: LLMパイプラインのための依存性注入

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

### ディレクトリ構成

```
chapter_3/section_13/
├── src/
│   ├── __init__.py
│   ├── config.py                # 設定管理
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── examples.py              # DIサンプル実装（6つの例）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   └── workflow/
│       ├── __init__.py          # ワークフローコンポーネントのエクスポート
│       ├── base.py              # 基底クラス（Node、ExecutionContext）
│       ├── workflow.py          # Workflowクラス（DAG管理）
│       ├── builder.py           # WorkflowBuilderパターン
│       ├── engine.py            # WorkflowEngine（実行エンジン）
│       ├── nodes.py             # ノード実装（Start、End、Prompt等）
│       ├── di.py                # DI関連コンポーネント（統合版）
│       ├── state.py             # ワークフロー状態管理
│       ├── mediator.py          # Mediatorパターン実装
│       └── memento.py           # Mementoパターン実装（チェックポイント）
├── checkpoints/                  # チェックポイント保存先（自動作成）
├── .envrc.example               # 環境変数設定のサンプル
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
├── CLAUDE.md                    # 設計原則と解説
├── REFACTORING_SUMMARY.md       # リファクタリング詳細
└── MIGRATION_SUMMARY.md         # マイグレーションガイド
```

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

```bash
# すべてのサンプルを実行
python -m src.main --workflow all

# 特定のサンプルを実行
python -m src.main --workflow example_1_manual_di

# 直接実行
python -m src.examples
```

#### 利用可能なワークフロー

```bash
# ワークフロー一覧を表示
python -m src.main --help

# 利用可能なワークフロー:
# - example_1_manual_di              # 手動DI
# - example_2_di_container_singleton # DIコンテナとシングルトン
# - example_3_swapping_providers     # プロバイダー切り替え（A/Bテスト）
# - example_4_multi_stage_pipeline   # 多段階パイプライン
# - example_5_structured_output      # 構造化出力
# - example_6_testing_pattern        # テストパターン
```

#### Example 1: 手動依存性注入

最もシンプルなDIの例：

```bash
python -m src.main --workflow example_1_manual_di
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
python -m src.main --workflow example_2_di_container_singleton
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
python -m src.main --workflow example_3_swapping_providers
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
============================================================
Example 1: Manual Dependency Injection
============================================================
[2025-11-09 15:29:44] [INFO] [src.workflow.engine] Workflow translation-workflow completed
Translation result: Bonjour le monde
Mock client was called 1 time(s)
✓ Workflow completed successfully
  Status: completed
  Nodes executed: 3
```

#### Example 4: 多段階パイプライン

```
============================================================
Example 4: Multi-Stage Pipeline with DI
============================================================
[2025-11-09 15:29:56] [INFO] [src.workflow.engine] Workflow multi-stage-workflow completed

Final formatted output:
## Key Points
Key points: A, B, C

## Summary
Professional summary of key points
✓ Workflow completed successfully
  Status: completed
  Nodes executed: 5
```

# Chapter 3 Section 13: LLMパイプラインのための依存性注入

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
- **後方互換性**: レガシーな実装方法も引き続きサポート
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
│       ├── memento.py           # Mementoパターン実装（チェックポイント）
│       └── llm_executors.py     # レガシーLLM実行関数
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

### 実装の詳細

#### 1. 依存性注入インターフェース (`src/workflow/di.py`)

3つの主要なインターフェースを定義：

```python
@runtime_checkable
class IPromptBuilder(Protocol):
    """プロンプト構築インターフェース"""
    def build_prompt(self, context: ExecutionContext) -> str | list[dict[str, Any]]:
        ...

@runtime_checkable
class ILLMClient(Protocol):
    """LLMクライアントインターフェース"""
    async def generate(
        self, prompt: str | list[dict[str, Any]],
        context: ExecutionContext,
        **kwargs: Any
    ) -> dict[str, Any]:
        ...

@runtime_checkable
class IResponseParser(Protocol):
    """レスポンス解析インターフェース"""
    def parse_response(
        self, raw_response: dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        ...
```

**ポイント**:
- `Protocol`による構造的部分型（Structural Subtyping）
- `@runtime_checkable`でランタイム型チェックを有効化
- 各コンポーネントが独立して実装・テスト可能

#### 2. DIコンテナ (`src/workflow/di.py`)

サービスライフタイムをサポートする軽量DIコンテナ：

```python
class DIContainer:
    """軽量依存性注入コンテナ"""

    def register_singleton(self, service_type: type[T], impl: Callable[..., T]) -> DIContainer:
        """シングルトンとして登録（アプリケーション全体で1インスタンス）"""
        ...

    def register_transient(self, service_type: type[T], impl: Callable[..., T]) -> DIContainer:
        """トランジェントとして登録（呼び出し毎に新インスタンス）"""
        ...

    def register_scoped(self, service_type: type[T], impl: Callable[..., T]) -> DIContainer:
        """スコープとして登録（ワークフロー実行毎に1インスタンス）"""
        ...

    def resolve(self, service_type: type[T], scope_id: str | None = None) -> T:
        """サービスを解決して取得"""
        ...
```

**ポイント**:
- 3つのサービスライフタイム（Singleton、Transient、Scoped）
- メソッドチェーンによる流暢なAPI
- 循環依存の検出機能

#### 3. LLMクライアント実装 (`src/workflow/di.py`)

統一インターフェースで複数のLLMプロバイダーを実装：

```python
class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLMクライアント"""

    def __init__(self, model: str = "gpt-4o-mini", response_format: type[BaseModel] | None = None, **params):
        super().__init__(model, **params)
        self.response_format = response_format

    async def generate(self, prompt: str | list[dict], context: ExecutionContext, **kwargs) -> dict:
        messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt
        params = {**self.params, **kwargs}

        if self.response_format:
            # 構造化出力
            result = await openai_client.responses.parse(
                model=self.model, input=messages, text_format=self.response_format, **params
            )
            return {"content": result.output_text, "parsed": result.output_parsed, ...}
        else:
            # 通常の出力
            result = await openai_client.chat.completions.create(
                model=self.model, messages=messages, **params
            )
            return {"content": result.choices[0].message.content, ...}
```

**特徴**:
- `BaseLLMClient`を継承して共通機能を再利用
- 構造化出力（Structured Outputs）をサポート
- パラメータのマージ機能
- 統一されたレスポンス形式

#### 4. ワークフロービルダー (`src/workflow/builder.py`)

Builderパターンでワークフローを構築：

```python
workflow = (
    WorkflowBuilder("translation-workflow", "Translation Example")
    .add_start_node(initial_data={"text": "Hello", "language": "French"})
    .add_prompt_node(
        "translate",
        name="Translate Text",
        injected_prompt_builder=prompt_builder,  # DI: プロンプトビルダー
        injected_llm_client=llm_client,          # DI: LLMクライアント
        injected_response_parser=parser,         # DI: レスポンスパーサー
    )
    .add_end_node()
    .add_edge("start", "translate")
    .add_edge("translate", "end")
    .build()
)
```

**ポイント**:
- メソッドチェーンによる流暢なAPI
- DI対応の`injected_*`パラメータ
- レガシーな`llm_executor`パラメータも引き続きサポート
- DAG構造の自動検証

#### 5. ワークフローエンジン (`src/workflow/engine.py`)

ワークフローを実行するエンジン：

```python
engine = WorkflowEngine(
    enable_checkpointing=True,      # チェックポイント有効化
    checkpoint_interval=5,           # 5ノード毎にチェックポイント
    max_retries=3,                   # 最大リトライ回数
    di_container=container           # DIコンテナ（オプション）
)

result = await engine.execute(
    workflow,
    initial_data={"text": "Hello world"},
    resume_from_checkpoint=None      # チェックポイントから再開（オプション）
)
```

**特徴**:
- DAGトラバーサルによるノード実行
- 自動リトライ機能（指数バックオフ）
- チェックポイントによる中断・再開
- Mediatorパターンによるノード間通信
- 詳細なログ出力

## 使い方

### 環境構成

- **Python**: 3.10以上
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

### テスト方法

#### 1. 全ワークフローの実行テスト

```bash
python -m src.main --workflow all
```

**期待される動作**:
- 6つすべてのサンプルワークフローが正常に完了
- エラーなく実行完了
- 各ワークフローの出力が正しく表示される

#### 2. 単体テストパターン

```python
import asyncio
from src.workflow import (
    WorkflowBuilder, WorkflowEngine,
    MockLLMClient, TemplatePromptBuilder, TextResponseParser
)

async def test_workflow():
    # テスト用のモッククライアントを使用
    mock_client = MockLLMClient(mock_response="Test output")

    workflow = (
        WorkflowBuilder("test")
        .add_start_node(initial_data={"input": "test"})
        .add_prompt_node(
            "process",
            prompt_template="Process {input}",
            injected_llm_client=mock_client,
        )
        .add_end_node()
        .add_edge("start", "process")
        .add_edge("process", "end")
        .build()
    )

    result = await WorkflowEngine(enable_checkpointing=False).execute(workflow)

    # アサーション
    assert result["status"] == "completed"
    assert mock_client.call_count == 1
    assert result["outputs"]["process"] == "Test output"

asyncio.run(test_workflow())
```

#### 3. DIコンテナのテスト

```python
from src.workflow import DIContainer, ILLMClient, MockLLMClient, ServiceLifetime

# シングルトンのテスト
container = DIContainer()
container.register_singleton(ILLMClient, lambda: MockLLMClient("response"))

client1 = container.resolve(ILLMClient)
client2 = container.resolve(ILLMClient)

assert client1 is client2  # 同一インスタンス
```

#### 4. プロバイダー切り替えのテスト

実際のAPIを使用する場合（.envrcにAPIキーを設定）：

```python
from src.workflow import OpenAILLMClient, GeminiLLMClient

# OpenAIでテスト
openai_client = OpenAILLMClient(model="gpt-4o-mini")
workflow = build_workflow(openai_client)
result = await engine.execute(workflow)

# Geminiでテスト（同じワークフロー定義）
gemini_client = GeminiLLMClient(model="gemini-2.0-flash-exp")
workflow = build_workflow(gemini_client)
result = await engine.execute(workflow)
```

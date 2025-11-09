# Chapter 3 Section 12: LLMワークフローのためのオーケストレーション

## 概要

このプロジェクトは、**ワークフローオーケストレーション（Workflow Orchestration）** を用いた複雑なLLM処理フローの管理と実行を実現するサンプル実装です。単一のLLM呼び出しではなく、複数のステップ（データ前処理、複数回のLLM呼び出し、外部API連携、条件分岐など）から構成される複雑なワークフローを、宣言的に定義し、効率的に実行するためのエンジンを提供します。

デザインパターン（Builder、Factory、Strategy、Mediator、Memento、State、Chain of Responsibility）を活用した堅牢なアーキテクチャにより、処理の順序、依存関係、エラーハンドリング、チェックポイント管理を統一的に扱うことができます。OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応し、マルチプロバイダー環境でのワークフロー実行を実現します。

## 機能

- **DAGベースワークフロー**: 有向非巡回グラフ（DAG）としてワークフローを定義
- **多様なノードタイプ**: Start、End、Prompt（LLM呼び出し）、IfElse（条件分岐）、Loop（反復処理）、PythonScript（カスタムロジック）
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **チェックポイント/リカバリ**: Mementoパターンによる自動チェックポイントと障害回復
- **リトライ機能**: ノード実行失敗時の自動リトライ（指数バックオフ）
- **実行状態管理**: Stateパターンによる詳細なワークフロー状態追跡
- **依存関係管理**: Mediatorパターンによるノード間の依存関係の調停
- **Builderパターン**: 流暢なインターフェースによる直感的なワークフロー構築
- **処理パイプライン**: Chain of Responsibilityパターンによる前処理・後処理の統一管理
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **詳細ログ**: 各ノードの実行状況を可視化

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_12/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── examples.py              # ワークフロー実装例
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   └── workflow/
│       ├── __init__.py
│       ├── base.py              # 基本データ構造（Node、Edge、Context）
│       ├── workflow.py          # Workflow クラス
│       ├── nodes.py             # 各種ノード実装
│       ├── engine.py            # ワークフロー実行エンジン
│       ├── builder.py           # Builder パターン実装
│       ├── factory.py           # Factory パターン実装
│       ├── strategy.py          # Strategy パターン実装
│       ├── mediator.py          # Mediator パターン実装
│       ├── memento.py           # Memento パターン（チェックポイント）
│       ├── state.py             # State パターン（ワークフロー状態）
│       ├── chain.py             # Chain of Responsibility パターン
│       └── llm_executors.py     # LLMエグゼキュータ実装
├── checkpoints/                  # チェックポイント保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト概念説明
```

### アーキテクチャ

このプロジェクトは、多層アーキテクチャと複数のデザインパターンの組み合わせで構成されています：

```
┌─────────────────────────────────────────┐
│      CLI Layer (main.py)                │
│  - コマンドライン引数解析                │
│  - ワークフロー選択・実行制御             │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Workflow Definition Layer            │
│  - Builder Pattern (builder.py)         │
│  - Factory Pattern (factory.py)         │
│  - ワークフロー定義 (examples.py)        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Execution Engine Layer               │
│  - WorkflowEngine (engine.py)           │
│  - Node Execution (nodes.py)            │
│  - LLM Executors (llm_executors.py)     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Pattern & State Management Layer     │
│  - Mediator (mediator.py)               │
│  - Memento (memento.py)                 │
│  - State (state.py)                     │
│  - Chain of Responsibility (chain.py)   │
│  - Strategy (strategy.py)               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                  │
│  - ログ管理 (logger.py)                  │
│  - 外部API (OpenAI, Gemini)              │
└─────────────────────────────────────────┘
```

### 実装の詳細

#### 1. 基本データ構造 (`src/workflow/base.py`)

ワークフローの基盤となるデータ構造を定義します：

```python
class Node(BaseModel):
    """ワークフローの実行単位"""
    node_id: str
    name: str
    node_type: NodeType

    async def execute(self, context: ExecutionContext) -> Any:
        """ノードの実行ロジック"""
        pass

class Edge(BaseModel):
    """ノード間の接続"""
    from_node_id: str
    to_node_id: str
    condition: str | None = None

class ExecutionContext:
    """実行コンテキスト（変数、出力を保持）"""
    workflow_id: str
    variables: dict[str, Any]
    node_outputs: dict[str, Any]
```

**ポイント**:
- Nodeは抽象基底クラスとして、各ノードタイプの共通インターフェースを定義
- ExecutionContextはワークフロー全体で共有される実行状態を保持
- Edgeはノード間の依存関係を表現

#### 2. ワークフロービルダー (`src/workflow/builder.py`)

Builderパターンによる流暢なワークフロー構築インターフェース：

```python
builder = WorkflowBuilder("workflow_id", "Workflow Name")

workflow = (
    builder
    .add_start_node("start", initial_data={"key": "value"})
    .add_prompt_node(
        "llm_call",
        name="Generate Content",
        prompt_template="Write about {topic}",
        llm_executor=gemini_executor
    )
    .add_if_else_node(
        "quality_check",
        name="Check Quality",
        condition=lambda ctx: ctx.get_variable("quality") >= 7
    )
    .set_if_else_branches("quality_check", "accept", "refine")
    .add_end_node("end")
    .add_edge("start", "llm_call")
    .add_edge("llm_call", "quality_check")
    .add_edge("accept", "end")
    .add_edge("refine", "end")
    .build()
)
```

**特徴**:
- メソッドチェーンによる直感的なワークフロー定義
- ノードの追加、エッジの接続を宣言的に記述
- 条件分岐やループの設定も簡潔に表現

#### 3. ノード実装 (`src/workflow/nodes.py`)

様々な処理を表現する多様なノードタイプ：

```python
class PromptNode(Node):
    """LLM呼び出しノード"""
    prompt_template: str
    llm_executor: Callable

    async def execute(self, context: ExecutionContext) -> dict:
        # テンプレートから変数を展開
        prompt = self.prompt_template.format(**context.variables)
        # LLMを呼び出し
        result = await self.llm_executor(prompt, context)
        return {"content": result}

class IfElseNode(Node):
    """条件分岐ノード"""
    condition: Callable[[ExecutionContext], bool]
    true_branch: str
    false_branch: str

    async def execute(self, context: ExecutionContext) -> dict:
        result = self.condition(context)
        return {"condition_result": result}

class LoopNode(Node):
    """反復処理ノード"""
    collection_key: str
    max_iterations: int

    async def execute(self, context: ExecutionContext) -> dict:
        collection = context.get_variable(self.collection_key, [])
        # コレクションの各要素に対して処理を実行
        for i, item in enumerate(collection[:self.max_iterations]):
            # ループ内処理...
        return {"iterations": i + 1}
```

**ポイント**:
- 各ノードは特定の責務を持つ単一目的の実行単位
- async/awaitによる非同期実行対応
- ノード固有のロジックをカプセル化

#### 4. ワークフローエンジン (`src/workflow/engine.py`)

ワークフローの実行を統括するメインエンジン：

```python
class WorkflowEngine:
    def __init__(
        self,
        enable_checkpointing: bool = True,
        checkpoint_interval: int = 5,
        max_retries: int = 3
    ):
        self.checkpoint_manager = CheckpointManager()
        self.mediator = NodeMediator()

    async def execute(
        self,
        workflow: Workflow,
        initial_data: dict | None = None,
        resume_from_checkpoint: str | None = None
    ) -> dict:
        # ワークフロー検証
        workflow.validate()

        # 状態の初期化/復元
        if resume_from_checkpoint:
            state, context = await self._resume_from_checkpoint(...)
        else:
            context = ExecutionContext(workflow_id=workflow.workflow_id)
            state = WorkflowState(workflow_id=workflow.workflow_id)

        # DAGに沿ってノードを実行
        current_node_id = workflow.start_node_id
        while current_node_id:
            node = workflow.get_node(current_node_id)

            # リトライ付き実行
            output = await self._execute_node_with_retry(node, context, state)

            # 結果を保存
            context.set_node_output(current_node_id, output)

            # チェックポイント作成
            if should_checkpoint:
                await self._create_checkpoint(...)

            # 次のノードを決定
            current_node_id = workflow.get_next_nodes(current_node_id, context)

        return {"status": "completed", "outputs": context.node_outputs}
```

**特徴**:
- DAG（有向非巡回グラフ）の順序に従ってノードを実行
- 自動チェックポイント（N個のノードごと）
- ノード実行失敗時の自動リトライ（指数バックオフ）
- ワークフロー状態の永続化と復元

#### 5. Mementoパターン (チェックポイント管理) (`src/workflow/memento.py`)

ワークフロー状態のスナップショットを保存・復元：

```python
class WorkflowMemento(BaseModel):
    """ワークフロー状態のスナップショット"""
    checkpoint_id: str
    workflow_id: str
    timestamp: str
    workflow_state: dict  # WorkflowStateのシリアライズ
    context_data: dict    # ExecutionContextのシリアライズ
    metadata: dict

class CheckpointManager:
    def create_checkpoint(
        self,
        workflow_id: str,
        workflow_state: WorkflowState,
        context: ExecutionContext,
        metadata: dict | None = None
    ) -> WorkflowMemento:
        """現在の状態をメメントとして保存"""
        return WorkflowMemento(
            checkpoint_id=self._generate_checkpoint_id(),
            workflow_id=workflow_id,
            timestamp=datetime.now().isoformat(),
            workflow_state=workflow_state.to_dict(),
            context_data=context.to_dict(),
            metadata=metadata or {}
        )

    def restore_from_checkpoint(
        self, memento: WorkflowMemento
    ) -> tuple[WorkflowState, ExecutionContext]:
        """メメントから状態を復元"""
        workflow_state = WorkflowState.from_dict(memento.workflow_state)
        context = ExecutionContext.from_dict(memento.context_data)
        return workflow_state, context
```

**ポイント**:
- ワークフロー実行中の任意の時点の状態を保存
- 障害発生時に最後のチェックポイントから再開可能
- JSONファイルとして永続化（`checkpoints/`ディレクトリ）

#### 6. Mediatorパターン (ノード間調停) (`src/workflow/mediator.py`)

ノード間の依存関係を一元管理：

```python
class NodeMediator:
    """ノード間の依存関係を調停"""
    def __init__(self):
        self._nodes: dict[str, Node] = {}
        self._dependencies: dict[str, list[str]] = {}

    def register_node(self, node: Node) -> None:
        """ノードを登録"""
        self._nodes[node.node_id] = node

    def add_dependency(self, node_id: str, depends_on: str) -> None:
        """依存関係を追加"""
        if node_id not in self._dependencies:
            self._dependencies[node_id] = []
        self._dependencies[node_id].append(depends_on)

    def notify_completion(
        self, node_id: str, output: Any, context: ExecutionContext
    ) -> None:
        """ノード完了を通知し、依存ノードに伝播"""
        # 依存しているノードに完了を通知
        for dependent_id in self._get_dependent_nodes(node_id):
            logger.debug(f"Notifying {dependent_id} of {node_id} completion")
```

**特徴**:
- ノード間の疎結合を実現
- 依存関係の可視化機能
- ノード完了イベントの伝播

#### 7. LLMエグゼキュータ (`src/workflow/llm_executors.py`)

OpenAIとGeminiの統一的な呼び出しインターフェース：

```python
def create_openai_executor(
    model: OpenAIModel = OpenAIModel.GPT_4O_MINI,
    temperature: float = 1.0
) -> Callable:
    """OpenAI LLMエグゼキュータを作成"""
    async def executor(
        prompt: str | list[dict], context: ExecutionContext
    ) -> str:
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        response = await openai_client.chat.completions.create(
            model=model.value,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

    return executor

def create_gemini_executor(
    model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
    system_instruction: str | None = None,
    temperature: float = 2.0
) -> Callable:
    """Gemini LLMエグゼキュータを作成"""
    async def executor(
        prompt: str | list[dict], context: ExecutionContext
    ) -> str:
        # プロンプトを抽出
        content = prompt if isinstance(prompt, str) else prompt[-1]["content"]

        result = await google_genai_client.aio.models.generate_content(
            model=model.value,
            contents=content,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature
            )
        )
        return result.text

    return executor
```

**ポイント**:
- Strategyパターンにより、LLMプロバイダーを交換可能
- Promptノードで使用するエグゼキュータを柔軟に指定
- 同一ワークフロー内で複数のプロバイダーを混在可能

#### 8. 複雑なワークフロー例 (`src/examples.py`)

実際のユースケースを示す実装例：

**コンテンツ生成パイプライン**（12ノード、条件分岐あり）:
```python
async def example_complex_content_pipeline():
    """
    START → トピック生成(Gemini) → トピック解析 →
    コンテンツ生成(OpenAI) → 品質分析(Gemini) →
    品質判定 → [高品質: 承認 | 低品質: 改善(OpenAI)] →
    結果統合 → サマリー生成(Gemini) → END
    """
    # Geminiでトピック生成
    .add_prompt_node(
        "generate_topics",
        prompt_template="Generate {num_topics} blog topics about {domain}",
        llm_executor=gemini_executor
    )
    # OpenAIで詳細コンテンツ生成
    .add_prompt_node(
        "generate_content",
        prompt_template="Write detailed content about: {selected_topic}",
        llm_executor=openai_executor
    )
    # Geminiで品質評価
    .add_prompt_node(
        "analyze_quality",
        prompt_template="Rate this content (1-10): {content}",
        llm_executor=gemini_executor
    )
    # 品質による条件分岐
    .add_if_else_node(
        "quality_check",
        condition=lambda ctx: ctx.get_variable("quality_score") >= 7
    )
    .set_if_else_branches("quality_check", "accept_content", "refine_content")
```

**リサーチ・レポート生成ワークフロー**（14ノード、複数LLM呼び出し）:
```python
async def example_complex_research_workflow():
    """
    START → リサーチ質問定義(Gemini) → 質問分割 →
    Q1研究(OpenAI) → Q2研究(Gemini) → Q3研究(OpenAI) →
    結果集約 → 完全性検証(Gemini) →
    [完全: レポート生成 | 不完全: 追加調査] →
    統合 → 最終レビュー(Gemini) → END
    """
    # 複数の研究質問を並列実行（実際は順次実行でDAG制約を回避）
    # 各質問を異なるプロバイダーで処理
```

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
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
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
# Gemini単純ワークフローを実行
uv run python -m src.main --workflow example_gemini_simple

# OpenAI単純ワークフローを実行
uv run python -m src.main --workflow example_openai_simple

# マルチプロバイダーワークフロー
uv run python -m src.main --workflow example_multi_provider

# 条件分岐ワークフロー
uv run python -m src.main --workflow example_conditional_workflow

# ループワークフロー
uv run python -m src.main --workflow example_loop_workflow

# チェックポイント/リカバリのデモ
uv run python -m src.main --workflow example_checkpoint_recovery

# 複雑なコンテンツ生成パイプライン（12ノード）
uv run python -m src.main --workflow example_complex_content_pipeline

# 複雑なリサーチワークフロー（14ノード）
uv run python -m src.main --workflow example_complex_research_workflow

# すべてのワークフローを実行
uv run python -m src.main --workflow all
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

  Run workflow orchestration examples.

Options:
  -w, --workflow [example_gemini_simple|example_openai_simple|example_multi_provider|example_checkpoint_recovery|example_loop_workflow|example_conditional_workflow|example_complex_content_pipeline|example_complex_research_workflow|all]
                                  The workflow example to run. Use 'all' to
                                  run all workflows.
  --help                          Show this message and exit.
```

### 出力例

#### シンプルなワークフロー実行

```bash
$ uv run python -m src.main --workflow example_gemini_simple
```

**実行ログ例**:
```
[2025-01-15 10:30:45] [INFO] Workflow engine initialized (checkpointing: False)
============================================================
Example: Gemini Simple Text Completion
============================================================
[2025-01-15 10:30:45] [INFO] Starting workflow execution: gemini_simple
[2025-01-15 10:30:45] [INFO] Executing node: start (Start)
[2025-01-15 10:30:45] [INFO] Executing node: generate (Generate Content)
[2025-01-15 10:30:47] [INFO] Executing node: display (Display Result)
[2025-01-15 10:30:47] [INFO] Reached end node: end
[2025-01-15 10:30:47] [INFO] Workflow gemini_simple completed successfully

✓ Workflow completed
Response: 人工知能（AI）は、機械が人間の知能を模倣して学習、推論、問題解決を行う技術です。
機械学習やディープラーニングなどの手法を用いて、データからパターンを抽出し、
新しい状況に適応することができます。
```

#### 複雑なコンテンツ生成パイプライン実行

```bash
$ uv run python -m src.main --workflow example_complex_content_pipeline
```

**実行ログ例**:
```
[2025-01-15 10:35:00] [INFO] Starting workflow execution: content_pipeline
[2025-01-15 10:35:00] [INFO] Executing node: start (Start)
[2025-01-15 10:35:00] [INFO] Executing node: generate_topics (Generate Topic Ideas)
[2025-01-15 10:35:02] [INFO] Executing node: parse_topics (Parse Topics)
[2025-01-15 10:35:02] [INFO] Executing node: select_topic (Select Topic)
[2025-01-15 10:35:02] [INFO] Executing node: generate_content (Generate Content)
[2025-01-15 10:35:05] [INFO] Executing node: store_content (Store Content)
[2025-01-15 10:35:05] [INFO] Executing node: analyze_quality (Analyze Quality)
[2025-01-15 10:35:07] [INFO] Executing node: extract_quality_score (Extract Quality Score)
[2025-01-15 10:35:07] [INFO] Executing node: store_quality (Store Quality Score)
[2025-01-15 10:35:07] [INFO] Checkpoint created: checkpoint_abc123
[2025-01-15 10:35:07] [INFO] Executing node: quality_check (Quality Check)
[2025-01-15 10:35:07] [INFO] Executing node: accept_content (Accept Content)
[2025-01-15 10:35:07] [INFO] Executing node: merge_results (Merge Results)
[2025-01-15 10:35:07] [INFO] Executing node: generate_summary (Generate Summary)
[2025-01-15 10:35:09] [INFO] Reached end node: end
[2025-01-15 10:35:09] [INFO] Workflow content_pipeline completed successfully

✓ Complex Content Pipeline Completed
  Nodes executed: 13
  Quality score: 8
  Content was refined: False

  Summary: このブログでは、大規模言語モデルがソフトウェア開発の生産性向上に与える影響について詳しく解説しています。
  コード生成、デバッグ支援、ドキュメント作成などの具体的なユースケースを紹介し...
```

#### チェックポイント管理例

チェックポイントは自動的に`checkpoints/`ディレクトリに保存されます：

```
checkpoints/
├── content_pipeline_checkpoint_20250115_103507_abc123.json
├── content_pipeline_checkpoint_20250115_103510_def456.json
└── research_workflow_checkpoint_20250115_104525_ghi789.json
```

**チェックポイントファイルの内容例**:
```json
{
  "checkpoint_id": "checkpoint_abc123",
  "workflow_id": "content_pipeline",
  "timestamp": "2025-01-15T10:35:07.123456",
  "workflow_state": {
    "workflow_id": "content_pipeline",
    "status": "running",
    "current_node_id": "store_quality",
    "completed_nodes": [
      "start",
      "generate_topics",
      "parse_topics",
      "select_topic",
      "generate_content",
      "store_content",
      "analyze_quality",
      "extract_quality_score"
    ]
  },
  "context_data": {
    "workflow_id": "content_pipeline",
    "variables": {
      "domain": "artificial intelligence",
      "num_topics": 3,
      "selected_topic": "AIによるソフトウェア開発の革新",
      "quality_score": 8
    },
    "node_outputs": {
      "generate_topics": {
        "content": "AIによるソフトウェア開発の革新, 機械学習の実践的応用, 自然言語処理の最新動向"
      },
      "generate_content": {
        "content": "大規模言語モデルは、ソフトウェア開発のプロセスを根本的に..."
      }
    }
  },
  "metadata": {
    "type": "auto",
    "node": "store_quality"
  }
}
```

### テスト方法

現在、このセクションには主に統合テストレベルでの動作確認が推奨されます。

#### 1. 全ワークフローの動作確認

```bash
uv run python -m src.main --workflow all
```

期待される動作：
- すべてのワークフロー例が順次実行される
- 各ワークフローが正常に完了する（`status: completed`）
- エラーが発生しない

#### 2. チェックポイント機能の確認

```bash
# チェックポイントディレクトリを確認
ls -la checkpoints/

# チェックポイントワークフローを実行
uv run python -m src.main --workflow example_checkpoint_recovery

# チェックポイントファイルが作成されていることを確認
cat checkpoints/checkpoint_workflow_*.json | jq .
```

期待される動作：
- `checkpoints/`ディレクトリにJSONファイルが作成される
- チェックポイントファイルに`workflow_state`と`context_data`が含まれる
- 実行ログにチェックポイント作成メッセージが表示される

#### 3. 条件分岐の動作確認

```bash
uv run python -m src.main --workflow example_conditional_workflow
```

期待される動作：
- `character_age`の値に応じて`adult_processing`または`minor_processing`が実行される
- 実行ログに分岐先のノードが表示される
- 最終出力に`category`フィールドが含まれる

#### 4. ループ処理の動作確認

```bash
uv run python -m src.main --workflow example_loop_workflow
```

期待される動作：
- `items`配列の各要素に対して処理が実行される
- ループの反復回数が正しくカウントされる
- 最終出力に`total_iterations`が含まれる

#### 5. マルチプロバイダーの動作確認

```bash
uv run python -m src.main --workflow example_multi_provider
```

期待される動作：
- OpenAIとGeminiの両方からレスポンスが返される
- 最終出力に両プロバイダーの結果が含まれる
- APIキーが正しく設定されている場合のみ成功する

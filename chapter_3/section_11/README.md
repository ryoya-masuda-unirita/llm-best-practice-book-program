# Chapter 3 Section 11: LLMシステムを機能単位の部品に分離する

## 概要

このプロジェクトは、**ストラテジーパターンを用いた機能単位のコンポーネント分離**によるRAG（Retrieval-Augmented Generation）システムの実装例です。複雑なLLMワークフローを、独立した責務を持つ小さなコンポーネントに分割し、それらをパイプラインとして組み合わせることで、柔軟性・再利用性・保守性の高いシステムを構築する方法を示します。

本実装では、文書の読み込み、意味的なチャンク分割、ベクトル化、検索、回答生成といったRAGの各ステップを独立したコンポーネントとして設計し、標準化されたインターフェース（`Component[InputType, OutputType]`）を通じて連携させています。これにより、各コンポーネントを差し替えることなく機能拡張が可能になります。

## 機能

- **コンポーネントベースアーキテクチャ**: 各機能を独立したコンポーネントとして実装
- **標準化されたインターフェース**: 全コンポーネントが`Component[InputType, OutputType]`基底クラスを継承
- **LLMベースのセマンティックチャンク分割**: 文書を意味的なまとまりで自動分割
- **ベクトル検索**: コサイン類似度による関連文書の検索
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **非同期処理**: async/awaitによる効率的なパイプライン実行
- **型安全性**: Pydanticによる厳密な型検証
- **CLIインターフェース**: Clickライブラリによるコマンドラインツール
- **柔軟な設定**: モデルやパラメータをコマンドラインから変更可能

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_11/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # CLIエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── rag_model.py         # Pydanticデータモデル定義
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── base.py              # 共通インターフェース定義
│   │   ├── loader.py            # 文書読み込みコンポーネント
│   │   ├── chunker.py           # セマンティックチャンク分割コンポーネント
│   │   ├── embedder.py          # 埋め込み生成コンポーネント
│   │   ├── retriever.py         # ベクトル検索コンポーネント
│   │   └── generator.py         # 回答生成コンポーネント
│   └── service/
│       ├── __init__.py
│       └── rag_pipeline.py      # パイプラインオーケストレーター
├── data/                         # ドキュメント格納ディレクトリ
│   ├── chapter2_section1.md
│   ├── chapter2_section2.md
│   └── chapter2_section3.md
├── outputs/                      # 回答出力先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── Makefile                      # ビルドとタスク管理
├── pyproject.toml                # プロジェクト依存関係
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト設計思想
```

### アーキテクチャ

このプロジェクトは、ストラテジーパターンに基づく3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────┐
│         CLI Layer (main.py)                     │
│     - コマンドライン引数解析                      │
│     - パイプライン初期化と実行                    │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Orchestration Layer (rag_pipeline.py)      │
│     - コンポーネントの組み立て                    │
│     - パイプラインフロー管理                      │
│     - インデックス作成とクエリ処理                │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Component Layer (strategy/*)               │
│  ┌────────────────────────────────────────┐    │
│  │ Component[InputType, OutputType]        │    │
│  │   - async def process(input) -> output │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  実装コンポーネント:                             │
│  - DocumentLoader: 文書読み込み                  │
│  - SemanticChunker: LLMベース意味分割            │
│  - Embedder: ベクトル化                         │
│  - Retriever: 類似検索                          │
│  - AnswerGenerator: 回答生成                    │
└──────────────────────────────────────────────────┘
```

#### コンポーネント間のデータフロー

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Document     │ --> │ Chunk        │ --> │ Chunk        │
│ Loader       │     │ (Semantic)   │     │ Embedder     │
│              │     │              │     │              │
│ str          │     │ list[Doc]    │     │ list[Chunk]  │
│ -> list[Doc] │     │ -> list[     │     │ -> list[     │
│              │     │   Chunk]     │     │   ChunkWith  │
│              │     │              │     │   Embedding] │
└──────────────┘     └──────────────┘     └──────────────┘
                                                   │
                                                   v
                                           ┌──────────────┐
                                           │ Vector       │
                                           │ Store        │
                                           │              │
                                           │ (In-memory)  │
                                           └──────────────┘
                                                   │
        ┌──────────────┐     ┌──────────────┐    │
        │ Answer       │ <-- │ Retriever    │ <--┘
        │ Generator    │     │              │
        │              │     │ str          │
        │ Generator    │     │ -> list[     │
        │ Input        │     │   Chunk]     │
        │ -> RAGAnswer │     │              │
        └──────────────┘     └──────────────┘
```

### 実装の詳細

#### 1. 共通インターフェース (`src/strategy/base.py`)

全てのコンポーネントが実装する基底クラス：

```python
class Component(ABC, Generic[InputType, OutputType]):
    """Base class for all pipeline components following the strategy pattern."""

    @abstractmethod
    async def process(self, input_data: InputType) -> OutputType:
        """
        Process input data and return output.

        Args:
            input_data: The input data to process

        Returns:
            The processed output data
        """
        pass
```

**ポイント**:
- ジェネリック型パラメータ`InputType`と`OutputType`で型安全性を確保
- 全コンポーネントが同じ`process`メソッドシグネチャを持つ
- 非同期処理をサポート（async/await）

#### 2. 文書読み込み (`src/strategy/loader.py`)

ディレクトリから文書を読み込むコンポーネント：

```python
class DocumentLoader(Component[str, list[Document]]):
    """Component for loading documents from a directory."""

    def __init__(self, file_extensions: list[str] | None = None):
        self.file_extensions = file_extensions or [".md"]

    async def process(self, input_data: str) -> list[Document]:
        # ディレクトリ内の指定拡張子のファイルを読み込み
        ...
```

**特徴**:
- 入力: ディレクトリパス（`str`）
- 出力: 文書リスト（`list[Document]`）
- ファイル拡張子をフィルタリング可能
- エラーハンドリングでファイル読み込み失敗を個別に処理

#### 3. セマンティックチャンク分割 (`src/strategy/chunker.py`)

LLMを使って文書を意味的なまとまりに分割：

```python
class SemanticChunker(Component[list[Document], list[Chunk]]):
    """Component for splitting documents into semantic chunks using LLM."""

    def __init__(self, model: OpenAIModel | GeminiModel = GeminiModel.GEMINI_2_5_FLASH):
        self.model = model

    async def process(self, input_data: list[Document]) -> list[Chunk]:
        # LLMに文書を渡して意味的な分割点を取得
        ...
```

**特徴**:
- 入力: 文書リスト（`list[Document]`）
- 出力: チャンクリスト（`list[Chunk]`）
- LLMに行番号付きテキストを渡し、セグメントの開始/終了行を取得
- 各セグメントにトピックと分割理由を付与
- OpenAIとGemini両方に対応

**LLMプロンプト例**:
```
あなたは文書を意味のあるセグメントに分割する専門家です。
与えられた文書を、トピックや意味的なまとまりに基づいて適切なセグメントに分割してください。

各セグメントは以下の条件を満たす必要があります：
1. 一つの明確なトピックや概念を扱っている
2. 文脈として独立して理解できる
3. 適切な長さ（最小3行、最大100行程度）
```

#### 4. 埋め込み生成 (`src/strategy/embedder.py`)

テキストチャンクをベクトル埋め込みに変換：

```python
class Embedder(Component[list[Chunk], list[ChunkWithEmbedding]]):
    """Component for creating embeddings from text chunks."""

    def __init__(
        self,
        model: OpenAIEmbeddingModel | GeminiEmbeddingModel = OpenAIEmbeddingModel.TEXT_EMBEDDING_3_SMALL
    ):
        self.model = model

    async def process(self, input_data: list[Chunk]) -> list[ChunkWithEmbedding]:
        # 各チャンクの埋め込みを作成
        ...
```

**特徴**:
- 入力: チャンクリスト（`list[Chunk]`）
- 出力: 埋め込み付きチャンクリスト（`list[ChunkWithEmbedding]`）
- OpenAI `text-embedding-3-small`またはGemini埋め込みモデルを使用
- エラーハンドリングで個別チャンクの失敗を処理

#### 5. ベクトル検索 (`src/strategy/retriever.py`)

クエリに関連するチャンクを検索：

```python
class VectorStore:
    """In-memory vector store for storing and searching embeddings."""

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Chunk]:
        # コサイン類似度で類似チャンクを検索
        ...

class Retriever(Component[str, list[Chunk]]):
    """Component for retrieving relevant chunks based on a query."""

    async def process(self, input_data: str) -> list[Chunk]:
        # クエリの埋め込みを作成し、ベクトルストアで検索
        ...
```

**特徴**:
- 入力: クエリ文字列（`str`）
- 出力: 関連チャンクリスト（`list[Chunk]`）
- インメモリベクトルストア（本番ではPinecone、Weaviateなどに置き換え可能）
- コサイン類似度による検索
- top_kパラメータで取得数を調整

#### 6. 回答生成 (`src/strategy/generator.py`)

検索されたチャンクに基づいて回答を生成：

```python
class AnswerGenerator(Component[AnswerGeneratorInput, RAGAnswer]):
    """Component for generating answers based on retrieved chunks."""

    def __init__(self, model: OpenAIModel | GeminiModel = GeminiModel.GEMINI_2_5_FLASH):
        self.model = model

    async def process(self, input_data: AnswerGeneratorInput) -> RAGAnswer:
        # 質問とチャンクからコンテキストを構築し、LLMで回答生成
        ...
```

**特徴**:
- 入力: 質問とチャンク（`AnswerGeneratorInput`）
- 出力: 回答と出典（`RAGAnswer`）
- システムプロンプトで「文書の情報のみを使用」を指示
- 各チャンクに出典番号を付与
- 回答に使用したソースファイルを追跡

#### 7. パイプラインオーケストレーター (`src/service/rag_pipeline.py`)

全コンポーネントを組み合わせてRAGワークフローを実現：

```python
class RAGPipeline:
    """Pipeline that orchestrates the RAG workflow."""

    def __init__(
        self,
        data_directory: str,
        chunker_model: OpenAIModel | GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        embedding_model: OpenAIEmbeddingModel | GeminiEmbeddingModel = OpenAIEmbeddingModel.TEXT_EMBEDDING_3_SMALL,
        generator_model: OpenAIModel | GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        top_k: int = 5,
    ):
        self.loader = DocumentLoader()
        self.chunker = SemanticChunker(model=chunker_model)
        self.embedder = Embedder(model=embedding_model)
        self.retriever = Retriever(vector_store=self.vector_store, top_k=top_k)
        self.generator = AnswerGenerator(model=generator_model)

    async def index_documents(self) -> None:
        """インデックス作成パイプライン"""
        documents = await self.loader.process(self.data_directory)
        chunks = await self.chunker.process(documents)
        chunks_with_embeddings = await self.embedder.process(chunks)
        self.vector_store.store(chunks_with_embeddings)

    async def query(self, question: str) -> RAGAnswer:
        """クエリ実行パイプライン"""
        relevant_chunks = await self.retriever.process(question)
        generator_input = AnswerGeneratorInput(question=question, chunks=relevant_chunks)
        answer = await self.generator.process(generator_input)
        return answer
```

**ポイント**:
- 各コンポーネントの出力が次のコンポーネントの入力になる
- インデックス作成とクエリ実行を分離
- コンポーネントの組み合わせを変更することで異なるパイプラインを構築可能

#### 8. データモデル (`src/model/rag_model.py`)

Pydanticを使用した型安全なデータモデル：

```python
class Document(BaseModel):
    """Represents a loaded document."""
    file_path: str
    content: str

class Chunk(BaseModel):
    """Represents a text chunk from a document."""
    text: str
    source_file: str
    chunk_index: int

class ChunkWithEmbedding(BaseModel):
    """Represents a chunk with its embedding vector."""
    chunk: Chunk
    embedding: list[float]

class ChunkSegment(BaseModel):
    """Represents a segment suggestion from LLM for chunking."""
    start_line: int
    end_line: int
    topic: str
    reason: str

class RAGAnswer(BaseModel):
    """Final answer from the RAG system."""
    question: str
    answer: str
    source_chunks: list[str]
```

**特徴**:
- `frozen=True`で不変性を保証
- `validate_assignment=True`で代入時のバリデーション
- 各ステップのデータ構造を明確に定義

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - numpy>=2.2.5
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

3. **ドキュメントの準備**

`data/`ディレクトリにMarkdownファイル（`.md`）を配置します。サンプルとして以下のファイルが含まれています：
- `chapter2_section1.md`
- `chapter2_section2.md`
- `chapter2_section3.md`

### 使用方法、実行方法

#### 基本的な使い方

```bash
# ドキュメントのインデックス作成
uv run python -m src.main index -d data

# 質問を実行
uv run python -m src.main query -d data -q "構造化出力の利点は何ですか？"
```

#### Makefileを使った簡易実行

```bash
# インデックス作成
make index

# 質問実行（質問を変数で指定）
make query Q="構造化出力の利点は何ですか？"

# サンプル質問を実行
make query-example
```

#### 詳細なオプション指定

```bash
# OpenAI APIを使用してインデックス作成
uv run python -m src.main index \
  -lp openai \
  -d data \
  -cm gpt-5-mini \
  -em text-embedding-3-small

# カスタムモデルで質問実行
uv run python -m src.main query \
  -lp gemini \
  -d data \
  -q "What are the main benefits of structured output for LLM systems?" \
  -cm gemini-2.5-flash \
  -em text-embedding-004 \
  -gm gemini-2.5-flash \
  -k 5 \
  -o outputs/answer.json
```

#### CLIオプション一覧

**`index`コマンド**:
- `-lp, --llm-provider`: LLMプロバイダー（`openai` または `gemini`）
- `-d, --data-directory`: ドキュメントディレクトリ（デフォルト: `data`）
- `-cm, --chunker-model`: チャンク分割に使用するモデル（デフォルト: `gpt-5-mini`）
- `-em, --embedding-model`: 埋め込みモデル（デフォルト: `text-embedding-3-small`）

**`query`コマンド**:
- `-lp, --llm-provider`: LLMプロバイダー（`openai` または `gemini`）
- `-d, --data-directory`: ドキュメントディレクトリ（デフォルト: `data`）
- `-q, --question`: 質問（必須）
- `-cm, --chunker-model`: チャンク分割に使用するモデル（デフォルト: `gpt-5-mini`）
- `-em, --embedding-model`: 埋め込みモデル（デフォルト: `text-embedding-3-small`）
- `-gm, --generator-model`: 回答生成に使用するモデル（デフォルト: `gpt-5-mini`）
- `-k, --top-k`: 検索するチャンク数（デフォルト: 5）
- `-o, --output-file`: 回答をJSONファイルとして保存するパス（オプション）

### 出力例

#### コマンド実行例

```bash
$ make query Q="構造化出力の主な利点は何ですか？"
```

#### ターミナル出力

```
[2025-11-01 12:00:45] [INFO] [__main__] Processing query: 構造化出力の主な利点は何ですか？
[2025-11-01 12:00:46] [INFO] [src.strategy.loader] Loaded 3 documents from data
[2025-11-01 12:00:50] [INFO] [src.strategy.chunker] Created 25 chunks from 3 documents
[2025-11-01 12:00:55] [INFO] [src.strategy.embedder] Created embeddings for 25 chunks
[2025-11-01 12:00:56] [INFO] [src.strategy.retriever] Retrieved 5 chunks for query
[2025-11-01 12:01:02] [INFO] [src.strategy.generator] Generated answer for question
[2025-11-01 12:01:02] [INFO] [__main__]
================================================================================
Question: 構造化出力の主な利点は何ですか？
================================================================================

Answer:
構造化出力の主な利点は以下の通りです：

1. **型安全性の向上**: PydanticモデルをAPI応答形式として直接利用することで、厳密な型検証とバリデーションが可能になります（文書1より）。

2. **パース処理の簡略化**: 従来はLLMの応答を手動でパースする必要がありましたが、構造化出力を使用することで、APIが自動的にPydanticモデルにパースしてくれます（文書1より）。

3. **信頼性の向上**: スキーマに準拠した出力が保証されるため、予期しない形式のエラーを防ぐことができます（文書2より）。

4. **開発効率の向上**: データモデルから自動的にスキーマ情報を抽出できるため、プロンプトとモデル定義の同期が容易になります（文書1より）。

--------------------------------------------------------------------------------
Sources: data/chapter2_section1.md, data/chapter2_section2.md
================================================================================
```

#### JSON出力例

`-o outputs/answer.json`オプションを指定した場合：

```json
{
  "question": "構造化出力の主な利点は何ですか？",
  "answer": "構造化出力の主な利点は以下の通りです：\n\n1. **型安全性の向上**: PydanticモデルをAPI応答形式として直接利用することで、厳密な型検証とバリデーションが可能になります（文書1より）。\n\n2. **パース処理の簡略化**: 従来はLLMの応答を手動でパースする必要がありましたが、構造化出力を使用することで、APIが自動的にPydanticモデルにパースしてくれます（文書1より）。\n\n3. **信頼性の向上**: スキーマに準拠した出力が保証されるため、予期しない形式のエラーを防ぐことができます（文書2より）。\n\n4. **開発効率の向上**: データモデルから自動的にスキーマ情報を抽出できるため、プロンプトとモデル定義の同期が容易になります（文書1より）。",
  "source_chunks": [
    "data/chapter2_section1.md",
    "data/chapter2_section2.md"
  ]
}
```

### テスト方法

#### 1. 基本的な動作確認

```bash
# サンプルドキュメントでインデックス作成
make index

# サンプルクエリを実行
make query-example
```

期待される動作：
- エラーなくインデックスが作成される
- 質問に対して関連する回答が生成される
- 回答に出典ファイルが含まれる

#### 2. 異なるモデルでのテスト

```bash
# OpenAI GPT-5-miniでテスト
uv run python -m src.main query \
  -lp openai \
  -d data \
  -q "What is RAG?" \
  -cm gpt-5-mini \
  -em text-embedding-3-small \
  -gm gpt-5-mini

# Gemini 2.5 Flashでテスト
uv run python -m src.main query \
  -lp gemini \
  -d data \
  -q "RAGとは何ですか？" \
  -cm gemini-2.5-flash \
  -em text-embedding-004 \
  -gm gemini-2.5-flash
```

#### 3. カスタムドキュメントでのテスト

```bash
# 独自のMarkdownファイルをdata/に配置
cp your_document.md data/

# インデックスを再作成
make index

# カスタムクエリを実行
make query Q="あなたのドキュメントに関する質問"
```

#### 4. 出力ファイルの検証

```bash
# JSON出力を生成
uv run python -m src.main query \
  -d data \
  -q "Test question" \
  -o outputs/test_answer.json

# jqで検証
cat outputs/test_answer.json | jq .

# Pythonで読み込みテスト
python -c "
from src.model.rag_model import RAGAnswer
import json

with open('outputs/test_answer.json') as f:
    data = json.load(f)
    answer = RAGAnswer(**data)
    print(f'Valid! Question: {answer.question}')
    print(f'Sources: {answer.source_chunks}')
"
```

#### 5. コンポーネント単体のテスト

```python
# Pythonインタラクティブシェルで個別コンポーネントをテスト
import asyncio
from src.strategy.loader import DocumentLoader

async def test_loader():
    loader = DocumentLoader()
    documents = await loader.process("data")
    print(f"Loaded {len(documents)} documents")
    for doc in documents:
        print(f"  - {doc.file_path}: {len(doc.content)} chars")

asyncio.run(test_loader())
```

#### 6. コードフォーマットと型チェック

```bash
# コードフォーマット
make fmt

# リント
make lint

# 型チェック
make mypy

# すべて実行
make fix && make mypy
```

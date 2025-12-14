# Chapter 4 Section 4: LLMシステムを機能単位の部品に分離する

## 概要

本プロジェクトは、**Strategy パターン**を活用したモジュラーなRAG（Retrieval-Augmented Generation）システムの実装例です。LLMを組み込んだ複雑なワークフローを、独立した機能単位のコンポーネントに分解し、標準化されたインターフェースを通じて柔軟に組み合わせる設計パターンを示します。

RAGシステムは「ドキュメント読み込み」「テキスト分割」「ベクトル化」「検索」「回答生成」など複数のステップで構成されます。これらを一枚岩（モノリシック）に実装すると、コードの肥大化、テストの困難さ、機能追加時のリスク増大といった問題が生じます。本プロジェクトでは、各ステップを独立したコンポーネントとして設計し、`process(input) -> output` という共通インターフェースで接続することで、これらの課題を解決します。

## 機能

- **コンポーネントベースアーキテクチャ**: 各機能を独立したコンポーネントとして実装
- **標準化されたインターフェース**: 全コンポーネントが`Component[InputType, OutputType]`基底クラスを継承
- **LLMベースのセマンティックチャンク分割**: Gemini を使用して文書を意味的なまとまりで自動分割
- **ベクトル検索**: コサイン類似度による関連文書の検索
- **非同期処理**: async/awaitによる効率的なパイプライン実行
- **型安全性**: Pydanticによる厳密な型検証とジェネリクスによる型安全なパイプライン
- **CLIインターフェース**: Clickライブラリによるコマンドラインツール

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
│   │   └── llm_client.py        # Gemini クライアント初期化
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
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── CLAUDE.md                     # プロジェクト設計思想
└── README.md                     # このファイル
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                │
│                        (main.py)                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAGPipeline Orchestrator                      │
│                    (rag_pipeline.py)                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Index Flow    │   │ Query Flow    │   │ VectorStore   │
└───────┬───────┘   └───────┬───────┘   └───────────────┘
        │                   │
        ▼                   ▼
┌───────────────────────────────────────────────────────────────┐
│                     Component Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Document │  │ Semantic │  │ Embedder │  │ Retriever│      │
│  │  Loader  │→ │ Chunker  │→ │          │→ │          │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                    │          │
│                                                    ▼          │
│                                            ┌──────────┐      │
│                                            │ Answer   │      │
│                                            │Generator │      │
│                                            └──────────┘      │
└───────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Gemini API                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### コンポーネント間のデータフロー

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Document     │ --> │ Semantic     │ --> │ Embedder     │
│ Loader       │     │ Chunker      │     │              │
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
        ┌──────────────┐     ┌──────────────┐     │
        │ Answer       │ <-- │ Retriever    │ <---┘
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
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")

class Component(ABC, Generic[InputType, OutputType]):
    """Base class for all pipeline components following the strategy pattern."""

    @abstractmethod
    async def process(self, input_data: InputType) -> OutputType:
        """Process input data and return output."""
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
        """Load all documents from the specified directory."""
        directory = Path(input_data)
        documents = []
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix in self.file_extensions:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                documents.append(Document(file_path=str(file_path), content=content))
        return documents
```

**特徴**:
- 入力: ディレクトリパス（`str`）
- 出力: 文書リスト（`list[Document]`）
- ファイル拡張子をフィルタリング可能

#### 3. セマンティックチャンク分割 (`src/strategy/chunker.py`)

Gemini を使って文書を意味的なまとまりに分割：

```python
class SemanticChunker(Component[list[Document], list[Chunk]]):
    """Component for splitting documents into semantic chunks using LLM."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH):
        self.model = model

    async def process(self, input_data: list[Document]) -> list[Chunk]:
        """Split documents into semantic chunks."""
        all_chunks = []
        for document in input_data:
            chunks = await self._chunk_document(document)
            all_chunks.extend(chunks)
        return all_chunks
```

**特徴**:
- 入力: 文書リスト（`list[Document]`）
- 出力: チャンクリスト（`list[Chunk]`）
- LLMに行番号付きテキストを渡し、セグメントの開始/終了行を取得
- 各セグメントにトピックと分割理由を付与

#### 4. 埋め込み生成 (`src/strategy/embedder.py`)

テキストチャンクをベクトル埋め込みに変換：

```python
class Embedder(Component[list[Chunk], list[ChunkWithEmbedding]]):
    """Component for creating embeddings from text chunks."""

    def __init__(self, model: GeminiEmbeddingModel = GeminiEmbeddingModel.GEMINI_EMBEDDING_001):
        self.model = model

    async def process(self, input_data: list[Chunk]) -> list[ChunkWithEmbedding]:
        """Create embeddings for all chunks."""
        chunks_with_embeddings = []
        for chunk in input_data:
            embedding = await self._create_embedding(chunk.text)
            chunks_with_embeddings.append(ChunkWithEmbedding(chunk=chunk, embedding=embedding))
        return chunks_with_embeddings
```

#### 5. ベクトル検索 (`src/strategy/retriever.py`)

クエリに関連するチャンクを検索：

```python
class VectorStore:
    """In-memory vector store for storing and searching embeddings."""

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[Chunk]:
        """Search for the most similar chunks using cosine similarity."""
        # コサイン類似度で類似チャンクを検索
        ...

class Retriever(Component[str, list[Chunk]]):
    """Component for retrieving relevant chunks based on a query."""

    async def process(self, input_data: str) -> list[Chunk]:
        """Retrieve relevant chunks for a query."""
        query_embedding = await self._create_query_embedding(input_data)
        return self.vector_store.search(query_embedding, self.top_k)
```

**特徴**:
- 入力: クエリ文字列（`str`）
- 出力: 関連チャンクリスト（`list[Chunk]`）
- インメモリベクトルストア（本番ではPinecone、Weaviateなどに置き換え可能）
- コサイン類似度による検索

#### 6. 回答生成 (`src/strategy/generator.py`)

検索されたチャンクに基づいて回答を生成：

```python
class AnswerGenerator(Component[AnswerGeneratorInput, RAGAnswer]):
    """Component for generating answers based on retrieved chunks."""

    def __init__(self, model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH):
        self.model = model

    async def process(self, input_data: AnswerGeneratorInput) -> RAGAnswer:
        """Generate an answer based on the question and retrieved chunks."""
        context = self._build_context(input_data.chunks)
        answer = await self._generate_answer(input_data.question, context)
        source_files = list(set([chunk.source_file for chunk in input_data.chunks]))
        return RAGAnswer(question=input_data.question, answer=answer, source_chunks=source_files)
```

**特徴**:
- 入力: 質問とチャンク（`AnswerGeneratorInput`）
- 出力: 回答と出典（`RAGAnswer`）
- システムプロンプトで「文書の情報のみを使用」を指示

#### 7. パイプラインオーケストレーター (`src/service/rag_pipeline.py`)

全コンポーネントを組み合わせてRAGワークフローを実現：

```python
class RAGPipeline:
    """Pipeline that orchestrates the RAG workflow."""

    def __init__(
        self,
        data_directory: str,
        chunker_model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
        embedding_model: GeminiEmbeddingModel = GeminiEmbeddingModel.GEMINI_EMBEDDING_001,
        generator_model: GeminiModel = GeminiModel.GEMINI_2_5_FLASH,
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
        return await self.generator.process(generator_input)
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

class RAGAnswer(BaseModel):
    """Final answer from the RAG system."""
    question: str
    answer: str
    source_chunks: list[str]
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - numpy>=2.2.5
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
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

`data/`ディレクトリにMarkdownファイル（`.md`）を配置します。

### 使用方法、実行方法

#### ドキュメントのインデックス作成

```bash
uv run python -m src.main index -d data/
```

**オプション:**

| オプション | 短縮形 | 説明 | デフォルト |
|------------|--------|------|------------|
| `--data-directory` | `-d` | ドキュメントディレクトリ | `data` |
| `--chunker-model` | `-cm` | チャンキング用モデル | `gemini-2.5-flash` |
| `--embedding-model` | `-em` | 埋め込み用モデル | `gemini-embedding-001` |

#### 質問応答（クエリ）

```bash
uv run python -m src.main query -d data/ -q "LLMの活用方法について教えてください"
```

**オプション:**

| オプション | 短縮形 | 説明 | デフォルト |
|------------|--------|------|------------|
| `--data-directory` | `-d` | ドキュメントディレクトリ | `data` |
| `--question` | `-q` | 質問文 | (必須) |
| `--chunker-model` | `-cm` | チャンキング用モデル | `gemini-2.5-flash` |
| `--embedding-model` | `-em` | 埋め込み用モデル | `gemini-embedding-001` |
| `--generator-model` | `-gm` | 回答生成用モデル | `gemini-2.5-flash` |
| `--top-k` | `-k` | 検索するチャンク数 | `5` |
| `--output-file` | `-o` | 結果のJSON出力先 | (なし) |

#### 利用可能なモデル

**Gemini モデル（チャンキング/回答生成用）:**
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

**Gemini 埋め込みモデル:**
- `gemini-embedding-001`

### 出力例

```bash
$ uv run python -m src.main query -d data/ -q "RAGシステムとは何ですか？"

[INFO] Processing query: RAGシステムとは何ですか？
[INFO] Starting document indexing from data/
[INFO] Loaded 3 documents from data/
[INFO] Created 8 chunks from 3 documents
[INFO] Created embeddings for 8 chunks
[INFO] Stored 8 chunks. Total: 8
[INFO] Document indexing completed
[INFO] Retrieved 5 chunks for query
[INFO] Generated answer for question: RAGシステムとは何ですか？

================================================================================
Question: RAGシステムとは何ですか？
================================================================================

Answer:
RAG（Retrieval-Augmented Generation）システムとは、外部のドキュメントやデータベースから
関連情報を検索し、その情報を基にLLMが回答を生成するシステムです。
これにより、LLMの知識カットオフ以降の情報や、特定ドメインの専門知識に基づいた
正確な回答が可能になります。

--------------------------------------------------------------------------------
Sources: data/chapter2_section1.md, data/chapter2_section2.md
================================================================================
```

#### JSON出力例

`-o` オプションで結果をJSONファイルに保存できます:

```bash
uv run python -m src.main query -d data/ -q "質問" -o output/answer.json
```

```json
{
  "question": "RAGシステムとは何ですか？",
  "answer": "RAG（Retrieval-Augmented Generation）システムとは...",
  "source_chunks": [
    "data/chapter2_section1.md",
    "data/chapter2_section2.md"
  ]
}
```

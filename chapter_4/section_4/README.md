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

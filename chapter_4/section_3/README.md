# Chapter 4 Section 3: LLMシステムを機能単位の部品に分離する

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
GEMINI_API_KEY=<your_gemini_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

3. **ドキュメントの準備**

`data/`ディレクトリにMarkdownファイル（`.md`）を配置します。

### 使用方法、実行方法

```shell
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS] COMMAND [ARGS]...

  RAG System CLI - A modular RAG system using strategy pattern.

Options:
  --help  Show this message and exit.

Commands:
  index  Index documents from the data directory.
  query  Query the RAG system with a question.
```


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
uv run python -m src.main query -d data/ -q "LLMのリクエストでタイムアウトが重要な理由を教えて下さい"
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
- `gemini-3.5-flash`
- `gemini-3.1-flash-lite`

**Gemini 埋め込みモデル:**
- `gemini-embedding-001`

### 出力例

```bash
$  uv run python -m src.main query -d data/ -q "構造化出力とはなんですか？"

[2026-02-07 08:32:09,676] [INFO] [__main__] [main.py:129] [query] Processing query: 構造化出力とはなんですか？
[2026-02-07 08:32:09,676] [INFO] [src.service.rag_pipeline] [rag_pipeline.py:38] [index_documents] Starting document indexing from data/
[2026-02-07 08:32:09,677] [INFO] [src.strategy.loader] [loader.py:35] [process] Loaded document: data/chapter2_section1.md
[2026-02-07 08:32:09,677] [INFO] [src.strategy.loader] [loader.py:35] [process] Loaded document: data/chapter2_section2.md
[2026-02-07 08:32:09,677] [INFO] [src.strategy.loader] [loader.py:35] [process] Loaded document: data/chapter2_section3.md
[2026-02-07 08:32:09,677] [INFO] [src.strategy.loader] [loader.py:41] [process] Loaded 3 documents from data
[2026-02-07 08:32:19,816] [INFO] [src.strategy.chunker] [chunker.py:25] [process] Created 7 chunks from data/chapter2_section1.md
[2026-02-07 08:32:29,273] [INFO] [src.strategy.chunker] [chunker.py:25] [process] Created 7 chunks from data/chapter2_section2.md
[2026-02-07 08:32:38,552] [INFO] [src.strategy.chunker] [chunker.py:25] [process] Created 7 chunks from data/chapter2_section3.md
[2026-02-07 08:32:38,552] [INFO] [src.strategy.chunker] [chunker.py:30] [process] Created total 21 chunks from 3 documents
[2026-02-07 08:32:45,320] [INFO] [src.strategy.embedder] [embedder.py:30] [process] Created embeddings for 21 chunks
[2026-02-07 08:32:45,320] [INFO] [src.strategy.retriever] [retriever.py:20] [store] Stored 21 chunks. Total: 21
[2026-02-07 08:32:45,320] [INFO] [src.service.rag_pipeline] [rag_pipeline.py:57] [index_documents] Document indexing completed
[2026-02-07 08:32:45,320] [INFO] [src.service.rag_pipeline] [rag_pipeline.py:63] [query] Processing query: 構造化出力とはなんですか？
[2026-02-07 08:32:45,643] [INFO] [src.strategy.retriever] [retriever.py:38] [search] Retrieved 5 chunks for query
[2026-02-07 08:32:47,188] [INFO] [src.strategy.generator] [generator.py:44] [process] Generated answer for question: 構造化出力とはなんですか？
[2026-02-07 08:32:47,188] [INFO] [src.service.rag_pipeline] [rag_pipeline.py:70] [query] Query processing completed
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:143] [query] 
================================================================================
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:144] [query] Question: 構造化出力とはなんですか？
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:145] [query] ================================================================================
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:146] [query] 
Answer:
構造化出力とは、LLM（大規模言語モデル）に対して事前に定義したデータ構造（スキーマ）に従って出力するよう明確に指示し、その構造に合致したJSONやデー タクラス形式で応答を受け取る手法です。(文書1, 文書2)

これにより、LLMの生成結果を安全かつ構造的に処理できるようになり、高い信頼性を持つシステム連携が実現できます。(文書1)
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:147] [query] 
--------------------------------------------------------------------------------
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:148] [query] Sources: data/chapter2_section1.md
[2026-02-07 08:32:47,188] [INFO] [__main__] [main.py:149] [query] ================================================================================

```

#### JSON出力例

`-o` オプションで結果をJSONファイルに保存できます:

```bash
uv run python -m src.main query -d data/ -q "質問" -o output/answer.json
```

```json
{
  "question": "構造化出力とはなんですか？",
  "answer": "構造化出力とは、LLM（大規模言語モデル）に対して事前に定義したデータ構造（スキーマ）に従って出力するよう明確に指示し、その構造に合致したJSONやデータクラス形式で応答を受け取る手法です。これにより、システムはLLMの生成結果を安全かつ構造的に処理できるようになり、高い信頼性を持つシステム連携が実現できます。(文書1、文書2)",
  "source_chunks": [
    "data/chapter2_section1.md"
  ]
}
```

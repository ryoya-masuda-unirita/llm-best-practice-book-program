# Chapter 2 Section 5: LLMのバッチ処理

## 概要

このプロジェクトは、**Batch API（バッチ処理API）** を用いたLLMの大量リクエスト処理の実装を示すサンプルコードです。Google Gemini 2.5のBatch APIを活用し、複数のリクエストを一括で効率的に処理する方法を学ぶことができます。

フィクションのキャラクター情報を大量生成するユースケースを通じて、Batch APIの実践的な実装方法、ジョブの状態監視、結果の取得と保存までの一連のフローを習得できます。

## 機能

- **Batch API処理**: Google Gemini Batch APIによる複数リクエストの一括実行
- **構造化出力**: Pydanticモデルを活用した型安全なLLM応答
- **ジョブ管理**: バッチジョブの状態監視とポーリング処理
- **モデル選択**: Gemini 2.5 Pro/Flash/Flash-Liteから選択可能
- **非同期処理**: 効率的なAPI呼び出しとリソース管理
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果を個別のJSONファイルとして保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_5/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── request_llm.py       # Batch API リクエスト処理
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # タスク自動化
└── README.md                     # このファイル
```

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────┐
│         CLI Layer (main.py)             │
│     - コマンドライン引数解析             │
│     - 出力ディレクトリ管理               │
│     - モデル選択                         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Business Logic Layer               │
│  - プロンプト生成 (prompt.py)           │
│  - LLMクライアント管理 (llm_client.py)  │
│  - データモデル (model.py)              │
│  - Batch API処理 (request_llm.py)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - 外部API (Google Gemini Batch API)    │
└─────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
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

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini 2.5 Flashを使用
uv run python -m src.main --model gemini-2.5-flash

# Gemini 2.5 Proを使用
uv run python -m src.main --model gemini-2.5-pro

# Gemini 2.5 Flash-Liteを使用（最も高速・低コスト）
uv run python -m src.main --model gemini-2.5-flash-lite

# 短縮オプション
uv run python -m src.main -m gemini-2.5-flash
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -m gemini-2.5-flash --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -m gemini-2.5-flash -od ./my_characters
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -m, --model [gemini-2.5-pro|gemini-2.5-flash|gemini-2.5-flash-lite]
                                  The model to use for the request.  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### Makefileを使用する場合

```bash
# デフォルトモデル（gemini-2.5-flash）で実行
make run

# 特定のモデルを指定
make run MODEL=gemini-2.5-pro

# 出力ディレクトリを指定
make run OUTPUT_DIR=./custom_output
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが複数生成されます：

**ファイル名**: `outputs/gemini_088221aadc0942c69878423b1d4221a8.json`

```json
{
    "first_name": "アキラ",
    "last_name": "タナカ",
    "gender": "male",
    "age": 29,
    "personalities": [
        {
            "short_personality": "内向的な観察者",
            "description": "アキラは物静かで、他者との交流よりも一人で物事を深く考えることを好む。彼は周囲の環境や人々の行動を注意深く観察し、その情報を自身の内なる世界で分析する傾向がある。"
        },
        {
            "short_personality": "革新的な発明家",
            "description": "彼は既存の概念にとらわれず、常に新しい解決策やアイデアを模索している。特に機械やテクノロジーに対する深い情熱を持ち、実用的で独創的な発明を生み出すことに喜びを感じる。しばしば突飛な発想をするが、それを形にするための忍耐力も持ち合わせている。"
        },
        {
            "short_personality": "控えめな忠実さ",
            "description": "口数は少ないが、一度信頼を置いた相手に対しては非常に忠実で、困っている人がいれば、言葉よりも行動で助けようとする。自分の感情を表に出すのが苦手なため、誤解されやすいこともあるが、その心の奥底には強い正義感と他者への思いやりを秘めている。"
        }
    ]
}
```

**実行ログ例**:
```
[2025-11-17 16:49:02] [INFO] [__main__] [main.py:44] [main] Model: gemini-2.5-flash
Output directory: outputs
[2025-11-17 16:49:03] [INFO] [src.service.request_llm] [request_llm.py:41] [request_gemini] Triggered job name: projects/123456789/locations/us-central1/batchPredictionJobs/structured-output-job-1
[2025-11-17 16:49:08] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_RUNNING. Waiting 5 seconds...
[2025-11-17 16:49:13] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_RUNNING. Waiting 5 seconds...
[2025-11-17 16:49:18] [INFO] [src.service.request_llm] [request_llm.py:46] [request_gemini] Batch job status: JOB_STATE_SUCCEEDED
[2025-11-17 16:49:18] [INFO] [__main__] [main.py:56] [main] File saved to outputs/gemini_088221aadc0942c69878423b1d4221a8.json
[2025-11-17 16:49:18] [INFO] [__main__] [main.py:56] [main] File saved to outputs/gemini_1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p.json
...
```

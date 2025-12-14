# Chapter 3 Section 3: LLMリクエストの適応的バックオフによるリトライ

## 概要

このプロジェクトは、**適応的エクスポネンシャルバックオフ（Adaptive Exponential Backoff）** を用いたLLM APIリクエストの堅牢な実装を示すサンプルコードです。Google Gemini 2.5専用に実装されており、レート制限や一時的な障害に対して自動的に再試行する仕組みを実装しています。

大量のキャラクター生成リクエストを並列バッチ処理するユースケースを通じて、本番環境で必要とされるリトライロジック、並行処理制御、エラーハンドリングの実践的な実装方法を学ぶことができます。

## 機能

- **エクスポネンシャルバックオフ**: 指数関数的に待機時間を増やす再試行戦略（1秒 → 2秒 → 4秒 → ...）
- **ランダムジッター**: 10-50%のランダムな揺らぎで複数クライアントの再試行を分散
- **インテリジェントなエラー判定**: Gemini APIエラーを判別し、リトライすべきエラーを自動判別
- **セマフォによる並行処理制御**: 同時実行数を制限して過負荷を防止
- **バッチ処理**: 複数リクエストを効率的に並列処理
- **部分的失敗への対応**: 一部のリクエストが失敗しても処理を継続
- **詳細なログ出力**: リトライ状況、成功/失敗統計を可視化
- **包括的なテストスイート**: 16個のテストケースでリトライロジックを検証

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_4/
├── src/
│   ├── __init__.py
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント（バッチ処理）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py             # Pydanticデータモデル定義
│   │   └── llmops_log.py        # LLMOpsログモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py       # リトライロジック＆バッチ処理（核心部分）
│       ├── llmops_logger.py     # LLMOps用ロガー
│       └── prompt_storage.py    # プロンプト保存機能
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytestフィクスチャ
│   └── test_request_llm.py      # リトライロジックのテスト（16ケース）
├── outputs/                      # 生成結果の保存先（自動作成）
├── prompt_storage/               # プロンプト保存先（自動作成）
├── character_requests.yaml       # キャラクター生成リクエスト定義（33件）
├── .envrc.example                # 環境変数設定のサンプル
├── pytest.ini                    # pytest設定
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # 開発用タスク
├── README.md                     # このファイル
└── CLAUDE.md                     # 開発ガイドライン
```

### アーキテクチャ

このプロジェクトは、以下の多層アーキテクチャで構成されています：

```
┌────────────────────────────────────────────────┐
│         CLI Layer (main.py)                    │
│  - コマンドライン引数解析                       │
│  - バッチ処理のオーケストレーション             │
│  - 出力ファイル管理                             │
└──────────────────┬─────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────┐
│      Service Layer (request_llm.py)            │
│  - リトライロジック                             │
│    ├── エクスポネンシャルバックオフ             │
│    ├── ランダムジッター                         │
│    └── エラー判定                               │
│  - バッチ処理                                   │
│    ├── 並列実行制御（セマフォ）                 │
│    ├── 部分的失敗のハンドリング                 │
│    └── 統計情報のログ出力                       │
└──────────────────┬─────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────┐
│      Business Logic Layer                      │
│  - プロンプト生成 (prompt.py)                  │
│  - LLMクライアント管理 (llm_client.py)         │
│  - データモデル (model.py)                     │
│  - LLMOpsロギング (llmops_logger.py)           │
└──────────────────┬─────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────┐
│      Infrastructure Layer                      │
│  - 設定管理 (config.py)                        │
│  - ログ管理 (logger.py)                        │
│  - 外部API (Gemini)                            │
└────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-api-core>=2.26.0
  - google-genai>=1.45.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - pyyaml>=6.0.3
- **開発依存**:
  - pytest>=8.4.2
  - pytest-asyncio>=1.2.0
  - pytest-mock>=3.15.1

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
uv sync --all-extras

# pipを使用する場合
pip install -e .[dev]
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用してバッチ処理（並行5リクエスト）
python -m src.main \
  --request-file character_requests.yaml \
  --model GEMINI_2_5_FLASH \
  --parallelism 5
```

#### 短縮オプション

```bash
# 短縮オプションを使用
python -m src.main \
  -rf character_requests.yaml \
  -m GEMINI_2_5_FLASH \
  -p 5 \
  -od outputs
```

#### 並行処理数の調整

```bash
# 低速・安全（並行2リクエスト）
python -m src.main -rf character_requests.yaml -m GEMINI_2_5_FLASH -p 2

# 標準（並行5リクエスト）
python -m src.main -rf character_requests.yaml -m GEMINI_2_5_FLASH -p 5

# 高速（並行10リクエスト）※レート制限に注意
python -m src.main -rf character_requests.yaml -m GEMINI_2_5_FLASH -p 10
```

#### ヘルプの表示

```bash
python -m src.main --help

Usage: python -m src.main [OPTIONS]

Options:
  -rf, --request-file PATH        Path to the YAML file containing character
                                  generation requests.  [required]
  -m, --model [GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The Gemini model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -p, --parallelism INTEGER       Number of parallel requests to make.
  -u, --user-id TEXT              User ID for logging purposes.
  -st, --storage-type [LOCAL]     The storage type for prompt logging.
  --help                          Show this message and exit.
```

### 出力例

#### 実行ログ

```
[2025-11-17 18:30:45] [INFO] Request file: character_requests.yaml
Model: gemini-2.5-flash
Output directory: outputs
Parallelism: 5
User ID: default_user
Storage type: local

[2025-11-17 18:30:45] [INFO] Loading character requests from character_requests.yaml
[2025-11-17 18:30:45] [INFO] Loaded 33 character requests

[2025-11-17 18:30:45] [INFO] Starting batch processing of 33 requests using Gemini gemini-2.5-flash (parallelism: 5)

[2025-11-17 18:30:48] [WARNING] Request failed (attempt 1/6). Error: ServiceUnavailable: 503 Service unavailable. Retrying in 1.34s...

[2025-11-17 18:31:15] [INFO] Batch processing completed. Successful: 33, Failed: 0

[2025-11-17 18:31:15] [INFO] Saving 33 character responses to outputs
[2025-11-17 18:31:15] [INFO] Saved character 1 to outputs/gemini_001_a1b2c3d4.json
[2025-11-17 18:31:15] [INFO] Saved character 2 to outputs/gemini_002_e5f6g7h8.json
...
[2025-11-17 18:31:16] [INFO] Batch processing complete. Generated 33 characters.
```

#### 生成されたJSONファイル例

**ファイル名**: `outputs/gemini_001_a1b2c3d4.json`

```json
{
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "神秘的な弓使い",
            "description": "過去について語ることは少ないが、その弓の腕前は伝説的。静かな森で修行を積んだと噂されている。"
        },
        {
            "short_personality": "寡黙な戦士",
            "description": "無駄な言葉を話さず、行動で示すタイプ。仲間からの信頼は厚い。"
        },
        {
            "short_personality": "孤高の守護者",
            "description": "一人で行動することを好むが、弱者を見過ごすことはできない正義感の持ち主。"
        }
    ]
}
```

#### リトライ発生時のログ詳細

```
[2025-11-17 18:30:50] [WARNING] Request failed (attempt 1/6). Error: ServiceUnavailable: 503 Service unavailable. Retrying in 1.42s...
[2025-11-17 18:30:51] [WARNING] Request failed (attempt 2/6). Error: ServiceUnavailable: 503 Service unavailable. Retrying in 2.89s...
[2025-11-17 18:30:54] [INFO] Request succeeded after 2 retries
```

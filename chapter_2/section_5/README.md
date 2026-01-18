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
# uvを使用する
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini 2.5 Flashを使用
uv run python -m src.main --model GEMINI_2_5_FLASH --output-directory outputs/

# Gemini 2.5 Proを使用
uv run python -m src.main --model GEMINI_2_5_PRO --output-directory outputs/

# Gemini 2.5 Flash-Liteを使用（最も高速・低コスト）
uv run python -m src.main --model GEMINI_2_5_FLASH_LITE --output-directory outputs/

# 短縮オプション
uv run python -m src.main -m GEMINI_2_5_FLASH -od outputs/
```

#### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -m, --model [GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが複数生成されます：

**ファイル名**: `outputs/gemini_088221aadc0942c69878423b1d4221a8.json`

```json
{
    "first_name": "海斗",
    "last_name": "田中",
    "gender": "male",
    "age": 78,
    "personalities": [
        {
            "short_personality": "細心かつ忍耐強い",
            "description": "マスター時計職人として、海斗は超人的なレベルの忍耐力を持っています。彼は一つの歯車に何日も費やし、その完璧さを追求します。この細心な性質は、道具の配置からお茶の淹れ方まで、彼の生活のあらゆる側面に及んでいます。彼は、どんなに小さな細部でも、宇宙の壮大なデザインに貢献していると信じています。"
        },
        {
            "short_personality": "風変わりで哲学的",
            "description": "その精密な性格にもかかわらず、海斗は時間に対して遊び心のある哲学的な見方をしています。彼はしばしば時計や時間に関する謎や比喩で話し、人生を独自のユニークなリズムを持つ複雑な時計と見なしています。彼は仕事を終えるために「明日から数秒借りた」と主張することがあり、周りの人々は彼が詩的なのか文字通りの意味なのか疑問に思います。"
        },
        {
            "short_personality": "内に秘めた憂鬱",
            "description": "風変わりな外見の下には、深い憂鬱が隠されています。彼は容赦なく進む時間と失われた愛する人々の記憶に苦しんでいます。彼の時計への執着は単なる職業ではなく、彼から多くを奪った唯一の力を理解し、おそらくは制御しようとする必死の試みです。彼はこのことについてめったに話しませんが、止まった時計を見つめるときの彼の物憂げな眼差しにそれが見て取れます。"
        }
    ]
}
```

**実行ログ例**:
```
$ uv run python -m src.main --model GEMINI_2_5_FLASH --output-directory outputs/

[2026-01-17 16:29:07,778] [INFO] [__main__] [main.py:43] [main] Model: gemini-2.5-flash
Output directory: outputs/
[2026-01-17 16:29:11,510] [INFO] [src.service.request_llm] [request_llm.py:41] [request_gemini] Triggered job name: batches/sf8jw91ll7t6yax3y7gdf8ec4mtpuw7k5v20
[2026-01-17 16:29:11,678] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:16,875] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:22,063] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:27,262] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:32,465] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:37,671] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:42,885] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:48,093] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:53,318] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:29:58,503] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:03,697] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:08,896] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:14,079] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:19,279] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:24,460] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:29,646] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:34,829] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_PENDING. Waiting 5 seconds...
[2026-01-17 16:30:40,034] [INFO] [src.service.request_llm] [request_llm.py:54] [request_gemini] Job not finished. Current state: JOB_STATE_RUNNING. Waiting 5 seconds...
[2026-01-17 16:30:45,680] [INFO] [src.service.request_llm] [request_llm.py:46] [request_gemini] Batch job status: JOB_STATE_SUCCEEDED
[2026-01-17 16:30:45,681] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_45e3731f88a84c4c8c004856b2943255.json
[2026-01-17 16:30:45,681] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_5eaed9b60b0549038a72f859e80f672f.json
[2026-01-17 16:30:45,681] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_fd6139bb3d5b4e6a89c3bc8d6d08c840.json
[2026-01-17 16:30:45,681] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_83e36889436645998c74005f7bbae14c.json
[2026-01-17 16:30:45,682] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_e574161150df4c23979b98657bc5b97d.json
[2026-01-17 16:30:45,682] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_fa8b764cb5944641b2543e19c7460248.json
[2026-01-17 16:30:45,682] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_c4bf50dfebd64a649e459b66d7801b21.json
[2026-01-17 16:30:45,682] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_12fa722d7db04965bfd6826041a3aedd.json
[2026-01-17 16:30:45,682] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_73463f0827014d9a9c2ac0fa59847c53.json
[2026-01-17 16:30:45,682] [INFO] [__main__] [main.py:55] [main] File saved to outputs/gemini_41ce153e594f41abbfa2d19f5bb3ab68.json
```

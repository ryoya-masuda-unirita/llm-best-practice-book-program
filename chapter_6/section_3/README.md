# Chapter 6 Section 3: 不要な過去を忘れる - 状態ベースロールバックパターン

## 概要

本プロジェクトは、LLMアプリケーションにおける**「不要な過去を忘れる」パターン**を、状態ベースのロールバックメカニズムによって実装しています。ユーザーはマルチステップパイプラインの任意のフェーズにロールバックでき、汚染されたコンテキストを「忘却」してクリーンな状態からコンテンツを再生成できます。

このシステムは、複数のコンテンツバリアントを並列生成し、LLM-as-a-Judgeで評価を行い、重要な分岐点でHuman-in-the-Loopの意思決定とロールバック機能を提供する「パラレルワールド記事生成パイプライン」を実装しています。

## 機能

- **パラレルワールド生成**: 複数のアウトラインと後半バリアントを並列生成
- **LLM-as-a-Judge**: 生成された記事を自動評価（1-5段階グレード）
- **Human-in-the-Loop**: 3つの重要な意思決定ポイントでユーザー介入
- **状態ベースロールバック**: 任意のフェーズへのロールバックによる再生成
- **フィードバックループ**: 拒否時に前回のフィードバックを活用した再生成
- **構造化出力**: Pydanticモデルによる型安全なLLM応答

## プロジェクト構成

### ディレクトリ構成

```
chapter_6/section_3/
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # 状態・データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # 各フェーズのプロンプト
│   ├── service/
│   │   ├── __init__.py
│   │   ├── generation_service.py # LLM生成ロジック
│   │   ├── runner_service.py     # パイプライン制御・ロールバック
│   │   └── helper.py             # UIヘルパー・ファイルI/O
│   ├── __init__.py
│   ├── config.py                 # 設定管理
│   ├── logger.py                 # ロギング設定
│   └── main.py                   # CLIエントリポイント
├── outputs/                       # 生成記事（自動作成）
├── .envrc.example                 # 環境変数テンプレート
├── pyproject.toml                 # プロジェクト依存関係
├── Makefile                       # 開発コマンド
└── README.md                      # 本ドキュメント
```

### アーキテクチャ

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         パイプライン制御フロー                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │  Phase 1    │   │  Phase 2    │   │  Phase 3    │   │  Phase 4    │      │
│  │ アウトライン │──▶│アウトライン │──▶│  前半生成   │──▶│  後半生成   │      │
│  │ 並列生成    │   │   選択      │   │             │   │  並列生成   │      │
│  └─────────────┘   └─────────────┘   └──────┬──────┘   └─────────────┘      │
│        │                │                   │                │              │
│        │                │           ┌──────▼──────┐          │              │
│        │                │           │ロールバック  │          │              │
│        │                │           │ポイント #1  │          │              │
│        │                │           └──────┬──────┘          │              │
│        │                │                  │                 │              │
│        ▼                ▼                  ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      ParallelWorldState                              │    │
│  │  ┌───────────────┬──────────────────┬──────────────────────────┐   │    │
│  │  │ theme         │ outline_sessions │ first_half_session       │   │    │
│  │  │ language      │ selected_outline │ second_half_sessions     │   │    │
│  │  │ model         │ _session_id      │ reviewed_sessions        │   │    │
│  │  │ num_variants  │                  │ final_selected_session_id│   │    │
│  │  │               │                  │ human_approved           │   │    │
│  │  └───────────────┴──────────────────┴──────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│        │                │                  │                 │              │
│        ▼                ▼                  ▼                 ▼              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │  Phase 5    │   │  Phase 6    │   │  Phase 7    │   │  Phase 8    │      │
│  │  記事評価   │──▶│  記事選択   │──▶│  承認判定   │──▶│  再生成     │      │
│  │ LLM-as-Judge│   │             │   │             │   │(拒否時のみ) │      │
│  └─────────────┘   └─────────────┘   └──────┬──────┘   └─────────────┘      │
│                                             │                                │
│                                     ┌──────▼──────┐                         │
│                                     │ロールバック  │                         │
│                                     │ポイント #2  │                         │
│                                     └──────┬──────┘                         │
│                                            │                                │
│                                     ┌──────▼──────┐                         │
│                                     │  Phase 9    │                         │
│                                     │  保存処理   │                         │
│                                     └─────────────┘                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                              モジュール構成                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   main.py                                                                    │
│      │                                                                       │
│      ▼                                                                       │
│   runner_service.py ◄──────────── generation_service.py                     │
│      │                                    │                                  │
│      ├── get_current_phase()              ├── generate_outline()            │
│      ├── forget_phases_after()            ├── generate_first_half()         │
│      ├── run_parallel_world_*()           ├── generate_second_half()        │
│      │                                    ├── review_article()              │
│      ▼                                    │                                  │
│   helper.py                               ▼                                  │
│      │                            llm_client.py                              │
│      ├── display_outlines()              │                                   │
│      ├── get_rollback_choice()           └── google_genai_client            │
│      ├── save_article_files()                                                │
│      │                                                                       │
│      ▼                                                                       │
│   model.py                                                                   │
│      │                                                                       │
│      ├── ParallelWorldState (TypedDict)                                     │
│      ├── ParallelSession (Pydantic)                                         │
│      ├── ArticleOutline (Pydantic)                                          │
│      ├── ArticleReview (Pydantic)                                           │
│      └── CompletedArticle (Pydantic)                                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - `click>=8.3.0`: CLIフレームワーク
  - `google-genai>=1.45.0`: Google Gemini連携
  - `pydantic>=2.12.2`: データバリデーション
  - `python-dotenv>=1.1.1`: 環境変数管理

### セットアップ

1. 環境変数ファイルを作成:

```bash
cp .envrc.example .envrc
```

2. APIキーを設定:

```bash
# .envrc
export GEMINI_API_KEY="your-gemini-api-key-here"
```

3. 依存関係をインストール:

```bash
uv sync
```

### 使用方法

**インタラクティブモード（ロールバック可能）**:

```bash
uv run python -m src.main \
  --theme "AIの未来" \
  --language ja \
  --model gemini-2.5-flash
```

**自動選択モード（ユーザー入力なし）**:

```bash
uv run python -m src.main \
  --theme "量子コンピューティング入門" \
  --language ja \
  --model gemini-2.5-flash \
  --auto-select
```

**カスタムバリアント数を指定**:

```bash
uv run python -m src.main \
  --theme "宇宙探査の最前線" \
  --language ja \
  --model gemini-2.5-pro \
  --num-outline-variants 5 \
  --num-second-half-variants 5
```

### CLIオプション

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|--------|------|-----------|------|
| `--theme` | `-t` | Yes | - | 記事のテーマ/トピック |
| `--language` | `-l` | Yes | - | 言語（`en`: 英語, `ja`: 日本語） |
| `--model` | `-m` | Yes | - | 使用モデル（`gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`） |
| `--output-directory` | `-od` | No | `outputs` | 出力ディレクトリ |
| `--num-outline-variants` | `-no` | No | `3` | アウトラインバリアント数 |
| `--num-second-half-variants` | `-ns` | No | `3` | 後半バリアント数 |
| `--auto-select` | `-a` | No | `False` | 自動選択モード |

### 出力例

```
╔════════════════════════════════════════════════════════════════════════════╗
║         Parallel World Article Generation - Human-in-the-Loop             ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: AIの未来
  Language: ja
  LLM Provider: gemini
  Model: gemini-2.5-flash
  Outline Variants: 3
  Second Half Variants: 3
  Mode: Interactive

📍 Current phase: 0 - Initial State

================================================================================

🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)
Creating 3 different article outlines in parallel...
✅ Generated 3 outline variants

================================================================================

👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline

[Variant 1]
Title: AIの未来：人類との共存と進化
Summary: 本記事では、AIの発展が人類社会にもたらす影響と...
Structure:
  1. はじめに
  2. AI技術の現状
  3. 社会への影響
  ...

Select an outline (1-3): 1
✅ Selected: AIの未来：人類との共存と進化

================================================================================

📝 PHASE 3: Generating First Half of Article
✅ Generated first half (1234 characters)

🔄 Rollback Option Available
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 0: Initial State
  2. Rollback to Phase 1: Outline Generation Complete
  3. Rollback to Phase 2: Outline Selected

Select phase to rollback to (0-3, 0=continue): 0

...

✅ Article Generation Complete!

Selected Article Details:
  Title: AIの未来：人類との共存と進化
  Grade: 4/5
  Total Length: 2456 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_abc123/parallel_world_article_abc123.json
  📝 Markdown: outputs/parallel_world_article_abc123/parallel_world_article_abc123.md

🎉 Parallel World Article Generation Complete!
```

### 出力ファイル

```
outputs/
└── parallel_world_article_{session_id}/
    ├── parallel_world_article_{session_id}.json  # 選択記事（JSON）
    ├── parallel_world_article_{session_id}.md    # 選択記事（Markdown）
    └── all_variants/
        ├── variant_1_grade_5.md
        ├── variant_2_grade_4.md
        └── variant_3_grade_3.md
```

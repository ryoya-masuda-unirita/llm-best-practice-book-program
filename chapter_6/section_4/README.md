# Chapter 6 Section 4: 不要な過去を忘れる - 状態ベースロールバックパターン

## 概要

本プロジェクトは、LLMアプリケーションにおける**「不要な過去を忘れる」パターン**を、状態ベースのロールバック機構を通じて実装しています。ユーザーは複数フェーズにまたがるパイプラインの任意の過去フェーズにロールバックでき、汚染されたコンテキストを「忘れ」、新鮮な状態からコンテンツを再生成できます。

このパターンは、LLMの生成結果が期待通りでない場合に、単純に再試行するのではなく、特定のフェーズまで状態を巻き戻して再生成することで、より高品質な結果を得ることを目的としています。状態変数の有無でフェーズの完了を判定し、ロールバック時には後続フェーズの状態変数を削除することで、シンプルかつ堅牢なロールバック機能を実現しています。

本実装は**並列世界記事生成パイプライン**として構築されており、以下の特徴を備えています：
- 複数のコンテンツバリアントを並列生成
- LLM-as-a-Judge による自動品質評価
- Human-in-the-Loop による意思決定ポイントとロールバック機能

## 機能

- **並列バリアント生成**: `asyncio.gather()` を使用して複数のアウトライン・記事後半を同時生成
- **状態ベースのフェーズ管理**: TypedDictの状態変数の有無でフェーズ完了を判定
- **柔軟なロールバック機構**: 任意のフェーズへのロールバックが可能
- **LLM-as-a-Judge**: 5段階評価による自動品質評価
- **Human-in-the-Loop**: 重要な意思決定ポイントでのユーザー介入
- **フィードバックループ**: 却下時に前回のフィードバックを活用した再生成
- **Pydantic構造化出力**: 型安全なJSON出力の保証

## プロジェクト構成

### ディレクトリ構成

```
chapter_6/section_4/
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # Geminiクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # 状態・データモデル (Pydantic)
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # 全フェーズのシステムプロンプト
│   ├── service/
│   │   ├── __init__.py
│   │   ├── generation_service.py # LLM生成ロジック
│   │   ├── runner_service.py     # パイプライン制御とロールバック
│   │   └── helper.py             # UIヘルパーとファイルI/O
│   ├── __init__.py
│   ├── config.py                 # 環境設定
│   ├── logger.py                 # ログ設定
│   └── main.py                   # CLIエントリポイント
├── outputs/                       # 生成記事 (自動作成)
├── .envrc.example                 # 環境変数テンプレート
├── pyproject.toml                 # プロジェクト依存関係
├── Makefile                       # 開発コマンド
└── README.md                      # 本ドキュメント
```

### アーキテクチャ

```
+-------------+     +-------------+     +-------------+     +-------------+
|  Phase 1    |     |  Phase 2    |     |  Phase 3    |     |  Phase 4    |
|  アウトライン|---->|  アウトライン|---->|  前半       |---->|  後半       |
|  生成       |     |  選択       |     |  生成       |     |  生成       |
+-------------+     +-------------+     +------+------+     +-------------+
                                               |                   |
                                               v                   |
                                        +-----------+              |
                                        | ロールバック|              |
                                        | ポイント #1|              |
                                        +-----------+              |
                                                                   v
+-------------+     +-------------+     +-------------+     +-------------+
|  Phase 9    |     |  Phase 7    |     |  Phase 6    |     |  Phase 5    |
|  記事       |<----|  承認       |<----|  記事       |<----|  レビュー   |
|  保存       |     |  判断       |     |  選択       |     |  (LLM Judge)|
+-------------+     +------+------+     +-------------+     +-------------+
                           |
                           v
                    +-----------+
                    | ロールバック|
                    | ポイント #2|
                    +-----------+
                           |
                           v (却下時)
                    +-------------+
                    |  Phase 8    |
                    | フィードバック|
                    | 付き再生成  |
                    +-------------+
```

### 設計原則

**ポイント**: 本実装の核心となる4つの設計原則

1. **状態としてのメモリ**: 状態オブジェクトがパイプラインのメモリとして機能。状態変数の存在/不在がフェーズ完了を示す
2. **削除による忘却**: ロールバック時に後続フェーズの状態変数を削除し、再生成をトリガー
3. **冪等なフェーズ**: 各フェーズは実行前に完了チェックを行い、任意のポイントからの再開を可能に
4. **Human-in-the-Loop**: 重要な意思決定ポイントでユーザーが進捗を確認しロールバック可能

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - `click>=8.3.0`: CLIフレームワーク
  - `google-genai>=1.45.0`: Google Gemini統合
  - `openai>=2.4.0`: OpenAI API (予備)
  - `pydantic>=2.12.2`: データバリデーションと構造化出力
  - `python-dotenv>=1.1.1`: 環境設定

- **開発用依存ライブラリ**:
  - `pytest>=8.4.2`: テストフレームワーク
  - `pytest-asyncio>=1.2.0`: 非同期テストサポート
  - `pytest-mock>=3.15.1`: モックユーティリティ

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

### 使用方法、実行方法

**インタラクティブモード** (ロールバックオプション付き):
```bash
uv run python -m src.main \
  --theme "AIの未来" \
  --language ja \
  --model gemini-2.5-flash
```

**自動選択モード** (ユーザー操作なし):
```bash
uv run python -m src.main \
  --theme "量子コンピューティング" \
  --language ja \
  --model gemini-2.5-flash \
  --auto-select
```

**カスタムバリアント数を指定**:
```bash
uv run python -m src.main \
  --theme "宇宙探査" \
  --language ja \
  --model gemini-2.5-pro \
  --num-outline-variants 5 \
  --num-second-half-variants 5
```

### CLIオプション

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|--------|-------|----------|---------|-------------|
| `--theme` | `-t` | Yes | - | 記事のテーマ |
| `--language` | `-l` | Yes | - | 言語 (`en` または `ja`) |
| `--model` | `-m` | Yes | - | Geminiモデル名 |
| `--output-directory` | `-od` | No | `outputs` | 出力ディレクトリ |
| `--num-outline-variants` | `-no` | No | `3` | アウトラインバリアント数 |
| `--num-second-half-variants` | `-ns` | No | `3` | 後半バリアント数 |
| `--auto-select` | `-a` | No | `False` | 自動選択モードフラグ |

**利用可能なモデル**:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

### 出力例

実行が完了すると、以下のような出力が得られます：

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
Reason: このアウトラインは...
Title: AIが変える2030年の社会
Summary: 人工知能技術の急速な発展が...
Structure:
  1. はじめに
  2. AI技術の現状
  3. 産業への影響
  ...

Select an outline (1-3): 1
✅ Selected: AIが変える2030年の社会

...

✅ Article Generation Complete!

Selected Article Details:
  Title: AIが変える2030年の社会
  Grade: 5/5
  Total Length: 2847 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_abc123/parallel_world_article_abc123.json
  📝 Markdown: outputs/parallel_world_article_abc123/parallel_world_article_abc123.md

📁 All variants saved to: outputs/parallel_world_article_abc123/all_variants

================================================================================
🎉 Parallel World Article Generation Complete!
```

### 出力ファイル構成

```
outputs/
└── parallel_world_article_{session_id}/
    ├── parallel_world_article_{session_id}.json
    ├── parallel_world_article_{session_id}.md
    └── all_variants/
        ├── variant_1_grade_5.md
        ├── variant_2_grade_4.md
        └── variant_3_grade_3.md
```

## 開発コマンド

```bash
# Lintとフォーマット
make fix

# Lintのみ
make lint

# フォーマットのみ
make fmt

# 型チェック
make mypy
```

## キーポイント

1. **状態ベースのロールバック**が複雑なチェックポイント管理を不要にする
2. **削除による忘却**がコンテキスト汚染を防止する
3. **フェーズ検出**により任意のポイントからの再開が可能
4. **Human-in-the-Loop**が重要な決定ポイントで品質を向上させる
5. **並列世界パターン**がより良い選択のためのバリアントを生成する
6. **LLM-as-a-Judge**が一貫した品質評価を自動化する
7. **フィードバックループ**が反復的な改善を可能にする
8. **型安全な構造化出力**が信頼性を確保する

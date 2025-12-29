# Chapter 6 Section 5: Parallel World パターンによる記事生成システム

## 概要

このプロジェクトは、**Parallel World（パラレルワールド）パターン**を活用した AI エージェント記事生成システムを実装しています。複数の並列 LLM セッション、Human-in-the-Loop（人間参加型）意思決定、および LLM-as-a-Judge（LLM 審査員）評価を組み合わせることで、高品質な記事コンテンツを生成します。

Parallel World パターンとは、AI エージェントシステムにおけるワークフロー技法の一つで、複数の異なる実行パス（並行世界）を同時に生成し、その中から最適な結果を選択する手法です。このアプローチにより、コンテンツの多様性を確保しながら、重要な意思決定ポイントでの戦略的な人間介入を通じて品質と制御性を維持できます。

本システムでは「Stable Core and Flexible Extensions」アーキテクチャパターンを採用し、再利用可能なエージェントコアと記事生成に特化した拡張機能を分離しています。

## 機能

- **Parallel World 記事生成**: 複数の記事バリエーションを同時並列で生成
- **Human-in-the-Loop**: 重要な意思決定ポイントでのユーザー介入
- **LLM-as-a-Judge**: 自動化された記事品質評価とレビュー
- **フィードバックループ**: 拒否された記事のフィードバックに基づく再生成
- **バイリンガル対応**: 英語または日本語での記事生成をサポート
- **状態管理**: Memento パターンによるフェーズベースの状態管理とロールバック機能

## プロジェクト構成

### ディレクトリ構成

```
chapter_6/section_5/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー）
│   ├── logger.py                # ログ設定
│   ├── main.py                  # メインエントリーポイント（CLI コマンド）
│   ├── agent/                   # AI エージェントフレームワーク
│   │   ├── __init__.py          # 公開 API のエクスポート
│   │   ├── core/                # 安定したコア抽象化
│   │   │   ├── base.py          # Tool, Strategy, Action, ToolResult
│   │   │   ├── states.py        # AgentState, AgentContext, AgentStatus
│   │   │   ├── memory.py        # Memory, MemorySnapshot
│   │   │   ├── toolbox.py       # ToolBox (Composite パターン)
│   │   │   ├── controller.py    # ExecutionHandler, ExecutionController
│   │   │   ├── mediator.py      # GraphMediator, Node, Edge
│   │   │   └── agent.py         # BaseAgent
│   │   └── extensions/          # 柔軟な実装
│   │       ├── tools/
│   │       │   └── generation.py  # 記事パイプライン用 LLM 生成ツール
│   │       ├── nodes/
│   │       │   └── pipeline.py    # 各生成フェーズのパイプラインノード
│   │       ├── memory/
│   │       │   └── pipeline.py    # フェーズベースのロールバック機能付きメモリ
│   │       └── mediators/
│   │           └── article_pipeline.py  # ArticlePipelineMediator
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLM クライアント初期化（Gemini）
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydantic データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── helper.py            # UI 表示およびファイル保存ヘルパー
│       └── runner_service.py    # エージェントパイプラインへのラッパー
├── outputs/                     # 生成結果（自動作成）
│   └── parallel_world_article_<uuid>/
│       ├── parallel_world_article_<uuid>.json  # 選択された記事（JSON）
│       ├── parallel_world_article_<uuid>.md    # 選択された記事（Markdown）
│       └── all_variants/        # 全候補バリアント
│           ├── variant_1_grade_5.md
│           ├── variant_2_grade_4.md
│           └── variant_3_grade_3.md
├── pyproject.toml               # プロジェクト依存関係
├── Makefile                     # 開発コマンド
├── .envrc.example               # 環境変数サンプル
├── CLAUDE.md                    # Claude Code 用プロジェクト指示書
└── README.md                    # このファイル
```

### アーキテクチャ

```
+------------------------------------------------------------------------------+
|                           CLI Layer (main.py)                                |
|   - コマンドライン引数パース                                                   |
|   - ユーザー入力とインタラクション                                              |
|   - 出力ディレクトリ管理                                                       |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------------------+
|                 Service Layer (runner_service.py)                            |
|   - エージェントパイプラインへの委譲                                            |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+----------------------------------+-------------------------------------------+
|             AI Agent Pipeline Layer (agent/extensions/)                      |
|   - ArticlePipelineMediator: ワークフローオーケストレーション                    |
|   - Pipeline Nodes: Outline, FirstHalf, SecondHalf, Review, Regeneration     |
|   - Generation Tools: LLM 生成関数                                            |
|   - PipelineMemory: フェーズベースの状態管理 (Memento パターン)                  |
+----------------------------------+-------------------------------------------+
                                   |
                                   v
+------------------------------------------------------------------------------+
|                         Infrastructure Layer                                 |
|   - LLM クライアント (llm_client.py)                                          |
|   - プロンプト生成 (prompt.py)                                                 |
|   - データモデル (model.py)                                                    |
|   - 設定 (config.py)                                                          |
|   - ロギング (logger.py)                                                      |
+------------------------------------------------------------------------------+
```

### ワークフローフェーズ

システムは 9 フェーズのパイプラインをオーケストレーションします：

```
START
  |
  v
Phase 1: 複数アウトライン生成 (Parallel World 分岐 #1)
  |
  v
Phase 2: ユーザーがアウトライン選択 (Human-in-the-Loop #1)
  |
  v
Phase 3: 記事前半を生成
  |
  v
Phase 4: 複数の記事後半を生成 (Parallel World 分岐 #2)
  |
  v
Phase 5: LLM-as-a-Judge で全記事をレビュー
  |
  v
Phase 6: ユーザーが最終記事を選択 (Human-in-the-Loop #2)
  |
  v
Phase 7: ユーザーが承認または拒否 (Human-in-the-Loop #3)
  |
  +--[承認]--> Phase 9: 記事を保存 --> END
  |
  +--[拒否]--> Phase 8: フィードバックに基づき再生成 --> Phase 5 へループ
```

## 実装の詳細

### データモデル (src/model/model.py)

| モデル | 説明 |
|-------|------|
| `ArticleOutline` | タイトル、要約、セクション構造を含む記事アウトライン |
| `ArticleHalf` | 記事の前半または後半のコンテンツ |
| `BestArticleSelection` | 最適なバリアントを選択した結果 |
| `ArticleReview` | LLM-as-a-Judge による評価とフィードバック |
| `CompletedArticle` | 全コンポーネントを含む完成記事 |
| `ParallelSession` | 単一のパラレルワールドセッション状態 |
| `ParallelWorldState` | パイプライン全体の状態を表す TypedDict |

### エージェントコンポーネント (src/agent/)

エージェント層は「Stable Core and Flexible Extensions」アーキテクチャパターンに従っています。

**Generation Tools** (`src/agent/extensions/tools/generation.py`):
- `OutlineGeneratorTool` - 記事アウトラインを生成
- `FirstHalfGeneratorTool` - 記事前半を生成
- `BestFirstHalfSelectorTool` - 候補から最適な前半を選択
- `SecondHalfGeneratorTool` - 記事後半を生成
- `ArticleReviewerTool` - LLM-as-a-Judge で記事をレビュー
- `SecondHalfRegeneratorTool` - フィードバックに基づき再生成
- `GenerationToolBox` - 全生成ツールのコンテナ

**Pipeline Nodes** (`src/agent/extensions/nodes/pipeline.py`):
- `OutlineGenerationNode` - 並列アウトライン生成
- `FirstHalfGenerationNode` - 前半生成と選択
- `SecondHalfGenerationNode` - 並列後半生成
- `ArticleReviewNode` - 並列記事レビュー
- `SecondHalfRegenerationNode` - フィードバックベース再生成
- `HumanDecisionNode` - Human-in-the-Loop 意思決定ポイント

**Pipeline Memory** (`src/agent/extensions/memory/pipeline.py`):
- `PipelineState` - パイプライン状態のデータクラス
- `PipelineMemory` - フェーズベースのロールバック機能付きメモリ（Memento パターン）
- `PipelineMemoryCaretaker` - メモリスナップショットを管理

**Article Pipeline Mediator** (`src/agent/extensions/mediators/article_pipeline.py`):
- `ArticlePipelineMediator` - パイプライン全体をオーケストレーション
- `run_article_pipeline()` - パイプライン実行のメインエントリーポイント

### Parallel World パターンの実装ポイント

**分岐ポイント**:

Phase 1 および Phase 4 では、`asyncio.gather()` を使用して N 個のバリアントを並列生成します：

```python
# src/agent/extensions/nodes/pipeline.py より
tasks = [
    self.toolbox.outline_generator.execute_async(
        state.theme,
        state.language,
        state.model,
        state.llm_provider,
    )
    for _ in range(state.num_outline_variants)
]
outlines = await asyncio.gather(*tasks)
```

**選択ポイント**:
- Phase 2: ユーザーが好みのアウトラインを選択
- Phase 6: ユーザーがレビュー済み候補から最終記事を選択

**フィードバックループ**:
- Phase 7-8: 拒否された場合、レビューからフィードバックを収集して再生成

### LLM-as-a-Judge 評価基準

| 基準 | 重み | 説明 |
|------|------|------|
| コンテンツ品質 | 30% | 正確性、情報量、価値 |
| 構造と流れ | 25% | アウトラインへの準拠、論理的な流れ |
| 文章品質 | 20% | 明確さ、読みやすさ、技巧 |
| 完成度 | 15% | テーマとセクションの網羅性 |
| 言語品質 | 10% | 適切さ、一貫性 |

**評価スケール**:
- 5 (Excellent): 全ての基準で期待を超える優れた記事
- 4 (Good): 軽微な改善点がある高品質な記事
- 3 (Acceptable): 顕著なギャップがある適切な記事
- 2 (Poor): 重大な問題がある記事
- 1 (Very Poor): 基本的な品質基準を満たさない記事

### 自動選択モードの動作

`--auto-select` が有効な場合:
- Phase 2: 最初のアウトラインバリアントを自動選択
- Phase 6: 最高評価の記事を自動選択
- Phase 7: グレード >= 4 なら自動承認、それ以外は自動拒否

### 状態管理（Memento パターン）

パイプラインは Memento パターンを使用して状態管理とロールバック機能を実装:
- `PipelineState` データクラスが全パイプライン状態を保持
- `PipelineMemory` がフェーズベースのロールバックで状態を管理
- `PipelineMemoryCaretaker` が各フェーズ完了時にスナップショットを保存
- エラー状態は `state.error` で追跡
- 無限ループ防止のため、レビューループは最大 5 回まで

## 使い方

### 環境構成

- **Python**: 3.13.2 以上
- **依存ライブラリ**:

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| click | >=8.3.0 | CLI フレームワーク |
| google-genai | >=1.45.0 | Google Gemini API クライアント |
| openai | >=2.4.0 | OpenAI API クライアント |
| pydantic | >=2.12.2 | データバリデーションとモデル |
| python-dotenv | >=1.1.1 | 環境変数読み込み |

### セットアップ

1. **環境変数ファイルの作成**

```bash
cat > .envrc << EOF
export GEMINI_API_KEY="your-gemini-api-key-here"
EOF

# direnv を使用する場合
direnv allow

# または手動でエクスポート
source .envrc
```

2. **依存関係のインストール**

```bash
# uv を使用（推奨）
uv sync

# pip を使用
pip install -e .
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# 英語記事の生成
uv run python -m src.main \
  --theme "The Future of Artificial Intelligence" \
  --language en \
  --model gemini-2.5-flash

# 日本語記事の生成
uv run python -m src.main \
  --theme "人工知能の未来" \
  --language ja \
  --model gemini-2.5-flash
```

#### 詳細設定

```bash
uv run python -m src.main \
  -t "量子コンピューティングの革新" \
  -l ja \
  -m gemini-2.5-pro \
  -od ./my_articles \
  -no 5 \
  -ns 4
```

#### 自動モード（人間介入なし）

```bash
uv run python -m src.main \
  -t "気候変動への解決策" \
  -l ja \
  -m gemini-2.5-flash \
  -a
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

### CLI オプション

| オプション | 短縮形 | 型 | デフォルト | 説明 |
|-----------|--------|-----|----------|------|
| `--theme` | `-t` | TEXT | 必須 | 記事のテーマ/トピック |
| `--language` | `-l` | en/ja | 必須 | 記事の言語 |
| `--model` | `-m` | Choice | 必須 | 使用する Gemini モデル |
| `--output-directory` | `-od` | PATH | outputs | 出力ディレクトリ |
| `--num-outline-variants` | `-no` | INT | 3 | アウトラインバリアント数 |
| `--num-second-half-variants` | `-ns` | INT | 3 | 後半バリアント数 |
| `--auto-select` | `-a` | FLAG | False | 人間介入なしで自動選択 |

**利用可能なモデル**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite

### 出力例

実行すると以下のような出力が表示されます：

```
╔════════════════════════════════════════════════════════════════════════════╗
║         Parallel World Article Generation - Human-in-the-Loop             ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: 人工知能の未来
  Language: ja
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
Title: 人工知能が切り開く未来
Summary: 本記事では...
Structure:
  1. はじめに
  2. AI の現状と課題
  3. 技術革新の方向性
  ...

Select an outline (1-3): 1
✅ Selected: 人工知能が切り開く未来

================================================================================

📝 PHASE 3: Generating First Half of Article
✅ Generated first half (1234 characters)

================================================================================

🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)
Creating 3 different endings in parallel...
✅ Generated 3 second half variants

================================================================================

⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge
✅ Reviewed 3 complete articles

================================================================================

👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article (Iteration 1)

[Article Variant 1] - Grade: 5/5
Reasoning: この記事は...
Strengths:
  ✓ 論理的な構成
  ✓ 専門用語の適切な説明
Weaknesses:
  ✗ 具体例がやや少ない

Select final article (1-3): 1

================================================================================

✅ PHASE 7: Human-in-the-Loop - Approve or Reject Article
📝 Selected Article Preview:
Title: 人工知能が切り開く未来
Grade: 5/5

✅ Do you approve this article? (yes/no): yes

✅ Article approved! Proceeding to save...

================================================================================

💾 Saving Final Article

✅ Article Generation Complete!

Selected Article Details:
  Title: 人工知能が切り開く未来
  Grade: 5/5
  Total Length: 2456 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_xxxxx/parallel_world_article_xxxxx.json
  📝 Markdown: outputs/parallel_world_article_xxxxx/parallel_world_article_xxxxx.md

📁 All variants saved to: outputs/parallel_world_article_xxxxx/all_variants

================================================================================
🎉 Parallel World Article Generation Complete!
```

### 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `GEMINI_API_KEY` | Yes | Google Gemini API キー |
| `LOG_LEVEL` | No | ログレベル（デフォルト: DEBUG） |

### 出力ファイル

各生成は一意のディレクトリを作成:
- `parallel_world_article_<uuid>.json` - 完全な記事データ
- `parallel_world_article_<uuid>.md` - Markdown 形式の記事
- `all_variants/` - 比較用の全候補バリアント

## 開発コマンド

```bash
# CLI を実行
uv run python -m src.main --help

# テストを実行
uv run pytest

# 依存関係を同期
uv sync

# 開発用依存関係をインストール
uv sync --group dev

# リント
make lint

# フォーマット
make fmt

# リント + フォーマット
make fix

# 型チェック
make mypy
```

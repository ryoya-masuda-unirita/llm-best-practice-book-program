# Chapter 6 Section 4: 不要な過去を忘れる - 状態ベースロールバックパターン

## 概要

本プロジェクトは、LLMアプリケーションにおける**「不要な過去を忘れる」パターン**を、状態ベースのロールバック機構を通じて実証します。ユーザーはマルチステップパイプラインの任意の過去フェーズにロールバックでき、汚染されたコンテキストを効果的に「忘却」して、フレッシュな状態からコンテンツを再生成できます。

このパターンは、LLMの文脈汚染問題に対処します。一度生成された低品質なコンテンツがコンテキストに残ると、その後の生成品質に悪影響を与える可能性があります。状態変数を削除することで「忘却」を実現し、過去の失敗した試行の影響を受けずに再生成を行えます。

実装は記事生成パイプラインで、以下の特徴を持ちます：

- **段階的コンテンツ生成**：アウトライン → 前半 → 後半の順に生成
- **LLM-as-a-Judge**：LLMによる自動品質評価（1-5段階の評価スケール）
- **Human-in-the-Loop**：人間による承認/却下とロールバック機能
- **Mementoパターン**：状態スナップショット管理による確実なロールバック

## 機能

- **状態ベースロールバック**: 任意のフェーズにロールバックし、以降のフェーズを再生成
- **自動品質評価**: LLM-as-a-Judgeによる5段階評価と詳細なフィードバック
- **フィードバックループ**: 却下時は前回のフィードバックを基に改善された再生成
- **インタラクティブモード**: 各決定ポイントでユーザー入力を受け付け
- **自動選択モード**: 評価4以上で自動承認する非対話型実行
- **構造化出力**: Pydanticモデルによる型安全なJSON出力

## プロジェクト構成

### ディレクトリ構成

```
chapter_6/section_4/
├── src/
│   ├── agent/
│   │   ├── core/                    # コア抽象クラス（安定したインターフェース）
│   │   │   ├── base.py              # Tool, Strategy, Action, ToolResult
│   │   │   ├── memory.py            # Memory抽象クラス, MemorySnapshot
│   │   │   ├── mediator.py          # Node基底クラス, NodeResult, NodeType
│   │   │   └── toolbox.py           # Toolbox基底クラス
│   │   └── extensions/              # 具象実装
│   │       ├── mediators/
│   │       │   └── article_pipeline.py  # ArticlePipelineMediator
│   │       ├── memory/
│   │       │   └── pipeline.py          # PipelineMemory, PipelineMemoryCaretaker
│   │       ├── nodes/
│   │       │   └── pipeline.py          # PipelineState, 各種生成ノード
│   │       └── tools/
│   │           └── generation.py        # LLM生成ツール群
│   ├── client/
│   │   └── llm_client.py            # Geminiクライアント, LLMProvider
│   ├── model/
│   │   └── model.py                 # Pydanticモデル（ArticleOutline等）
│   ├── prompt/
│   │   └── prompt.py                # 各フェーズ用システムプロンプト
│   ├── service/
│   │   ├── runner_service.py        # パイプラインエントリーポイント
│   │   └── helper.py                # UIヘルパー、ファイルI/O
│   ├── config.py                    # 環境設定
│   └── main.py                      # CLIエントリーポイント
├── outputs/                         # 生成された記事（自動作成）
├── .envrc.example                   # 環境変数テンプレート
├── pyproject.toml                   # プロジェクト依存関係
└── Makefile                         # 開発コマンド
```

### アーキテクチャ

#### パイプラインフロー

```
+-------------+     +-------------+     +-------------+     +-------------+
|  Phase 1    |     |  Phase 2    |     |  Phase 3    |     |  Phase 4    |
|  アウトライン |---->|  前半生成    |---->|  後半生成    |---->|  レビュー    |
|  生成       |     |             |     |             |     | (LLM Judge) |
+-------------+     +------+------+     +-------------+     +------+------+
                           |                                       |
                           v                                       v
                    +-----------+                           +-------------+
                    | Rollback  |                           |  Phase 5    |
                    | Point #1  |                           |  承認判定    |
                    +-----------+                           +------+------+
                                                                   |
                                                            +-----------+
                                                            | Rollback  |
                                                            | Point #2  |
                                                            +-----------+
                                                                   |
                                                                   v (却下時)
                                                            +-------------+
                                                            | フィードバック |
                                                            | 基づく再生成  |
                                                            +-------------+
```

#### エージェントアーキテクチャ

```
+----------------------+
|      Mediator        |  パイプライン統制
| (ArticlePipeline     |
|      Mediator)       |
+----------+-----------+
           |
    +------+------+------+------+------+
    |      |      |      |      |      |
    v      v      v      v      v      v
+------+ +------+ +------+ +------+ +------+
| Node | | Node | | Node | | Node | | Node |
|Outln | |First | |Second| |Review| |Regen |
| Gen  | |Half  | |Half  | |      | |      |
+--+---+ +--+---+ +--+---+ +--+---+ +--+---+
   |        |        |        |        |
   v        v        v        v        v
+--------------------------------------------------+
|              GenerationToolBox                   |
+--------------------------------------------------+
| OutlineGenerator    | FirstHalfGenerator         |
| SecondHalfGenerator | ArticleReviewer            |
| SecondHalfRegenerator                            |
+--------------------------------------------------+
                      |
                      v
              +---------------+
              |  Gemini API   |
              +---------------+
```

#### Mementoパターンによる状態管理

```
+-------------------+        +--------------------+
|    Originator     |        |     Caretaker      |
| (PipelineMemory)  |<------>| (MemoryCaretaker)  |
+---------+---------+        +--------------------+
          |                            |
          v                            v
     +---------+                 +-----------+
     |  State  |                 | Snapshots |
     +---------+                 +-----------+
          |                      | Phase 0   |
          |                      | Phase 1   |
     状態変数の                   | Phase 2   |
     有無が完了を示す              | ...       |
                                 +-----------+
```

### 設計原則

**ポイント**: 本実装の核心となる4つの設計原則

1. **状態としてのメモリ**: 状態オブジェクトがパイプラインのメモリとして機能。状態変数の存在/不在がフェーズ完了を示す
2. **削除による忘却**: ロールバック時に後続フェーズの状態変数を削除し、再生成をトリガー
3. **冪等なフェーズ**: 各フェーズは実行前に完了チェックを行い、任意のポイントからの再開を可能に
4. **Human-in-the-Loop**: 重要な意思決定ポイントでユーザーが進捗を確認しロールバック可能

## 主要コンポーネント

### PipelineState（状態モデル）

```python
@dataclass
class PipelineState:
    """State passed through pipeline nodes."""

    theme: str
    language: Literal["en", "ja"]
    llm_provider: LLMProvider
    model: str

    # Phase 1: アウトライン生成
    outline: ArticleOutline | None = None

    # Phase 2: 前半生成
    first_half: str | None = None

    # Phase 3: 後半生成
    second_half: str | None = None

    # Phase 4: レビュー
    review: ArticleReview | None = None

    # Phase 5: 人間による承認
    human_approved: bool | None = None

    # 再生成追跡
    review_loop_iteration: int = 0
    previous_feedback: list[tuple[str, ArticleReview]] | None = None

    # エラー追跡
    error: str | None = None
```

### フェーズ検出

**ポイント**: 状態変数のチェックにより現在のフェーズを判定します。

```python
def get_current_phase(self) -> int:
    if self._state.human_approved is not None:
        return 5
    elif self._state.review is not None:
        return 4
    elif self._state.second_half is not None:
        return 3
    elif self._state.first_half is not None:
        return 2
    elif self._state.outline is not None:
        return 1
    else:
        return 0
```

### ロールバック実装（忘却機構）

**ポイント**: 対象フェーズ以降の状態変数を`None`に設定することで「忘却」を実現します。

```python
def forget_phases_after(self, target_phase: int) -> None:
    if target_phase < 5:
        self._state.human_approved = None
        self._state.review_loop_iteration = 0
        self._state.previous_feedback = None
    if target_phase < 4:
        self._state.review = None
    if target_phase < 3:
        self._state.second_half = None
    if target_phase < 2:
        self._state.first_half = None
    if target_phase < 1:
        self._state.outline = None
    self._state.error = None
```

### 生成ツール（GenerationToolBox）

- `OutlineGeneratorTool`: 記事アウトラインを生成
- `FirstHalfGeneratorTool`: 記事前半を生成
- `SecondHalfGeneratorTool`: 記事後半を生成
- `ArticleReviewerTool`: LLM-as-a-Judge評価
- `SecondHalfRegeneratorTool`: フィードバック付き後半再生成

### パイプラインノード

- `OutlineGenerationNode`: アウトライン生成
- `FirstHalfGenerationNode`: 前半生成
- `SecondHalfGenerationNode`: 後半生成
- `ArticleReviewNode`: LLM-as-a-Judgeレビュー
- `SecondHalfRegenerationNode`: フィードバック基づく再生成
- `HumanDecisionNode`: ユーザーインタラクション処理

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - `click>=8.3.0`: CLIフレームワーク
  - `google-genai>=1.45.0`: Google Gemini統合
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

### 使用方法

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
  --theme "Quantum Computing" \
  --language en \
  --model gemini-2.5-flash \
  --auto-select
```

### CLIオプション

```
Usage: python -m src.main [OPTIONS]

  Generate an article using state-based rollback pattern (forget the past).

Options:
  -t, --theme TEXT                Article theme/topic.  [required]
  -l, --language [en|ja]          Article language (en: English, ja:
                                  Japanese).  [required]
  -m, --model [gemini-2.5-pro|gemini-2.5-flash|gemini-2.5-flash-lite]
                                  The model to use (e.g., gemini-2.5-flash).
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -a, --auto-select               Automatically select best options without
                                  human interaction.
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|--------|------|-----------|------|
| `--theme` | `-t` | Yes | - | 記事のテーマ/トピック |
| `--language` | `-l` | Yes | - | 言語（`en`または`ja`） |
| `--model` | `-m` | Yes | - | Geminiモデル名 |
| `--output-directory` | `-od` | No | `outputs` | 出力ディレクトリ |
| `--auto-select` | `-a` | No | `False` | 自動選択モードフラグ |

**利用可能なモデル**:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

### 出力例

実行が完了すると、以下のような出力が得られます：

```
╔════════════════════════════════════════════════════════════════════════════╗
║       Article Generation with State-Based Rollback (Forget the Past)      ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: AIの未来
  Language: ja
  LLM Provider: gemini
  Model: gemini-2.5-flash
  Mode: Interactive

📍 Current phase: 0 - Initial State

================================================================================

📝 PHASE 1: Generating Article Outline
✅ Generated outline: AIの未来：技術革新と社会への影響

Summary: 人工知能（AI）は急速に進化し、私たちの生活や社会に大きな変革をもたらしています...

Structure:
  1. AIの現状と最新技術動向
  2. 産業への影響と自動化の進展
  3. 医療・教育分野での応用
  ...

================================================================================

📝 PHASE 2: Generating First Half of Article
✅ Generated first half (1523 characters)

Preview:
## はじめに

人工知能（AI）技術は、21世紀最も重要な技術革新の一つとして...

🔄 Rollback Option Available
You can go back to a previous phase if you want to try different choices.
This will 'forget' all subsequent phases and regenerate them.

Available phases:
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 1: Outline Generation Complete

Select phase to rollback to (0-1, 0=continue) [0]:

================================================================================

📝 PHASE 3: Generating Second Half of Article
✅ Generated second half (1456 characters)

================================================================================

⚖️  PHASE 4: Reviewing Article with LLM-as-a-Judge
✅ Review completed: Grade 4/5

Reasoning: 記事は全体的によく構成されており、AIの未来について包括的な視点を提供しています...

Strengths:
  ✓ テーマに沿った論理的な構成
  ✓ 具体的な事例の適切な使用
  ✓ 読みやすい文体と適切な段落分け

Weaknesses:
  ✗ 一部の技術用語の説明が不足
  ✗ 結論部分がやや急ぎ足

================================================================================

✅ PHASE 5: Human-in-the-Loop - Approve or Reject Article (Iteration 1)

📝 Article Preview:
Title: AIの未来：技術革新と社会への影響
Grade: 4/5
Review: 記事は全体的によく構成されており...

✅ Do you approve this article? (yes/no): yes

✅ Article approved! Proceeding to save...

🔄 Rollback Option Available
...

================================================================================

💾 Saving Final Article

✅ Article Generation Complete!

Article Details:
  Title: AIの未来：技術革新と社会への影響
  Grade: 4/5
  Total Length: 2979 characters
  Review Loop Iterations: 0

Files saved:
  📄 JSON: outputs/article_abc123/article_abc123.json
  📝 Markdown: outputs/article_abc123/article_abc123.md

Session Metadata:
  Session ID: abc123def456
  Created: 2025-01-15T10:30:00

================================================================================

🎉 Article Generation Complete!
```

### 出力ファイル構成

```
outputs/
└── article_{session_id}/
    ├── article_{session_id}.json    # 構造化データ（全メタデータ含む）
    └── article_{session_id}.md      # 人間可読なMarkdown形式
```

## LLM-as-a-Judge 評価基準

記事は以下の基準で1-5段階評価されます：

| 基準 | 重み | 説明 |
|------|------|------|
| Content Quality | 30% | 内容の正確性、情報価値 |
| Structure & Flow | 25% | アウトラインへの準拠、論理的な流れ |
| Writing Quality | 20% | 文章の明確さ、エンゲージメント |
| Completeness | 15% | テーマと全セクションの網羅性 |
| Language Quality | 10% | 言語の適切性、一貫性、正確性 |

| グレード | 評価 | 説明 |
|---------|------|------|
| 5 | Excellent | 全基準で期待を上回る傑出した記事 |
| 4 | Good | 軽微な改善点がある高品質な記事 |
| 3 | Acceptable | 目立つ弱点がある許容レベルの記事 |
| 2 | Poor | 価値を損なう重大な問題がある記事 |
| 1 | Very Poor | 基本的な品質基準を満たさない記事 |

自動選択モードでは、グレード4以上の記事が自動承認されます。

## フィードバックループ

記事が却下された場合、システムは以下を実行します：

1. 却下された後半とそのレビューを`previous_feedback`に保存
2. 前回の試行からのフィードバックを基に後半を再生成
3. 新しいコンテンツを再レビュー
4. 最大5回まで繰り返し（`max_iterations`）

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
5. **LLM-as-a-Judge**が一貫した品質評価を自動化する
6. **フィードバックループ**が反復的な改善を可能にする
7. **型安全な構造化出力**が信頼性を確保する
8. **Mementoパターン**による堅牢なスナップショット管理

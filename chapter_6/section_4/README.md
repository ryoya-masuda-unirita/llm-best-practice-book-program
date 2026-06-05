# Chapter 6 Section 4: 不要な過去を忘れ、やり直し、未来を作る

## 概要

本プロジェクトは、LLMアプリケーションにおける対話履歴管理の3つの課題を解決する**「忘れる（Forget）・やり直す（Replay）・未来を作る（Speculate）」**の3段階アプローチを、記事生成パイプラインを通じて実証するサンプル実装です。

Section 4の状態ベースロールバック（Forget）をベースに、2つの機構を新たに追加しています。

| 段階 | 名称 | 解決する課題 | 着想元 |
|------|------|-------------|--------|
| 1 | **忘れる（Forget）** | コンテキスト汚染による品質劣化 | Mementoパターン |
| 2 | **やり直す（Replay）** | ロールバック時の有効入力の消失 | データベースのWALリプレイ |
| 3 | **未来を作る（Speculate）** | 単一の未来しか見えない意思決定 | CPUの投機的実行（分岐予測） |

## 機能

- **チェックポイントとロールバック（Forget）**: 任意のフェーズに巻き戻し、以降の状態を破棄して再生成
- **ユーザー要件の収集とWAL記録（Replay）**: アウトライン確認後にユーザーが追加指示を入力でき、WAL（Write-Ahead Log）に記録される。ロールバック時に有効な指示を自動的に再適用し、手動再入力を不要にする
- **投機的並列世界実行（Speculate）**: N個のアウトライン候補から記事を並列に完成させ、最終結果のレビュー評価まで比較して選択できる
- **LLM-as-a-Judge**: 5段階の自動品質評価と詳細なフィードバック
- **フィードバックループ**: 記事却下時に過去のフィードバックを活用した後半の再生成（最大5回）
- **インタラクティブモード**: ロールバック、要件追加、記事承認の各決定ポイントで対話的に操作
- **自動選択モード**: 評価4以上で自動承認、投機的世界の最高評価を自動選択する非対話型実行

## アーキテクチャ

### パイプラインフロー

本パイプラインは5つのフェーズで構成され、各フェーズの区切りでチェックポイントを保存します。ロールバックポイントではForget + Replayが連動し、Phase 1では投機的実行（Speculate）が発動します。

```
Phase 1                Phase 2         Phase 3         Phase 4
アウトライン生成  ─────> 前半生成 ─────> 後半生成 ─────> レビュー
   │                     │                              │
   │ num_outlines>1      │                              v
   v                     v                          Phase 5
 Speculate            Rollback                      承認判定
 N個のアウトライン      + Replay                        │
 → 並列に記事完成      Point #1                        v
 → 結果比較で選択                                   Rollback
                                                    + Replay
                                                    Point #2
                                                        │
                                                        v (却下時)
                                                    フィードバック
                                                    基づく再生成
```

### 3段階の統合

```
+-------------------------------+
|       PipelineMediator        |  3段階統合オーケストレーション
| (Forget + Replay + Speculate) |
+------+--------+--------+-----+
       |        |        |
       v        v        v
  +--------+ +-------+ +----------------+
  |Pipeline| |Replay | |  World         |
  |Memory  | |Engine | |  Manager       |
  |(Forget)| |(WAL)  | | (Speculative)  |
  +--------+ +-------+ +----------------+
       |        |        |
       v        v        v
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
                      |
                      v
              +---------------+
              |  Gemini API   |
              +---------------+
```

### 状態管理: Memento + WAL

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
          |
          v
   +-------------+
   | Prompt WAL  |  ← ユーザー要件のログ
   +-------------+    ロールバック後のリプレイに使用
   | Entry 1     |
   | Entry 2     |
   +-------------+

+-------------------+
|  World Manager    |  投機的並列世界の管理
+-------------------+
| World A (outline1)|---> Phase 2-4 を並列実行
| World B (outline2)|---> Phase 2-4 を並列実行
| World C (outline3)|---> Phase 2-4 を並列実行
+-------------------+
         |
    ユーザーが1つ選択
    残りは破棄
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **主要な依存ライブラリ**:
  - `click>=8.3.0` : CLIフレームワーク
  - `google-genai>=1.45.0` : Google Gemini API統合
  - `pydantic>=2.12.2` : データバリデーションと構造化出力
  - `python-dotenv>=1.1.1` : 環境設定の読み込み
- **開発用依存ライブラリ**:
  - `ruff>=0.12.4` : リンター/フォーマッター
  - `mypy>=1.17.0` : 型チェック
  - `isort>=6.0.1` : インポート整理

### セットアップ

1. 環境変数ファイルを作成:

```bash
cp .envrc.example .envrc
```

2. APIキーを設定:

```bash
# .envrc
GEMINI_API_KEY=<your_gemini_api_key_here>
```

3. 依存関係をインストール:

```bash
uv sync --all-packages
```

### 実行方法

#### インタラクティブモード（基本）

ロールバック＋リプレイ機能付きで、対話しながら記事を生成します。アウトライン確認後に追加の指示（例：「具体的な事例を多く含めて」）を入力でき、ロールバック時にはその指示が自動的に再適用されます。

```bash
uv run python -m src.main \
  --theme "AIの未来" \
  --language ja \
  --model gemini-2.5-flash
```

#### 自動選択モード

ユーザー操作なし。LLM-as-a-Judgeの評価が4以上なら自動承認します。

```bash
uv run python -m src.main \
  --theme "Quantum Computing" \
  --language en \
  --model gemini-2.5-flash \
  --auto-select
```

#### 投機的実行モード

複数のアウトラインから記事を並列に完成させ、レビュー評価付きで比較して選べます。

```bash
uv run python -m src.main \
  --theme "気候変動の解決策" \
  --language ja \
  --model gemini-2.5-flash \
  --num-outlines 3
```

### CLIオプション

```
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Generate an article using the Forget, Replay, Speculate pattern.

Options:
  -t, --theme TEXT                Article theme/topic.  [required]
  -l, --language [en|ja]          Article language (en: English, ja:
                                  Japanese).  [required]
  -m, --model [gemini-2.5-pro|gemini-2.5-flash|gemini-2.5-flash-lite|gemini-3.5-flash|gemini-3.1-flash-lite]
                                  The model to use (e.g., gemini-2.5-flash).
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -a, --auto-select               Automatically select best options without
                                  human interaction.
  -n, --num-outlines INTEGER RANGE
                                  Number of outline candidates for speculative
                                  execution (1=no speculation, max 5).
                                  [1<=x<=5]
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|--------|------|-----------|------|
| `--theme` | `-t` | Yes | - | 記事のテーマ/トピック |
| `--language` | `-l` | Yes | - | 言語（`en`または`ja`） |
| `--model` | `-m` | Yes | - | Geminiモデル名 |
| `--output-directory` | `-od` | No | `outputs` | 出力ディレクトリ |
| `--auto-select` | `-a` | No | `False` | 自動選択モード |
| `--num-outlines` | `-n` | No | `1` | アウトライン候補数（1=投機なし、最大5） |

## 3段階パターンの詳細

### Stage 1: 忘れる（Forget）

対話の重要な区切りでチェックポイント（状態スナップショット）を保存し、コンテキスト汚染の発生時やユーザーの明示的な指示により、指定フェーズまでロールバックします。

**動作原理**: `PipelineState`の各フェーズに対応する状態変数（`outline`, `first_half`, `second_half`等）の有無でフェーズ完了を判定します。ロールバック時は対象フェーズ以降の状態変数を`None`に設定することで「忘却」を実現します。

```python
# PipelineMemory.forget_phases_after()
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

**ロールバックポイント**: Phase 2（前半生成後）と Phase 5（承認判定後）の2箇所。

### Stage 2: やり直す（Replay）

ロールバック後、ユーザーが過去に入力した有効な指示を自動的に再適用します。

**ユーザー要件の収集**: Phase 1（アウトライン生成）完了後、ユーザーは任意で追加指示を入力できます（例：「具体的な事例を多く含めて」「倫理面にも触れて」）。この指示は`PipelineState.user_requirements`に保存され、以降の前半・後半生成時にプロンプトの追加コンテキストとしてLLMに渡されます。

**WAL（Write-Ahead Log）**: すべてのユーザー入力は`PromptLog`に記録されます。ロールバック時に`ReplayFilter`が以下のルールで各入力を分類し、有効な指示のみを自動再適用します。

| 分類 | リプレイ判定 | 例 |
|------|------------|-----|
| `REQUIREMENT` | 再適用する | 「具体的な事例を多く含めて」 |
| `FEEDBACK` | スキップ | 「はい」「いいえ」 |
| `CONFIRMATION` | スキップ | 「承認」「却下」 |
| `CONTEXT_DEPENDENT` | ユーザーに確認 | 「それについてもう少し詳しく」 |

**リプレイの流れ**:

1. ロールバック地点を決定（Forget）
2. WALからリプレイ対象のエントリーを特定
3. WALをクリアして重複を防止
4. 有効なREQUIREMENT入力を`user_requirements`に再適用
5. リプレイ差分（Before/After）をユーザーに表示

**文脈依存の検出**: 「それ」「これ」「上記」「もう少し詳しく」などの指示語パターンを単語境界を考慮した正規表現で検出し、前のLLM応答に依存するプロンプトを識別します。

### Stage 3: 未来を作る（Speculate）

分岐点（Phase 1）で複数のアウトライン候補を生成し、各候補の「その先の未来」（完成記事とレビュー評価）を並列に推論します。

**動作フロー**:

1. `--num-outlines N`（2以上）を指定するとPhase 1でN個のアウトライン候補を生成
2. ユーザーが追加指示を入力（`user_requirements`として各世界に反映）
3. 各アウトラインについて独立した「世界（World）」を作成し、Phase 2〜4を`asyncio.gather`で並列実行
4. 各世界の最終結果（記事本文・レビュー評価）をサマリーとして一覧表示
5. ユーザーが最も良い世界を選択（自動モードでは最高評価の世界を自動選択）
6. 選択された世界の状態（outline, first_half, second_half, review）をメインパイプラインに反映し、Phase 5（承認判定）へ進行
7. 選択されなかった世界は破棄

**コスト制御**:
- 並列世界数の上限: `max_parallel_worlds=3`（デフォルト）
- CLI側の上限: `--num-outlines` は1〜5の範囲に制限
- 投機的実行のコストはN倍。選ばれなかった世界の推論コストは無駄になるため、2〜3程度が実用的

## 出力例

### インタラクティブ実行（1アウトライン + ユーザー要件入力）

```
$ uv run python -m src.main \
  --theme "AIの未来" \
  --language ja \
  --model gemini-2.5-flash

+============================================================================+
|    Article Generation with Forget, Replay, Speculate                       |
+============================================================================+

Configuration:
  Theme: AIの未来
  Language: ja
  LLM Provider: gemini
  Model: gemini-2.5-flash
  Mode: Interactive
  Speculation: Disabled (1 outline(s))

  Current phase: 0 - Initial State

================================================================================

  PHASE 1: Generating Article Outline
  Generated outline: AIの未来を読み解く：技術革新の波が社会と私たちの生活をどう変えるか

Summary: この記事では、急速に進化するAI技術の最前線を概観し、...

Structure:
  1. はじめに：AIが拓く新たな時代と私たちの問い
  2. AI技術の最前線：進化を続ける主要トレンド
  3. 産業への影響：ビジネスモデルと労働市場の変革
  ...

  Additional Instructions (Optional)
  You can provide extra requirements to guide the next generation steps.
  These will be saved and automatically replayed if you rollback later.
  Press Enter to skip.

  Your instruction (or Enter to skip): 具体的な事例やデータを多く含めてください
  Requirement recorded: "具体的な事例やデータを多く含めてください"

================================================================================

  PHASE 2: Generating First Half of Article
  Generated first half (2500 characters)

Preview:
# AIの未来を読み解く：技術革新の波が社会と私たちの生活をどう変えるか
...

  Rollback Option Available
You can go back to a previous phase if you want to try different choices.
This will 'forget' all subsequent phases and regenerate them.
Valid user prompts will be automatically replayed (Replay).

Available phases:
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 0: Initial State
  2. Rollback to Phase 1: Outline Generation Complete

Select phase to rollback to (0-2, 0=continue) [0]: 2

  Rolling back to Phase 1: Outline Generation Complete
   Forgetting all subsequent phases...

  Replay: Re-applying 1 valid prompt(s)...
    + Replayed: "具体的な事例やデータを多く含めてください"

  Replay Diff:
    Before rollback: 1 requirement(s)
      "具体的な事例やデータを多く含めてください"
    After replay: 1 requirement(s) restored
      "具体的な事例やデータを多く含めてください"

================================================================================

  PHASE 2: Generating First Half of Article
  Generated first half (2800 characters)
  ...
```

### 投機的実行モード（3アウトライン）

```
$ uv run python -m src.main \
  --theme "AIの未来" \
  --language ja \
  --model gemini-2.5-flash \
  --num-outlines 3

  PHASE 1 (Speculate): Generating 3 Outline Candidates

  Generated 3 outline candidates:
    1. AIの未来を読み解く：技術革新の波が社会を変える
    2. 人工知能と人間の共創：2030年への展望
    3. AI革命の光と影：私たちは何に備えるべきか

  Additional Instructions (Optional)
  ...
  Your instruction (or Enter to skip): 倫理的な観点を重視してください

================================================================================

  SPECULATIVE EXECUTION: Running parallel worlds...

  Launching 3 parallel worlds for speculative execution...
  Speculative execution complete: 3 succeeded, 0 failed

  Speculative Execution Results:
  ======================================================================

  ✅ World 1: AIの未来を読み解く：技術革新の波が社会を変える
     Status: completed
     Grade: 4/5
     Review: 内容は正確で情報量が多く、バランスの取れた視点を提供...

  ✅ World 2: 人工知能と人間の共創：2030年への展望
     Status: completed
     Grade: 5/5
     Review: 非常に質の高い記事で、倫理面の考察が特に充実...

  ✅ World 3: AI革命の光と影：私たちは何に備えるべきか
     Status: completed
     Grade: 3/5
     Review: 基本的なカバレッジはあるが、深掘りが不足...

  ======================================================================

  Select the world you want to continue with:
    1. AIの未来を読み解く：技術革新の波が社会を変える (Grade: 4/5)
    2. 人工知能と人間の共創：2030年への展望 (Grade: 5/5)
    3. AI革命の光と影：私たちは何に備えるべきか (Grade: 3/5)

  Enter your choice (1-3): 2

  Selected: 人工知能と人間の共創：2030年への展望

================================================================================

  PHASE 5: Human-in-the-Loop - Approve or Reject Article (Iteration 1)
  ...
```

### 出力ファイル

実行完了時に、以下の2ファイルが `outputs/` ディレクトリに保存されます。

```
outputs/
+-- article_{session_id}/
    +-- article_{session_id}.json     # 構造化データ（全フィールド）
    +-- article_{session_id}.md       # Markdown形式の記事
```

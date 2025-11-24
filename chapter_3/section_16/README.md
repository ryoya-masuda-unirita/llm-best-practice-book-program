# Chapter 4 Section 5: 不要な過去を忘れる - State-Based Rollback Pattern

## 概要

このプロジェクトは、**「不要な過去を忘れる」パターン**をLLMアプリケーションに実装するサンプルコードです。長時間の対話や複雑なタスク実行において、過去の誤った情報がコンテキストを汚染し、出力品質を低下させる問題を解決します。

状態（State）自体をメモリとして活用し、ユーザーが任意のフェーズまでロールバックできる仕組みを提供します。ロールバック時には、それ以降の状態変数を削除することで「過去を忘れ」、LLMに新鮮なコンテキストで再生成させます。

並列世界パターン（Parallel World Pattern）を用いた記事生成パイプラインを通じて、チェックポイント管理とロールバック機構の実践的な実装方法を学ぶことができます。

## 機能

- **状態ベースのメモリ管理**: 状態変数の有無でフェーズ完了を判定
- **柔軟なロールバック**: ユーザーが任意のフェーズまで巻き戻し可能
- **自動フェーズ検出**: 現在の進捗を自動的に認識して適切なフェーズから再開
- **スマートな「忘却」**: 不要な状態変数を削除して過去を忘れる
- **Human-in-the-Loop統合**: 重要な意思決定ポイントでユーザー介入
- **並列世界パターン**: 複数のバリエーションを並列生成して品質を向上
- **LLM-as-a-Judge**: 生成されたコンテンツを自動評価
- **マルチプロバイダー対応**: Anthropic Claude、OpenAI、Google Geminiをサポート

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_5/
├── src/
│   ├── __init__.py
│   ├── config.py                      # 設定管理
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── parallel_world_model.py    # 状態管理モデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── outline_prompt.py          # アウトライン生成プロンプト
│   │   ├── first_half_prompt.py       # 前半生成プロンプト
│   │   ├── second_half_prompt.py      # 後半生成プロンプト
│   │   └── review_prompt.py           # レビュープロンプト
│   └── service/
│       ├── __init__.py
│       ├── generation_service.py      # 生成ロジック
│       ├── runner_service.py          # パイプライン実行とロールバック管理
│       └── helper.py                  # ヘルパー関数
├── outputs/                            # 生成結果の保存先（自動作成）
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── Makefile                            # 便利なコマンド集
├── README.md                           # このファイル
└── CLAUDE.md                           # 実装ガイド
```

### アーキテクチャ

このプロジェクトは、状態ベースのロールバック機構を中心とした以下のアーキテクチャで構成されています：

```
┌──────────────────────────────────────────────┐
│         CLI Layer (main.py)                  │
│   - コマンドライン引数解析                    │
│   - パイプライン実行制御                      │
└─────────────────┬────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────┐
│      Pipeline Orchestration Layer            │
│   (runner_service.py)                        │
│   - フェーズ検出 (get_current_phase)         │
│   - ロールバック (forget_phases_after)       │
│   - 状態管理とループ制御                      │
└─────────────────┬────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────┐
│      Business Logic Layer                    │
│   - 生成サービス (generation_service.py)     │
│   - プロンプト生成 (prompt/*.py)              │
│   - ヘルパー関数 (helper.py)                 │
└─────────────────┬────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────┐
│      State & Model Layer                     │
│   - ParallelWorldState (状態管理)            │
│   - データモデル (parallel_world_model.py)   │
└─────────────────┬────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────┐
│      Infrastructure Layer                    │
│   - LLMクライアント (llm_client.py)          │
│   - 設定管理 (config.py)                     │
│   - ログ管理 (logger.py)                     │
└──────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. 状態ベースのメモリ管理 (`src/model/parallel_world_model.py`)

`ParallelWorldState`は、`total=False`を指定したTypedDictとして定義され、フェーズ固有のフィールドをオプショナルにします：

```python
class ParallelWorldState(TypedDict, total=False):
    """
    状態自体がパイプラインの進捗メモリとして機能します。
    フィールドの存在が、そのフェーズの完了を示します。
    """
    # 必須: 常に存在する設定情報
    theme: str
    language: Literal["en", "ja"]
    llm_provider: str
    model: str
    num_outline_variants: int
    num_second_half_variants: int

    # オプショナル: 存在がフェーズ完了を示す
    outline_sessions: list[ParallelSession]  # Phase 1
    selected_outline_session_id: str | None  # Phase 2
    first_half_session: ParallelSession | None  # Phase 3
    second_half_sessions: list[ParallelSession]  # Phase 4
    reviewed_sessions: list[ParallelSession]  # Phase 5
    final_selected_session_id: str | None  # Phase 6
    human_approved: bool | None  # Phase 7
```

**ポイント**:
- フィールドの有無で進捗を判定する「自己文書化」された設計
- チェックポイントオブジェクトが不要でメモリ効率が良い
- 状態変数の削除=「忘却」という直感的な実装

#### 2. フェーズ検出 (`src/service/runner_service.py`)

現在のフェーズを状態から自動検出します：

```python
def get_current_phase(state: ParallelWorldState) -> int:
    """
    状態変数の存在から現在のフェーズを判定します。

    Returns:
        0-7のフェーズ番号
    """
    if state.get("human_approved") is not None:
        return 7
    elif state.get("final_selected_session_id") is not None:
        return 6
    elif state.get("reviewed_sessions"):
        return 5
    elif state.get("second_half_sessions"):
        return 4
    elif state.get("first_half_session") is not None:
        return 3
    elif state.get("selected_outline_session_id") is not None:
        return 2
    elif state.get("outline_sessions"):
        return 1
    else:
        return 0  # 初期状態
```

**特徴**:
- 逆順（Phase 7→0）でチェックすることで最新フェーズを取得
- 状態を読むだけで副作用なし
- フェーズ名とマッピングする`get_phase_name()`も提供

#### 3. 「忘却」の実装 (`src/service/runner_service.py`)

指定したフェーズ以降の状態変数を削除することで「過去を忘れる」：

```python
def forget_phases_after(state: ParallelWorldState, target_phase: int) -> ParallelWorldState:
    """
    ターゲットフェーズ以降の状態変数を削除して「過去を忘れる」。

    これがロールバックの核心機能です。状態変数を削除することで、
    パイプラインはそれらのフェーズを未完了と判定し、再生成します。

    Args:
        state: 現在の状態
        target_phase: ロールバック先のフェーズ（これ以前は保持）

    Returns:
        更新された状態（未来のフェーズが削除されている）
    """
    click.echo(f"\n🔄 Rolling back to Phase {target_phase}: {get_phase_name(target_phase)}")
    click.echo("   Forgetting all subsequent phases...\n")

    # ターゲットフェーズより後の状態変数を削除
    if target_phase < 7:
        state.pop("human_approved", None)
        state.pop("rejected_session_ids", None)
        state.pop("review_loop_iteration", None)

    if target_phase < 6:
        state.pop("final_selected_session_id", None)

    if target_phase < 5:
        state.pop("reviewed_sessions", None)

    if target_phase < 4:
        state.pop("second_half_sessions", None)

    if target_phase < 3:
        state.pop("first_half_session", None)

    if target_phase < 2:
        state.pop("selected_outline_session_id", None)

    if target_phase < 1:
        state.pop("outline_sessions", None)

    state.pop("error", None)  # エラー状態もクリア

    click.echo(f"✅ Rolled back to Phase {target_phase}. Forgotten phases will be regenerated.\n")
    return state
```

**ポイント**:
- `state.pop(key, None)`で安全に削除（キーがなくてもエラーにならない）
- 削除された変数に依存するフェーズは自動的に再実行される
- ユーザーに何が削除されたかを明示的に通知

#### 4. パイプライン制御 (`src/service/runner_service.py`)

メイン関数は状態ベースのループで各フェーズを条件付き実行します：

```python
async def run_parallel_world_article_generation(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
    output_directory: str,
    num_outline_variants: int,
    num_second_half_variants: int,
    auto_select: bool,
) -> CompletedArticle | None:
    """
    状態ベースのロールバック機能を持つ記事生成パイプライン。

    ワークフロー:
    1. 現在のフェーズを検出
    2. 未完了のフェーズのみ実行
    3. 重要なポイントでロールバックオプションを提供
    4. ロールバック時は状態を削除して再実行
    """

    # 必須設定のみで状態を初期化
    state: ParallelWorldState = {
        "theme": theme,
        "language": language,
        "llm_provider": llm_provider.value,
        "model": model,
        "num_outline_variants": num_outline_variants,
        "num_second_half_variants": num_second_half_variants,
    }

    while True:
        current_phase = get_current_phase(state)
        click.echo(f"\n📍 Current phase: {current_phase} - {get_phase_name(current_phase)}")

        # Phase 1: アウトライン生成（未完了の場合のみ）
        if current_phase < 1:
            state = await generate_outlines(state)
            if state.get("error"):
                return None

        # Phase 2: アウトライン選択（未完了の場合のみ）
        if current_phase < 2:
            state = await select_outline(state, auto_select)
            if state.get("error"):
                return None

        # Phase 3: 前半生成（未完了の場合のみ）
        if current_phase < 3:
            state = await generate_first_half(state)
            if state.get("error"):
                return None

            # ロールバックポイント #1: Phase 3完了後
            available_phases = get_available_rollback_phases(state)
            rollback_phase = get_rollback_choice(available_phases, auto_select)
            if rollback_phase is not None:
                state = forget_phases_after(state, rollback_phase)
                continue  # ループを再開して忘れたフェーズを再実行

        # Phase 4-5: 後半生成とレビュー
        if current_phase < 4:
            state = await generate_second_halves(state)
            if state.get("error"):
                return None

        if current_phase < 5:
            state = await review_articles(state)
            if state.get("error"):
                return None

        # Phase 6-7: レビューループ（選択・承認・再生成）
        if current_phase < 7 or not state.get("human_approved"):
            state, final_article, approved, iteration = await review_loop(
                state, auto_select, max_iterations=5
            )

            if not final_article:
                return None

            # ロールバックポイント #2: レビューループ完了後
            available_phases = get_available_rollback_phases(state)
            rollback_phase = get_rollback_choice(available_phases, auto_select)
            if rollback_phase is not None:
                state = forget_phases_after(state, rollback_phase)
                continue  # ループを再開

            if approved:
                break  # 承認されたらループ終了

        # すでに完了している場合は最終記事を取得
        else:
            reviewed_sessions = state.get("reviewed_sessions", [])
            final_session_id = state.get("final_selected_session_id")
            final_session = next(
                (s for s in reviewed_sessions if s.session_id == final_session_id),
                reviewed_sessions[0] if reviewed_sessions else None,
            )
            if final_session:
                final_article = final_session.to_completed_article(state["language"])
                iteration = state.get("review_loop_iteration", 0)
                break

    # Phase 9: 最終記事を保存
    save_article(state, final_article, output_directory, iteration)
    return final_article
```

**特徴**:
- `if current_phase < N:`で条件付き実行（すでに完了したフェーズはスキップ）
- ロールバック後は`continue`でループを再開
- 状態の整合性を常に維持

#### 5. ユーザーインタラクション (`src/service/helper.py`)

ロールバック選択UI：

```python
def get_rollback_choice(available_phases: list[tuple[int, str]], auto_select: bool) -> int | None:
    """
    ユーザーにロールバックオプションを提示します。

    Args:
        available_phases: (phase_number, phase_name)のリスト
        auto_select: 自動選択モード（常にロールバックしない）

    Returns:
        ロールバック先のフェーズ番号、またはNone（継続）
    """
    if auto_select:
        return None  # 自動モードではロールバックしない

    if not available_phases:
        return None

    click.echo("\n🔄 Rollback Option Available")
    click.echo("You can go back to a previous phase if you want to try different choices.")
    click.echo("This will 'forget' all subsequent phases and regenerate them.\n")
    click.echo("Available phases:")
    click.echo("  0. Continue without rollback (keep current progress)")

    for i, (phase_num, phase_name) in enumerate(available_phases, 1):
        click.echo(f"  {i}. Rollback to Phase {phase_num}: {phase_name}")

    while True:
        try:
            choice = click.prompt(
                f"\nSelect phase to rollback to (0-{len(available_phases)}, 0=continue)",
                type=int,
                default=0,
            )

            if choice == 0:
                return None
            elif 1 <= choice <= len(available_phases):
                phase_num, _ = available_phases[choice - 1]
                return phase_num
            else:
                click.echo(f"Please enter a number between 0 and {len(available_phases)}")
        except (ValueError, click.Abort):
            click.echo("Invalid input. Continuing without rollback.")
            return None
```

**ポイント**:
- ユーザーフレンドリーなプロンプト表示
- 入力検証とエラーハンドリング
- デフォルトは「継続」（安全側）

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.42.0
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、使用するLLMプロバイダーのAPIキーを設定
# .envrc
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
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

#### 基本的な使い方（インタラクティブモード）

```bash
# Claude 3.5 Sonnetを使用（デフォルト）
uv run python -m src.main --theme "The Future of AI"

# または make コマンドで
make run
```

**インタラクティブモードでは**:
- Phase 2でアウトライン選択を求められます
- Phase 3完了後にロールバックオプションが提示されます
- Phase 6で最終記事の選択を求められます
- Phase 7で記事の承認/拒否を求められます
- Phase 7完了後にロールバックオプションが提示されます

#### 自動選択モード（ロールバックなし）

```bash
# 自動選択モード（テストやデモ用）
uv run python -m src.main \
  --theme "量子コンピューティングの未来" \
  --language ja \
  --auto-select

# または make コマンドで
make run-auto
```

**自動選択モードでは**:
- すべての選択が自動的に行われます
- ロールバックオプションは表示されません
- 最高評価の記事が自動選択されます
- グレード4以上で自動承認されます

#### 詳細なオプション指定

```bash
# すべてのオプションを指定
uv run python -m src.main \
  --theme "宇宙探査の新時代" \
  --language ja \
  --llm-provider anthropic \
  --model claude-3-5-sonnet-20241022 \
  --output-directory ./my_articles \
  --num-outline-variants 5 \
  --num-second-half-variants 5
```

#### 利用可能なオプション

```bash
uv run python -m src.main --help
```

**出力例**:
```
Options:
  --theme TEXT                    Article theme/topic
  --language [en|ja]              Target language (default: en)
  --llm-provider [anthropic|openai|gemini]
                                  LLM provider to use (default: anthropic)
  --model TEXT                    Model name (default: claude-3-5-sonnet-20241022)
  --output-directory PATH         Output directory (default: outputs)
  --num-outline-variants INTEGER  Number of outline variants (default: 3)
  --num-second-half-variants INTEGER
                                  Number of second half variants (default: 3)
  --auto-select                   Auto-select without user input
  --help                          Show this message and exit.
```

### 出力例

#### ロールバック動作の例

Phase 3完了後のロールバックプロンプト：

```
📍 Current phase: 3 - First Half Complete

🔄 Rollback Option Available
You can go back to a previous phase if you want to try different choices.
This will 'forget' all subsequent phases and regenerate them.

Available phases:
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 0: Initial State
  2. Rollback to Phase 1: Outline Generation Complete
  3. Rollback to Phase 2: Outline Selected

Select phase to rollback to (0-3, 0=continue): 2

🔄 Rolling back to Phase 2: Outline Selected
   Forgetting all subsequent phases...

✅ Rolled back to Phase 2. Forgotten phases will be regenerated.

📍 Current phase: 2 - Outline Selected
```

ユーザーが「2」を選択すると：
1. Phase 3の`first_half_session`が削除される
2. 現在のフェーズが2に戻る
3. Phase 3以降が再実行される

#### 生成される記事ファイル

**ファイル構造**:
```
outputs/
└── parallel_world_article_a1b2c3d4e5f6/
    ├── parallel_world_article_a1b2c3d4e5f6.json  # 選択された記事（JSON）
    ├── parallel_world_article_a1b2c3d4e5f6.md    # 選択された記事（Markdown）
    └── all_variants/                              # すべてのバリエーション
        ├── variant_1_grade_5.md
        ├── variant_2_grade_4.md
        └── variant_3_grade_3.md
```

**JSONファイル例** (`parallel_world_article_*.json`):
```json
{
    "session_id": "a1b2c3d4e5f6",
    "outline": {
        "reason": "This outline provides a comprehensive exploration...",
        "title": "The Quantum Leap: How Quantum Computing Will Transform Our World",
        "summary": "An in-depth exploration of quantum computing's potential...",
        "structure": [
            "Introduction to Quantum Computing",
            "Key Principles and Mechanics",
            "Current State of Technology",
            "Transformative Applications",
            "Challenges and Limitations",
            "Future Outlook and Predictions"
        ]
    },
    "first_half": "# The Quantum Leap: How Quantum Computing Will Transform Our World\n\n## Introduction to Quantum Computing\n\n...",
    "second_half": "## Transformative Applications\n\n...",
    "review": {
        "reasoning": "This article demonstrates exceptional depth and clarity...",
        "grade": 5,
        "strengths": [
            "Clear explanations of complex quantum concepts",
            "Well-structured progression from basics to applications",
            "Balanced discussion of benefits and challenges"
        ],
        "weaknesses": [
            "Could include more specific timeline predictions"
        ]
    },
    "language": "en",
    "created_at": "2025-01-26T10:30:45.123456"
}
```

**Markdownファイル例** (`parallel_world_article_*.md`):
```markdown
# The Quantum Leap: How Quantum Computing Will Transform Our World

## Introduction to Quantum Computing

In the realm of modern technology, few innovations promise to be as revolutionary...

## Key Principles and Mechanics

At the heart of quantum computing lies the qubit...

[... 記事本文 ...]

---

# Article Review

## Review Grade: 5/5

### Reasoning
This article demonstrates exceptional depth and clarity...

### Strengths
- Clear explanations of complex quantum concepts
- Well-structured progression from basics to applications
- Balanced discussion of benefits and challenges

### Weaknesses
- Could include more specific timeline predictions
```

#### 実行ログ例

```
[2025-01-26 10:30:00] [INFO] Starting parallel world article generation
[2025-01-26 10:30:00] [INFO] Theme: The Future of AI
[2025-01-26 10:30:00] [INFO] Language: en
[2025-01-26 10:30:00] [INFO] LLM Provider: anthropic
[2025-01-26 10:30:00] [INFO] Model: claude-3-5-sonnet-20241022

📍 Current phase: 0 - Initial State

================================================================================

🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)
Creating 3 different article outlines in parallel...
✅ Generated 3 outline variants

================================================================================

👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline

[Variant 1]
Reason: This outline takes a balanced, comprehensive approach...
Title: The AI Revolution: Transforming Every Aspect of Human Life
Summary: An exploration of how artificial intelligence...
Structure:
  1. Introduction: The AI Age
  2. Current State of AI Technology
  3. AI in Healthcare and Medicine
  4. AI in Education and Learning
  5. Ethical Considerations and Challenges
  6. The Road Ahead

[Variant 2]
...

Select an outline (1-3): 1
✅ Selected: The AI Revolution: Transforming Every Aspect of Human Life

================================================================================

📝 PHASE 3: Generating First Half of Article
✅ Generated first half (3250 characters)

Preview:
# The AI Revolution: Transforming Every Aspect of Human Life
...

🔄 Rollback Option Available
You can go back to a previous phase if you want to try different choices.
This will 'forget' all subsequent phases and regenerate them.

Available phases:
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 0: Initial State
  2. Rollback to Phase 1: Outline Generation Complete
  3. Rollback to Phase 2: Outline Selected

Select phase to rollback to (0-3, 0=continue): 0

[... 続く ...]

✅ Article Generation Complete!

Selected Article Details:
  Title: The AI Revolution: Transforming Every Aspect of Human Life
  Grade: 5/5
  Total Length: 6543 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_a1b2c3d4e5f6/parallel_world_article_a1b2c3d4e5f6.json
  📝 Markdown: outputs/parallel_world_article_a1b2c3d4e5f6/parallel_world_article_a1b2c3d4e5f6.md

Session Metadata:
  Session ID: a1b2c3d4e5f6
  Created: 2025-01-26T10:35:12.345678
  Outline variants generated: 3
  Second half variants generated: 3

📁 All variants saved to: outputs/parallel_world_article_a1b2c3d4e5f6/all_variants

🎉 Parallel World Article Generation Complete!
```

### テスト方法

#### 1. 基本的な動作テスト

```bash
# インタラクティブモードで動作確認
make run
```

期待される動作：
- Phase 1でアウトラインが3つ生成される
- Phase 2で選択肢が表示される
- Phase 3完了後にロールバックオプションが表示される
- 各フェーズが正常に進行する

#### 2. ロールバック機能のテスト

```bash
# Phase 3完了後のロールバックをテスト
uv run python -m src.main --theme "Test Rollback" --language en
# Phase 3でロールバックオプションが表示されたら、Phase 2を選択
# 異なるアウトラインを選択して、Phase 3が再実行されることを確認
```

期待される動作：
- Phase 2にロールバック後、Phase 3の内容が削除される
- Phase 3が再実行される
- 新しい内容が生成される

#### 3. 自動選択モードのテスト

```bash
# 自動選択モードで最後まで実行
make run-auto
```

期待される動作：
- ユーザー入力なしで完了まで進む
- ロールバックオプションが表示されない
- 最終的な記事ファイルが生成される

#### 4. 複数プロバイダーのテスト

```bash
# Anthropic Claude
uv run python -m src.main --theme "Provider Test" --llm-provider anthropic --auto-select

# OpenAI GPT
uv run python -m src.main --theme "Provider Test" --llm-provider openai --auto-select

# Google Gemini
uv run python -m src.main --theme "Provider Test" --llm-provider gemini --auto-select
```

期待される動作：
- 各プロバイダーで正常に記事が生成される
- 構造化出力が適切に動作する
- エラーが発生しない

#### 5. 状態の整合性テスト

状態が正しく管理されているか確認するには、ロガーの出力を確認します：

```bash
# ログレベルをDEBUGに設定して実行
# src/logger.pyの設定を一時的に変更するか、環境変数で制御
uv run python -m src.main --theme "State Test"
```

ログで以下を確認：
- `Checkpoint created: Phase N - ...` が表示されない（削除されたため）
- `Forgot Phase N: ...` がロールバック時に表示される
- `Current phase: N - ...` が正しいフェーズを示している

#### 6. バリデーションの確認

生成されたJSONファイルが正しい構造を持っているか確認：

```bash
# jqでJSON構造を確認
cat outputs/parallel_world_article_*/parallel_world_article_*.json | jq .

# Pythonでモデル検証
python -c "
from src.model.parallel_world_model import CompletedArticle
import json
import glob

json_file = glob.glob('outputs/*/parallel_world_article_*.json')[0]
with open(json_file) as f:
    data = json.load(f)
    article = CompletedArticle(**data)
    print(f'✅ Valid! Title: {article.outline.title}')
    print(f'   Grade: {article.review.grade if article.review else \"N/A\"}/5')
    print(f'   Length: {len(article.get_full_content())} characters')
"
```

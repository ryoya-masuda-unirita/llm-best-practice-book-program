# Chapter 6 Section 6: 複数のLLMセッションを実現するパラレルワールドパターン

## 概要

このプロジェクトは、**パラレルワールドパターン（Parallel World Pattern）** を用いたLLMマルチセッション管理の実装例です。LangGraphのステートマシンを活用し、記事生成プロセスにおいて複数の並行セッションを作成・比較・選択する高度なAIエージェントワークフローを実現します。

パラレルワールドパターンは、同一の起点から複数の異なるセッション（世界線）を並列実行し、各可能性を探索・評価した上で最適な結果を選び出す設計手法です。本実装では、記事の構成案（アウトライン）や後半部分の生成において、複数のバリエーションを同時に生成し、ユーザーによる選択とLLM-as-a-Judgeによる評価を組み合わせることで、高品質な記事を効率的に作成します。

### 主な特徴

- **LangGraphによるワークフロー管理**: ステートマシンとして定義された明確な実行フロー
- **Human-in-the-Loop**: LangGraphの`interrupt_before`機能を用いた人間による意思決定の統合
- **パラレルワールド生成**: 複数のアウトラインや後半部分を並列生成し比較
- **LLM-as-a-Judge**: 生成された記事バリエーションをLLMが自動評価・採点
- **反復改善ループ**: ユーザー承認が得られるまで記事を再生成する品質管理機構
- **マルチプロバイダー対応**: OpenAI GPTシリーズとGoogle Geminiの両方をサポート
- **構造化出力**: Pydanticモデルによる型安全な記事データ管理

## 機能

### コア機能

- **9フェーズワークフロー**: アウトライン生成から最終記事保存までの体系的なプロセス
- **並列セッション管理**: 各セッションに固有IDを付与し、親子関係を追跡
- **人間による介入ポイント**:
  1. アウトライン選択（複数候補から1つを選択）
  2. 最終記事選択（レビュー済み候補から1つを選択）
  3. 記事承認／却下（yes/no判定と改善ループ）
- **自動評価システム**: 1-5段階のグレーディングと強み・弱点の分析
- **フィードバック駆動再生成**: 却下された記事のレビュー内容を活用した改善
- **多言語対応**: 日本語（ja）と英語（en）の記事生成
- **自動保存**: JSON形式とMarkdown形式での出力、全バリエーションの保存

### 技術的特徴

- **非同期処理**: async/awaitによる効率的なLLM API呼び出し
- **ステート永続化**: LangGraphのMemorySaverによるチェックポイント管理
- **型安全性**: TypedDictとPydanticによる厳密な型管理
- **条件付きルーティング**: 状態に基づく動的なワークフロー分岐
- **エラーハンドリング**: 各ノードでのエラー検出と安全な終了処理

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_6/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── config.py                      # 設定管理（APIキー読み込み）
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # CLIエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # OpenAI/Geminiクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── parallel_world_model.py    # データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── parallel_world_prompt.py   # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── parallel_world_service.py  # LangGraphワークフロー定義
│       ├── generation_service.py      # LLM呼び出しノード実装
│       ├── runner_service.py          # ワークフロー実行とUI統合
│       └── helper.py                  # ヘルパー関数
├── outputs/                            # 生成記事の保存先（自動作成）
│   └── parallel_world_article_XXXX/
│       ├── parallel_world_article_XXXX.json
│       ├── parallel_world_article_XXXX.md
│       └── all_variants/
│           ├── variant_1_grade_4.md
│           ├── variant_2_grade_3.md
│           └── ...
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── README.md                           # このファイル
├── CLAUDE.md                           # プロジェクト概要（日本語）
├── LANGGRAPH_REFACTORING.md            # LangGraph移行の詳細説明
└── LANGGRAPH_INTERRUPT_FLOW.md         # Human-in-the-Loopの実装詳細
```

### アーキテクチャ

このプロジェクトは、LangGraphのステートマシンを中核とした3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────────┐
│         Presentation Layer (runner_service.py)          │
│  - CLIインターフェース (main.py)                        │
│  - Human-in-the-Loop処理（表示・入力）                  │
│  - ファイル出力管理                                     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│   Workflow Orchestration (parallel_world_service.py)    │
│  - LangGraphステートマシン定義                          │
│  - ノード間ルーティング（条件分岐）                     │
│  - 状態遷移管理                                         │
│  - チェックポイント管理                                 │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│      Business Logic (generation_service.py)             │
│  - LLM API呼び出し（並列実行）                          │
│  - プロンプト生成 (parallel_world_prompt.py)            │
│  - データモデル管理 (parallel_world_model.py)           │
│  - セッション状態更新                                   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│         Infrastructure Layer                            │
│  - 設定管理 (config.py)                                 │
│  - ロガー (logger.py)                                   │
│  - LLMクライアント (llm_client.py)                      │
│  - 外部API (OpenAI, Gemini)                             │
└─────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/parallel_world_model.py`)

**ParallelWorldState** - ワークフロー全体の状態を管理するTypedDict：

```python
class ParallelWorldState(TypedDict):
    """パラレルワールド記事生成パイプラインの状態"""
    theme: str                                    # 記事テーマ
    language: Literal["en", "ja"]                 # 言語
    outline_sessions: list[ParallelSession]       # フェーズ1: 複数アウトライン
    selected_outline_session_id: str | None       # フェーズ2: 選択されたアウトライン
    first_half_session: ParallelSession | None    # フェーズ3: 前半部分
    second_half_sessions: list[ParallelSession]   # フェーズ4: 複数の後半部分
    reviewed_sessions: list[ParallelSession]      # フェーズ5: レビュー済みセッション
    final_selected_session_id: str | None         # フェーズ6: 最終選択
    human_approved: bool | None                   # フェーズ7: 人間承認
    rejected_session_ids: list[str]               # 却下されたセッションの追跡
    review_loop_iteration: int                    # 改善ループのカウンタ
    llm_provider: str                             # LLMプロバイダー
    model: str                                    # モデル名
    error: str | None                             # エラー情報
    num_outline_variants: int                     # アウトラインバリエーション数
    num_second_half_variants: int                 # 後半バリエーション数
```

**ParallelSession** - 各セッション（世界線）の状態：

```python
class ParallelSession(BaseModel):
    """単一のパラレルワールドセッション"""
    session_id: str                       # 固有セッションID
    parent_session_id: str | None         # 親セッションID（分岐元）
    outline: ArticleOutline | None        # アウトライン
    first_half: str | None                # 前半部分
    second_half: str | None               # 後半部分
    review: ArticleReview | None          # レビュー評価
    metadata: dict                        # 追加メタデータ
    created_at: str                       # 作成タイムスタンプ
```

**ArticleReview** - LLM-as-a-Judgeによる評価：

```python
class ArticleReview(BaseModel):
    """LLM-as-a-Judgeによる記事レビュー"""
    reasoning: str                        # 評価理由（3-5文）
    grade: int                            # グレード（1-5、制約: ge=1, le=5）
    strengths: list[str]                  # 強み（2-4項目）
    weaknesses: list[str]                 # 弱点（2-4項目）

    def is_acceptable(self) -> bool:
        """グレード4以上で合格と判定"""
        return self.grade >= 4
```

**ポイント**:
- `grade`フィールドは`int`型で`ge=1, le=5`制約（Gemini互換性のため`Literal`は不使用）
- セッションIDにより分岐構造を追跡可能
- `frozen=True`で不変性を保証（CompletedArticle以外）

#### 2. LangGraphワークフロー (`src/service/parallel_world_service.py`)

**グラフ構造の定義**:

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

def create_parallel_world_graph(checkpointer: MemorySaver | None = None):
    """パラレルワールド記事生成グラフの構築"""
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(ParallelWorldState)

    # ノード追加
    graph.add_node("generate_outlines", generate_multiple_outlines_node)
    graph.add_node("wait_for_outline_selection", wait_for_outline_selection_node)
    graph.add_node("generate_first_half", generate_first_half_node)
    graph.add_node("generate_second_halves", generate_multiple_second_halves_node)
    graph.add_node("review_articles", review_all_articles_node)
    graph.add_node("wait_for_final_selection", wait_for_final_selection_node)
    graph.add_node("wait_for_human_approval", wait_for_human_approval_node)
    graph.add_node("regenerate_second_halves", regenerate_second_halves_after_rejection_node)

    # エッジ追加（条件分岐含む）
    graph.add_edge(START, "generate_outlines")
    graph.add_conditional_edges(
        "generate_outlines",
        route_after_outline_generation,
        {"wait_for_outline_selection": "wait_for_outline_selection", "end": END}
    )
    # ... 他のエッジ定義

    # 改善ループの実現
    graph.add_conditional_edges(
        "wait_for_human_approval",
        route_after_human_approval,  # approved → END, rejected → regenerate
        {"regenerate_second_halves": "regenerate_second_halves", "end": END}
    )
    graph.add_edge("regenerate_second_halves", "review_articles")  # ループバック

    # コンパイル（interrupt_before設定）
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "wait_for_outline_selection",    # Human-in-the-Loop #1
            "wait_for_final_selection",      # Human-in-the-Loop #2
            "wait_for_human_approval"        # Human-in-the-Loop #3
        ],
    )
```

**ワークフローフロー図**:

```
START → generate_outlines (並列生成)
          ↓
        [INTERRUPT] wait_for_outline_selection (人間選択 #1)
          ↓
        generate_first_half
          ↓
        generate_second_halves (並列生成)
          ↓
        review_articles (LLM-as-a-Judge)
          ↓
        [INTERRUPT] wait_for_final_selection (人間選択 #2)
          ↓
        [INTERRUPT] wait_for_human_approval (承認/却下 #3)
          ↓
          ├─ [承認] → END
          └─ [却下] → regenerate_second_halves
                          ↓
                        review_articles (ループバック)
```

#### 3. Human-in-the-Loop実装 (`src/service/runner_service.py`)

LangGraphの`interrupt_before`機能を用いた実装：

```python
async def run_parallel_world_article_generation(...):
    # グラフ作成
    graph = create_parallel_world_graph()
    config = {"configurable": {"thread_id": "article-generation-1"}}

    # 初期状態
    initial_state: ParallelWorldState = {
        "theme": theme,
        "language": language,
        # ... その他の初期値
    }

    # 割り込みループ
    while True:
        # グラフ実行（次の割り込みまで実行）
        result = await graph.ainvoke(initial_state, config)

        # 状態スナップショット取得
        state_snapshot = graph.get_state(config)

        if not state_snapshot.next:
            # ワークフロー完了
            break

        # 次のノード（割り込みポイント）を確認
        next_node = state_snapshot.next[0]
        current_state = state_snapshot.values

        # 割り込みポイント別処理
        if next_node == "wait_for_outline_selection":
            # アウトライン表示と選択
            display_outlines(current_state["outline_sessions"])
            selected_idx = get_outline_selection(outline_sessions, auto_select)

            # 状態更新
            initial_state = {
                **current_state,
                "selected_outline_session_id": selected_session.session_id,
            }

        elif next_node == "wait_for_final_selection":
            # レビュー表示と選択
            display_reviews(current_state["reviewed_sessions"])
            best_idx = get_final_article_selection(reviewed_sessions, auto_select)

            # 状態更新
            initial_state = {
                **current_state,
                "final_selected_session_id": final_session.session_id,
            }

        elif next_node == "wait_for_human_approval":
            # 承認/却下判定
            human_approved = get_human_approval(completed_article, auto_select)

            if human_approved:
                initial_state = {**current_state, "human_approved": True}
            else:
                # 却下されたセッションを追跡
                rejected_ids = current_state.get("rejected_session_ids", [])
                rejected_ids.append(final_session.session_id)

                initial_state = {
                    **current_state,
                    "human_approved": False,
                    "rejected_session_ids": rejected_ids,
                    "review_loop_iteration": review_iteration,
                }

    # 最終記事の保存と返却
    # ...
```

**ポイント**:
- `graph.get_state(config).next`で次のノードを確認
- 割り込みごとにユーザー入力を取得し、状態を更新
- 更新された状態で`graph.ainvoke()`を再度呼び出すことで再開

#### 4. 並列生成ノード (`src/service/generation_service.py`)

複数のバリエーションを並列生成する例（アウトライン生成）：

```python
async def generate_multiple_outlines_node(state: ParallelWorldState) -> ParallelWorldState:
    """複数のアウトラインを並列生成するノード"""
    theme = state["theme"]
    language = state["language"]
    num_variants = state["num_outline_variants"]

    # 並列実行タスクを作成
    tasks = [
        generate_outline_with_llm(theme, language, llm_provider, model)
        for _ in range(num_variants)
    ]

    # 並列実行
    outlines = await asyncio.gather(*tasks, return_exceptions=True)

    # セッション作成
    outline_sessions = []
    for outline in outlines:
        if isinstance(outline, ArticleOutline):
            session = ParallelSession(outline=outline)
            outline_sessions.append(session)

    return {**state, "outline_sessions": outline_sessions}
```

#### 5. LLM-as-a-Judge実装 (`src/service/generation_service.py`)

```python
async def review_all_articles_node(state: ParallelWorldState) -> ParallelWorldState:
    """全記事をLLM-as-a-Judgeでレビューするノード"""
    second_half_sessions = state["second_half_sessions"]
    first_half_session = state["first_half_session"]

    # 各セッションのレビュータスクを作成
    review_tasks = []
    for session in second_half_sessions:
        full_article = first_half_session.first_half + "\n\n" + session.second_half
        review_tasks.append(
            review_article_with_llm(full_article, outline, language, llm_provider, model)
        )

    # 並列レビュー実行
    reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

    # レビュー結果をセッションに追加
    reviewed_sessions = []
    for session, review in zip(second_half_sessions, reviews):
        if isinstance(review, ArticleReview):
            session.review = review
            reviewed_sessions.append(session)

    return {**state, "reviewed_sessions": reviewed_sessions}
```

#### 6. プロンプト生成 (`src/prompt/parallel_world_prompt.py`)

**再生成時のフィードバック組み込み**:

```python
def make_second_half_regeneration_system_instruction(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
    previous_attempts: list[tuple[str, ArticleReview]],
) -> tuple[str, str]:
    """前回の失敗を踏まえた再生成プロンプト"""

    # フィードバックセクション構築
    feedback_section = ""
    if previous_attempts:
        feedback_section = "\n**過去の試行とフィードバック:**\n\n"
        for i, (prev_content, prev_review) in enumerate(previous_attempts, 1):
            feedback_section += f"試行 {i} (グレード: {prev_review.grade}/5):\n"
            feedback_section += f"フィードバック: {prev_review.reasoning}\n"
            if prev_review.weaknesses:
                feedback_section += "回避すべき問題点:\n"
                for weakness in prev_review.weaknesses:
                    feedback_section += f"  - {weakness}\n"

    system = f"""あなたは経験豊富なライターです。
以下のアウトラインと前半部分に基づいて、記事の後半を執筆してください。

{feedback_section}

**重要**: 上記のフィードバックを考慮し、指摘された弱点を改善した内容にしてください。
"""
    return system, user_prompt
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - langgraph>=0.3.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
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
# Gemini APIを使用（対話型）
python -m src.main \
  -t "SF世界の平和について" \
  -l ja \
  -lp GEMINI \
  -m gemini-2.5-flash \
  -od outputs/ \
  -no 3 \
  -ns 3

# OpenAI APIを使用（対話型）
python -m src.main \
  -t "Future of AI in Healthcare" \
  -l en \
  -lp OPENAI \
  -m gpt-4o-mini \
  -od outputs/ \
  -no 4 \
  -ns 4
```

#### 自動選択モード（デモ・テスト用）

```bash
# --auto-selectフラグで人間の入力をスキップ
python -m src.main \
  -t "量子コンピューティングの未来" \
  -l ja \
  -lp GEMINI \
  -m gemini-2.5-flash \
  -od outputs/ \
  -no 2 \
  -ns 2 \
  --auto-select
```

自動選択モードの動作：
- アウトライン選択: 最初のバリエーションを自動選択
- 最終記事選択: 最高グレードの記事を自動選択
- 承認判定: グレード4以上なら自動承認、3以下なら自動却下

#### CLIオプション詳細

```bash
python -m src.main --help
```

**オプション一覧**:

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| `--theme` | `-t` | 記事のテーマ | 必須 |
| `--language` | `-l` | 言語（en/ja） | 必須 |
| `--llm-provider` | `-lp` | LLMプロバイダー（OPENAI/GEMINI） | 必須 |
| `--model` | `-m` | モデル名 | 必須 |
| `--output-directory` | `-od` | 出力先ディレクトリ | `outputs/` |
| `--num-outline-variants` | `-no` | アウトラインバリエーション数 | `3` |
| `--num-second-half-variants` | `-ns` | 後半バリエーション数 | `3` |
| `--auto-select` | なし | 自動選択モード（人間入力スキップ） | `False` |

**利用可能なモデル**:

OpenAI:
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

Gemini:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

### 実行フロー例

```
🚀 Starting Parallel World Article Generation with LangGraph
The workflow will pause at human interaction points...

================================================================================

✅ Generated 3 outline variants

================================================================================

👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline

[Variant 1]
Reason: SF世界における平和は、技術進歩と倫理の調和が鍵となる...
Title: 星間平和条約：技術と倫理の新時代
Summary: 本記事では、SFで描かれる未来社会における平和構築について...
Structure:
  1. はじめに：SF世界の平和概念
  2. 技術進歩がもたらす平和の可能性
  3. 倫理的ジレンマと課題
  4. 星間外交と文化理解
  5. 結論：持続可能な平和への道筋

[Variant 2]
...

Select an outline (1-3): 1

✅ Selected: 星間平和条約：技術と倫理の新時代

================================================================================

📝 PHASE 3: Generating First Half of Article

✅ Generated first half (2847 characters)

Preview:
# はじめに：SF世界の平和概念

SF作品において「平和」とは、しばしば技術的進歩と倫理的...
...

================================================================================

🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)
Creating 3 different endings in parallel...

✅ Generated 3 second half variants

================================================================================

⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge

✅ Reviewed 3 complete articles

================================================================================

👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article (Iteration 1)

[Article Variant 1] - Grade: 4/5
Reasoning: この記事は技術と倫理のバランスについて深い洞察を提供...
Strengths:
  ✓ 具体的なSF作品の事例を効果的に引用している
  ✓ 論理的な構成で読みやすい
  ✓ 技術と倫理の両面から多角的に分析している
Weaknesses:
  ✗ 一部の議論がやや表面的

[Article Variant 2] - Grade: 3/5
...

Select final article (1-3): 1

✅ Selected: Article Variant 1

================================================================================

✅ PHASE 7: Human-in-the-Loop - Approve or Reject Article

📝 Selected Article Preview:
Title: 星間平和条約：技術と倫理の新時代
Grade: 4/5
Review: この記事は技術と倫理のバランスについて深い洞察を提供...

✅ Do you approve this article? (yes/no): yes

✅ Article approved! Proceeding to save...

================================================================================

💾 PHASE 9: Saving Final Article

✅ Article Generation Complete!

Selected Article Details:
  Title: 星間平和条約：技術と倫理の新時代
  Grade: 4/5
  Total Length: 5234 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_a1b2c3d4.../parallel_world_article_a1b2c3d4....json
  📝 Markdown: outputs/parallel_world_article_a1b2c3d4.../parallel_world_article_a1b2c3d4....md

Session Metadata:
  Session ID: a1b2c3d4e5f6...
  Created: 2025-10-26T15:30:45.123456
  Outline variants generated: 3
  Second half variants generated: 3

📁 All variants saved to: outputs/parallel_world_article_a1b2c3d4.../all_variants

================================================================================

🎉 Parallel World Article Generation Complete!
```

### 出力例

#### ディレクトリ構造

```
outputs/
└── parallel_world_article_a1b2c3d4e5f6.../
    ├── parallel_world_article_a1b2c3d4e5f6....json      # 選択された記事（JSON形式）
    ├── parallel_world_article_a1b2c3d4e5f6....md        # 選択された記事（Markdown形式）
    └── all_variants/                                     # 全バリエーション
        ├── variant_1_grade_4.md
        ├── variant_2_grade_3.md
        └── variant_3_grade_4.md
```

#### JSON出力例

**ファイル名**: `parallel_world_article_a1b2c3d4e5f6....json`

```json
{
    "session_id": "a1b2c3d4e5f6...",
    "outline": {
        "reason": "SF世界における平和は、技術進歩と倫理の調和が鍵となる...",
        "title": "星間平和条約：技術と倫理の新時代",
        "summary": "本記事では、SFで描かれる未来社会における平和構築について...",
        "structure": [
            "はじめに：SF世界の平和概念",
            "技術進歩がもたらす平和の可能性",
            "倫理的ジレンマと課題",
            "星間外交と文化理解",
            "結論：持続可能な平和への道筋"
        ]
    },
    "first_half": "# はじめに：SF世界の平和概念\n\nSF作品において「平和」とは...",
    "second_half": "# 星間外交と文化理解\n\n異なる文明間の相互理解は...",
    "review": {
        "reasoning": "この記事は技術と倫理のバランスについて深い洞察を提供しており...",
        "grade": 4,
        "strengths": [
            "具体的なSF作品の事例を効果的に引用している",
            "論理的な構成で読みやすい",
            "技術と倫理の両面から多角的に分析している"
        ],
        "weaknesses": [
            "一部の議論がやや表面的"
        ]
    },
    "language": "ja",
    "created_at": "2025-10-26T15:30:45.123456"
}
```

#### Markdown出力例

**ファイル名**: `parallel_world_article_a1b2c3d4e5f6....md`

```markdown
# 星間平和条約：技術と倫理の新時代

# はじめに：SF世界の平和概念

SF作品において「平和」とは、しばしば技術的進歩と倫理的課題の狭間で...

（記事本文）

---

# Article Review

## Review Grade: 4/5

### Reasoning
この記事は技術と倫理のバランスについて深い洞察を提供しており...

### Strengths
- 具体的なSF作品の事例を効果的に引用している
- 論理的な構成で読みやすい
- 技術と倫理の両面から多角的に分析している

### Weaknesses
- 一部の議論がやや表面的
```

### テスト方法

#### 1. 基本動作テスト（自動選択モード）

```bash
# Geminiで簡易テスト
python -m src.main \
  -t "テストテーマ" \
  -l ja \
  -lp GEMINI \
  -m gemini-2.5-flash \
  -od test_outputs/ \
  -no 2 \
  -ns 2 \
  --auto-select
```

**期待される動作**:
- `test_outputs/`ディレクトリが作成される
- `parallel_world_article_XXXX/`サブディレクトリが作成される
- JSON、Markdown、全バリエーションが保存される
- 自動選択により人間入力なしで完了する

#### 2. 対話型テスト

```bash
# 実際のユーザー入力をテスト
python -m src.main \
  -t "人工知能の倫理" \
  -l ja \
  -lp OPENAI \
  -m gpt-4o-mini \
  -od test_outputs/ \
  -no 3 \
  -ns 3
```

**確認ポイント**:
- 各割り込みポイントで正しく一時停止するか
- ユーザー選択が正しく反映されるか
- 却下時に再生成ループが動作するか
- 最大反復回数制限が機能するか

#### 3. エラーハンドリングテスト

```bash
# 不正なAPIキーでエラーハンドリングを確認
OPENAI_API_KEY=invalid_key python -m src.main \
  -t "テスト" \
  -l en \
  -lp OPENAI \
  -m gpt-4o-mini \
  -od test_outputs/
```

**期待される動作**:
- エラーが適切にログに記録される
- 状態の`error`フィールドにエラーメッセージが設定される
- グラフが安全に終了する

#### 4. 出力検証

```bash
# jqでJSON構造を検証
cat test_outputs/parallel_world_article_*/parallel_world_article_*.json | jq .

# Pythonでモデル検証
python -c "
from src.model.parallel_world_model import CompletedArticle
import json

with open('test_outputs/parallel_world_article_XXXX/parallel_world_article_XXXX.json') as f:
    data = json.load(f)
    article = CompletedArticle(**data)
    print(f'Valid! Title: {article.outline.title}')
    print(f'Grade: {article.review.grade}/5')
"
```

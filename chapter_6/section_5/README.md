# Chapter 6 Section 4: パラレルワールドパターンによる記事生成システム

## 概要

本プロジェクトは、**パラレルワールドパターン**を活用したAIエージェント記事生成システムです。複数の並列LLMセッションとHuman-in-the-Loop（人間参加型）の意思決定、LLM-as-a-Judge評価を組み合わせて、高品質な記事コンテンツを生成します。

パラレルワールドパターンとは、AIエージェントシステムにおけるワークフロー技法で、複数の異なる実行パス（並列世界）を同時に生成し、その中から最適な結果を選択するアプローチです。このアプローチにより、コンテンツの多様性を確保しながら、重要な決定ポイントでの戦略的な人間の介入を通じて品質と制御性を維持します。

**主な特徴**: 複数の記事バリアントを並列に作成し、LLM-as-a-Judgeで体系的に評価し、継続的な品質向上のためのレビューループで人間のフィードバックを取り入れることで、自動化と人間の監視のバランスを実現しています。

## 機能

- **パラレルワールド記事生成**: 複数の記事バリエーションを同時並列で生成
- **Human-in-the-Loop**: 重要な決定ポイントでのユーザー介入
- **LLM-as-a-Judge**: 自動化された記事品質評価とレビュー
- **フィードバックループ**: 却下された記事からのフィードバックに基づく再生成
- **バイリンガル対応**: 英語または日本語での記事生成

## プロジェクト構成

### ディレクトリ構成

```
src/
├── __init__.py
├── client/
│   ├── __init__.py
│   └── llm_client.py        # LLMクライアント初期化
├── config.py                 # 設定管理（APIキー）
├── logger.py                 # ロギング設定
├── main.py                   # メインエントリーポイント（CLI）
├── model/
│   ├── __init__.py
│   └── model.py              # Pydanticデータモデル定義
├── prompt/
│   ├── __init__.py
│   └── prompt.py             # プロンプト生成ロジック
└── service/
    ├── __init__.py
    ├── generation_service.py # LLM生成とパイプラインノード
    ├── helper.py             # UI表示とファイル保存ヘルパー
    └── runner_service.py     # ワークフローオーケストレーション
```

### アーキテクチャ

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           CLIレイヤー (main.py)                              │
│   - コマンドライン引数解析                                                   │
│   - ユーザー入力とインタラクション                                            │
│   - 出力ディレクトリ管理                                                      │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────────┐
│                    オーケストレーションレイヤー (runner_service.py)           │
│   - ワークフローフェーズ管理                                                  │
│   - Human-in-the-Loop制御                                                    │
│   - レビューループオーケストレーション                                        │
│   - ファイル保存と出力管理                                                    │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────────┐
│                AIエージェントパイプラインレイヤー (generation_service.py)     │
│   - LLM生成関数（アウトライン、記事半分、レビュー）                          │
│   - パイプラインノード（並列生成、レビュー、再生成）                          │
│   - パラレルワールド分岐とマージロジック                                      │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────────┘
│                         インフラストラクチャレイヤー                          │
│   - LLMクライアント (llm_client.py)                                          │
│   - プロンプト生成 (prompt.py)                                               │
│   - データモデル (model.py)                                                  │
│   - 設定 (config.py)                                                         │
│   - ロギング (logger.py)                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### ワークフローフェーズ

システムは9フェーズのパイプラインを管理します：

```
START → Phase 1: アウトライン並列生成 (パラレルワールド分岐点 #1)
          ↓
        Phase 2: ユーザーがアウトライン選択 (Human-in-the-Loop #1)
          ↓
        Phase 3: 記事前半生成
          ↓
        Phase 4: 記事後半並列生成 (パラレルワールド分岐点 #2)
          ↓
        Phase 5: LLM-as-a-Judgeでレビュー
          ↓
        Phase 6: ユーザーが最終記事選択 (Human-in-the-Loop #2)
          ↓
        Phase 7: ユーザーが承認/却下 (Human-in-the-Loop #3)
          ↓
          ├─ [承認] → Phase 9: 保存 → END
          └─ [却下] → Phase 8: フィードバックで再生成 → Phase 5へループ
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrcファイルを作成
cat > .envrc << EOF
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
EOF

# direnvを使用している場合
direnv allow

# または手動でエクスポート
source .envrc
```

2. **依存関係のインストール**

```bash
# uvを使用（推奨）
uv sync

# pipを使用
pip install -e .
```

### 使用方法

#### 基本的な使用方法

```bash
# 英語記事を生成
uv run python -m src.main \
  --theme "The Future of Artificial Intelligence" \
  --language en \
  --model gpt-4o

# 日本語記事を生成
uv run python -m src.main \
  --theme "人工知能の未来" \
  --language ja \
  --model gpt-4o
```

#### 詳細設定

```bash
# カスタム設定
uv run python -m src.main \
  -t "量子コンピューティングの革新" \
  -l ja \
  -m gpt-4o \
  -od ./my_articles \
  -no 5 \
  -ns 4

# オプション説明:
# -t, --theme: 記事テーマ/トピック
# -l, --language: 言語 (en または ja)
# -m, --model: 使用するモデル
# -od, --output-directory: 出力ディレクトリ
# -no, --num-outline-variants: アウトラインバリエーション数（デフォルト: 3）
# -ns, --num-second-half-variants: 後半バリエーション数（デフォルト: 3）
```

#### 自動モード（人間介入なし）

```bash
# 完全自動実行
uv run python -m src.main \
  -t "Climate Change Solutions" \
  -l en \
  -m gpt-4o \
  -a

# -a, --auto-select フラグの動作:
# - Phase 2: 最初のアウトラインを自動選択
# - Phase 6: 最高グレードの記事を自動選択
# - Phase 7: グレード >= 4 なら自動承認、それ以外は自動却下
```

#### ヘルプ表示

```bash
uv run python -m src.main --help
```

**出力**:
```
Usage: python -m src.main [OPTIONS]

  Generate an article using parallel world pattern with human-in-the-loop.

Options:
  -t, --theme TEXT                Article theme/topic.  [required]
  -l, --language [en|ja]          Article language (en: English, ja:
                                  Japanese).  [required]
  -m, --model [gpt-5|gpt-5-mini|gpt-5-nano|gpt-4.1|gpt-4.1-mini|gpt-4.1-nano|gpt-4o|gpt-4o-mini]
                                  The model to use (e.g., gpt-4o, gpt-4o-
                                  mini).  [required]
  -od, --output-directory PATH    The directory to save output files.
  -no, --num-outline-variants INTEGER
                                  Number of outline variants to generate
                                  (default: 3).
  -ns, --num-second-half-variants INTEGER
                                  Number of second half variants to generate
                                  (default: 3).
  -a, --auto-select               Automatically select best options without
                                  human interaction.
  --help                          Show this message and exit.
```

### 出力例

#### ワークフロー実行出力

```
╔════════════════════════════════════════════════════════════════════════════╗
║         Parallel World Article Generation - Human-in-the-Loop             ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: 人工知能の未来
  Language: ja
  Model: gpt-4o
  Outline Variants: 3
  Second Half Variants: 3
  Mode: Interactive

================================================================================

🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)
Creating 3 different article outlines in parallel...
✅ Generated 3 outline variants

================================================================================

👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline

[Variant 1]
Reason: このアウトラインは技術と社会の両面からAIの未来を包括的に...
Title: 人工知能の未来：技術革新と社会変革の展望
Summary: 人工知能技術は急速に進化しており、私たちの生活や働き方を...
Structure:
  1. はじめに：AI革命の現在地
  2. 最新AI技術の動向
  3. 産業への影響と活用事例
  4. 社会的課題と倫理的考慮
  5. 未来への展望

[Variant 2]
...

Select an outline (1-3): 1
✅ Selected: 人工知能の未来：技術革新と社会変革の展望

================================================================================

📝 PHASE 3: Generating First Half of Article
✅ Generated first half (2847 characters)

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
Reasoning: この記事は技術的な深さとアクセシビリティのバランスが取れて...
Strengths:
  ✓ 読者の興味を維持する明確で魅力的な文章
  ✓ 複数のドメインにわたるAI応用の包括的なカバレッジ
  ✓ 現状から将来予測への論理的な流れ
Weaknesses:
  (重大な弱点は特定されませんでした)

Select final article (1-3): 1

================================================================================

✅ PHASE 7: Human-in-the-Loop - Approve or Reject Article

📝 Selected Article Preview:
Title: 人工知能の未来：技術革新と社会変革の展望
Grade: 5/5

✅ Do you approve this article? (yes/no): yes

✅ Article approved! Proceeding to save...

================================================================================

💾 Saving Final Article

✅ Article Generation Complete!

Selected Article Details:
  Title: 人工知能の未来：技術革新と社会変革の展望
  Grade: 5/5
  Total Length: 5482 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_a1b2c3d4.../parallel_world_article_a1b2c3d4....json
  📝 Markdown: outputs/parallel_world_article_a1b2c3d4.../parallel_world_article_a1b2c3d4....md

📁 All variants saved to: outputs/parallel_world_article_a1b2c3d4.../all_variants

================================================================================

🎉 Parallel World Article Generation Complete!
```

#### 生成ファイル

**ディレクトリ構造**:
```
outputs/parallel_world_article_a1b2c3d4e5f6.../
├── parallel_world_article_a1b2c3d4e5f6....json     # 選択された記事 (JSON)
├── parallel_world_article_a1b2c3d4e5f6....md       # 選択された記事 (Markdown)
└── all_variants/                                   # 全候補
    ├── variant_1_grade_5.md
    ├── variant_2_grade_4.md
    └── variant_3_grade_3.md
```

**Markdown出力例** (`parallel_world_article_<uuid>.md`):

```markdown
# 人工知能の未来：技術革新と社会変革の展望

## はじめに：AI革命の現在地

人工知能技術は2025年現在、重要な転換点を迎えています...

## 最新AI技術の動向

今日のAIシステムは単純なパターン認識を超えて進化しています...

[... 記事コンテンツ続く ...]

## 未来への展望

この岐路に立つ今、AIの未来は私たちの選択にかかっています...

---

# Article Review

## Review Grade: 5/5

### Reasoning
この記事は技術的な深さとアクセシビリティのバランスが優れており...

### Strengths
- 読者の興味を維持する明確で魅力的な文章
- 複数のドメインにわたるAI応用の包括的なカバレッジ
- 現状から将来予測への論理的な流れ
- 倫理的考慮と課題への思慮深い議論

### Weaknesses
No significant weaknesses identified.
```

## 設計パターンと実装特徴

### パラレルワールドパターン

**分岐ポイント**:
- **分岐 #1 (Phase 1)**: 複数のアウトラインバリアントを並列生成
- **分岐 #2 (Phase 4)**: 複数の後半バリアントを並列生成

**選択ポイント**:
- **選択 #1 (Phase 2)**: ユーザーがアウトラインを選択 (Human-in-the-Loop)
- **選択 #2 (Phase 6)**: ユーザーが最終記事を選択 (Human-in-the-Loop)

**フィードバックループ**:
- **Phase 7-8**: 却下された記事のレビューを次の生成にフィードバック

### LLM-as-a-Judge評価基準

| 基準 | 重み | 説明 |
|------|------|------|
| コンテンツ品質 | 30% | 正確性、情報量、価値 |
| 構造と流れ | 25% | アウトラインへの準拠、論理的な流れ |
| 文章品質 | 20% | 明確さ、魅力、技巧 |
| 完全性 | 15% | テーマとセクションのカバレッジ |
| 言語品質 | 10% | 適切さ、一貫性、エラーフリー |

**グレードスケール**:
- **5 (Excellent)**: 優れた記事、全基準で期待を超える
- **4 (Good)**: 高品質、軽微な改善点あり
- **3 (Acceptable)**: 適切だが顕著なギャップあり
- **2 (Poor)**: 重大な問題あり
- **1 (Very Poor)**: 基本的な品質基準を満たさない

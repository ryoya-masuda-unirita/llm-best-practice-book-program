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
GEMINI_API_KEY=<your_gemini_api_key_here>
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

```bash
$ uv run python -m src.main --help
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


### 出力例

実行が完了すると、以下のような出力が得られます：

```bash
$ uv run python -m src.main \
  --theme "AIの未来" \
  --language ja \
  --model gemini-2.5-flash

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
[2026-02-08 09:41:26,527] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:84] [execute_async] Generating outline for theme: AIの未来
[2026-02-08 09:41:32,162] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:103] [execute_async] Successfully generated outline: AIの未来 を読み解く：技術革新の波が社会と私たちの生活をどう変えるか
✅ Generated outline: AIの未来を読み解く：技術革新の波が社会と私たちの生活をどう変えるか

Summary: この記事では、急速に進化するAI技術の最前線を概観し、それが産業構造、労働市場、そして私たちの日常生活にどのような変革をもたらすかを深く掘 り下げます。AIがもたらす機会と同時に、倫理的課題や社会的な影響にも焦点を当て、人間とAIが共存する未来のあるべき姿について考察します。

Structure:
  1. はじめに：AIが拓く新たな時代と私たちの問い
  2. AI技術の最前線：進化を続ける主要トレンド（生成AI、特化型AI、自律型AIなど）
  3. 産業への影響：ビジネスモデルと労働市場の変革
  4. 社会と生活への浸透：私たちの日常はどう変わるか（医療、教育、交通、エンターテインメントなど）
  5. AIがもたらす倫理的・法的課題：公平性、プライバシー、責任の所在
  6. AIとの共存：人類の役割と新しいスキルの必要性
  7. 未来を形作るための提言：個人、企業、政府が果たすべき役割
  8. おわりに：AIと共創する持続可能な未来への展望

================================================================================

📝 PHASE 2: Generating First Half of Article
[2026-02-08 09:41:32,162] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:126] [execute_async] Generating first half of article...
[2026-02-08 09:41:44,965] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:154] [execute_async] Successfully generated first half (2417 characters)
✅ Generated first half (2417 characters)

Preview:
# AIの未来を読み解く：技術革新の波が社会と私たちの生活をどう変えるか

## 1. はじめに：AIが拓く新たな時代と私たちの問い

現代は、人工知能（AI）技術がかつてないスピードで進化し、社会のあらゆる側面に深く浸透しつつある時代です。私たちの働き方、学び方、コミュニケーションの取り方、さらには私たちの存在そのものまでが、AIの登場によって再定義されようとしています。生成AIによる文章や画像の自動生成から、複雑なデータ分析、自律的な意思決定まで、AIの能力は日々拡張されており、その可能性は無限大に広がっているように見えます。

この技術革新の波は、私たちに多くの希望と同時に、漠然とした不安ももたらします。AIは人類にどのような機会をもたらし、どのような課題を突きつけるのでしょうか？私たちの社会や経済、そして個人の生活は、具体的にどう変わっていくのでしょうか？この記事では、AIが拓く新たな時代の本質を深く掘り下げ、技術の最前線から、それがもたらす産業構造や労働市場の変革、さらには私たちの日常生活への影響までを考察します。

## 2. AI技術の最前線：進化を続ける主要トレンド

AI技術は単一の分野ではなく、多様なアプローチと応用領域を持つ広範な学際的分野です。現在、特に注目されている主要なトレンドをいくつか見てみましょう。

### 生成AIの台頭
「生成AI」は、人間が作成したかのようなテキスト、画像、音声、さらにはコードや動画までを自ら生み出す能力を持つAIを指します。OpenAIのChatGPTやDALL-E 、GoogleのGeminiなどがその代表例であり、これらの技術はコンテンツ制作、デザイン、ソフトウェア開発といった分野に革命をもたらし、これまで人間のみが可能とされてきた創造的なタスクの自動化・支援を可能にしています。

### 特化型AIの進化
特定のタスクやドメインに特化したAIは、「特化型AI」と呼ばれ、以前からその実用性が証明されてきました。例えば、医療分野における病気の診断支援、金融分野での不正取引検知、製造業における品質管理などが挙げられます。これらのAIは、大量の専門データを学習することで、人間を凌駕する精度と速度で特定の問題を解決し、各産業の効率性と信頼性を劇的に向上させています。

### 自律型AIの進展
「自律型AI」は、環境を認識し、状況判断を行い、自身の行動を決定・実行する能力を持つAIです。自動運転車やドローン、ロボットなどがその典型であり、物理的な世界で自律的に活動することで、物流、探査、介護、危険作業など、多岐にわたる分野での応用が期待されています。これらのAIは、安全性と倫理的側面において特に厳格な議論が求められますが、その潜在的な社会貢献度は計り知れません。

これらのAI技術はそれぞれが進化するだけでなく、互いに連携し合うことで、より高度で複雑な問題解決能力を持つAIシステムの開発を加速させています。この止まることのない技術革新が、私たちの社会全体に波及していくのです。

## 3. 産業への影響：ビジネスモデルと労働市場の変革

AIの進化は、既存の産業構造を根底から揺るがし、新たなビジネスモデルの創出と労働市場の変革を促しています。

### ビジネスモデルの再構築
AIは、企業が製品やサービスを提供する方法、顧客との関係を構築する方法を劇的に変えています。データ駆動型マーケティング、パーソナライズされた顧客体験、予測分析によるサプライチェーン最適化、そして全く新しいAI駆動型サービスの登場などがその例です。例えば、金融業界ではAIによる高速取引やリスク管理が常態化し、製造業ではスマートファクトリーが生産効率を飛躍的に高めています。AIを活用することで、企業はこれまで不可能だったレベルでの効率化とイノベーションを実現し、競争優位性を確立しようとしています。

### 労働市場への影響とスキルの再定義
AIによる自動化は、これまで人間が行っていた定型的なタスクの多くを代替し始めています。事務作業、データ入力、カスタマーサポートの一部などは、AIによって効率的に処理されるようになるでしょう。これにより、一部の職種では仕事の性質が変化したり、あるいは需要が減少したりする可能性があります。

しかし、これは必ずしも「仕事がなくなる」ことを意味するものではありません。むしろ、AIは新たな職種を生み出し、既存の職種においては人間がより創造的で、戦略的、かつ人間らしいタスクに集中できる機会を提供します。AIシステムの開発、保守、倫理的運用に関わる専門家はもちろん、AIでは代替しにくいクリティカルシンキング、複雑な問題解決能力、共感、リーダーシップといった「人間ならではのスキル」の重要性が一層高まるでしょう。労働市場は、AIとの協働を前提としたリスキリング（学び直し）やアップスキリング（スキルの向上）が常に求められる時代へと突入しています。

## 4. 社会と生活への浸透：私たちの日常はどう変わるか

AIは、産業の舞台裏だけでなく、私たちの日常生活にも知らず知らずのうちに深く浸透しつつあります。スマートフォンを介したパーソナルアシスタントから、スマートホームデバイス、推薦システム、あるいは医療診断や交通管制の裏側で働くAIまで、その存在はますます身近なものとなっています。私たちは、AIがもたらす日々の利便性を享受する一方で、それが私たちの生活の質、プライバシー、そして社会的なつながりにどのような影響を与えるのかを理解する必要があります。

次章では、医療、教育、交通、エンターテインメントといった具体的な分野におけるAIの導入が、私たちの日常をどのように変えていくのか、さらに詳しく見ていきます。


🔄 Rollback Option Available
You can go back to a previous phase if you want to try different choices.
This will 'forget' all subsequent phases and regenerate them.

Available phases:
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 0: Initial State
  2. Rollback to Phase 1: Outline Generation Complete

Select phase to rollback to (0-2, 0=continue) [0]: 0

================================================================================

📝 PHASE 3: Generating Second Half of Article
[2026-02-08 09:42:49,710] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:177] [execute_async] Generating second half of article...
[2026-02-08 09:43:02,835] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:206] [execute_async] Successfully generated second half (3014 characters)
✅ Generated second half (3014 characters)

================================================================================

⚖️  PHASE 4: Reviewing Article with LLM-as-a-Judge
[2026-02-08 09:43:02,836] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:229] [execute_async] Reviewing article...
[2026-02-08 09:43:12,173] [INFO] [src.agent.extensions.nodes.pipeline] [pipeline.py:259] [execute_async] Successfully reviewed article: Grade 4/5
✅ Review completed: Grade 4/5

Reasoning: この論文は、提供されたアウトラインに非常によく従っており、AIの未来というテーマを包括的にカバーしています。内容は正確で情報量が多く、AI の機会と課題の両方についてバランスの取れた視点を提供しています。文章は明瞭で魅力的であり、プロフェッショナルなトーンが維持されています。唯一の顕著な欠点は、セクション4のタイトルが重複しているという軽微な構成上の問題です。全体的に非常に質の高い記事です。

Strengths:
  ✓ 提供されたアウトラインに優れた準拠性を示し、論理的かつ明確な記事構成を実現している点
  ✓ AIの社会、産業、倫理的側面への影響を網羅的に深く掘り下げた、質の高い情報提供
  ✓ 生成AI、特化型AI、自律型AIといった複雑な概念を明瞭かつ簡潔に説明している点
  ✓ AIがもたらす機会と課題の両方について、バランスの取れた客観的な視点を提供している点

Weaknesses:
  ✗ セクション4「社会と生活への浸透」の見出しが本文中で重複している構造上の軽微な欠陥
  ✗ 「責任の所在」などの特定のサブセクションは、より具体的な事例や議論を深めることで、さらに内容を充実させることが可能

================================================================================

✅ PHASE 5: Human-in-the-Loop - Approve or Reject Article (Iteration 1)

📝 Article Preview:
Title: AIの未来を読み解く：技術革新の波が社会と私たちの生活をどう変えるか
Grade: 4/5
Review: この論文は、提供されたアウトラインに非常によく従っており、AIの未来というテーマを包括的にカバーしています。内容は正確で情報量が多く、AIの機会と課題の両方についてバランスの取れた視点を提供しています。文章は明瞭で魅力的であり、プロフェッショナルなトーンが維持されています。唯一の顕著な欠点は、セクション4のタイトルが重複しているという軽微な構成上の問題です。全体的に非常に質の高い記事です。

✅ Do you approve this article? (yes/no): yes

✅ Article approved! Proceeding to save...

🔄 Rollback Option Available
You can go back to a previous phase if you want to try different choices.
This will 'forget' all subsequent phases and regenerate them.

Available phases:
  0. Continue without rollback (keep current progress)
  1. Rollback to Phase 0: Initial State
  2. Rollback to Phase 1: Outline Generation Complete
  3. Rollback to Phase 2: First Half Complete
  4. Rollback to Phase 3: Second Half Complete
  5. Rollback to Phase 4: Article Reviewed

Select phase to rollback to (0-5, 0=continue) [0]: 0

================================================================================

💾 Saving Final Article

✅ Article Generation Complete!

Article Details:
  Title: AIの未来を読み解く：技術革新の波が社会と私たちの生活をどう変えるか
  Grade: 4/5
  Total Length: 5433 characters
  Review Loop Iterations: 0

Files saved:
  📄 JSON: outputs/article_0061f7cf25a74e618559e0288f92093d/article_0061f7cf25a74e618559e0288f92093d.json
  📝 Markdown: outputs/article_0061f7cf25a74e618559e0288f92093d/article_0061f7cf25a74e618559e0288f92093d.md

Session Metadata:
  Session ID: 80eecd0738f04486ab052f62d6857dd2
  Created: 2026-02-08T09:43:19.035544


================================================================================

🎉 Article Generation Complete!
```

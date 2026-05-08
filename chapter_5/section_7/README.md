# Chapter 5 Section 7: 学習AIエージェント

## 概要

本プロジェクトは、**学習AIエージェント（Learning AI Agent）** パターンを実装したシステムです。ユーザーのプロフィール、学習履歴、フィードバックをメモリとして蓄積し、過去の経験から学習パターンを抽出することで、継続的に改善されるパーソナライズされた1週間のトレーニングプランを生成します。

従来の静的なプロンプトベースのシステムとは異なり、本システムはフィードバックループを構築し、運用を通じてシステム自体が学習・適応します。ユーザーからのフィードバック（改善提案、自由記述コメント、難易度評価など）を分析してパターンを抽出し、次回のプラン生成時にプロンプトに注入することで、より適切なトレーニングプランを生成します。

## 機能

- **パーソナライズされたトレーニングプラン生成**: ユーザーの学習目標、スキルレベル、利用可能時間に基づいて1週間のトレーニングプランを自動生成
- **メモリ管理**: ユーザープロフィール、トレーニング履歴、フィードバックをJSONファイルとして永続化
- **フィードバック学習**: ユーザーフィードバックからパターンを抽出し、将来のプラン生成に反映
- **学習パターン分析**: 複数のフィードバックを分析して、好み・難易度・ペースなどのパターンを自動抽出
- **構造化出力**: LangChainの`with_structured_output()`を使用した信頼性の高いJSON出力

## プロジェクト構成

### アーキテクチャ

```
+------------------------------------------------------------------+
|                     学習AIエージェントシステム                      |
+------------------------------------------------------------------+
                                  |
      +---------------------------+---------------------------+
      |                           |                           |
      v                           v                           v
+-------------+           +---------------+           +-------------+
|   ユーザー   |           |  メモリストア  |           |   LLM API   |
|  プロフィール |           |  (JSON Files)  |           |  (OpenAI)   |
+-------------+           +---------------+           +-------------+
      |                           |                           |
      |                           |                           |
      v                           v                           v
+------------------------------------------------------------------+
|                                                                  |
|  +--------------------+    +-------------------+                 |
|  | パターン分析エージェント |    | プラン生成エージェント |                 |
|  | (Pattern Analyzer) |    | (Plan Generator) |                 |
|  +--------------------+    +-------------------+                 |
|           |                         |                            |
|           | 学習パターン抽出         | パーソナライズされたプラン生成  |
|           v                         v                            |
|  +------------------+      +------------------+                  |
|  | LearnedPattern   |  -->  | TrainingPlan     |                  |
|  | (プロンプト注入)   |      | (1週間のプラン)   |                  |
|  +------------------+      +------------------+                  |
|                                                                  |
+------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------+
|                      フィードバックループ                          |
|                                                                  |
|    ユーザーフィードバック --> パターン分析 --> プロンプト改善       |
|                                                                  |
+------------------------------------------------------------------+
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要な依存ライブラリ:
  - `langchain-openai>=1.1.0` - OpenAI LLM統合
  - `langgraph>=1.0.0` - エージェントワークフロー
  - `pydantic>=2.12.2` - データバリデーション
  - `click>=8.3.0` - CLIフレームワーク
  - `python-dotenv>=1.1.1` - 環境変数管理

### セットアップ

1. 環境変数の設定:

```bash
# テンプレートをコピー
cp .envrc.example .envrc

# .envrcを編集してAPIキーを設定
OPENAI_API_KEY=<your_openai_api_key_here>
```

2. 依存関係のインストール:

```bash
uv sync
```

### 使用方法

#### トレーニングプランの生成

**新規ユーザー（コマンドラインオプション）:**

```bash
uv run python -m src.main generate \
  -g "Pythonプログラミングを習得してデータ分析ができるようになる" \
  -h 10 \
  -s beginner \
  -lp moderate
```

**プロフィールファイルから:**

```bash
uv run python -m src.main generate -p example/profile_data_analysis.json
```

**既存ユーザー（メモリから自動読み込み）:**

```bash
uv run python -m src.main generate -u user_analysis
```

**オプションの組み合わせ:**

```bash
# プロフィールファイル + 目標の上書き
uv run python -m src.main generate \
  -p example/profile_data_analysis.json \
  -g "機械学習エンジニアになる"

# 既存ユーザー + 新しい目標で更新
uv run python -m src.main generate \
  -u user_analysis \
  -g "Become professional Python programmer"
```

#### フィードバックの提出

```bash
# 基本的なフィードバック
uv run python -m src.main feedback \
  -u user_analysis \
  -r good \
  -d just_right

# 詳細なフィードバック
uv run python -m src.main feedback \
  -u user_analysis \
  -r excellent \
  -d challenging \
  -is "もっと実践的な演習を増やしてほしい,動画の長さを短くしてほしい" \
  -ft "全体的に良いプランでした。特にDay 3の制御構造の説明がわかりやすかったです。"
```

#### ユーザー一覧の表示

```bash
uv run python -m src.main list
```

#### ユーザー詳細の表示

```bash
# 基本情報のみ
uv run python -m src.main show -u user_analysis

# トレーニングプランも表示
uv run python -m src.main show -u user_analysis --show-plans

# 学習パターンも表示
uv run python -m src.main show -u user_analysis --show-patterns
```

### CLIオプション一覧

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS] COMMAND [ARGS]...

  Learning AI Agent - Training Plan Generator

  A learning AI agent that generates personalized 1-week training plans and
  improves based on user feedback.

  Commands:
    generate  Generate a new training plan
    feedback  Submit feedback on a training plan
    list      List users and their training history
    show      Show details of a user's memory

  Examples:
    # Generate a training plan for a new user
    python -m src.main generate -g "Learn Python programming" -h 10

    # Generate a plan using a profile file   python -m src.main generate -p
    profile.json

    # Generate a plan for an existing user (uses memory)   python -m src.main
    generate -u user_abc123

    # Submit feedback on a training plan   python -m src.main feedback -u
    user_abc123 -f feedback.json

    # List all users   python -m src.main list

Options:
  --help  Show this message and exit.

Commands:
  feedback  Submit feedback on a completed training plan.
  generate  Generate a personalized 1-week training plan.
  list      List all users and their training history.
  show      Show details of a user's memory.
```

#### `generate` コマンド

```bash
$ uv run python -m src.main generate --help
Usage: python -m src.main generate [OPTIONS]

  Generate a personalized 1-week training plan.

  You can either: 1. Provide a profile file with user details 2. Provide a
  user-id to load existing memory 3. Provide learning goal and options to
  create a new user

  Examples:
    # New user with command-line options
    python -m src.main generate -g "Learn Python" -h 10 -s beginner

    # Load from profile file   python -m src.main generate -p
    example/profile.json

    # Existing user (loads memory automatically)   python -m src.main generate
    -u user_abc123

Options:
  -m, --model [GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO]
                                  OpenAI model to use.
  -o, --output-dir PATH           Directory to save output files.
  -p, --profile-file PATH         Path to a JSON file containing user profile.
  -u, --user-id TEXT              User ID to load existing memory.
  -g, --goal TEXT                 Learning goal (e.g., 'Learn Python
                                  programming').
  -h, --hours-per-week INTEGER    Available study hours per week.
  -s, --skill-level [beginner|elementary|intermediate|upper_intermediate|advanced]
                                  Current skill level.
  -k, --current-knowledge TEXT    Current knowledge/skills (comma-separated).
  -lp, --learning-pace [slow|moderate|fast]
                                  Preferred learning pace.
  --skip-analysis / --with-analysis
                                  Skip pattern analysis even if feedback
                                  exists.
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 説明 |
|-----------|-------|------|
| `--model` | `-m` | 使用するOpenAIモデル（デフォルト: gpt-5.4） |
| `--output-dir` | `-o` | 出力ディレクトリ（デフォルト: outputs） |
| `--profile-file` | `-p` | ユーザープロフィールJSONファイルへのパス |
| `--user-id` | `-u` | 既存ユーザーのID（メモリを自動読み込み） |
| `--goal` | `-g` | 学習目標 |
| `--hours-per-week` | `-h` | 週あたりの学習可能時間 |
| `--skill-level` | `-s` | スキルレベル（beginner/elementary/intermediate/upper_intermediate/advanced） |
| `--current-knowledge` | `-k` | 現在の知識（カンマ区切り） |
| `--learning-pace` | `-lp` | 学習ペース（slow/moderate/fast） |
| `--skip-analysis` | - | パターン分析をスキップ |

#### `feedback` コマンド

```bash
$ uv run python -m src.main feedback --help
Usage: python -m src.main feedback [OPTIONS]

  Submit feedback on a completed training plan.

  Feedback is used by the learning agent to improve future training plan
  generation for this user.

  Examples:
    python -m src.main feedback -u user_abc123 -r good -d just_right
    python -m src.main feedback -u user_abc123 -r excellent -d challenging -ft "Great content!"

Options:
  -u, --user-id TEXT              User ID to add feedback for.  [required]
  -pid, --plan-id TEXT            Plan ID to add feedback for (uses latest if
                                  not specified).
  -r, --rating [excellent|good|neutral|poor|very_poor]
                                  Overall rating.  [required]
  -d, --difficulty [too_easy|easy|just_right|challenging|too_hard]
                                  Difficulty rating.  [required]
  -is, --improvement-suggestions TEXT
                                  Comma-separated improvement suggestions.
  -ft, --free-text TEXT           Free text feedback.
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 説明 |
|-----------|-------|------|
| `--user-id` | `-u` | ユーザーID（必須） |
| `--plan-id` | `-pid` | プランID（未指定時は最新のプランを使用） |
| `--rating` | `-r` | 全体評価（excellent/good/neutral/poor/very_poor）（必須） |
| `--difficulty` | `-d` | 難易度評価（too_easy/easy/just_right/challenging/too_hard）（必須） |
| `--improvement-suggestions` | `-is` | 改善提案（カンマ区切り） |
| `--free-text` | `-ft` | 自由記述フィードバック |

### 出力例

#### トレーニングプラン生成結果

```bash
$ uv run python -m src.main generate \
  -p example/profile_data_analysis.json \
  -g "機械学習エンジニアになる"
[2026-02-07 09:28:37,632] [INFO] [__main__] [main.py:71] [_load_profile_from_file] Loading profile from: example/profile_data_analysis.json
[2026-02-07 09:28:37,636] [INFO] [__main__] [main.py:284] [generate] Generating training plan for user: user_analysis
[2026-02-07 09:28:37,636] [INFO] [__main__] [main.py:285] [generate] Model: gpt-5-mini
[2026-02-07 09:28:37,636] [INFO] [src.service.service] [service.py:320] [run_training_plan_generation] ================================================================================
[2026-02-07 09:28:37,636] [INFO] [src.service.service] [service.py:321] [run_training_plan_generation] LEARNING AI AGENT - TRAINING PLAN GENERATION
[2026-02-07 09:28:37,636] [INFO] [src.service.service] [service.py:322] [run_training_plan_generation] ================================================================================
[2026-02-07 09:28:37,637] [INFO] [src.service.memory_service] [memory_service.py:91] [load_memory] Loading memory from: memory/user_analysis_20251221_113116.json
[2026-02-07 09:28:37,649] [INFO] [src.service.service] [service.py:327] [run_training_plan_generation] Loaded latest memory for user: user_analysis
[2026-02-07 09:28:37,649] [INFO] [src.service.service] [service.py:330] [run_training_plan_generation] Updated profile in memory
[2026-02-07 09:28:37,649] [INFO] [src.service.service] [service.py:337] [run_training_plan_generation] Training history: 5 plans
[2026-02-07 09:28:37,649] [INFO] [src.service.service] [service.py:338] [run_training_plan_generation] Learned patterns: 14
[2026-02-07 09:28:37,649] [INFO] [src.service.service] [service.py:339] [run_training_plan_generation] Weeks completed: 4
[2026-02-07 09:28:37,650] [INFO] [src.service.service] [service.py:276] [analyze_feedback_patterns] ============================================================
[2026-02-07 09:28:37,650] [INFO] [src.service.service] [service.py:277] [analyze_feedback_patterns] ANALYZING FEEDBACK PATTERNS
[2026-02-07 09:28:37,650] [INFO] [src.service.service] [service.py:278] [analyze_feedback_patterns] ============================================================
[2026-02-07 09:28:37,650] [INFO] [src.service.service] [service.py:279] [analyze_feedback_patterns] Feedback entries: 4
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:300] [analyze_feedback_patterns] Patterns extracted: 5
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:344] [run_training_plan_generation] New patterns learned: 5
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:193] [generate_training_plan] ============================================================
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:194] [generate_training_plan] GENERATING TRAINING PLAN
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:195] [generate_training_plan] ============================================================
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:210] [generate_training_plan] User: user_analysis
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:211] [generate_training_plan] Week number: 5
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:212] [generate_training_plan] Patterns loaded: 18
[2026-02-07 09:29:08,239] [INFO] [src.service.service] [service.py:213] [generate_training_plan] Recent feedback: 3
[2026-02-07 09:30:25,018] [INFO] [src.service.service] [service.py:234] [generate_training_plan] Plan generated: plan_user_analysis_5_36132213
[2026-02-07 09:30:25,018] [INFO] [src.service.service] [service.py:235] [generate_training_plan] Goal: Pythonでの構造的プログラミング（クラス設計 ／OOP）の基礎を身につけ、データ分析に適用できる簡単なクラスベースのツールを作成できるようになること。
[2026-02-07 09:30:25,018] [INFO] [src.service.service] [service.py:236] [generate_training_plan] Daily plans: 7
[2026-02-07 09:30:25,021] [INFO] [src.service.memory_service] [memory_service.py:78] [save_memory] Memory saved: memory/user_analysis_20260207_093025.json
[2026-02-07 09:30:25,021] [INFO] [src.service.service] [service.py:350] [run_training_plan_generation] ================================================================================
[2026-02-07 09:30:25,021] [INFO] [src.service.service] [service.py:351] [run_training_plan_generation] TRAINING PLAN GENERATION COMPLETE
[2026-02-07 09:30:25,021] [INFO] [src.service.service] [service.py:352] [run_training_plan_generation] ================================================================================
[2026-02-07 09:30:25,021] [INFO] [src.service.service] [service.py:353] [run_training_plan_generation] Plan ID: plan_user_analysis_5_36132213
[2026-02-07 09:30:25,021] [INFO] [src.service.service] [service.py:354] [run_training_plan_generation] Memory saved: memory/user_analysis_20260207_093025.json
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:300] [generate] 
============================================================
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:301] [generate] TRAINING PLAN GENERATED SUCCESSFULLY
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:302] [generate] ============================================================
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:303] [generate] Plan ID: plan_user_analysis_5_36132213
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:304] [generate] User ID: user_analysis
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:305] [generate] Week: 5
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:306] [generate] Goal: Pythonでの構造的プログラミング（クラス設計／OOP）の基礎を身につけ、データ分析に適用できる簡単なクラスベースのツールを作成できるようになること。
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:307] [generate] Daily plans: 7
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:308] [generate] 
Plan saved: outputs/training_plan_plan_user_analysis_5_36132213.md
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:309] [generate] Memory saved: memory/user_analysis_20260207_093025.json
[2026-02-07 09:30:25,022] [INFO] [__main__] [main.py:310] [generate] ============================================================
```

#### 生成されたトレーニングプラン（Markdown）

```markdown
# 週間トレーニングプラン

## 基本情報
- **プランID**: plan_user_analysis_5_ee59f9d4
- **ユーザーID**: user_analysis
- **週番号**: 第5週
- **作成日時**: 2026-02-07T09:35:01.117707

## 今週の目標
Pythonでの構造的なクラス設計（OOP）を学び、データ分析向けにクラスを使った小さなパイプラインを設計・実装できるようになること。

## 前提知識
- 基本的なPython文法（変数、リスト、辞書、関数）
- 簡単なプログラムの実行環境（Jupyter / VSCode / Google Colab）を使えること
- 基本的なデータ操作の知識（Excelレベルのデータ理解があれば可）

## 期待される成果
- Pythonでクラス設計の基礎（定義、属性、メソッド、プロパティ）を説明できる
- 継承と合成を用途に応じて使い分けられる
- SOLID原則の基本的な考え方を設計に適用できる
- Factory/Strategy等の簡単な設計パターンを使って拡張性のあるモジュールを実装できる
- データ分析向けに責務を分けたクラス（DataPipeline等）を設計・実装し、簡単なMLフローを動かせる

---

## 日別プラン

### Day 1 - 月曜日

**テーマ**: OOP入門：クラスとインスタンスの基礎
**合計時間**: 85分

#### タスク

##### 1. 動画：Pythonのクラスとインスタンスの基礎（入門）
- **タイプ**: video
- **所要時間**: 20分
- **説明**: クラス定義、インスタンス生成、属性とメソッドの基本概念を短く学ぶ（概念重視）。
- **学習目標**:
  - クラスとインスタンスの違いを説明できる
  - 簡単なクラスを定義してインスタンスを作成できる
- **推奨リソース**:
  - Corey Schafer - Python OOP (YouTube)（入門節）
  - Real Python: Classes and Objects（記事・補助）

##### 2. 演習：簡単なクラスを作ってみる（Person, BankAccount等）
- **タイプ**: exercise
- **所要時間**: 30分
- **説明**: 属性、メソッド、__init__を使って2つの小さなクラスを実装する。メソッド呼び出しと属性更新を実際に試す。
- **学習目標**:
  - __init__の使い方を理解する
  - インスタンス属性とメソッドの操作ができる
- **推奨リソース**:
  - 演習テンプレート（GitHub gist / Colabノートブック）
  - ヒント：属性は状態、メソッドは振る舞い。責務を1つに絞ることを意識

##### 3. 動画：Pythonでの属性管理とメソッドの実務的ポイント
- **タイプ**: video
- **所要時間**: 20分
- **説明**: プロパティ、クラス属性、インスタンス属性の違いと使い分けを学ぶ。
- **学習目標**:
  - プロパティ(property)やクラス属性の使いどころが分かる
  - 属性のスコープと設計上の考え方を理解する
- **推奨リソース**:
  - YouTube: Python properties & class vs instance attributes（おすすめ解説動画）

##### 4. 短い理解確認クイズ（10問程度）
- **タイプ**: quiz
- **所要時間**: 15分
- **説明**: 学んだ基礎知識の理解を確認する短いクイズ（選択／簡答）。
- **学習目標**:
  - 基礎概念の定着確認
  - 誤解しやすいポイントの自己チェック
- **推奨リソース**:
  - セルフチェック用クイズ（Colab / Google Form）


### Day 2 - 火曜日

**テーマ**: クラス設計の実践：メソッド設計とテストの基礎
**合計時間**: 85分

#### タスク

##### 1. 動画：良いメソッド設計と責務の分離
- **タイプ**: video
- **所要時間**: 20分
- **説明**: メソッドは何を持つべきか、単一責任の原則（SRP）を実例で学ぶ。
- **学習目標**:
  - メソッドを小さく保つ理由を説明できる
  - クラスの責務を意識してメソッドを設計できる
- **推奨リソース**:
  - Real Python / YouTube: Function & Method Design（短い解説動画）

##### 2. 演習：データ行を表すクラスを設計して操作する
- **タイプ**: exercise
- **所要時間**: 40分
- **説明**: CSVの1行を表すクラス（DataRow等）を設計。パース、検証、文字列化メソッドを実装してユニットテスト風に確認する。
- **学習目標**:
  - 実データに即したクラス設計ができる
  - 簡単なテストで動作を検証する習慣をつける
- **推奨リソース**:
  - 演習ノートブック（Colab）＋サンプルCSV
  - ヒント：入力検証はコンストラクタで行う／例外設計に注意

##### 3. 短記事：よくある設計上の落とし穴（読み物）
- **タイプ**: article
- **所要時間**: 10分
- **説明**: アンチパターン、可変デフォルト引数、過度な結合などを短くまとめて読む。
- **学習目標**:
  - よくあるバグ原因とその回避法を理解する
- **推奨リソース**:
  - 記事：Common Python OOP Pitfalls（日本語訳または要約）

##### 4. 動画：テスト入門（unittest / pytestの基本）
- **タイプ**: video
- **所要時間**: 15分
- **説明**: クラスの簡単なユニットテストの書き方を学ぶ。
- **学習目標**:
  - 簡単なテストを書いてクラスの振る舞いを確認できる
- **推奨リソース**:
  - YouTube: pytest 入門（短編）


### Day 3 - 水曜日

**テーマ**: 継承と合成（composition）の使い分け、SOLID入門
**合計時間**: 85分

#### タスク

##### 1. 動画：継承 vs 合成（composition）
- **タイプ**: video
- **所要時間**: 25分
- **説明**: 継承の利点と欠点、合成の使いどころを実例で学ぶ。
- **学習目標**:
  - 継承と合成を適切に選べる
  - 過度な継承による問題点を挙げられる
- **推奨リソース**:
  - YouTube: Inheritance vs Composition（例あり）

##### 2. 演習：継承と合成を使った設計（Animal/Vehicle → 実務的データ例）
- **タイプ**: exercise
- **所要時間**: 35分
- **説明**: 2つの異なる設計で同じ機能を実装して比較。利点・欠点をコメントでまとめる。
- **学習目標**:
  - 設計選択のトレードオフを実践で理解する
  - コードリーディング力を高める
- **推奨リソース**:
  - Colab演習ノート（テンプレ）
  - ヒント：変更に強い設計を意識して小さな単位で実装する

##### 3. 動画：SOLID原則の短い導入
- **タイプ**: video
- **所要時間**: 15分
- **説明**: SOLIDそれぞれの原則に対する直感的な説明と簡単なコード例を学ぶ。
- **学習目標**:
  - SOLIDの各原則の意図を説明できる
  - 簡単なリファクタリング案を考えられる
- **推奨リソース**:
  - 動画：SOLID Principles in Python（概説）

##### 4. 短いセルフチェッククイズ
- **タイプ**: quiz
- **所要時間**: 10分
- **説明**: 継承・合成・SOLIDの基礎理解を確認するクイズ。
- **学習目標**:
  - 重要概念の理解度を自己評価する
- **推奨リソース**:
  - クイズ（Colab / Google Form）


### Day 4 - 木曜日

**テーマ**: 設計パターン入門：実用パターンとPythonでの実装例
**合計時間**: 85分

#### タスク

##### 1. 動画：設計パターン概観（Factory, Strategy, Observer）
- **タイプ**: video
- **所要時間**: 20分
- **説明**: 各パターンの目的といつ使うかをコード例とともに学ぶ。
- **学習目標**:
  - 3つの主要パターンの用途を説明できる
  - 簡単なコード例の流れを追える
- **推奨リソース**:
  - YouTube: Design Patterns in Python（入門解説）
  - 記事：Factory/Strategy/Observerの比較（サマリ）

##### 2. 演習：小さなモジュールをFactory/Strategyで実装
- **タイプ**: exercise
- **所要時間**: 40分
- **説明**: データ変換器やモデル選択をStrategyまたはFactoryで実装する。動作確認と短いリポート作成。
- **学習目標**:
  - 設計パターンを用いて拡張性のあるコードを書く
  - 実装のメリットをコードで体験する
- **推奨リソース**:
  - Colabテンプレ：Strategyパターンでモデル選択を実装
  - ヒント：インターフェースを明確にすること（共通メソッド名）

##### 3. 短記事：パターン適用時の注意点（過剰設計の回避）
- **タイプ**: article
- **所要時間**: 10分
- **説明**: 設計パターンは万能でない。適用判断の基準を学ぶ。
- **学習目標**:
  - 過剰設計を避ける判断基準が分かる
- **推奨リソース**:
  - 記事：When Not to Use Design Patterns（要点まとめ）

##### 4. 動画：簡単なリファクタリングのデモ
- **タイプ**: video
- **所要時間**: 15分
- **説明**: 手続き的コードをパターンでリファクタリングする短いデモを視聴。
- **学習目標**:
  - リファクタリングの流れを理解する
  - パターン導入の効果を比較できる
- **推奨リソース**:
  - YouTube: Refactoring to Patterns（実例）


### Day 5 - 金曜日

**テーマ**: データ分析向けクラス設計（実務的応用）
**合計時間**: 85分

#### タスク

##### 1. 動画：データパイプラインをクラスで構築する考え方
- **タイプ**: video
- **所要時間**: 25分
- **説明**: 前処理、特徴量エンジニアリング、モデルラップの各責務をクラスで分ける設計例を学ぶ。
- **学習目標**:
  - 分析パイプラインを責務ごとに分割する設計ができる
  - モデルラッパーやパイプラインクラスの役割を理解する
- **推奨リソース**:
  - 動画：Building Data Pipelines with Classes（実例）

##### 2. 演習：DataPipelineクラスを実装（pandasを使用）
- **タイプ**: exercise
- **所要時間**: 40分
- **説明**: 簡単なCSVから読み込み、欠損処理、簡易特徴量生成、学習用データ出力を行うクラスを実装する。
- **学習目標**:
  - データ操作をクラスにまとめて再利用性を高める
  - 実際のデータ処理フローをクラス設計で表現できる
- **推奨リソース**:
  - 演習ノート（Colab）＋サンプルデータ（小規模）
  - ヒント：各ステップは小さなメソッドで分け、テスト可能にする

##### 3. 動画：実務でのベストプラクティス（ログ・エラーハンドリング）
- **タイプ**: video
- **所要時間**: 10分
- **説明**: 実際のワークフローでのログ出力、例外処理、設定の分離などを学ぶ。
- **学習目標**:
  - 実務的なコード健全性を保つ方法を理解する
- **推奨リソース**:
  - 動画/記事：Logging and Error Handling Best Practices

##### 4. 短い確認クイズ
- **タイプ**: quiz
- **所要時間**: 10分
- **説明**: データパイプライン設計の要点を確認するクイズ。
- **学習目標**:
  - 設計の重要ポイントを復習して定着させる
- **推奨リソース**:
  - クイズ（Colab / Google Form）


### Day 6 - 土曜日

**テーマ**: 総合演習：小さなMLパイプラインをクラスで実装する（プロジェクト）
**合計時間**: 85分

#### タスク

##### 1. プロジェクト：ミニMLパイプライン（クラスベース）
- **タイプ**: project
- **所要時間**: 60分
- **説明**: Datasetクラス、Preprocessorクラス、ModelWrapperクラス、Evaluatorクラスを設計・実装して、簡単な分類タスクを実行する（ダミーデータ可）。主要な機能をまず動かすことを目標とする。
- **学習目標**:
  - クラスを組み合わせて実用的なフローを作れる
  - 設計をドキュメント化して引き継げる形にできる
- **推奨リソース**:
  - プロジェクトテンプレ（Colabノート）＋サンプルデータ
  - 模範解答のポイント：責務分離、メソッド名の一貫性、簡単なユニットチェック

##### 2. 動画：プロジェクト解説（模範解答の歩き方）
- **タイプ**: video
- **所要時間**: 15分
- **説明**: 模範解答を見ながら設計上の意図を確認。改善ポイントをメモする。
- **学習目標**:
  - 模範解答から良い設計手法を吸収する
  - 自分の実装との違いを見つけられる
- **推奨リソース**:
  - 録画解説または解説ノート（提供）

##### 3. 演習（短）：発展チャレンジ（オプション）
- **タイプ**: exercise
- **所要時間**: 10分
- **説明**: Strategyパターンでモデル切替を導入する等の発展課題（時間があれば）。
- **学習目標**:
  - 拡張性を高める小さな改良を実装できる
- **推奨リソース**:
  - Colab追加セル（オプション実装ガイド）


### Day 7 - 日曜日

**テーマ**: 復習と週次評価（振り返り・弱点補強）
**合計時間**: 90分

#### タスク

##### 1. 動画：今週の振り返りと模範解答のポイント解説
- **タイプ**: video
- **所要時間**: 20分
- **説明**: 週の重要ポイントを短く再確認。各演習の模範解答の解説を視聴する。
- **学習目標**:
  - 今週習得した主要概念を再確認できる
  - 模範解答と自分の差分を明確にできる
- **推奨リソース**:
  - 週次解説動画（提供）

##### 2. 演習：リファクタリング課題（バグ修正＋設計改善）
- **タイプ**: exercise
- **所要時間**: 30分
- **説明**: 過去課題のコードを持ち寄り、設計上の改善点を1〜2箇所実装してリファクタリングする。
- **学習目標**:
  - 既存コードの設計改善手順を実践できる
  - 変更が少ない安全なリファクタリングができる
- **推奨リソース**:
  - 過去の演習ノート（自分の実装）
  - ヒント：小さなテストを先に書いてから変更する

##### 3. 週次評価（クイズ＋プロジェクトチェック）
- **タイプ**: quiz
- **所要時間**: 30分
- **説明**: 短い理解確認クイズ（20問相当）＋プロジェクトでの必須チェック（DataPipelineが動く、ModelWrapperが動く等）で評価。
- **学習目標**:
  - 主要概念の定着度を測る
  - プロジェクトの基本的要件が動作するか確認する
- **推奨リソース**:
  - 評価フォーム（自動採点クイズ）＋プロジェクトチェックリスト

##### 4. 短い振り返りと次週の学習提案（記事）
- **タイプ**: article
- **所要時間**: 10分
- **説明**: 学習ログをまとめ、苦手な箇所に対する次週の短期習慣を提案する。
- **学習目標**:
  - 自己評価を行い次週改善点を明確にする
- **推奨リソース**:
  - 振り返りテンプレ（提供）



---

## 週次評価

### 評価タイプ
ハイブリッド（クイズ + 実践プロジェクトチェック）

### 説明
短答式の理解確認クイズ（主要概念・用語・選択肢）と、Day6のミニプロジェクトに対するチェックリスト評価を組み合わせる。プロジェクト評価は『Dataset → Preprocessor → ModelWrapper → Evaluator』が基本要件通りに動作するかを確認する。

### カバーするトピック
- クラスとインスタンスの基礎
- 継承・合成の使い分け
- SOLID原則の基礎
- Factory/Strategy/Observerの基本
- データ分析向けクラス設計（DataPipeline等）
- 簡易ユニットテストの確認

### 合格基準
クイズで70%以上、かつプロジェクトチェックリストの必須項目（データ読み込み、前処理、学習実行、評価出力）がすべて満たされていること。クイズ未達成でもプロジェクトが確実に動く場合は再学習課題を提示。

---

## 調整メモ
ユーザーの『構造的なプログラミング／クラス設計志向』と『video, exercise優先』の好みを優先して動画と演習を中心に構成しました。過去のフィードバックで「難しい」と感じている点を踏まえ、各演習にヒント・模範解答ポイントを添付し、基礎→応用→統合（プロジェクト）と段階的に難易度を上げています。負荷が高い場合は：
- 各日の演習を分割して2日にまたがって実施（所要時間を半分に）
- Day6プロジェクトの必須要件のみ実装して発展課題は翌週に回す
- クイズで低得点の場合は該当トピックの短動画（10–15分）を追加視聴することを推奨します。
次週は今回の成果を基に「モデル実装と評価（scikit-learn利用）」「パイプライン自動化（sklearn.Pipeline / joblib）」「コード品質（型ヒント・docstring）」あたりを進めると自然な継続になります。

---
*このプランは学習AIエージェントによって生成されました。*

```

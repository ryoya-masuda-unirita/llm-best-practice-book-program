# Chapter 5 Section 5: 学習AIエージェント

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

### ディレクトリ構成

```
chapter_5/section_5/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定（APIキー管理）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # CLIエントリポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # OpenAIモデル定義
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプトテンプレート
│   └── service/
│       ├── __init__.py
│       ├── service.py           # トレーニングプラン生成サービス
│       └── memory_service.py    # メモリ管理サービス
├── example/
│   ├── profile_data_analysis.json  # サンプルプロフィール（データ分析）
│   └── profile_management.json     # サンプルプロフィール（マネジメント）
├── memory/                      # ユーザーメモリ保存ディレクトリ（自動生成）
├── outputs/                     # 生成されたプラン保存ディレクトリ（自動生成）
├── .envrc.example               # 環境変数テンプレート
├── pyproject.toml               # プロジェクト依存関係
├── Makefile                     # ビルドコマンド
└── README.md                    # このファイル
```

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

### データフロー

```
1. プラン生成フロー:
   ユーザープロフィール
         |
         v
   メモリ読み込み (最新のメモリファイルを自動検索)
         |
         v
   パターン分析 (フィードバックが2件以上ある場合)
         |
         v
   学習コンテキスト生成 (パターン + フィードバック情報)
         |
         v
   プラン生成 (LLM with 構造化出力)
         |
         v
   メモリ保存 & プラン出力

2. フィードバックループ:
   トレーニング完了
         |
         v
   フィードバック提出 (評価、難易度、改善提案、自由記述)
         |
         v
   メモリ更新 (進捗情報の更新)
         |
         v
   次回プラン生成時にパターンとして活用
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
# OPENAI_API_KEY=your_api_key_here
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

#### `generate` コマンド

| オプション | 短縮形 | 説明 |
|-----------|-------|------|
| `--model` | `-m` | 使用するOpenAIモデル（デフォルト: gpt-4o） |
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

```
============================================================
TRAINING PLAN GENERATED SUCCESSFULLY
============================================================
Plan ID: plan_user_analysis_1_adb42838
User ID: user_analysis
Week: 1
Goal: Pythonの基礎文法とJupyter/Pandasの基本操作を習得し、簡単なデータ読み込み・集計・可視化ができるようになること
Daily plans: 7

Plan saved: outputs/training_plan_plan_user_analysis_1_adb42838.md
Memory saved: memory/user_analysis_20251221_105233.json
============================================================
```

#### 生成されたトレーニングプラン（Markdown）

```markdown
# 週間トレーニングプラン

## 基本情報
- **プランID**: plan_user_analysis_1_adb42838
- **ユーザーID**: user_analysis
- **週番号**: 第1週
- **作成日時**: 2025-12-21T10:52:33.840086

## 今週の目標
Pythonの基礎文法とJupyter/Pandasの基本操作を習得し、簡単なデータ読み込み・集計・可視化ができるようになること

## 前提知識
- 基本的なPC操作（ファイル操作、ブラウザの使用）
- Excelでの基本的なデータ操作（フィルター、並べ替え、簡単な関数）
- 基礎的な論理的思考（条件分岐の理解が容易になる）

## 期待される成果
- Pythonの基本文法を使って簡単なスクリプトを書けるようになる
- Jupyter Notebook上でデータを読み込み、基本的な確認と簡単な前処理ができる
- pandasで簡単な集計（平均・合計・グルーピング）や基本的な可視化ができる

---

## 日別プラン

### Day 1 - 月曜日

**テーマ**: Python入門と学習環境の準備（Jupyter）
**合計時間**: 85分

#### タスク

##### 1. Pythonの概要（動画）
- **タイプ**: video
- **所要時間**: 30分
- **説明**: Pythonとは何か、どんな用途があるかを学び、今週の学習の全体像を把握する。
- **学習目標**:
  - Pythonの用途と強みを理解する
  - 今週の学習のゴールと学習順序を把握する

...
```

## 実装のポイント

### 学習フィードバックループ

本システムの核心は、ユーザーフィードバックから学習パターンを抽出し、次回のプラン生成に活用するフィードバックループです。

**ポイント1: パターン抽出**

```python
# src/service/service.py
def analyze_feedback_patterns(memory: UserMemory, model: str) -> list[LearnedPattern]:
    """フィードバックを分析してパターンを抽出"""
    feedback_list = memory.get_recent_feedback(limit=10)

    # 最低2件のフィードバックが必要
    if len(feedback_list) < MIN_FEEDBACK_FOR_LEARNING:
        return []

    # LLMでパターンを分析
    response = invoke_with_structured_output(
        llm, messages, PatternAnalysisResponse, "Pattern Analyzer"
    )
    return [convert_to_pattern(p) for p in response.patterns]
```

**ポイント2: プロンプトへのパターン注入**

```python
# src/prompt/prompt.py
LEARNED_CONTEXT_TEMPLATE = """
## 過去の学習から得られた知見

### ユーザーの好み・傾向
{preferences}

### 難易度に関する情報
{difficulty_info}

### ユーザーからの改善要望
{improvement_suggestions}

### ユーザーからの自由記述フィードバック
{free_text_feedback}
"""
```

### 構造化出力

LangChainの`with_structured_output()`を使用して、LLMの出力を確実にPydanticモデルに変換します。

**ポイント3: 構造化出力の使用**

```python
# src/service/service.py
def invoke_with_structured_output(
    model: ChatOpenAI,
    messages: list,
    response_model: type[T],
    agent_name: str,
) -> T:
    """構造化出力でLLMを呼び出し"""
    structured_model = model.with_structured_output(response_model)

    for attempt in range(MAX_RETRIES):
        try:
            response = structured_model.invoke(messages)
            if response is not None:
                return response
        except Exception as e:
            logger.warning(f"{agent_name}: Error on attempt {attempt + 1}: {e}")
            time.sleep(RETRY_DELAY_SECONDS)

    raise ValueError(f"{agent_name} failed after {MAX_RETRIES} attempts")
```

### メモリ管理

ユーザーメモリはJSONファイルとして永続化され、`{user_id}_{timestamp}.json`の形式で保存されます。

**ポイント4: 最新メモリの自動読み込み**

```python
# src/service/memory_service.py
def load_memory(user_id: str) -> UserMemory | None:
    """ユーザーの最新メモリを読み込み"""
    files = _get_user_memory_files(user_id)  # タイムスタンプで降順ソート

    if not files:
        return None

    latest_file = files[0]  # 最新のファイル
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return UserMemory.from_dict(data)
```

## 開発コマンド

```bash
# 依存関係のインストール
uv sync

# リンター実行
make lint

# フォーマット実行
make fmt

# リンター + フォーマット
make fix

# 型チェック
make mypy

# テスト実行
uv run pytest
```

## プロフィールファイルの形式

```json
{
  "user_id": "user_analysis",
  "learning_goal": "Pythonプログラミングを習得して、データ分析ができるようになりたい",
  "current_knowledge": [
    "基本的なPC操作",
    "Excel"
  ],
  "skill_level": "beginner",
  "available_hours_per_week": 10,
  "preferred_content_types": [
    "video",
    "exercise"
  ],
  "learning_pace": "moderate"
}
```

### フィールド説明

| フィールド | 型 | 説明 |
|-----------|------|------|
| `user_id` | string | ユーザー識別子 |
| `learning_goal` | string | 学習目標 |
| `current_knowledge` | string[] | 現在の知識・スキル |
| `skill_level` | string | スキルレベル（beginner/elementary/intermediate/upper_intermediate/advanced） |
| `available_hours_per_week` | int | 週あたりの学習可能時間 |
| `preferred_content_types` | string[] | 好みのコンテンツタイプ（video/article/exercise/project/quiz） |
| `learning_pace` | string | 学習ペース（slow/moderate/fast） |

# Chapter 5 Section 1: ReAct型AIエージェント - 夕食メニューアドバイザー

## 概要

このプロジェクトは、**ReAct（Reasoning and Acting）パターン** を用いたAIエージェントの実装を示すサンプルコードです。LangChainとLangGraphを活用し、「思考（Thought）→ 行動（Action）→ 観察（Observation）」のサイクルを繰り返すことで、複雑なタスクを段階的に解決するエージェントを構築します。

夕食メニューのアドバイザーエージェントを通じて、ReActパターンの実践的な実装方法を学ぶことができます。エージェントはレシピ検索、栄養情報確認、旬の食材取得、調理時間見積もりなどのツールを活用し、ユーザーのリクエストに基づいて最適な夕食メニューを提案します。

## 機能

- **ReActパターン実装**: Thought-Action-Observationループによる段階的な問題解決
- **ツール連携**: 4種類の専用ツール（レシピ検索、栄養情報、旬の食材、調理時間見積もり）
- **構造化出力**: Pydanticモデルによる型安全な推薦結果の生成
- **LangGraph状態管理**: StateGraphによるエージェントの状態遷移管理
- **無限ループ防止**: 最大イテレーション数（10回）による安全機構
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **Markdown出力**: 推薦結果をMarkdown形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_5/section_1/
├── src/
│   ├── __init__.py
│   ├── config.py                 # 設定管理（APIキー読み込み）
│   ├── logger.py                 # ロギング設定
│   ├── main.py                   # メインエントリーポイント（CLI）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py         # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py              # エージェント状態・データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py             # システムプロンプト・ユーザープロンプト
│   └── service/
│       ├── __init__.py
│       └── service.py            # ReActエージェント実装・ツール定義
├── outputs/                       # 推薦結果の保存先（自動作成）
├── .envrc.example                 # 環境変数設定のサンプル
├── pyproject.toml                 # プロジェクト依存関係
├── README.md                      # このファイル
└── CLAUDE.md                      # プロジェクト設計ドキュメント
```

### アーキテクチャ

```
┌─────────────────────────────────────────┐
│         CLI Layer (main.py)             │
│     - コマンドライン引数解析             │
│     - 出力ディレクトリ管理               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      ReAct Agent Layer                  │
│  - StateGraph (LangGraph)               │
│  - Thought-Action-Observation Loop      │
│  - ツール実行・結果観察                  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Tool Layer                         │
│  - search_recipes (レシピ検索)          │
│  - check_nutrition (栄養情報確認)       │
│  - get_seasonal_ingredients (旬の食材)  │
│  - estimate_cooking_time (調理時間)     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - 外部API (Anthropic Claude)           │
└─────────────────────────────────────────┘
```

### ReActエージェントのフロー

```
    ┌─────────────┐
    │    Start    │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │    Agent    │ ◄──────────────────┐
    │  (Thought)  │                    │
    └──────┬──────┘                    │
           │                           │
           ▼                           │
    ┌─────────────┐    Yes      ┌──────┴──────┐
    │ Tool Call?  │────────────►│    Tools    │
    └──────┬──────┘             │(Observation)│
           │ No                 └─────────────┘
           ▼
    ┌─────────────┐
    │   Respond   │
    │ (Response)  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │     End     │
    └─────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - langchain-anthropic>=1.2.0
  - langgraph>=1.0.0
  - click>=8.3.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
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
# リクエストを指定して実行
uv run python -m src.main -r "今日は疲れているので簡単な料理がいい"

# 健康志向のリクエスト
uv run python -m src.main -r "健康的な和食を作りたい"

# 時間制限のあるリクエスト
uv run python -m src.main -r "30分以内で作れるイタリアン"
```

#### モデルの指定

```bash
# デフォルト（claude-haiku-4-5）
uv run python -m src.main -r "簡単な夕食"

# 別のモデルを使用
uv run python -m src.main -m claude-sonnet-4-5 -r "簡単な夕食"
uv run python -m src.main -m claude-opus-4-5 -r "本格的なフレンチ"
```

利用可能なモデル:
- `claude-haiku-4-5`（デフォルト）
- `claude-sonnet-4-5`
- `claude-opus-4-5`
- `claude-opus-4-1`

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -r "簡単な夕食" -od ./my_recommendations
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

  Dinner Menu Advisor - A ReAct AI Agent

  This agent recommends dinner menus based on your request. It uses tools to
  search recipes, check nutrition, find seasonal ingredients, and estimate
  cooking times.

  REQUEST: Your dinner request in natural language.

  Examples:

      python -m src.main -r "今日は疲れているので簡単な料理がいい"

      python -m src.main -r "健康的な和食を作りたい"

      python -m src.main -r "30分以内で作れるイタリアン"

Options:
  -m, --model [claude-opus-4-5|claude-haiku-4-5|claude-sonnet-4-5|claude-opus-4-1]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  -r, --request TEXT              Your dinner request in natural language.
                                  [required]
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のようなMarkdownファイルが生成されます：

**ファイル名**: `outputs/dinner_recommendation_xxxxxxxx.md`

```markdown
# おすすめ夕食メニュー: 白菜と豚バラの簡単ミルフィーユ鍋

## 概要
- **調理時間**: 35分
- **難易度**: 簡単

## おすすめ理由
今日は疲れているとのことなので、下ごしらえが少なく短時間で作れる「白菜と豚バラのミルフィーユ鍋」を提案します。材料は冬の旬の白菜を使い、重ねて鍋に入れて煮るだけで完成。洗い物も少なく、温かくて消化にも良い一品です。

## 材料
- 白菜
- 豚バラ薄切り肉
- 水（または和風だし）
- 顆粒だし（小さじ1）
- 酒（大さじ1）
- 薄口醤油（小さじ1）
- ねぎ（飾り用）
- ポン酢または柚子胡椒（お好みで）

## 作り方
1. 白菜の葉を1枚ずつはがし、大きければ半分に切る。豚バラは5〜6cmに切る（そのままでも可）。
2. 鍋に白菜→豚バラの順で交互に重ね、ミルフィーユ状に詰めていく。鍋の高さに合わせて層を作る。
3. 水500ml（またはだし500ml）を鍋底が浸る程度に注ぎ、顆粒だし小さじ1、酒大さじ1、薄口醤油小さじ1を加える。
4. 蓋をして中火にかけ、沸騰したら弱めの中火〜中火で約15〜20分、白菜がしんなりして豚肉に火が通るまで煮る。
5. 好みで豆腐やしめじを一緒に入れても良い。火から下ろして器に盛り、刻みねぎを散らす。ポン酢や柚子胡椒を添えて召し上がれ。
6. 後片付けを楽にするため、使った鍋はぬるま湯に浸けておくと簡単です。
```

## 開発コマンド

```bash
make lint   # ruffでリンターを実行（自動修正付き）
make fmt    # ruffでコードをフォーマット
make fix    # lintとfmtを両方実行
make mypy   # 型チェックを実行
```

## 実装のポイント

### 無限ループ防止

`MAX_ITERATIONS = 10`により、ツール実行のサイクル数を制限し、エージェントの暴走を防止しています。

```python
if tool_message_count >= MAX_ITERATIONS:
    logger.warning(f"Agent: Max iterations ({MAX_ITERATIONS}) reached, forcing response")
    return "respond"
```

### 構造化出力

`tool_choice="any"`と`DinnerRecommendation`をレスポンスツールとして使用することで、モデルが必ずツールを呼び出し、構造化された出力を生成するよう強制しています。

```python
model_with_tools = model.bind_tools(all_tools, tool_choice="any")
```

### データソース

レシピ、栄養情報、旬の食材データは`model.py`内に定数として定義されています。本番環境では、外部APIやデータベースに接続することを想定しています。

```python
RECIPES_DATABASE: dict[str, list[dict]] = {
    "Japanese": [
        {"name": "鶏の照り焼き", "ingredients": ["鶏もも肉", "醤油", "みりん", "砂糖"], "time": 25},
        # ...
    ],
    # ...
}
```

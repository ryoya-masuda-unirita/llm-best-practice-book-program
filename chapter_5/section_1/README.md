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
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
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
uv run python -m src.main -m claude-sonnet-4-6 -r "簡単な夕食"
uv run python -m src.main -m claude-opus-4-6 -r "本格的なフレンチ"
```

利用可能なモデル:
- `claude-haiku-4-5`（デフォルト）
- `claude-sonnet-4-6`
- `claude-opus-4-6`

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
$ uv run python -m src.main --help 
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
  -m, --model [CLAUDE_OPUS_4_6|CLAUDE_HAIKU_4_5|CLAUDE_SONNET_4_6]
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
# おすすめ夕食メニュー: 簡単チャーハン

## 概要
- **調理時間**: 42分
- **難易度**: 簡単

## おすすめ理由
疲れている時は、手早く調理できる料理がおすすめです。チャーハンは準備も調理も簡単で、冷ご飯を活用できるため、最小限の手間で栄養バランスの取れた夕食が完成します。冬の旬のネギも使用でき、季節感も感じられます。

## 材料
- ご飯
- 卵
- ネギ
- ハム
- 塩
- こしょう
- 油

## 作り方
1. ご飯を用意し、卵を軽く溶いておきます
2. ハムとネギを細かく切ります
3. フライパンに油を熱し、溶いた卵を流し入れて軽く炒めます
4. 卵が半熟状になったら、ご飯とハム、ネギを加えます
5. ご飯をほぐしながら中火で炒めます（約3～5分）
6. 塩とこしょうで味を整えて完成です

```

```bash
$ uv run python -m src.main -r "今日は疲れているので簡単な料理がいい" -od outputs -m CLAUDE_HAIKU_4_5
[2026-02-07 09:00:54,193] [INFO] [__main__] [main.py:69] [main] Dinner Menu Advisor
Model: claude-haiku-4-5
Request: 今日は疲れているので簡単な料理がいい
Output directory: outputs

[2026-02-07 09:00:54,193] [INFO] [src.service.service] [service.py:263] [run_dinner_advisor] Starting dinner advisor for request: 今日は疲れているので簡単な料理がいい
[2026-02-07 09:00:54,193] [INFO] [src.service.service] [service.py:264] [run_dinner_advisor] Using model: claude-haiku-4-5
[2026-02-07 09:00:54,193] [INFO] [src.service.service] [service.py:232] [create_dinner_advisor_graph] Creating dinner advisor ReAct agent graph with structured output...
[2026-02-07 09:00:54,193] [INFO] [src.service.service] [service.py:254] [create_dinner_advisor_graph] Dinner advisor graph created successfully
[2026-02-07 09:00:54,200] [INFO] [src.service.service] [service.py:138] [call_model] Agent: Calling model for reasoning...
[2026-02-07 09:00:55,045] [INFO] [src.service.service] [service.py:149] [call_model] Agent: Model response received (has_tool_calls=True)
[2026-02-07 09:00:55,046] [INFO] [src.service.service] [service.py:202] [should_continue] Agent: Tool calls detected, continuing to tool execution
[2026-02-07 09:00:55,047] [INFO] [src.service.service] [service.py:156] [tool_node] Agent: Executing tool calls...
[2026-02-07 09:00:55,047] [INFO] [src.service.service] [service.py:166] [tool_node] Agent: Executing tool 'search_recipes' with args: {'query': ' 簡単 疲れた時'}
[2026-02-07 09:00:55,048] [INFO] [src.service.service] [service.py:38] [search_recipes] Tool: search_recipes called with query='簡単 疲れた時', cuisine_type='None'
[2026-02-07 09:00:55,048] [INFO] [src.service.service] [service.py:170] [tool_node] Agent: Tool 'search_recipes' returned result
[2026-02-07 09:00:55,048] [INFO] [src.service.service] [service.py:166] [tool_node] Agent: Executing tool 'get_seasonal_ingredients' with args: {}
[2026-02-07 09:00:55,048] [INFO] [src.service.service] [service.py:91] [get_seasonal_ingredients] Tool: get_seasonal_ingredients called with season='None'
[2026-02-07 09:00:55,048] [INFO] [src.service.service] [service.py:170] [tool_node] Agent: Tool 'get_seasonal_ingredients' returned result
[2026-02-07 09:00:55,049] [INFO] [src.service.service] [service.py:138] [call_model] Agent: Calling model for reasoning...
[2026-02-07 09:00:56,079] [INFO] [src.service.service] [service.py:149] [call_model] Agent: Model response received (has_tool_calls=True)
[2026-02-07 09:00:56,079] [INFO] [src.service.service] [service.py:202] [should_continue] Agent: Tool calls detected, continuing to tool execution
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:156] [tool_node] Agent: Executing tool calls...
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:166] [tool_node] Agent: Executing tool 'estimate_cooking_time' with args: {'dish_name': 'チャーハン', 'skill_level': 'beginner'}
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:109] [estimate_cooking_time] Tool: estimate_cooking_time called with dish_name='チャーハン', skill_level='beginner'
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:170] [tool_node] Agent: Tool 'estimate_cooking_time' returned result
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:166] [tool_node] Agent: Executing tool 'check_nutrition' with args: {'dish_name': 'チャーハン'}
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:69] [check_nutrition] Tool: check_nutrition called with dish_name='チャーハン'
[2026-02-07 09:00:56,080] [INFO] [src.service.service] [service.py:170] [tool_node] Agent: Tool 'check_nutrition' returned result
[2026-02-07 09:00:56,081] [INFO] [src.service.service] [service.py:138] [call_model] Agent: Calling model for reasoning...
[2026-02-07 09:00:59,553] [INFO] [src.service.service] [service.py:149] [call_model] Agent: Model response received (has_tool_calls=True)
[2026-02-07 09:00:59,554] [INFO] [src.service.service] [service.py:199] [should_continue] Agent: DinnerRecommendation tool called, proceeding to respond
[2026-02-07 09:00:59,554] [INFO] [src.service.service] [service.py:217] [respond] Agent: Extracting structured DinnerRecommendation from tool call
[2026-02-07 09:00:59,554] [INFO] [src.service.service] [service.py:220] [respond] Agent: Successfully created DinnerRecommendation: 簡単チャーハン
[2026-02-07 09:00:59,554] [INFO] [src.service.service] [service.py:280] [run_dinner_advisor] Dinner advisor completed successfully: 簡単チャーハン
[2026-02-07 09:00:59,555] [INFO] [__main__] [main.py:91] [main] Recommendation saved: outputs/dinner_recommendation_50bc0e0b2818477bb4f737216dce816b.md
[2026-02-07 09:00:59,555] [INFO] [__main__] [main.py:92] [main] Menu: 簡単チャーハン
[2026-02-07 09:00:59,555] [INFO] [__main__] [main.py:93] [main] Cooking time: 42 minutes
[2026-02-07 09:00:59,555] [INFO] [__main__] [main.py:94] [main] Difficulty: 簡単
```

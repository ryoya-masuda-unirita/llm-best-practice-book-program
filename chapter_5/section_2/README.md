# Chapter 5 Section 2: 熟考型AIエージェント

## 概要

本プロジェクトは、Google Geminiの**Deep Thinking（拡張思考）機能**を活用したAIエージェントによる短編小説生成システムです。LangGraphを用いたReAct（Reasoning + Acting）パターンを実装し、テーマ分析、キャラクター生成、プロット構築、文体調整の各ツールを組み合わせて、高品質な物語を自動生成します。

Deep Thinkingは、Gemini 2.5シリーズで利用可能な機能で、モデルが回答を生成する前に内部的な推論プロセスを実行することで、より深い思考と創造的な出力を可能にします。本システムでは、`thinking_budget`パラメータを使用して推論トークン数を制御し、複雑な創作活動に必要な思考の深さを確保しています。

ユーザーは自然言語でリクエストを入力するだけで、エージェントが自律的に創作プロセスを進め、感情的に響く物語を生成します。日本語・英語の両方に対応しています。

## 機能

- **Deep Thinking対応**: Geminiの拡張思考機能（`thinking_budget=10000`）を活用した深い推論
- **ReActエージェント**: LangGraphによるThought-Action-Observationループの実装
- **テーマ分析ツール**: 孤独、贖罪、愛、喪失、成長などのテーマを文学的要素に分解
- **キャラクター生成ツール**: 主人公、触媒、鏡像などの役割に基づくキャラクターテンプレート
- **プロット構築ツール**: ドラマティック、希望的、ほろ苦いなどのトーンに応じた3幕構成
- **文体調整ツール**: 文学的、ミニマリスト、叙情的、現代的な文体ガイド
- **多言語対応**: リクエスト言語に応じた出力（日本語/英語）

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_2/
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLIエントリーポイント
│   ├── config.py               # 設定管理
│   ├── logger.py               # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py       # LLMクライアント定義
│   ├── model/
│   │   ├── __init__.py
│   │   └── llm_pipeline_model.py  # データモデル・定数
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── llm_pipeline_prompt.py # プロンプト定義
│   └── service/
│       ├── __init__.py
│       └── llm_pipeline_service.py # エージェントロジック
├── outputs/                    # 生成された小説の出力先
├── pyproject.toml              # プロジェクト設定
├── Makefile                    # 開発用コマンド
├── .envrc.example              # 環境変数テンプレート
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                            │
│              "孤独な宇宙飛行士が地球を見つめながら..."              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      main.py (CLI)                              │
│                   Click-based interface                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LangGraph StateGraph                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ReAct Loop                             │   │
│  │  ┌─────────┐    ┌─────────┐    ┌──────────┐              │   │
│  │  │  Agent  │───▶│  Tools  │───▶│  Agent   │──▶ ...       │   │
│  │  │(Think)  │    │(Action) │    │(Observe) │              │   │
│  │  └─────────┘    └─────────┘    └──────────┘              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ analyze_theme │    │  generate_    │    │ create_plot_  │
│               │    │  characters   │    │  structure    │
│ テーマ分析    │    │ キャラ生成   │    │ プロット構築  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Gemini 2.5 Flash                              │
│              with Deep Thinking (thinking_budget=10000)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Generated Novel                              │
│                   outputs/novel_xxx.md                          │
└─────────────────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要な依存ライブラリ:
  - `langchain-google-genai>=3.2.0` - Gemini統合
  - `langgraph>=1.0.0` - エージェントグラフ
  - `click>=8.3.0` - CLIフレームワーク
  - `pydantic>=2.12.2` - データバリデーション

### セットアップ

1. 環境変数の設定：

```bash
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定
```

`.envrc`の内容：
```
GEMINI_API_KEY=<your_gemini_api_key_here>
```

2. 依存関係のインストール：

```bash
uv sync
```

### 使用方法、実行方法

```bash
# ヘルプの表示
python -m src.main --help

# 基本的な使用方法
python -m src.main -r "孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語"

# モデルを指定して実行
python -m src.main -m GEMINI_2_5_PRO -r "A bittersweet tale of childhood friends reuniting after 20 years"

# 出力ディレクトリを指定
python -m src.main -od my_novels -r "希望と絶望の狭間で戦う少女の物語"
```

**CLIオプション：**

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|----------|
| `--model` | `-m` | 使用するGeminiモデル | `GEMINI_2_5_FLASH` |
| `--output-directory` | `-od` | 出力ディレクトリ | `outputs` |
| `--request` | `-r` | 小説のリクエスト（必須） | - |

**利用可能なモデル：**
- `GEMINI_2_5_PRO` - 最高品質、低速
- `GEMINI_2_5_FLASH` - バランス型（推奨）
- `GEMINI_2_5_FLASH_LITE` - 高速、軽量

### 出力例

実行ログ：
```
[2025-11-29 16:32:34,682] [INFO] [__main__] Deep Think Novel Writer
Model: gemini-2.5-flash
Request: 孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語
Output directory: outputs

[INFO] Starting novel writer for request: 孤独な宇宙飛行士が...
[INFO] Agent: Calling Gemini model with deep thinking...
[INFO] Agent: Model response received (has_tool_calls=True)
[INFO] Agent: Executing tool 'analyze_theme' with args: {'theme': '孤独な宇宙飛行士...'}
[INFO] Tool: analyze_theme called with theme='孤独な宇宙飛行士...'
[INFO] Agent: Executing tool 'generate_characters' with args: {...}
[INFO] Agent: Executing tool 'create_plot_structure' with args: {...}
[INFO] Agent: No tool calls, ending loop with final novel
[INFO] Novel writer completed successfully (thinking_depth=4)
[INFO] Novel saved: outputs/novel_xxx.md
```

生成された小説の例（`outputs/novel_xxx.md`）：

```markdown
宇宙船「ホタル」の寂寥とした操縦室で、ケンジ・タナカは地球を眺めていた。
漆黒の宇宙に浮かぶ、息をのむほどに青く、緑豊かで、白く輝くビー玉。
それは彼にとって、ただの惑星ではなかった。
そこは、彼の記憶、彼の夢、彼の失われた愛が息づく場所だった。

「ホタル」は深宇宙探査の最中にあった。半年間、ケンジはこの小さなカプセルの中で、
人類史上最も遠い地点から地球を見つめ続けている。当初は科学的発見への渇望が
彼の心を燃やしたが、今ではその熱も冷め、代わりに底知れない孤独が胸の奥に広がっていた。

...

ケンジは、かすかな笑みを浮かべた。宇宙の果てで、彼はついに自分自身と和解した。
そして、遥か彼方の故郷へ、無言の約束を交わした。再び、地球の光が彼の瞳に映し出される。
その光は、もう孤独ではなく、宇宙の深淵に灯る希望の道標のように見えた。
```

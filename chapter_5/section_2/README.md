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
uv run python -m src.main --help

# 基本的な使用方法
uv run python -m src.main -r "孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語"

# モデルを指定して実行
uv run python -m src.main -m GEMINI_2_5_PRO -r "A bittersweet tale of childhood friends reuniting after 20 years"

# 出力ディレクトリを指定
uv run python -m src.main -od my_novels -r "希望と絶望の狭間で戦う少女の物語"
```

**CLIオプション：**

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Deep Think Novel Writer - An AI Agent for Creative Writing

  This agent generates short novels based on your request using deep thinking.
  It uses Gemini's extended thinking capabilities to craft compelling
  narratives with rich characters, engaging plots, and evocative prose.

  REQUEST: Your novel request in natural language.

  Examples:

      python -m src.main -r "Write a story about a lonely lighthouse keeper
      who discovers a message in a bottle"

      python -m src.main -r "A bittersweet tale of childhood friends reuniting
      after 20 years"

      python -m src.main -r "孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語"

Options:
  -m, --model [GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The Gemini model to use for deep thinking.
  -od, --output-directory PATH    The directory to save output files.
  -r, --request TEXT              Your novel request in natural language.
                                  [required]
  --help                          Show this message and exit.
```

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
```shell
$ uv run python -m src.main -r "孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語" -od outputs
[2026-02-07 09:03:34,332] [INFO] [__main__] [main.py:69] [main] Deep Think Novel Writer
Model: gemini-2.5-flash
Request: 孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語
Output directory: outputs

[2026-02-07 09:03:34,332] [INFO] [src.service.service] [service.py:294] [run_novel_writer] Starting novel writer for request: 孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語
[2026-02-07 09:03:34,332] [INFO] [src.service.service] [service.py:295] [run_novel_writer] Using model: gemini-2.5-flash
[2026-02-07 09:03:34,333] [INFO] [src.service.service] [service.py:263] [create_novel_writer_graph] Creating deep think novel writer agent graph...
[2026-02-07 09:03:34,333] [INFO] [src.service.service] [service.py:285] [create_novel_writer_graph] Novel writer graph created successfully
[2026-02-07 09:03:34,337] [INFO] [src.service.service] [service.py:166] [call_model] Agent: Calling Gemini model with deep thinking...
[2026-02-07 09:03:40,931] [INFO] [src.service.service] [service.py:183] [call_model] Agent: Model response received (has_tool_calls=True)
[2026-02-07 09:03:40,931] [INFO] [src.service.service] [service.py:233] [should_continue] Agent: Tool calls detected, continuing to tool execution
[2026-02-07 09:03:40,932] [INFO] [src.service.service] [service.py:192] [tool_node] Agent: Executing tool calls...
[2026-02-07 09:03:40,932] [INFO] [src.service.service] [service.py:202] [tool_node] Agent: Executing tool 'analyze_theme' with args: {'theme': '孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語'}
[2026-02-07 09:03:40,933] [INFO] [src.service.service] [service.py:37] [analyze_theme] Tool: analyze_theme called with theme='孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語'
[2026-02-07 09:03:40,933] [INFO] [src.service.service] [service.py:206] [tool_node] Agent: Tool 'analyze_theme' returned result
[2026-02-07 09:03:40,933] [INFO] [src.service.service] [service.py:166] [call_model] Agent: Calling Gemini model with deep thinking...
[2026-02-07 09:03:47,002] [INFO] [src.service.service] [service.py:183] [call_model] Agent: Model response received (has_tool_calls=True)
[2026-02-07 09:03:47,002] [INFO] [src.service.service] [service.py:233] [should_continue] Agent: Tool calls detected, continuing to tool execution
[2026-02-07 09:03:47,003] [INFO] [src.service.service] [service.py:192] [tool_node] Agent: Executing tool calls...
[2026-02-07 09:03:47,003] [INFO] [src.service.service] [service.py:202] [tool_node] Agent: Executing tool 'generate_characters' with args: {'story_context': '孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語。主人公は人生の後半に差し掛かり、静かで内省的な性格。なぜ宇宙飛行士になったのか、過去にどんな経験があったのかが、回想の形で語られる。', 'num_characters': 1}
[2026-02-07 09:03:47,003] [INFO] [src.service.service] [service.py:72] [generate_characters] Tool: generate_characters called with context='孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語。主人公は人生の後半に差し掛かり、静かで内省的な性格。なぜ宇宙飛行士になったのか、過去にどんな経験があったのかが、回想の形で語られる。', num=1
[2026-02-07 09:03:47,004] [INFO] [src.service.service] [service.py:206] [tool_node] Agent: Tool 'generate_characters' returned result
[2026-02-07 09:03:47,004] [INFO] [src.service.service] [service.py:166] [call_model] Agent: Calling Gemini model with deep thinking...
[2026-02-07 09:03:51,414] [INFO] [src.service.service] [service.py:183] [call_model] Agent: Model response received (has_tool_calls=True)
[2026-02-07 09:03:51,415] [INFO] [src.service.service] [service.py:233] [should_continue] Agent: Tool calls detected, continuing to tool execution
[2026-02-07 09:03:51,415] [INFO] [src.service.service] [service.py:192] [tool_node] Agent: Executing tool calls...
[2026-02-07 09:03:51,415] [INFO] [src.service.service] [service.py:202] [tool_node] Agent: Executing tool 'create_plot_structure' with args: {'tone': '内省的で、やや感傷的だが、最終的には希望に満ちた静かな感動', 'premise': '孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語。'}
[2026-02-07 09:03:51,415] [INFO] [src.service.service] [service.py:98] [create_plot_structure] Tool: create_plot_structure called with premise='孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語。', tone='内省的で、やや感傷的だが、最終的には希望に満ちた静かな感動'
[2026-02-07 09:03:51,416] [INFO] [src.service.service] [service.py:206] [tool_node] Agent: Tool 'create_plot_structure' returned result
[2026-02-07 09:03:51,416] [INFO] [src.service.service] [service.py:166] [call_model] Agent: Calling Gemini model with deep thinking...
[2026-02-07 09:04:09,354] [INFO] [src.service.service] [service.py:183] [call_model] Agent: Model response received (has_tool_calls=False)
[2026-02-07 09:04:09,355] [INFO] [src.service.service] [service.py:236] [should_continue] Agent: No tool calls, ending loop with final novel
[2026-02-07 09:04:09,355] [INFO] [src.service.service] [service.py:316] [run_novel_writer] Novel writer completed successfully (thinking_depth=4)
[2026-02-07 09:04:09,356] [INFO] [__main__] [main.py:91] [main] Novel saved: outputs/novel_7bf1af22543b4a74aa1d61d854c971ec.md
```

生成された小説の例（`outputs/novel_xxx.md`）：

```markdown
## 青い大理石の記憶

宇宙船「アストライア」の展望デッキで、藤原健は窓ガラスに額を押し付けていた。眼前には、言葉を失うほどの青い大理石が浮かんでいる。地球だ。彼の故郷であり、彼が残してきた全ての記憶が眠る場所。船内の穏やかなハミング音だけが、彼の孤独な瞑想を邪魔しないよう、静かに響いていた。

健は、50代後半の男だった。顔には深い皺が刻まれ、その瞳の奥には、宇宙の深淵を覗き込んだ者だけが持つ静かな諦念と、どこか少年のような輝きが同居している。長年の宇宙飛行士としてのキャリアは、彼に比類なき経験と知識をもたらしたが、その代償として、彼は地球での多くの絆を置き去りにしてきた。

地球の夜の面が、ゆっくりと視界に現れる。無数の都市の光が、まるで宝石を散りばめたように輝いていた。その光の一つ一つが、彼の人生の断片を呼び覚ますトリガーとなった。

初めて宇宙を目指した日のことを思い出す。幼い頃、彼は近所のプラネタリウムで星々に魅せられ、いつかあの暗闇の向こう側に行きたいと願った。それは純粋な探求心だった。だが、ふと彼の心に疑問がよぎる。本当にそれだけだったのか？ 地球の、あまりにも複雑で、あまりにも面倒な人間関係から逃れたいという、幼いながらの逃避願望も、心の奥底には潜んでいなかったか？

ガラスの向こう、太平洋の上空を船は滑っていく。あの青い海は、彼がかつて愛した女性、美咲との思い出の場所だった。彼女の瞳も、あの海のように深く、穏やかだった。健は宇宙飛行士の訓練に没頭し、日々地球を離れる準備を進めていた。美咲はいつも、彼の夢を応援してくれた。しかし、二人の距離は、地球と宇宙のように広がる一方だった。

「健、本当にそれでいいの？」

ある夜、美咲は静かにそう尋ねた。彼の研究室の窓から見える夜景は、あの地球の都市の光のように小さく、遠かった。彼は答えられなかった。彼の心はすでに、重力圏を飛び出すことに囚われていた。彼女の手を握る代わりに、彼は分厚い宇宙飛行計画書を握っていた。二人の関係は、彼の夢と共に、静かに、そして決定的に、終わりを告げた。その時感じた寂しさが、今、この宇宙の静寂の中で、まるで魂の叫びのように共鳴する。

窓の向こう、アフリカ大陸の輪郭が浮かび上がる。健は、老いた両親の顔を思い浮かべた。彼らがどれほど、自分の活躍を誇りに思ってくれたか。だが、どれほど、会えない時間を寂しがったか。疎遠になった兄弟姉妹は、地球でそれぞれの家族を築き、それぞれの人生を歩んでいる。彼は、遠い宇宙から彼らの存在を感じ、漠然とした罪悪感と、不思議な安心感がない交ぜになった感情を抱いた。彼らは彼を必要としていたのだろうか？ 彼がそこにいなかったことは、彼らを傷つけたのだろうか？

彼の心は、達成できなかったこと、後悔している決断の数々を巡る。宇宙での栄光と達成感と引き換えに、彼は何を失ったのだろう？ 彼の人生の選択は、本当に正しかったのか？ 地球はますます遠く、手の届かない場所のように感じられた。

その時、地球がゆっくりと回転し、アジアの夜景が目の前に広がった。無数の光が、まるで生命の脈動のように点滅している。それは彼がかつて美咲と歩いた都市であり、両親が今も暮らす故郷の町だった。一つ一つの光の中に、彼の愛した人々が息づき、それぞれの人生を紡いでいる。その光は、彼が決して置き去りにしてきたのではない、地球上の全ての営みの証だった。

健の心臓が、鼓動を早める。彼は窓ガラスにそっと手のひらを置いた。冷たいガラスの向こうに、温かい命の輝きがある。彼の孤独は、この広大な宇宙の中で、地球という揺りかごの一部であり、彼の人生もまたその一部なのだと、彼は深く理解した。

過去への後悔が、感謝へと変わっていく。彼は深呼吸をし、宇宙の匂いを吸い込んだ。宇宙は彼から多くのものを奪ったかもしれないが、同時に、彼にこの比類ない視点を与えてくれた。この場所から、彼の人生の全てを、愛しい地球を、そしてそこに生きる人々を、俯瞰して見つめることができる。それは、彼にしかできない、彼にしか許されない特権だった。

彼の表情に、穏やかな笑みが浮かんだ。彼はもう、孤独ではなかった。宇宙の広がりと、自身の内面が、今、静かに調和している。彼の人生は、決して間違っていなかった。そして、失ったものがあるからこそ、今ここにあるものの尊さを知ることができたのだ。

地球の夜明けが近づいてくる。薄明かりの中で、青い大理石は息を吹き返すように、ゆっくりと、しかし力強く輝き始めた。健は静かにその光景を見つめ、未来への静かな希望を胸に抱いた。彼の旅は、まだ終わらない。そして、この孤独な宇宙飛行士は、今、心から満たされていた。
```

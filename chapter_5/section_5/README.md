# Chapter 5 Section 6: パイプライン型AIエージェント

## 概要

このプロジェクトは、**パイプライン型AIエージェント**パターンを実装した契約書リスクコンプライアンス評価システムです。複雑なLLM処理を一連のステージに分割し、各ステージで特定の役割を持つエージェントが順番にデータを処理していく設計パターンを示します。

パイプラインは契約書ドキュメントを読み込み、その構造（章・条）を抽出し、各セクションのリスクを評価し、包括的なコンプライアンスレポートを生成します。各ステージの出力が次のステージの入力となる直線的なフロー構造により、処理の透明性、保守性、スケーラビリティを実現します。

## 機能

- **抽出ステージ**: 契約書テキストを解析し、章・条・当事者情報を構造化データとして抽出
- **リスク評価ステージ**: 各条文のリスクレベル（low/medium/high/critical）と10カテゴリのリスク分類を評価
- **レポート生成ステージ**: 評価結果を統合し、エグゼクティブサマリー・推奨事項を含む包括的レポートを生成
- **構造化出力**: Pydanticモデルによる型安全なLLMレスポンス
- **非同期並行処理**: リスク評価ステージでセマフォベースの並行処理（最大20並列）
- **Markdown出力**: 日本語のコンプライアンスレポートをMarkdown形式で出力

## プロジェクト構成

### ディレクトリ構成

```
chapter_5/section_6/
├── src/
│   ├── __init__.py
│   ├── main.py                         # CLIエントリーポイント
│   ├── config.py                       # 環境設定
│   ├── logger.py                       # ロギングユーティリティ
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py               # OpenAIモデル定義
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py                    # Pydanticデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py                   # 各ステージのプロンプトテンプレート
│   ├── layer/
│   │   ├── __init__.py
│   │   ├── base.py                     # 抽象基底エージェントクラス
│   │   └── contract_pipeline/
│   │       ├── __init__.py
│   │       ├── extraction.py           # 抽出ステージエージェント
│   │       ├── risk_scoring.py         # リスク評価ステージエージェント
│   │       └── report.py               # レポート生成ステージエージェント
│   └── service/
│       ├── __init__.py
│       └── service.py                  # LangGraphパイプラインオーケストレーション
├── data/
│   ├── contract_0.md                   # サンプル契約書（ソフトウェア開発委託）
│   ├── contract_1.md                   # サンプル契約書
│   ├── contract_2.md                   # サンプル契約書
│   └── contract_3.md                   # サンプル契約書
├── outputs/                            # 生成レポート出力先
├── .envrc.example                      # 環境変数テンプレート
├── pyproject.toml                      # プロジェクト依存関係
├── Makefile                            # 開発コマンド
├── CLAUDE.md                           # プロジェクト技術仕様
└── README.md                           # このファイル
```

### アーキテクチャ

```
+------------------------------------------------------------------+
|                    Contract Pipeline                              |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------+                                            |
|  |   Input Stage     |  契約書ファイルを読み込み                   |
|  |   (main.py)       |                                            |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Extraction Stage  |  文書構造を解析                             |
|  | (extraction.py)   |  -> 章・条を抽出                           |
|  |                   |  -> 当事者を特定                           |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Risk Scoring      |  各条文を評価（並列処理）                   |
|  | Stage             |  -> リスクレベル判定                       |
|  | (risk_scoring.py) |  -> カテゴリ分類                           |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Report Stage      |  最終レポート生成                           |
|  | (report.py)       |  -> エグゼクティブサマリー                  |
|  |                   |  -> 推奨事項                               |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|        [Output]         Markdownコンプライアンスレポート            |
|                                                                   |
+------------------------------------------------------------------+
```

### 実装の詳細

#### パイプライン状態管理

LangGraphのStateGraphを使用して、各ステージ間でデータを受け渡します：

```python
class ContractPipelineState(TypedDict):
    contract_input: ContractInput           # 入力: 契約書データ
    extraction_output: ExtractionOutput     # 抽出ステージの出力
    risk_scoring_output: RiskScoringOutput  # リスク評価ステージの出力
    compliance_report: ComplianceReport     # 最終レポート
    current_stage: str                      # 現在のステージ名
    pending_sections: list[ContractSection] # 処理待ちセクション
```

#### パイプライングラフ構築

```python
def create_contract_pipeline_graph() -> StateGraph:
    graph = StateGraph(ContractPipelineState)

    graph.add_node("extraction", extraction_stage_node)
    graph.add_node("risk_scoring", risk_scoring_stage_node)
    graph.add_node("report", report_stage_node)

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "risk_scoring")
    graph.add_edge("risk_scoring", "report")
    graph.add_edge("report", END)

    return graph.compile()
```

**ポイント**: 各ステージは独立したノードとして実装され、`add_edge`で直線的に接続されます。これにより、特定のステージだけを修正・テストすることが容易になります。

#### リスク評価カテゴリ

システムは10種類のリスクカテゴリで契約書を評価します：

| カテゴリ | 説明 |
|---------|------|
| intellectual_property | 知的財産権に関するリスク |
| liability | 責任・損害賠償に関するリスク |
| confidentiality | 秘密保持に関するリスク |
| termination | 契約解除に関するリスク |
| payment | 支払条件に関するリスク |
| compliance | 法令遵守に関するリスク |
| warranty | 保証に関するリスク |
| indemnification | 補償に関するリスク |
| dispute_resolution | 紛争解決に関するリスク |
| other | その他のリスク |

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - langchain-openai>=1.1.0
  - langgraph>=1.0.0
  - pydantic>=2.12.2
  - click>=8.3.0
  - python-dotenv>=1.1.1
  - openai>=2.4.0

### セットアップ

1. **環境変数ファイルの作成**

```bash
cp .envrc.example .envrc
```

2. **APIキーの設定**

`.envrc`を編集し、OpenAI APIキーを設定：

```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

3. **依存関係のインストール**

```bash
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# 契約書ファイルを指定して実行
python -m src.main -c data/contract_0.md

# モデルを指定
python -m src.main -c data/contract_0.md -m gpt-4o

# 出力ディレクトリを指定
python -m src.main -c data/contract_0.md -od reports
```

#### CLIオプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| --contract-file | -c | 契約書ファイルパス（必須） | - |
| --model | -m | 使用するOpenAIモデル | gpt-4o-mini |
| --output-directory | -od | レポート出力ディレクトリ | outputs |
| --help | - | ヘルプ表示 | - |

#### 利用可能なモデル

- gpt-4o, gpt-4o-mini
- gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
- gpt-5, gpt-5-mini, gpt-5-nano

#### ヘルプの表示

```bash
python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

  Contract Risk Compliance Pipeline - A Pipeline AI Agent System

Options:
  -m, --model [gpt-5|gpt-5-mini|gpt-5-nano|gpt-4.1|gpt-4.1-mini|gpt-4.1-nano|gpt-4o|gpt-4o-mini]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  -c, --contract-file PATH        Path to the contract document file.
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下のような構造のMarkdownレポートが生成されます：

**ファイル名**: `outputs/compliance_report_report_xxxxxxxx.md`

```markdown
# 契約書リスクコンプライアンスレポート

**契約書**: ソフトウェア開発業務委託契約書
**レポートID**: report_5905d471
**生成日時**: 2025-12-06 10:22:04

---

## エグゼクティブサマリー

### 総合評価
- **コンプライアンス状態**: ❌ 不適合
- **リスクスコア**: 78/100

本契約書は主要な業務要件を包含する一方で、知的財産権の帰属条件...

### 主要な懸念事項
- 知的財産権（著作権等）の帰属が検収・支払完了を条件としており...
- 検査・検収プロセスに黙示的承認（黙示検収）が含まれ...

### 即時対応が必要な事項
- ⚠️ 重要な合意前に署名を行わない
- ⚠️ 知的財産権条項を改定し、移転タイミングを確定する

---

## リスク分析
...

## セクション別評価詳細
...

## 総合的な推奨事項
1. 知的財産権条項の明確化
2. 検収・受入手続の整備
...

## 結論
...
```

**実行ログ例**:
```
[INFO] Contract Risk Compliance Pipeline
Model: gpt-4o-mini
Contract file: data/contract_0.md
Output directory: outputs
[INFO] ============================================================
[INFO] PIPELINE LAYER - ExtractionAgent: Extracting contract structure
[INFO] ============================================================
[INFO] Processing contract: contract_12345678
[INFO] Received structured response from LLM
[INFO] Extraction complete: 20 sections
[INFO] ============================================================
[INFO] PIPELINE LAYER - RiskScoringAgent: Risk Scoring
[INFO] ============================================================
[INFO] Assessing 20 sections concurrently (limit: 20)...
[INFO] Assessing section: 第1条 目的
[INFO] Completed: 第1条 - Risk: medium
...
[INFO] Risk scoring complete: 85 findings, 12 high/critical
[INFO] ============================================================
[INFO] PIPELINE LAYER - ReportAgent: Report Generation
[INFO] ============================================================
[INFO] Generating report for: ソフトウェア開発業務委託契約書
[INFO] Report generated: report_5905d471 - Status: non_compliant
[INFO] ================================================================================
[INFO] COMPLIANCE REPORT GENERATED SUCCESSFULLY
[INFO] Report ID: report_5905d471
[INFO] Overall Status: non_compliant
[INFO] Risk Score: 78/100
[INFO] ================================================================================
[INFO] Report saved: outputs/compliance_report_report_5905d471.md
```

## 開発コマンド

```bash
# コードリント
make lint

# コードフォーマット
make fmt

# リント＆フォーマット
make fix

# 型チェック
make mypy
```

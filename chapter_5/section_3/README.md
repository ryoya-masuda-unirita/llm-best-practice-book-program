# Chapter 5 Section 3: マルチエージェント契約書レビューシステム

## 概要

本プロジェクトは、LangGraphとGoogle Geminiを活用したマルチエージェントAIシステムによる契約書レビューシステムです。6つの専門エージェントが協調して契約書を分析し、リスク評価、標準テンプレートとの比較、包括的なレビューレポートを生成します。

複雑なタスクを分解して専門エージェントに委任し、結果を統合するマルチAIエージェントアーキテクチャパターンを実装しています。オーケストレーター・ワーカーパターンにより、Document Parserによる条項抽出後、Clause Classifier、Risk Assessment、Diff Checkerが並列で動作し、効率的な処理を実現します。

## 機能

- **契約書構造解析**: 契約書テキストを条項単位で構造化データに変換
- **条項分類**: 守秘義務、責任制限、知的財産など8カテゴリへの自動分類
- **リスク評価**: 受領者（乙）視点での1-10スケールリスクスコアリング
- **差分検出**: 自社標準テンプレートとの差分を追加/削除/修正として検出
- **修正案提案**: 高リスク条項に対する修正文言と交渉ポイントの提案
- **レポート生成**: 非法務ステークホルダー向けMarkdown形式レポート出力

## プロジェクト構成

### ディレクトリ構成

```
chapter_5/section_3/
├── src/
│   ├── __init__.py
│   ├── main.py                      # CLIエントリーポイント
│   ├── config.py                    # 環境設定
│   ├── logger.py                    # ログ設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py            # LLMクライアント・モデル定義
│   ├── model/
│   │   ├── __init__.py
│   │   └── multi_agent_model.py     # Pydanticデータモデル・AgentState
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── multi_agent_prompt.py    # 各エージェント用システムプロンプト
│   └── service/
│       ├── __init__.py
│       └── multi_agent_service.py   # LangGraphパイプライン実装
├── example/                          # サンプル契約書・テンプレート
│   ├── standard_nda_template.md
│   ├── sample_nda.md
│   ├── sample_nda_02.md
│   ├── sample_nda_03.md
│   ├── standard_purchase_order_template.md
│   ├── sample_purchase_order_01.md
│   ├── sample_purchase_order_02.md
│   ├── standard_consulting_template.md
│   ├── sample_consulting_01.md
│   └── sample_consulting_02.md
├── outputs/                          # 生成されたレビューレポート
├── pyproject.toml
├── Makefile
├── .envrc.example
└── README.md
```

### アーキテクチャ

```
+-------------------------------------------------------------------------+
|                   オーケストレーター・ワーカーパイプライン                    |
+-------------------------------------------------------------------------+
|                                                                          |
|  +----------------+    +-------------------+                             |
|  |   契約書入力    |--->|   Orchestrator    |                             |
|  | (Contract/     |    |      Agent        |                             |
|  |  Template)     |    +--------+----------+                             |
|  +----------------+             |                                        |
|                                 v                                        |
|                    +-------------------+                                 |
|                    | Document Parser   |                                 |
|                    |     Worker        |                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|          +------------------+------------------+                         |
|          |                  |                  |                         |
|          v                  v                  v                         |
|  +---------------+  +---------------+  +---------------+                 |
|  |    Clause     |  |     Risk      |  |     Diff      |  (並列処理)     |
|  |  Classifier   |  |  Assessment   |  |    Checker    |                 |
|  |    Worker     |  |    Worker     |  |    Worker     |                 |
|  +-------+-------+  +-------+-------+  +-------+-------+                 |
|          |                  |                  |                         |
|          +------------------+------------------+                         |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |     Collector     |                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |    Amendment      |                                 |
|                    |    Proposer       |                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |   Synthesizer     |                                 |
|                    | (Report Generator)|                                 |
|                    +--------+----------+                                 |
|                             |                                            |
|                             v                                            |
|                    +-------------------+                                 |
|                    |  レビューレポート   |                                 |
|                    |   (Markdown)      |                                 |
|                    +-------------------+                                 |
+-------------------------------------------------------------------------+
```

### エージェント一覧

| エージェント | 機能 | 出力 |
|------------|------|------|
| Orchestrator | ワークフロー計画・タスク割当 | `orchestrator_plan` |
| Document Parser | 契約書を条項ごとに構造化 | `parsed_clauses` |
| Clause Classifier | 条項をカテゴリ分類 | `clause_categories` |
| Risk Assessment | リスクレベル評価（1-10） | `risk_assessments` |
| Diff Checker | 標準テンプレートとの差分検出 | `diffs` |
| Amendment Proposer | 高リスク条項の修正案提案 | `amendments` |
| Report Generator | 最終Markdownレポート生成 | `final_report` |

### データモデル

```python
# 条項データ
class ContractClause(BaseModel):
    clause_number: str   # 例: "第1条"
    title: str           # 条項タイトル
    content: str         # 条項本文

# カテゴリ分類
class ClauseCategory(BaseModel):
    clause_number: str
    category: str        # 守秘義務, 責任制限, 知的財産, etc.
    reason: str

# リスク評価
class RiskAssessment(BaseModel):
    clause_number: str
    risk_level: str      # 高, 中, 低
    risk_score: int      # 1-10
    risk_factors: list[str]
    explanation: str

# 差分
class ClauseDiff(BaseModel):
    clause_number: str
    diff_type: str       # 追加, 削除, 修正, 一致
    original_text: str
    standard_text: str
    summary: str

# 修正提案
class AmendmentProposal(BaseModel):
    clause_number: str
    original_text: str
    proposed_text: str
    rationale: str
    negotiation_points: list[str]
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **主要依存ライブラリ**:
  - `langchain-google-genai>=3.2.0` - LangChain Google Gemini統合
  - `langgraph>=1.0.0` - マルチエージェントグラフオーケストレーション
  - `anthropic>=0.74.1` - Anthropic APIクライアント
  - `pydantic>=2.12.2` - データバリデーション・モデル
  - `click>=8.3.0` - CLIフレームワーク
  - `python-dotenv>=1.1.1` - 環境変数管理

### セットアップ

```bash
# 環境変数テンプレートをコピー
cp .envrc.example .envrc

# .envrcを編集してAPIキーを設定
GEMINI_API_KEY=<your_gemini_api_key_here>

# 依存関係をインストール
uv sync
```

### 使用方法

```bash
# 基本的な使用方法
python -m src.main -c <契約書ファイル> -t <テンプレートファイル>

# 例: NDA契約書のレビュー
python -m src.main \
  -c example/sample_nda.md \
  -t example/standard_nda_template.md

# モデル選択とカスタム出力ディレクトリ
python -m src.main \
  -m gemini-2.5-flash \
  -c example/sample_consulting_02.md \
  -t example/standard_consulting_template.md \
  -od reports
```

### CLIオプション

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|-------|------|-----------|------|
| `--contract-file` | `-c` | Yes | - | 契約書ファイルパス（Markdown形式） |
| `--template-file` | `-t` | Yes | - | 標準テンプレートファイルパス |
| `--model` | `-m` | No | `gemini-2.5-pro` | 使用モデル（`gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`） |
| `--output-directory` | `-od` | No | `outputs` | 出力ディレクトリ |

### 出力例

レビュー実行後、以下のようなMarkdownレポートが生成されます:

```markdown
# 契約書レビューレポート

## エグゼクティブサマリー
**総合リスクレベル**: 高
**総合リスクスコア**: 7.5 / 10.0

本契約書には受領者（乙）にとって重大なリスクを伴う条項が複数含まれています...

## 主要な論点
1. 第4条：再委託に関する責任免除条項
2. 第7条：過度に低い損害賠償上限
3. 第9条：乙の独自開発知財の無償譲渡
4. 第10条：無制限の監査権限

## 推奨アクション
1. 相手方に修正依頼（第4条、第7条、第9条）
2. 法務部門の詳細レビュー必要
3. 上長決裁が必要

## リスク評価詳細

### 高リスク条項

#### 第4条
- **リスクスコア**: 9/10
- **リスク要因**:
  - 再委託先の選定権限が乙に無制限
  - 再委託先の行為に対する責任免除
- **詳細説明**: 秘密情報の管理において...

## 修正提案

### 第7条
**現行文言**:
> 乙は甲に対し、直接損害に限り、上限1万円までの賠償責任を負うものとする。

**修正案**:
> 乙は甲に対し、直接損害について、本契約に基づく報酬総額を上限として賠償責任を負うものとする。

**修正理由**: 損害賠償上限が著しく低く設定されており...

**交渉ポイント**:
- 業界標準では報酬総額が上限とされることが多い
- 双方にとって予測可能性が高まるメリットがある
```

## 開発コマンド

```bash
# ruffによるリント
make lint

# ruffによるフォーマット
make fmt

# リントとフォーマットを両方実行
make fix

# mypyによる型チェック
make mypy
```

## 実装のポイント

### オーケストレーター・ワーカーパターン

本システムはLangGraphの`Send` APIを使用したオーケストレーター・ワーカーパターンを採用しています。

```python
def dispatch_to_parallel_analyzers(state: AgentState) -> list[Send]:
    """並列分析ワーカーへのタスクディスパッチ"""
    return [
        Send("clause_classifier_worker", {...}),
        Send("risk_assessment_worker", {...}),
        Send("diff_checker_worker", {...}),
    ]
```

**ポイント**: Document Parser完了後、Clause Classifier、Risk Assessment、Diff Checkerが並列実行され、Collectorで結果を集約します。

### エージェント間状態共有

エージェント間はTypedDictベースの`AgentState`で状態を共有します。

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    contract_text: str
    standard_template: str
    parsed_clauses: Annotated[list[dict], reduce_list]
    clause_categories: Annotated[list[dict], reduce_list]
    risk_assessments: Annotated[list[dict], reduce_list]
    diffs: Annotated[list[dict], reduce_list]
    amendments: Annotated[list[dict], reduce_list]
    final_report: str | None
    orchestrator_plan: OrchestratorPlan | None
    completed_tasks: Annotated[list[str], operator.add]
    current_phase: str
```

**ポイント**: `reduce_list`カスタムリデューサーにより、並列ワーカーからの結果更新を適切にマージします。

### リスク評価基準

受領者（乙）の立場から以下の観点でリスクを評価:

| 観点 | 説明 |
|-----|------|
| 一方的な不利益 | 受領者に一方的に不利な条件 |
| 過度な義務 | 通常の商慣習を超えた義務 |
| 曖昧な表現 | 紛争原因となりうる解釈余地 |
| 実務上の困難 | 遵守困難な条件 |
| 法的リスク | 法令違反・公序良俗違反の可能性 |
| 財務リスク | 過大な損害賠償・違約金 |

### サンプル契約書

`example/`ディレクトリには、システムのリスク検出能力をテストするため、意図的に問題のある条項を含む契約書が用意されています:

- 無制限の責任条項
- 一方的な知財帰属
- 無制限の監査権限
- 過少な損害賠償上限

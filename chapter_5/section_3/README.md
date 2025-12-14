# Chapter 5 Section 3: マルチAIエージェント

## 概要

本プロジェクトは、マルチAIエージェントアーキテクチャを用いた契約書レビューシステムです。単一のLLMでは対応が困難な複雑な契約書レビュータスクを、6つの専門エージェントが協調して処理することで、高精度なリスク評価と修正提案を実現します。

マルチAIエージェントは、それぞれが特定の役割や専門知識を持つ複数のAIエージェントを協調させて動作させるアーキテクチャパターンです。タスクの分解、各エージェントへの割り当て、そして結果の統合という一連のプロセスを通じて、システム全体として高度な問題解決能力を実現します。

本システムでは、契約書のアップロードから、条項の抽出、カテゴリ分類、リスク評価、標準契約との差分検出、修正案の提案、最終レポートの生成までを自動化します。法務部門の支援ツールとして、「どこを重点的に確認すべきか」のナビゲーションを提供します。

## 機能

- **契約書構造解析**: マークダウン形式の契約書を条項ごとに構造化データとして抽出
- **条項カテゴリ分類**: 守秘義務、損害賠償、再委託、知的財産など9種類のカテゴリに自動分類
- **リスク評価**: 各条項を1-10のスコアでリスク評価し、リスク要因を特定
- **標準契約との差分検出**: 自社標準テンプレートとの差分を検出し、追加・削除・修正を明示
- **修正案の自動提案**: 高リスク条項に対する修正文案と交渉ポイントを提案
- **レビューレポート生成**: 非法務ステークホルダー向けのエグゼクティブサマリーを含む包括的レポートを生成

## プロジェクト構成

### ディレクトリ構成

```
chapter_4/section_3/
├── src/
│   ├── __init__.py
│   ├── main.py                      # CLIエントリーポイント
│   ├── config.py                    # 環境設定
│   ├── logger.py                    # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py            # Anthropic LLMクライアント
│   ├── model/
│   │   ├── __init__.py
│   │   └── multi_agent_model.py     # データモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── multi_agent_prompt.py    # 各エージェントのプロンプト
│   └── service/
│       ├── __init__.py
│       └── multi_agent_service.py   # マルチエージェントサービス
├── example/                          # サンプル契約書
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
├── outputs/                          # 出力レポート保存先
├── pyproject.toml
├── .envrc.example
├── CLAUDE.md
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Contract Review Pipeline                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Contract   │───▶│  Document    │───▶│   Clause     │               │
│  │    Input     │    │   Parser     │    │  Classifier  │               │
│  └──────────────┘    │   Agent      │    │    Agent     │               │
│                      └──────────────┘    └──────┬───────┘               │
│                                                 │                        │
│                                                 ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Standard   │───▶│    Diff      │◀───│    Risk      │               │
│  │   Template   │    │   Checker    │    │  Assessment  │               │
│  └──────────────┘    │    Agent     │    │    Agent     │               │
│                      └──────┬───────┘    └──────────────┘               │
│                             │                                            │
│                             ▼                                            │
│                      ┌──────────────┐    ┌──────────────┐               │
│                      │  Amendment   │───▶│   Report     │               │
│                      │  Proposer    │    │  Generator   │               │
│                      │    Agent     │    │    Agent     │               │
│                      └──────────────┘    └──────┬───────┘               │
│                                                 │                        │
│                                                 ▼                        │
│                                          ┌──────────────┐               │
│                                          │   Review     │               │
│                                          │   Report     │               │
│                                          └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. エージェント状態管理 (`src/model/multi_agent_model.py`)

LangGraphの`TypedDict`を使用して、エージェント間で共有される状態を管理します。

```python
class AgentState(TypedDict):
    """State for the multi-agent contract review system."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    contract_text: str
    standard_template: str
    parsed_clauses: list[dict]
    clause_categories: list[dict]
    risk_assessments: list[dict]
    diffs: list[dict]
    amendments: list[dict]
    final_report: str | None
```

**ポイント**: 各エージェントの出力が次のエージェントの入力となるパイプライン構造を、`AgentState`で一元管理しています。

#### 2. データモデル (`src/model/multi_agent_model.py`)

契約書レビューの各段階で生成されるデータをPydanticモデルで定義しています。

```python
class RiskAssessment(BaseModel):
    """Risk assessment for a clause."""

    clause_number: str = Field(..., description="Clause number")
    risk_level: str = Field(..., description="Risk level: 高, 中, 低")
    risk_score: int = Field(..., ge=1, le=10, description="Risk score from 1 to 10")
    risk_factors: list[str] = Field(..., description="List of risk factors identified")
    explanation: str = Field(..., description="Detailed explanation of risk assessment")
```

**ポイント**: `Field`のバリデーション機能（`ge=1, le=10`）により、LLMの出力が期待される範囲内であることを保証します。

#### 3. エージェントプロンプト (`src/prompt/multi_agent_prompt.py`)

各専門エージェントのシステムプロンプトと、動的なユーザープロンプト生成関数を定義しています。

```python
RISK_ASSESSMENT_SYSTEM_PROMPT = """あなたは契約リスクを評価する専門AIエージェントです。

## 役割
各契約条項のリスクレベルを評価し、リスク要因を特定します。

## 評価基準
以下の観点からリスクを評価してください：

1. **一方的な不利益**: 受領者（乙）に一方的に不利な条件
2. **過度な義務**: 通常の商慣習を超えた義務の課せられ方
3. **曖昧な表現**: 解釈の余地が大きく紛争の原因になりうる表現
4. **実務上の困難**: 実際の業務遂行上、遵守が困難な条件
5. **法的リスク**: 法令違反や公序良俗に反する可能性
6. **財務リスク**: 過大な損害賠償、違約金のリスク

## リスクレベル
- 高（スコア7-10）: 直ちに修正交渉が必要
- 中（スコア4-6）: 注意が必要、可能であれば修正を検討
- 低（スコア1-3）: 標準的な条項、特段の問題なし
"""
```

**ポイント**: 各エージェントの役割と評価基準を明確に定義することで、一貫性のある分析結果を得られます。

#### 4. LangGraphによるパイプライン構築 (`src/service/multi_agent_service.py`)

6つのエージェントノードを順次接続するグラフを構築します。

```python
def create_contract_review_graph() -> StateGraph:
    """Create the multi-agent contract review graph."""
    graph = StateGraph(AgentState)

    # ノードの追加
    graph.add_node("document_parser", document_parser_node)
    graph.add_node("clause_classifier", clause_classifier_node)
    graph.add_node("risk_assessment", risk_assessment_node)
    graph.add_node("diff_checker", diff_checker_node)
    graph.add_node("amendment_proposer", amendment_proposer_node)
    graph.add_node("report_generator", report_generator_node)

    # エントリーポイントの設定
    graph.set_entry_point("document_parser")

    # エッジの定義（パイプライン構造）
    graph.add_edge("document_parser", "clause_classifier")
    graph.add_edge("clause_classifier", "risk_assessment")
    graph.add_edge("risk_assessment", "diff_checker")
    graph.add_edge("diff_checker", "amendment_proposer")
    graph.add_edge("amendment_proposer", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()
```

**ポイント**: LangGraphの`StateGraph`を使用することで、エージェント間のデータフローを宣言的に定義できます。

#### 5. LLM応答のJSON抽出 (`src/service/multi_agent_service.py`)

LLMの応答からJSONを安全に抽出するユーティリティ関数を実装しています。

```python
def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from LLM response text."""
    # ```json ... ``` 形式の抽出を試みる
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 直接JSONオブジェクトを探す
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text

    return json.loads(json_str)
```

**ポイント**: LLMの出力形式の揺らぎに対応するため、複数のパターンでJSON抽出を試みます。

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要な依存ライブラリ:
  - `anthropic>=0.74.1` - Anthropic API クライアント
  - `langchain-anthropic>=1.2.0` - LangChain Anthropic統合
  - `langgraph>=1.0.0` - マルチエージェントグラフ構築
  - `pydantic>=2.12.2` - データバリデーション
  - `click>=8.3.0` - CLIフレームワーク

### セットアップ

1. 環境変数の設定

```bash
cp .envrc.example .envrc
```

`.envrc`を編集してAPIキーを設定:

```
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. 依存関係のインストール

```bash
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
python -m src.main -c <契約書ファイル> -t <テンプレートファイル>
```

#### CLIオプション

```
Usage: python -m src.main [OPTIONS]

  Contract Review Multi-Agent System

  This system reviews contract documents using multiple specialized AI agents:

  1. Document Parser Agent - Parses contract into structured clauses
  2. Clause Classifier Agent - Categorizes each clause
  3. Risk Assessment Agent - Evaluates risk levels
  4. Diff Checker Agent - Compares with standard template
  5. Amendment Proposer Agent - Suggests modifications for high-risk clauses
  6. Report Generator Agent - Creates comprehensive review report

Options:
  -m, --model [claude-sonnet-4-5|claude-opus-4-1]
                                  The Anthropic model to use for the review.
  -od, --output-directory PATH    The directory to save output files.
  -c, --contract-file PATH        Path to the contract file to review (markdown format). [required]
  -t, --template-file PATH        Path to the standard contract template file (markdown format). [required]
  --help                          Show this message and exit.
```

#### 実行例

**NDA契約書のレビュー:**

```bash
python -m src.main \
  -c example/sample_nda.md \
  -t example/standard_nda_template.md \
  -od outputs
```

**物品売買契約書のレビュー:**

```bash
python -m src.main \
  -c example/sample_purchase_order_01.md \
  -t example/standard_purchase_order_template.md
```

**コンサルティング契約書のレビュー（モデル指定）:**

```bash
python -m src.main \
  -m claude-opus-4-1 \
  -c example/sample_consulting_02.md \
  -t example/standard_consulting_template.md \
  -od reports
```

### 出力例

レビュー結果は`outputs/`ディレクトリにMarkdown形式で保存されます。

```markdown
# 契約書レビューレポート

## エグゼクティブサマリー
**総合リスクレベル**: 高
**総合リスクスコア**: 7.5 / 10.0

本契約書には、受領者（乙）にとって重大なリスクを含む条項が複数存在します。
特に、第4条（再委託）、第7条（損害賠償）、第9条（知的財産権）、第11条（契約解除）
については、自社標準から大きく逸脱しており、早急な修正交渉が必要です。

## 主要な論点
1. 再委託条項で受領者の責任が免除されており、管理リスクが高い
2. 損害賠償の上限が1万円と極端に低く設定されている
3. 独自開発した知的財産も開示者に帰属する条項がある
4. 事前通知なしの監査権限が付与されている

## 推奨アクション
1. 相手方に修正依頼（第4条、第7条、第9条、第11条）
2. 上長決裁が必要
3. 法務部門の詳細レビュー必要

## リスク評価詳細

### 高リスク条項

#### 第7条
- **リスクスコア**: 9/10
- **リスク要因**:
  - 損害賠償上限が1万円と極端に低い
  - 間接損害・逸失利益が完全に免責されている
- **詳細説明**: 契約違反による損害が発生しても、実質的な補償を受けられない...

## 修正提案

### 第7条
**現行文言**:
> 乙が本契約に違反し、甲に損害を与えた場合、乙は甲に対し、直接損害に限り、
> 上限1万円までの賠償責任を負うものとする。

**修正案**:
> 甲または乙が本契約に違反し、相手方に損害を与えた場合、違反当事者は
> 相手方に対し、通常かつ直接の損害について賠償責任を負う。

**修正理由**: 双方対等な損害賠償責任とし、適切な賠償範囲を設定する

**交渉ポイント**:
- 現行の上限1万円では実質的に無責任であり、契約の拘束力が弱まる
- 双方向の義務とすることで、相手方にもメリットがある
```

## サンプル契約書

`example/`ディレクトリには、3種類の契約書タイプのサンプルとテンプレートが含まれています：

| 契約タイプ | テンプレート | サンプル |
|-----------|-------------|---------|
| NDA（秘密保持契約） | `standard_nda_template.md` | `sample_nda.md`, `sample_nda_02.md`, `sample_nda_03.md` |
| 物品売買契約 | `standard_purchase_order_template.md` | `sample_purchase_order_01.md`, `sample_purchase_order_02.md` |
| コンサルティング契約 | `standard_consulting_template.md` | `sample_consulting_01.md`, `sample_consulting_02.md` |

サンプル契約書には意図的に問題のある条項（一方的な責任制限、過度な知的財産権の帰属など）が含まれており、システムの動作確認に使用できます。

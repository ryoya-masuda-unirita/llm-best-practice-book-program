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
uv run python -m src.main -c <契約書ファイル> -t <テンプレートファイル>

# 例: NDA契約書のレビュー
uv run python -m src.main \
  -c example/sample_nda.md \
  -t example/standard_nda_template.md

# モデル選択とカスタム出力ディレクトリ
uv run python -m src.main \
  -m GEMINI_2_5_FLASH \
  -c example/sample_consulting_02.md \
  -t example/standard_consulting_template.md \
  -od reports
```

### CLIオプション

```bash
$ uv run python -m src.main --help                                                                          
Usage: python -m src.main [OPTIONS]

  Contract Review Multi-Agent System

  This system reviews contract documents using multiple specialized AI agents:

  1. Document Parser Agent - Parses contract into structured clauses 2. Clause
  Classifier Agent - Categorizes each clause 3. Risk Assessment Agent -
  Evaluates risk levels 4. Diff Checker Agent - Compares with standard
  template 5. Amendment Proposer Agent - Suggests modifications for high-risk
  clauses 6. Report Generator Agent - Creates comprehensive review report

  Examples:

      python -m src.main -c example/sample_nda.md -t
      example/standard_nda_template.md

      python -m src.main -m claude-sonnet-4-6 -c contract.md -t template.md
      -od reports

Options:
  -m, --model [GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The Google Gemini model to use for the
                                  review.
  -od, --output-directory PATH    The directory to save output files.
  -c, --contract-file PATH        Path to the contract file to review
                                  (markdown format).  [required]
  -t, --template-file PATH        Path to the standard contract template file
                                  (markdown format).  [required]
  --help                          Show this message and exit.
```

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|-------|------|-----------|------|
| `--contract-file` | `-c` | Yes | - | 契約書ファイルパス（Markdown形式） |
| `--template-file` | `-t` | Yes | - | 標準テンプレートファイルパス |
| `--model` | `-m` | No | `GEMINI_2_5_FLASH` | 使用モデル（GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE） |
| `--output-directory` | `-od` | No | `outputs` | 出力ディレクトリ |

### 出力例

```bash
$ uv run python -m src.main \
  -m GEMINI_2_5_FLASH \
  -c example/sample_consulting_02.md \
  -t example/standard_consulting_template.md \
  -od reports
[2026-02-07 09:06:46,741] [INFO] [__main__] [main.py:78] [main] Contract Review Multi-Agent System
Model: gemini-2.5-flash
Contract file: example/sample_consulting_02.md
Template file: example/standard_consulting_template.md
Output directory: reports

[2026-02-07 09:06:46,745] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:632] [run_contract_review] Starting contract review multi-agent system
[2026-02-07 09:06:46,745] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:633] [run_contract_review] Using model: gemini-2.5-flash
[2026-02-07 09:06:46,745] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:586] [create_contract_review_graph] Creating orchestrator-worker contract review graph...
[2026-02-07 09:06:46,746] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:617] [create_contract_review_graph] Orchestrator-worker graph created successfully
[2026-02-07 09:06:46,753] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:288] [orchestrator_node] Orchestrator Agent: Planning contract review workflow...
[2026-02-07 09:06:56,102] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:310] [orchestrator_node] Orchestrator Agent: Received plan from LLM
[2026-02-07 09:06:56,102] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:311] [orchestrator_node] Orchestrator Agent: Strategy - レビュー対象契約書を包括的に解析し、自社標準テンプレートとの差異を明確化する。特に、契約期間の自動更新、報酬体系、費用負担、再委託の可否、成果物 の取り扱いといった主要な商業条件およびリスク条項に焦点を当て、潜在的なリスクを特定し、適切な修正案を提案する。
[2026-02-07 09:06:56,102] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:312] [orchestrator_node] Orchestrator Agent: Focus areas - ['第3条（契約期間）: 自動更新条項の有無と条件', '第4条（報酬）: 固定報酬と成功報酬の支払い条件、消費税の扱い', '第5条（費用負担）: 費用負担の 範囲と例外規定', '第7条（再委託の禁止）: 再委託の可否と標準テンプレートとの差異', '第9条（成果物）: 成果物の定義と帰属（プレビューにはないが、レビュー時に確認すべき重要事項）', '第6条（稼働場所）: 稼働場所の指定と甲の規則への準拠義務']
[2026-02-07 09:06:56,102] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:313] [orchestrator_node] Orchestrator Agent: Planned 6 tasks
[2026-02-07 09:06:56,103] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:335] [dispatch_to_document_parser] Dispatching to Document Parser...
[2026-02-07 09:06:56,104] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:426] [document_parser_worker] Document Parser Worker: Parse contract into clauses
[2026-02-07 09:06:56,104] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:62] [document_parser_node] Document Parser Agent: Starting document parsing...
[2026-02-07 09:07:10,063] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:79] [document_parser_node] Document Parser Agent: Received response from LLM
[2026-02-07 09:07:10,064] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:81] [document_parser_node] Document Parser Agent: Parsed 22 clauses
[2026-02-07 09:07:10,064] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:358] [dispatch_to_parallel_analyzers] Dispatching to parallel analyzers...
[2026-02-07 09:07:10,065] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:436] [clause_classifier_worker] Clause Classifier Worker: Classify clauses into categories
[2026-02-07 09:07:10,065] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:90] [clause_classifier_node] Clause Classifier Agent: Starting classification...
[2026-02-07 09:07:10,065] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:446] [risk_assessment_worker] Risk Assessment Worker: Assess risk for each clause
[2026-02-07 09:07:10,065] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:122] [risk_assessment_node] Risk Assessment Agent: Starting risk assessment...
[2026-02-07 09:07:10,071] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:456] [diff_checker_worker] Diff Checker Worker: Check differences with standard template
[2026-02-07 09:07:10,071] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:154] [diff_checker_node] Diff Checker Agent: Starting diff check...
[2026-02-07 09:07:26,656] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:111] [clause_classifier_node] Clause Classifier Agent: Received response from LLM
[2026-02-07 09:07:26,656] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:113] [clause_classifier_node] Clause Classifier Agent: Classified 22 clauses
[2026-02-07 09:07:34,625] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:143] [risk_assessment_node] Risk Assessment Agent: Received response from LLM
[2026-02-07 09:07:34,626] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:145] [risk_assessment_node] Risk Assessment Agent: Assessed 22 clauses
[2026-02-07 09:07:45,933] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:179] [diff_checker_node] Diff Checker Agent: Received response from LLM
[2026-02-07 09:07:45,933] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:181] [diff_checker_node] Diff Checker Agent: Found 22 diff entries
[2026-02-07 09:07:45,933] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:402] [collector_node] Collector: Aggregating results from parallel analyzers...
[2026-02-07 09:07:45,934] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:403] [collector_node] Collector: Clause categories count: 22
[2026-02-07 09:07:45,934] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:404] [collector_node] Collector: Risk assessments count: 22
[2026-02-07 09:07:45,934] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:405] [collector_node] Collector: Diffs count: 22
[2026-02-07 09:07:45,934] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:466] [amendment_proposer_worker] Amendment Proposer Worker: Propose amendments for high-risk clauses
[2026-02-07 09:07:45,934] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:190] [amendment_proposer_node] Amendment Proposer Agent: Starting amendment proposals...
[2026-02-07 09:07:59,724] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:216] [amendment_proposer_node] Amendment Proposer Agent: Received response from LLM
[2026-02-07 09:07:59,724] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:218] [amendment_proposer_node] Amendment Proposer Agent: Proposed 3 amendments
[2026-02-07 09:07:59,725] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:415] [synthesizer_node] Synthesizer: Combining worker outputs into final report...
[2026-02-07 09:07:59,725] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:227] [report_generator_node] Report Generator Agent: Starting report generation...
[2026-02-07 09:08:15,927] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:252] [report_generator_node] Report Generator Agent: Received response from LLM
[2026-02-07 09:08:15,928] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:273] [report_generator_node] Report Generator Agent: Report generated successfully
[2026-02-07 09:08:15,928] [INFO] [src.service.multi_agent_service] [multi_agent_service.py:658] [run_contract_review] Contract review completed successfully
[2026-02-07 09:08:15,929] [INFO] [__main__] [main.py:108] [main] Review report saved: reports/contract_review_4571109f96714bfdafe72c1fe7965d5b.md
```

レビュー実行後、以下のようなMarkdownレポートが生成されます:

```markdown
# 契約書レビューレポート
## エグゼクティブサマリー
**総合リスクレベル**: 高
**総合リスクスコア**: 8.0 / 10.0

本契約は、再委託の全面禁止、過度な競業避止義務、甲による一方的な短期解除権など、乙にとって重大なリスクを伴う条項が複数含まれており、総合的なリスクレベルは「高」と評価されます。特に、乙の事業活動の自由度を著しく制限し、予期せぬ財務的損失を招く可能性のある条項については、締結前に相手方との詳細な交渉と修正が不可欠です。法務部門による詳細なレビューと上長決裁を推奨します。

## 主要な論点
1. 第7条（再委託の全面禁止）：業務遂行の柔軟性を著しく損ない、専門性の活用を妨げるリスクがあります。
2. 第13条（過度な競業避止義務）：契約終了後2年間の競業避止は、乙の職業選択の自由を過度に制限し、法的有効性にも疑問があります。
3. 第16条（甲による一方的な短期解除権）：甲が2週間前の通知で理由を問わず解除でき、成功報酬が支払われないため、乙の事業計画や収益に重大な影響を与える可能性があります。
4. 第5条（広範な費用負担）：原則として全ての費用が乙負担とされており、想定外の財務的負担が生じるリスクがあります。
5. 第10条（著作権の発生時帰属と著作者人格権不行使）：乙が汎用的に利用するノウハウ等の利用が制限される可能性があります。
6. 第11条（無期限の秘密保持義務）：乙にとって永続的な負担となり、将来の事業活動に制約を与えるリスクがあります。

## 推奨アクション
1. 相手方に修正依頼：第7条（再委託）、第13条（競業避止義務）、第16条（契約解除）については、乙の事業継続に重大な影響を及ぼすため、強く修正を交渉してください。
2. 相手方に修正依頼：第5条（費用負担）、第10条（著作権）、第11条（秘密保持義務）についても、乙にとって不利な条件であるため、修正を交渉してください。
3. 法務部門の詳細レビュー必要：上記の主要な論点に加え、曖昧な表現や実務上の困難を伴う条項（第2条、第4条、第6条、第9条など）について、法務部門による詳細なレビューを実施してください。
4. 上長決裁が必要：本契約は乙にとって高リスクな条項が複数含まれるため、最終的な締結判断には上長決裁が必要です。
5. 通知期限の管理徹底：第3条の自動更新条項について、契約終了を希望する場合の通知期限管理を徹底してください。

## リスク評価詳細

### 高リスク条項

#### 第7条
- **リスクスコア**: 7/10
- **リスク要因**:
  - 実務上の困難
  - 過度な義務
- **詳細説明**: 本業務の再委託を全面的に禁止する条項です。コンサルティング業務においては、特定の専門分野を持つ第三者や一時的なリソースを外部に委託することで、より高品質なサービスを提供できる場合があります。この禁止条項は、乙の業務遂行の柔軟性を著しく損ない、実務上の困難を生じさせる可能性があります。甲の書面による事前承諾を条件とするなど、柔軟性を持たせる修正を強く交渉すべきです。

#### 第13条
- **リスクスコア**: 9/10
- **リスク要因**:
  - 一方的な不利益
  - 過度な義務
  - 実務上の困難
  - 法的リスク
- **詳細説明**: 競業避止義務に関する条項です。契約期間中の競業避止は一般的ですが、「契約終了後2年間」という期間は、コンサルティング業界において乙の事業活動を著しく制限する過度な義務です。特に「甲の競合他社に対して同種のコンサルティングサービス」の範囲が不明確な場合、乙の生業を奪う可能性があり、法的にもその有効性が争われるリスクがあります。乙の事業継続に重大な影響を与えるため、期間の短縮（例：6ヶ月〜1年）、対象範囲の明確化、または削除を強く交渉すべきです。

#### 第16条
- **リスクスコア**: 8/10
- **リスク要因**:
  - 一方的な不利益
  - 財務リスク
  - 実務上の困難
- **詳細説明**: 契約解除に関する条項です。甲は「2週間前の書面通知により、理由の如何を問わず」本契約を解除できるとされており、甲の一方的な都合で非常に短い通知期間で契約を終了させることが可能です。この場合、成功報酬は支払われないため、乙の事業計画や収益に大きな影響を与えるリスクがあります。一方、乙の解除権は1ヶ月前の書面通知が必要であり、甲に比べて通知期間が長く、一方的に不利な条件です。甲の解除権の通知期間の延長（例：1ヶ月以上）、または解除理由の限定を強く交渉すべきです。

## 標準契約との差分

### 第1条 (修正)
**概要**: レビュー対象契約は、当事者の具体的な名称と委託業務の内容（ITシステム導入に関するコンサルティング）を明記している点で、標準テンプレートよりも詳細です。

**レビュー対象契約**:
> 本契約は、委託者（スタートアップ株式会社、以下「甲」という）が受託者（ITアドバイザリー合同会社、以下「乙」という）に対し、ITシステム導入に関するコンサルティング業務を委託し、乙がこれを受託することに関する事項を定めるものである。...

**自社標準**:
> 本契約は、委託者（以下「甲」という）が受託者（以下「乙」という）に対し、コンサルティング業務を委託し、乙がこれを受託することに関する基本的事項を定めるものである。...

### 第2条 (修正)
**概要**: レビュー対象契約は、委託業務の内容を具体的に列挙しているのに対し、標準テンプレートは別紙参照および協議による決定としています。レビュー対象契約の方が業務範囲が明確です。

**レビュー対象契約**:
> 甲は乙に対し、以下の業務（以下「本業務」という）を委託する。
1. 業務要件の整理および分析
2. システム選定に関する調査および推奨
3. ベンダー選定支援
4. 導入プロジェクトの監理および助言
5. その他甲が指定する関連業務...

**自社標準**:
> 1. 甲は乙に対し、以下の業務（以下「本業務」という）を委託する。
   - 業務内容：別紙にて定める
2. 本業務の詳細、スケジュール、成果物等は、甲乙協議の上、別途定める。...

### 第3条 (修正)
**概要**: レビュー対象契約には、期間満了時の自動更新条項（6ヶ月間）が追加されています。標準テンプレートには自動更新の定めがありません。

**レビュー対象契約**:
> 1. 本契約の有効期間は、契約締結日から1年間とする。
2. 期間満了の1ヶ月前までに、いずれの当事者からも書面による終了の通知がない場合、本契約は同一条件で6ヶ月間自動更新され、以後も同様とする。...

**自社標準**:
> 本契約の有効期間は、契約締結日から1年間とする。...

### 第4条 (修正)
**概要**: レビュー対象契約は、固定報酬と成功報酬の具体的な金額、およびそれぞれの支払期日を詳細に定めています。標準テンプレートは報酬額を別紙参照とし、支払期日も「翌月末日」と一般的です。

**レビュー対象契約**:
> 1. 甲は乙に対し、本業務の対価として、以下の報酬を支払う。
   - 固定報酬：月額金50万円（消費税別）
   - 成功報酬：システム導入完了時に金100万円（消費税別）
2. 固定報酬の支払は、毎月末日締めとし、乙の請求に基づき、請求月の翌月15日までに支払う。
3. 成功報酬の支払は、システム導入完了を甲が確認後30日以内に支払う。
4. 乙が指定する銀行口座に振り込む方法により支払い、振...

**自社標準**:
> 1. 甲は乙に対し、本業務の対価として、別紙に定める報酬を支払う。
2. 報酬の支払は、乙の請求に基づき、請求月の翌月末日までに、乙が指定する銀行口座に振り込む方法により行う。
3. 振込手数料は甲の負担とする。...

### 第5条 (修正)
**概要**: レビュー対象契約は、原則として費用を乙の負担とし、甲の要請による遠方出張費のみ甲負担としています。標準テンプレートは協議による決定としており、レビュー対象契約の方が乙にとって厳しい条件です。

**レビュー対象契約**:
> 本業務の遂行に必要な費用は、全て乙の負担とする。ただし、甲の要請による遠方への出張に係る交通費および宿泊費は甲の負担とする。...

**自社標準**:
> 本業務の遂行に必要な費用は、甲乙協議の上、負担者を定める。実費精算とする場合は、乙は甲に対し領収書等の証憑を提出する。...

### 第6条 (追加)
**概要**: レビュー対象契約には、稼働場所に関する条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 1. 乙は、本業務を乙の事務所において遂行する。
2. 甲の要請により甲の事業所において業務を行う場合、乙は甲の就業規則および施設利用規程に従う。...

**自社標準**:
> （該当条項なし）...

### 第7条 (修正)
**概要**: レビュー対象契約は再委託を全面的に禁止しています。標準テンプレートは甲の書面による事前承諾があれば再委託を認めており、レビュー対象契約の方が乙にとって厳しい条件です。

**レビュー対象契約**:
> 乙は、本業務を第三者に再委託してはならない。...

**自社標準**:
> 乙は、甲の書面による事前承諾を得た場合に限り、本業務の一部を第三者に再委託することができる。この場合、乙は再委託先の行為について甲に対し責任を負う。...

### 第8条 (修正)
**概要**: レビュー対象契約は、週次での電子メール報告と月次定例会議への出席を義務付けており、標準テンプレートの「求めに応じ報告」よりも具体的な報告義務を課しています。

**レビュー対象契約**:
> 1. 乙は、週次で業務進捗状況を電子メールにて甲に報告する。
2. 甲は、必要に応じて月次の定例会議を設定することができ、乙はこれに出席する。...

**自社標準**:
> 乙は、甲の求めに応じ、本業務の進捗状況を報告するものとする。...

### 第9条 (追加)
**概要**: レビュー対象契約には、具体的な成果物の種類とフォーマットに関する条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 1. 乙は、本業務の成果物として、以下を甲に納品する。
   - 業務要件定義書
   - システム選定報告書
   - ベンダー評価報告書
   - プロジェクト監理報告書
2. 成果物のフォーマットは甲の指定に従う。...

**自社標準**:
> （該当条項なし）...

### 第10条 (修正)
**概要**: レビュー対象契約は、著作権が「発生と同時に」甲に帰属するとしており、著作者人格権の不行使も定めています。標準テンプレートは「報酬の完済をもって」甲に帰属するとしており、著作権帰属のタイミングが異なります。また、レビュー対象契約は乙のツール等の権利留保を明記しています。

**レビュー対象契約**:
> 1. 本業務により生じた成果物に関する著作権（著作権法第27条および第28条の権利を含む）は、その発生と同時に甲に帰属する。
2. 乙は、成果物について著作者人格権を行使しない。
3. 乙が本業務の遂行に使用したツール、テンプレート、フレームワーク等の権利は、乙に帰属する。...

**自社標準**:
> 1. 本業務により生じた成果物に関する著作権（著作権法第27条および第28条の権利を含む）は、報酬の完済をもって甲に帰属する。
2. 乙が従前から有していた知的財産権は、乙に留保される。...

### 第11条 (修正)
**概要**: レビュー対象契約は、秘密保持義務の期間を「無期限」としており、標準テンプレートの「契約終了後3年間」よりも長く、乙にとって厳しい条件です。また、乙による秘密情報の目的外使用禁止が追加されています。

**レビュー対象契約**:
> 1. 甲および乙は、本契約に関連して知り得た相手方の秘密情報を、相手方の書面による承諾なく第三者に開示してはならない。
2. 乙は、秘密情報を本業務以外の目的に使用してはならない。
3. 秘密保持義務は、契約終了後も無期限に存続する。...

**自社標準**:
> 1. 甲および乙は、本契約に関連して知り得た相手方の秘密情報を、相手方の書面による承諾なく第三者に開示してはならない。
2. 秘密保持義務は、契約終了後3年間存続する。...

### 第12条 (追加)
**概要**: レビュー対象契約には、個人情報の取扱いに関する条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 1. 乙は、本業務において甲から提供される個人情報を、個人情報保護法その他の法令に従い適切に取り扱う。
2. 乙は、個人情報の漏洩、滅失、毀損を防止するため、必要かつ適切な安全管理措置を講じる。...

**自社標準**:
> （該当条項なし）...

### 第13条 (修正)
**概要**: レビュー対象契約は、競業避止義務の期間を「契約終了後2年間」としており、標準テンプレートの「契約終了後1年間」よりも長く、乙にとって厳しい条件です。

**レビュー対象契約**:
> 乙は、本契約期間中および契約終了後2年間、甲の書面による承諾なく、甲の競合他社に対して同種のコンサルティングサービスを提供してはならない。...

**自社標準**:
> 乙は、本契約期間中および契約終了後1年間、甲の書面による承諾なく、甲の競合他社に対して同種のコンサルティングサービスを提供してはならない。...

### 第14条 (修正)
**概要**: レビュー対象契約は、乙の損害賠償責任の範囲を「直接かつ現実に生じた損害」とし、賠償額の上限を報酬総額としています。また、乙が甲の意思決定の結果について責任を負わない旨の条項が追加されており、乙にとって有利な修正です。

**レビュー対象契約**:
> 1. 乙が本契約に違反し、甲に損害を与えた場合、乙は甲に対し、直接かつ現実に生じた損害を賠償する。
2. 前項の賠償額は、本契約に基づき甲が乙に支払った報酬総額を上限とする。
3. 乙は、甲が乙の助言に基づいて行った意思決定の結果について、責任を負わない。...

**自社標準**:
> 甲または乙が本契約に違反し、相手方に損害を与えた場合、違反当事者は相手方に対し、通常かつ直接の損害を賠償する。賠償額の上限は、本契約に基づく報酬総額とする。...

### 第15条 (追加)
**概要**: レビュー対象契約には、乙の保証を否認する条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 乙は、本業務において提供する情報、助言、成果物について、その正確性、完全性、特定目的への適合性を保証しない。...

**自社標準**:
> （該当条項なし）...

### 第16条 (修正)
**概要**: レビュー対象契約は、債務不履行解除の是正期間を「7日間」と具体的に定めています（標準は「相当期間」）。また、甲による任意解除の通知期間が「2週間前」と短縮され、成功報酬を支払わない旨が明記されています。さらに、乙による任意解除の条項が追加されています。

**レビュー対象契約**:
> 1. 甲または乙は、相手方が本契約に違反し、7日間の期間を定めて是正を催告したにもかかわらず是正されない場合、本契約を解除することができる。
2. 甲は、2週間前の書面通知により、理由の如何を問わず本契約を解除することができる。この場合、甲は解除日までに提供された業務に対応する報酬を乙に支払い、成功報酬は支払わない。
3. 乙は、1ヶ月前の書面通知により、理由の如何を問わず本契約を解除することがで...

**自社標準**:
> 1. 甲または乙は、相手方が本契約に違反し、相当期間を定めて是正を催告したにもかかわらず是正されない場合、本契約を解除することができる。
2. 甲は、1ヶ月前の書面通知により、理由の如何を問わず本契約を解除することができる。この場合、甲は解除日までに提供された業務に対応する報酬を乙に支払う。...

### 第17条 (追加)
**概要**: レビュー対象契約には、契約終了後の措置に関する条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 契約終了時、乙は甲から提供された資料、データ、その他の物品を速やかに甲に返還または廃棄する。...

**自社標準**:
> （該当条項なし）...

### 第19条 (追加)
**概要**: レビュー対象契約には、権利義務の譲渡禁止に関する条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 甲および乙は、相手方の書面による事前承諾なく、本契約上の地位または権利義務を第三者に譲渡してはならない。...

**自社標準**:
> （該当条項なし）...

### 第20条 (修正)
**概要**: レビュー対象契約は、管轄裁判所を「乙の本店所在地を管轄する地方裁判所」としています。標準テンプレートは「東京地方裁判所」と定めており、管轄裁判所が異なります。

**レビュー対象契約**:
> 本契約は日本法に準拠し、本契約に関する紛争については、乙の本店所在地を管轄する地方裁判所を第一審の専属的合意管轄裁判所とする。...

**自社標準**:
> 本契約は日本法に準拠し、本契約に関する紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。...

### 第22条 (追加)
**概要**: レビュー対象契約には、完全合意条項が追加されています。標準テンプレートにはこの条項がありません。

**レビュー対象契約**:
> 本契約は、本契約の主題に関する当事者間の完全な合意を構成し、本契約締結前の一切の合意、了解、協議に優先する。...

**自社標準**:
> （該当条項なし）...

## 修正提案

### 第7条
**現行文言**:
> 乙は、本業務を第三者に再委託してはならない。

**修正案**:
> 乙は、甲の書面による事前の承諾を得た場合に限り、本業務の全部または一部を第三者に再委託することができる。この場合、乙は、再委託先の行為について甲に対し一切の責任を負う。

**修正理由**: 本業務の性質上、特定の専門業務を外部の専門業者に委託する必要が生じる場合があります。再委託を全面的に禁止することは、業務の効率性や専門性の確保を阻害する可能性があります。甲の事前承諾を条件とすることで、甲の管理権を維持しつつ、乙の業務遂行の柔軟性を確保できます。

**交渉ポイント**:
- 業務の専門性や効率性を考慮し、再委託の必要性を説明する。
- 甲の管理権を確保するため、事前承諾を条件とすること、および再委託先の行為に対する乙の全責任を明確にすることを強調する。
- 再委託を許可することで、甲がより広範な専門知識やリソースにアクセスできるメリットを提示する。

### 第13条
**現行文言**:
> 乙は、本契約期間中および契約終了後2年間、甲の書面による承諾なく、甲の競合他社に対して同種のコンサルティングサービスを提供してはならない。

**修正案**:
> 乙は、本契約期間中、甲の書面による事前の承諾なく、本契約に基づき乙が甲に提供するサービスと同一または実質的に同一のサービスを、甲が乙に開示した特定の競合他社に対して提供してはならない。本契約終了後、乙は、本契約に基づき甲に提供したサービスに関連して取得した甲の秘密情報を利用して、甲の事業を不当に害する行為を行わないものとする。

**修正理由**: 現行の競業避止義務は、期間（契約終了後2年間）および範囲（甲の競合他社、同種のコンサルティングサービス）が広範に過ぎ、乙の職業選択の自由を過度に制限し、法的にも無効とされるリスクがあります。より限定的な範囲と期間に修正することで、甲の正当な利益（秘密情報の保護など）を保護しつつ、乙の事業活動への不必要な制約を避けることができます。

**交渉ポイント**:
- 現行条項が過度に広範であり、乙の生計維持を困難にする可能性があること、および法的有効性に疑問があることを説明する。
- 競業避止義務の対象を「本契約に基づき提供するサービスと同一または実質的に同一のサービス」に限定し、期間を契約期間中に限定することで、甲の具体的な営業秘密や顧客基盤の保護に焦点を当てる。
- 契約終了後の制限については、秘密保持義務で対応可能であることを提案し、競業避止義務は原則として契約期間中に限定することを求める。
- もし契約終了後の制限が必要な場合でも、期間を大幅に短縮（例：6ヶ月〜1年）し、対象となる競合他社やサービスを具体的に特定するよう交渉する。

### 第16条
**現行文言**:
> 2. 甲は、2週間前の書面通知により、理由の如何を問わず本契約を解除することができる。この場合、甲は解除日までに提供された業務に対応する報酬を乙に支払い、成功報酬は支払わない。

**修正案**:
> 2. 甲は、30日前の書面通知により、理由の如何を問わず本契約を解除することができる。この場合、甲は解除日までに提供された業務に対応する報酬および、解除日までに発生した合理的な費用を乙に支払う。また、成功報酬が設定されている業務については、解除日までの乙の貢献度に応じて、甲乙協議の上、合理的な成功報酬の一部または全部を支払うものとする。

**修正理由**: 甲による理由の如何を問わない解除（任意解除）の通知期間が2週間では、乙が次の業務を見つける時間的猶予が少なく、不測の損害を被るリスクが高いです。また、成功報酬が一切支払われないとするのは、乙が既に成功に向けて相当な努力を投じていた場合に不公平です。通知期間を延長し、成功報酬についても貢献度に応じた支払いを行うことで、乙の財務的リスクを軽減し、より公平な契約関係を構築できます。

**交渉ポイント**:
- 通知期間の延長（30日以上）を求めることで、乙が解除による影響を最小限に抑えるための準備期間を確保できることを説明する。
- 成功報酬について、解除日までの乙の貢献度を考慮した支払いを求めることで、乙が投じた努力や費用が無駄にならないようにすることを強調する。
- 任意解除権は双方にとって重要な権利であるため、その行使に伴う影響を公平に分担することの重要性を訴える。
- 甲にとっても、乙が円滑に業務を終了し、引き継ぎを行うために十分な期間が必要であることを指摘する。

```

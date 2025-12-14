# Chapter 5 Section 6: パイプライン型AIエージェント

## 概要

本プロジェクトは、パイプライン型AIエージェントパターンを用いた契約書リスクコンプライアンス評価システムの実装例です。複雑なLLM処理を一連の逐次的なステージに分解し、各ステージが特定の責任を持ち、その出力を次のステージに渡す設計パターンを実証します。

パイプラインは契約書ドキュメントを読み込み、その構造（章と条）を抽出し、各セクションのリスクを評価し、包括的なコンプライアンスレポートを生成します。このアプローチにより、各処理ステージの責任が明確に分離され、保守性とテスト容易性が向上します。

## 機能

- **契約書構造抽出**: 契約書テキストから章・条構造を自動解析
- **リスク評価**: 各条文に対する10カテゴリのリスク評価（知的財産権、責任・賠償、秘密保持など）
- **4段階リスクレベル**: low / medium / high / critical の4段階でリスクを分類
- **コンプライアンスレポート生成**: エグゼクティブサマリー、リスク分析、推奨事項を含む日本語レポート
- **Markdownレポート出力**: 構造化されたMarkdown形式でレポートを出力

## プロジェクト構成

### ディレクトリ構成

```
.
|-- CLAUDE.md                           # プロジェクト説明（Claude Code用）
|-- Makefile                            # 開発用コマンド
|-- README.md                           # 本ドキュメント
|-- pyproject.toml                      # 依存関係定義
|-- .envrc.example                      # 環境変数テンプレート
|-- data/
|   |-- contract_0.md                   # サンプル契約書
|   |-- contract_1.md
|   |-- contract_2.md
|   +-- contract_3.md
+-- src/
    |-- __init__.py
    |-- main.py                         # CLIエントリーポイント
    |-- config.py                       # 環境設定
    |-- logger.py                       # ロギングユーティリティ
    |-- client/
    |   |-- __init__.py
    |   +-- llm_client.py               # OpenAIモデル定義
    |-- model/
    |   |-- __init__.py
    |   +-- contract_pipeline_model.py  # Pydanticデータモデル
    |-- prompt/
    |   |-- __init__.py
    |   +-- contract_pipeline_prompt.py # プロンプトテンプレート
    |-- layer/
    |   |-- __init__.py
    |   |-- base.py                     # 抽象基底エージェントクラス
    |   +-- contract_pipeline/
    |       |-- __init__.py
    |       |-- extraction.py           # 抽出ステージエージェント
    |       |-- risk_scoring.py         # リスク評価ステージエージェント
    |       +-- report.py               # レポート生成ステージエージェント
    +-- service/
        |-- __init__.py
        +-- contract_pipeline_service.py # LangGraphパイプラインオーケストレーション
```

### アーキテクチャ

```
+------------------------------------------------------------------+
|                    Contract Pipeline                              |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------+                                            |
|  |   Input Stage     |  ディスクから契約書ファイルを読み込み      |
|  |   (main.py)       |                                            |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Extraction Stage  |  ドキュメント構造を解析                    |
|  | (extraction.py)   |  -> 章と条を抽出                           |
|  |                   |  -> 当事者を特定                           |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Risk Scoring      |  各セクションを評価                        |
|  | Stage             |  -> リスクレベル評価 (low/med/high/crit)   |
|  | (risk_scoring.py) |  -> 発見事項をカテゴリ分類                 |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|  +-------------------+                                            |
|  | Report Stage      |  最終レポートを生成                        |
|  | (report.py)       |  -> エグゼクティブサマリー                 |
|  |                   |  -> 推奨事項                               |
|  +---------+---------+                                            |
|            |                                                      |
|            v                                                      |
|        [Output]         Markdownコンプライアンスレポート          |
|                                                                   |
+------------------------------------------------------------------+
```

### 実装の詳細

#### 1. データモデル (`src/model/contract_pipeline_model.py`)

パイプライン全体で使用されるPydanticモデルを定義します。

```python
class RiskLevel(StrEnum):
    """リスクレベルの分類"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(StrEnum):
    """契約リスクのカテゴリ"""
    INTELLECTUAL_PROPERTY = "intellectual_property"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    PAYMENT = "payment"
    COMPLIANCE = "compliance"
    WARRANTY = "warranty"
    INDEMNIFICATION = "indemnification"
    DISPUTE_RESOLUTION = "dispute_resolution"
    OTHER = "other"


class ContractPipelineState(TypedDict):
    """パイプラインの状態管理用TypedDict"""
    contract_input: ContractInput
    extraction_output: ExtractionOutput | None
    risk_scoring_output: RiskScoringOutput | None
    compliance_report: ComplianceReport | None
    current_stage: str
    pending_sections: list[ContractSection]
    current_section_index: int
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

**ポイント**: `ContractPipelineState`はLangGraphの状態管理に使用され、各ステージ間でデータを受け渡します。

#### 2. 抽出ステージ (`src/layer/contract_pipeline/extraction.py`)

契約書テキストを解析し、章・条構造を抽出します。

```python
class ExtractionAgent(BaseAgent):
    """抽出ステージエージェント"""

    def __init__(self):
        super().__init__(layer_name="PIPELINE", agent_name="ExtractionAgent")

    def execute(
        self, state: ContractPipelineState, config: RunnableConfig
    ) -> dict:
        """抽出ステージを実行"""
        contract_input = state["contract_input"]
        user_prompt = make_extraction_user_prompt(contract_input.raw_content)

        result = self._invoke_and_parse(
            config, make_extraction_system_prompt(), user_prompt
        )
        extraction_output = self._parse_extraction_result(
            result, contract_input.contract_id
        )

        # 次のステージ用に全セクションをフラット化
        all_sections = []
        for chapter in extraction_output.structure.chapters:
            all_sections.extend(chapter.sections)

        return {
            "extraction_output": extraction_output,
            "pending_sections": all_sections,
            "current_stage": "risk_scoring",
        }
```

**ポイント**: LLMが返すJSONを解析し、構造化されたデータモデルに変換します。

#### 3. リスク評価ステージ (`src/layer/contract_pipeline/risk_scoring.py`)

各条文のリスクを評価し、発見事項をカテゴリ分類します。

```python
class RiskScoringAgent(BaseAgent):
    """リスク評価ステージエージェント"""

    def _assess_section(
        self,
        section: ContractSection,
        parties: list[str],
        config: RunnableConfig,
    ) -> SectionRiskAssessment:
        """単一セクションのリスク評価"""
        user_prompt = make_risk_scoring_user_prompt(
            section_id=section.section_id,
            section_number=section.section_number,
            section_title=section.title,
            section_content=section.content,
            parties=parties,
        )

        result = self._invoke_and_parse(
            config, make_risk_scoring_system_prompt(), user_prompt
        )
        return self._parse_section_assessment(result, section)

    def execute(
        self, state: ContractPipelineState, config: RunnableConfig
    ) -> dict:
        """全セクションのリスク評価を実行"""
        pending_sections = state["pending_sections"]
        parties = state["extraction_output"].structure.parties

        assessments: list[SectionRiskAssessment] = []
        for section in pending_sections:
            assessment = self._assess_section(section, parties, config)
            assessments.append(assessment)

        return {
            "risk_scoring_output": risk_output,
            "current_stage": "report",
        }
```

**ポイント**: 各セクションに対して個別にLLM呼び出しを行い、詳細なリスク評価を実施します。

#### 4. レポート生成ステージ (`src/layer/contract_pipeline/report.py`)

全評価結果を統合し、包括的なコンプライアンスレポートを生成します。

```python
class ReportAgent(BaseAgent):
    """レポート生成ステージエージェント"""

    def execute(
        self, state: ContractPipelineState, config: RunnableConfig
    ) -> dict:
        """レポート生成ステージを実行"""
        extraction = state["extraction_output"]
        risk_output = state["risk_scoring_output"]

        user_prompt = make_report_user_prompt(
            contract_title=extraction.structure.title,
            parties=extraction.structure.parties,
            total_sections=extraction.structure.total_sections,
            high_risk_count=risk_output.high_risk_count,
            total_findings=risk_output.total_findings,
            section_assessments=self._format_section_assessments(state),
        )

        result = self._invoke_and_parse(
            config, make_report_system_prompt(), user_prompt
        )
        report = self._parse_report_result(result, state)

        return {
            "compliance_report": report,
            "current_stage": "complete",
        }
```

#### 5. パイプラインオーケストレーション (`src/service/contract_pipeline_service.py`)

LangGraphを使用してパイプラインフローを定義・実行します。

```python
def create_contract_pipeline_graph() -> StateGraph:
    """契約リスクコンプライアンスパイプライングラフを作成"""
    graph = StateGraph(ContractPipelineState)

    # パイプラインステージノードを追加
    graph.add_node("extraction", extraction_stage_node)
    graph.add_node("risk_scoring", risk_scoring_stage_node)
    graph.add_node("report", report_stage_node)

    # 線形パイプラインフローを定義
    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "risk_scoring")
    graph.add_edge("risk_scoring", "report")
    graph.add_edge("report", END)

    return graph.compile()


async def run_contract_compliance_pipeline(
    contract_file_path: str,
    model: str = OpenAIModel.GPT_4O,
) -> ComplianceReport | None:
    """契約リスクコンプライアンスパイプラインを実行"""
    graph = create_contract_pipeline_graph()
    config = RunnableConfig(configurable={"model": model})

    initial_state = _create_initial_state(contract_file_path)
    final_state = await graph.ainvoke(initial_state, config)
    return _extract_report_from_state(final_state)
```

**ポイント**: `StateGraph`を使用して、ステージ間の依存関係と実行順序を宣言的に定義します。

#### 6. 基底エージェントクラス (`src/layer/base.py`)

全エージェントに共通する機能を提供する抽象基底クラスです。

```python
class BaseAgent(ABC):
    """全パイプラインエージェントの抽象基底クラス"""

    def _invoke_with_retry(
        self, model: ChatOpenAI, messages: list, config: RunnableConfig
    ) -> str:
        """リトライロジック付きLLM呼び出し"""
        for attempt in range(MAX_RETRIES):
            try:
                response = model.invoke(messages, config)
                if response.content and response.content.strip():
                    return response.content
            except Exception as e:
                self.logger.warning(f"Error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

        raise ValueError(f"Failed after {MAX_RETRIES} attempts")

    def _invoke_and_parse(
        self,
        config: RunnableConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """共通ワークフロー: メッセージ構築 -> LLM呼び出し -> JSON解析"""
        model = self._create_chat_model(config)
        messages = self._build_messages(system_prompt, user_prompt)
        response_content = self._invoke_with_retry(model, messages, config)
        return extract_json_from_response(response_content)
```

**ポイント**: リトライロジックとJSON解析を共通化し、各エージェントの実装を簡潔にします。

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - langchain-openai >= 1.1.0
  - langgraph >= 1.0.0
  - pydantic >= 2.12.2
  - click >= 8.3.0
  - python-dotenv >= 1.1.1

### セットアップ

1. 環境変数テンプレートをコピー:

```bash
cp .envrc.example .envrc
```

2. `.envrc`にOpenAI APIキーを設定:

```
OPENAI_API_KEY=your_api_key_here
```

3. 依存関係をインストール:

```bash
uv sync
```

### 使用方法、実行方法

```bash
# 基本的な使用方法
python -m src.main -c data/contract_0.md

# モデルを指定
python -m src.main -c data/contract_0.md -m gpt-4o

# 出力ディレクトリを指定
python -m src.main -c data/contract_0.md -od reports
```

### CLIオプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| --contract-file | -c | 契約書ファイルパス（必須） | - |
| --model | -m | 使用するOpenAIモデル | gpt-4o-mini |
| --output-directory | -od | レポート出力ディレクトリ | outputs |
| --help | - | ヘルプを表示 | - |

### 利用可能なモデル

- gpt-4o, gpt-4o-mini
- gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
- gpt-5, gpt-5-mini, gpt-5-nano

### 出力例

実行後、以下のようなMarkdownレポートが生成されます:

```markdown
# 契約書リスクコンプライアンスレポート

**契約書**: ソフトウェア開発業務委託契約書
**レポートID**: report_a1b2c3d4
**生成日時**: 2024-01-15 14:30:00

---

## エグゼクティブサマリー

### 総合評価
- **コンプライアンス状態**: ⚠️ 要確認
- **リスクスコア**: 45/100

本契約書は全体として標準的な業務委託契約の形式を取っていますが、
いくつかの条項について確認・交渉が推奨されます。

### 主要な懸念事項
- 再委託に関する制限が緩い
- 損害賠償の上限が委託料総額に制限されている

### 即時対応が必要な事項
- ⚠️ 第6条（再委託）の条件を明確化する必要があります

---

## リスク分析

### 責任・賠償
- **検出件数**: 2件
- **主な問題点**:
  - 損害賠償額の上限設定
  - 間接損害の扱いが不明確

---

## セクション別評価詳細

### ⚠️ 第6条 再委託
- **リスクレベル**: 🟠 高
- **コンプライアンス**: 要確認

**検出されたリスク:**

- **再委託の無制限許可**
  - カテゴリ: 責任・賠償
  - レベル: 🟠 高
  - 推奨対応: 再委託先の事前承認制度を導入する

---

## 総合的な推奨事項

1. 第6条の再委託条項について、事前承認制度の導入を検討
2. 第18条の損害賠償上限について、間接損害の取り扱いを明確化
3. 秘密保持期間（3年）の適切性を再検討

---

## 結論

本契約書は基本的な構成は整っていますが、いくつかの条項について
リスク軽減のための修正交渉を推奨します。特に再委託条項と
損害賠償条項については、契約締結前に詳細な検討が必要です。
```

## 開発コマンド

```bash
# コードのリント
make lint

# コードのフォーマット
make fmt

# リントとフォーマットを両方実行
make fix

# 型チェック
make mypy
```

## 実装のポイント

### パイプライン状態フロー

各ステージは共有の`ContractPipelineState`を更新します:

1. **extraction**: `extraction_output`と`pending_sections`を設定
2. **risk_scoring**: 全セクションから`risk_scoring_output`を設定
3. **report**: 最終分析を含む`compliance_report`を設定

### リスク評価カテゴリ

システムは10のリスクカテゴリで契約書を評価します:

| カテゴリ | 日本語名 |
|---------|---------|
| intellectual_property | 知的財産権 |
| liability | 責任・賠償 |
| confidentiality | 秘密保持 |
| termination | 契約解除 |
| payment | 支払条件 |
| compliance | 法令遵守 |
| warranty | 保証 |
| indemnification | 補償 |
| dispute_resolution | 紛争解決 |
| other | その他 |

### エラーハンドリング

- LLM呼び出しにはリトライロジック（3回試行、2秒間隔）を実装
- JSON解析には切り詰められたレスポンスの修正機能を含む
- 評価に失敗したセクションにはデフォルトでMEDIUMリスクレベルを設定

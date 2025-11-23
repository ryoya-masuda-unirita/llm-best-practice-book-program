# Chapter 2 Section 12: LLMパイプラインの実装

## 概要

このプロジェクトは、**LangGraphを活用したLLMパイプライン**の実践的な実装例を示すサンプルコードです。複雑なタスクを複数のステージに分割し、各ステージでLLMの役割を明確に分担することで、高精度な文書分析システムを実現します。

LLM-as-a-Judge（LLMを評価者として活用する）パターンを採用し、分析結果の品質を自動評価して、必要に応じて改善フィードバックを与えながら再実行する仕組みを実装しています。OpenAI GPT-4oとGoogle Gemini 2.5の両方に対応し、構造化出力による型安全な実装を実現しています。

## 機能

- **LangGraphパイプライン**: 複数の処理ステップを明確な状態管理のもとで連鎖実行
- **LLM-as-a-Judge**: 分析結果の品質を別のLLM呼び出しで評価し、客観的な品質保証を実現
- **自動リトライ機構**: 評価が基準値（grade 4/5）未満の場合、改善フィードバックを与えて自動再実行
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **構造化出力**: Pydanticモデルによる厳密な型検証とバリデーション
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **柔軟な制御フロー**: 条件分岐による動的なパイプライン実行
- **詳細なログ**: 各ステージの実行状況を可視化し、デバッグを容易に
- **複数形式での出力**: JSON形式とMarkdown形式の両方で結果を保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_12/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── llm_pipeline_model.py    # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── llm_pipeline_prompt.py   # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       └── llm_pipeline_service.py  # LangGraphパイプライン実装
├── dataset/                      # サンプル文書データ
│   ├── document_0.md
│   ├── document_1.md
│   └── document_2.md
├── outputs/                      # 生成結果の保存先（自動作成）
├── tests/                        # テストファイル
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   └── test_llm_pipeline_service.py
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── pytest.ini                    # Pytestの設定ファイル
├── Makefile                      # タスク自動化スクリプト
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト設計ドキュメント
```

### アーキテクチャ

このプロジェクトは、LangGraphを中心とした多段階パイプラインアーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────────────┐
│              CLI Layer (main.py)                            │
│  - コマンドライン引数解析                                     │
│  - パイプライン実行の起動                                     │
│  - 結果の保存（JSON/Markdown）                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│      LangGraph Pipeline (llm_pipeline_service.py)          │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Read       │───>│   Analyze    │───>│    Judge     │ │
│  │  Document    │    │   Document   │    │   Analysis   │ │
│  └──────────────┘    └──────────────┘    └──────┬───────┘ │
│                              ▲                   │         │
│                              │                   │         │
│                              │   Grade < 4 ?     │         │
│                              └───────────────────┘         │
│                           (Retry with Feedback)            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│         Business Logic Layer                                │
│  - プロンプト生成 (llm_pipeline_prompt.py)                   │
│  - データモデル (llm_pipeline_model.py)                      │
│  - LLMクライアント管理 (llm_client.py)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│         Infrastructure Layer                                │
│  - 設定管理 (config.py)                                      │
│  - ログ管理 (logger.py)                                      │
│  - 外部API (OpenAI, Gemini)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/llm_pipeline_model.py`)

Pydanticを使用して、3つの主要なデータモデルを定義します：

```python
class DocumentAnalysis(BaseModel):
    """文書分析結果モデル"""
    theme: str  # 文書の主要テーマ（1-2文）
    value: str  # 文書の価値と重要性（2-3文）
    improvement_requests: list[str]  # 改善要望リスト（3-5項目）

class AnalysisEvaluation(BaseModel):
    """分析結果の評価モデル（LLM-as-a-Judge）"""
    grade: Literal[1, 2, 3, 4, 5]  # 1（非常に悪い）〜5（非常に良い）
    reasoning: str  # 評価の詳細な理由（3-5文）
    specific_improvements: list[str]  # 具体的な改善提案（grade < 4の場合）

class PipelineState(TypedDict):
    """LangGraphパイプラインの状態管理"""
    document_path: str
    document_content: str
    analysis_result: DocumentAnalysis | None
    evaluation_result: AnalysisEvaluation | None
    retry_count: int
    error: str | None
```

**ポイント**:
- `frozen=True`により不変オブジェクトを保証
- `validate_assignment=True`で代入時のバリデーションを有効化
- `TypedDict`でLangGraphの状態を型安全に管理

#### 2. LangGraphパイプライン (`src/service/llm_pipeline_service.py`)

LangGraphを使用して、以下の5つのノードで構成されるパイプラインを実装します：

**パイプラインフロー**:

1. **read_document_node**: Markdownファイルを読み込み
2. **analyze_document_[openai|gemini]_node**: 文書を分析してtheme、value、improvement_requestsを抽出
3. **judge_analysis_[openai|gemini]_node**: 分析結果の品質を評価（LLM-as-a-Judge）
4. **route_after_judge**: 評価結果に基づいて次のアクションを決定
   - grade >= 4: パイプライン終了
   - grade < 4 かつ retry_count < MAX_RETRIES: 改善フィードバック付きで再分析
   - retry_count >= MAX_RETRIES: パイプライン終了（現在の結果を受け入れ）

```python
def create_document_analysis_graph() -> StateGraph:
    """LangGraphパイプラインの構築"""
    graph = StateGraph(PipelineState)

    # ノードの追加
    graph.add_node("read_document", read_document_node)
    graph.add_node("analyze_openai", analyze_document_openai_node)
    graph.add_node("analyze_gemini", analyze_document_gemini_node)
    graph.add_node("judge_openai", judge_analysis_openai_node)
    graph.add_node("judge_gemini", judge_analysis_gemini_node)

    # エッジと条件分岐の設定
    graph.add_edge(START, "read_document")
    graph.add_conditional_edges("read_document", route_to_llm_provider)
    graph.add_conditional_edges("analyze_openai", route_to_judge)
    graph.add_conditional_edges("judge_openai", route_after_judge)
    # ... 以下同様

    return graph.compile()
```

**特徴**:
- **条件分岐**: `add_conditional_edges`で動的にルーティング
- **プロバイダー選択**: OpenAIまたはGeminiを実行時に選択
- **自動リトライ**: 評価が低い場合、最大2回まで自動再試行
- **フィードバックループ**: Judge→Analyzerのフィードバックループで品質向上

#### 3. LLM-as-a-Judge実装 (`src/service/llm_pipeline_service.py:177-273`)

分析結果の品質を別のLLM呼び出しで評価する仕組み：

```python
async def judge_analysis_openai_node(state: PipelineState) -> PipelineState:
    """分析結果を評価（OpenAI）"""
    prompt = make_judge_prompt(state["document_content"], state["analysis_result"])

    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=AnalysisEvaluation,
        temperature=0.3,  # 一貫した評価のため低温度設定
    )

    evaluation_result = result.choices[0].message.parsed
    logger.info(f"Evaluation complete: Grade {evaluation_result.grade}/5")

    return {**state, "evaluation_result": evaluation_result}
```

**評価基準**:
1. **Theme Accuracy (20%)**: テーマが主題を正確に捉えているか
2. **Value Assessment (30%)**: 価値の説明が明確で説得力があるか
3. **Improvement Quality (30%)**: 改善提案が具体的で実行可能か
4. **Completeness (10%)**: 分析が文書の重要な側面をカバーしているか
5. **Clarity (10%)**: 分析が明確で理解しやすいか

#### 4. プロンプト生成 (`src/prompt/llm_pipeline_prompt.py`)

2種類のプロンプトを動的に生成します：

**分析プロンプト** (make_document_analysis_prompt):
```python
def make_document_analysis_prompt(document_content: str) -> list[dict[str, str]]:
    """文書分析用プロンプト生成"""
    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an excellent document analyst.
You will analyze technical documents from these perspectives:
1. Theme (1-2 sentences)
2. Value (2-3 sentences)
3. Improvement Requests (3-5 items)

JSON structure:
{schema_json}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this document:\n\n{document_content}"},
    ]
```

**評価プロンプト** (make_judge_prompt):
```python
def make_judge_prompt(document_content: str, analysis_result: DocumentAnalysis):
    """LLM-as-a-Judge用プロンプト生成"""
    system_prompt = f"""You are an expert evaluator of document analysis quality.

Evaluation Criteria:
- Theme Accuracy (20%)
- Value Assessment (30%)
- Improvement Quality (30%)
- Completeness (10%)
- Clarity (10%)

Grading Scale: 1 (Very Poor) to 5 (Excellent)
"""

    user_prompt = f"""Evaluate this analysis:

**Original Document:**
{document_content}

**Analysis:**
{analysis_result.model_dump_json()}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
```

#### 5. API呼び出しの実装

##### OpenAI実装 (`src/service/llm_pipeline_service.py:55-112`)

```python
async def analyze_document_openai_node(state: PipelineState) -> PipelineState:
    prompt = make_document_analysis_prompt(state["document_content"])

    # リトライ時はフィードバックを追加
    if state.get("evaluation_result") and state.get("retry_count", 0) > 0:
        feedback_msg = f"""Previous grade: {evaluation_result.grade}/5
Feedback: {evaluation_result.reasoning}
Improvements needed: {evaluation_result.specific_improvements}
"""
        prompt.append({"role": "user", "content": feedback_msg})

    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=DocumentAnalysis,
        temperature=0.7,
    )

    return {**state, "analysis_result": result.choices[0].message.parsed}
```

##### Gemini実装 (`src/service/llm_pipeline_service.py:114-174`)

```python
async def analyze_document_gemini_node(state: PipelineState) -> PipelineState:
    system_instruction, user_content = make_document_analysis_system_instruction(
        state["document_content"]
    )

    # リトライ時はフィードバックを追加
    if state.get("evaluation_result") and state.get("retry_count", 0) > 0:
        user_content += f"\n\nFeedback: {evaluation_result.reasoning}..."

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=DocumentAnalysis,
            temperature=0.7,
        ),
    )

    return {**state, "analysis_result": result.parsed}
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - langgraph>=1.0.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
  - pyyaml>=6.0.3

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
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
# Gemini APIを使用（デフォルト）
uv run python -m src.main \
  --llm-provider gemini \
  --model gemini-2.5-flash \
  --document-path dataset/document_0.md

# OpenAI APIを使用
uv run python -m src.main \
  --llm-provider openai \
  --model gpt-4o \
  --document-path dataset/document_1.md

# 短縮オプション
uv run python -m src.main \
  -lp openai \
  -m gpt-4o \
  -dp dataset/document_0.md
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main \
  -lp gemini \
  -m gemini-2.5-flash \
  -dp dataset/document_0.md \
  --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main \
  -lp gemini \
  -m gemini-2.5-flash \
  -dp dataset/document_0.md \
  -od ./my_analysis
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [openai|gemini]
                                  The LLM provider to use.
  -m, --model [gpt-5|gpt-5-mini|gpt-5-nano|gpt-4.1|gpt-4.1-mini|gpt-4.1-nano|gpt-4o|gpt-4o-mini|gemini-2.5-pro|gemini-2.5-flash|gemini-2.5-flash-lite]
                                  The model to use for the request.
  -od, --output-directory PATH    The directory to save output files.
  -dp, --document-path PATH       Path to the markdown document to analyze.
  --help                          Show this message and exit.
```

#### Makefileを使用した実行

```bash
# Gemini APIで分析実行
make run-gemini

# OpenAI APIで分析実行
make run-openai

# テストの実行
make test

# コードフォーマット
make format
```

### 出力例

実行すると、以下の2種類のファイルが生成されます：

#### 1. JSON出力 (`outputs/gemini_analysis_a1b2c3d4e5f6.json`)

```json
{
    "theme": "このドキュメントは、LLMを活用したシステムにおけるLLMパイプラインパターンについて解説しています。複雑なタスクを段階的に処理することで、単一呼び出しでは実現困難な高精度なシステムを構築する方法を示しています。",
    "value": "このドキュメントは、LLMアプリケーション開発者にとって非常に価値があります。複雑なタスクを適切に分割し、各ステージで明確な責務を持たせることで、デバッグ性やメンテナンス性を大幅に向上させる実践的な設計パターンを提供します。また、LangChainやLangGraphなどの具体的なフレームワークの活用方法も示されており、即座に実装に移せる知識が得られます。",
    "improvement_requests": [
        "具体的なコード例やスニペットを追加して、実装イメージをより明確にする",
        "パイプラインのパフォーマンス最適化に関する具体的なベストプラクティスを追加する",
        "エラーハンドリングとリトライ戦略の実装例を詳細に説明する",
        "小規模プロジェクトから段階的に導入する際の具体的なロードマップを提示する",
        "コストとレイテンシのトレードオフを定量的に分析した事例を追加する"
    ]
}
```

#### 2. Markdown出力 (`outputs/gemini_analysis_a1b2c3d4e5f6.md`)

```markdown
# Document Analysis Result

## Theme
このドキュメントは、LLMを活用したシステムにおけるLLMパイプラインパターンについて解説しています。複雑なタスクを段階的に処理することで、単一呼び出しでは実現困難な高精度なシステムを構築する方法を示しています。

## Value
このドキュメントは、LLMアプリケーション開発者にとって非常に価値があります。複雑なタスクを適切に分割し、各ステージで明確な責務を持たせることで、デバッグ性やメンテナンス性を大幅に向上させる実践的な設計パターンを提供します。また、LangChainやLangGraphなどの具体的なフレームワークの活用方法も示されており、即座に実装に移せる知識が得られます。

## Improvement Requests
1. 具体的なコード例やスニペットを追加して、実装イメージをより明確にする
2. パイプラインのパフォーマンス最適化に関する具体的なベストプラクティスを追加する
3. エラーハンドリングとリトライ戦略の実装例を詳細に説明する
4. 小規模プロジェクトから段階的に導入する際の具体的なロードマップを提示する
5. コストとレイテンシのトレードオフを定量的に分析した事例を追加する
```

#### 実行ログ例

```
[2025-10-19 10:30:45] [INFO] [__main__] [main.py:61] [main] LLM provider: gemini
Model: gemini-2.5-flash
Document path: dataset/document_0.md
Output directory: outputs

[2025-10-19 10:30:45] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:484] [run_document_analysis_pipeline] Starting document analysis pipeline for: dataset/document_0.md
[2025-10-19 10:30:45] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:485] [run_document_analysis_pipeline] LLM Provider: LLMProvider.GEMINI, Model: gemini-2.5-flash

[2025-10-19 10:30:45] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:32] [read_document_node] Reading document from: dataset/document_0.md
[2025-10-19 10:30:45] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:38] [read_document_node] Successfully read document (3245 characters)

[2025-10-19 10:30:45] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:294] [route_to_llm_provider] Routing to Gemini

[2025-10-19 10:30:45] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:125] [analyze_document_gemini_node] Analyzing document with Gemini (attempt 1)
[2025-10-19 10:30:48] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:160] [analyze_document_gemini_node] Successfully analyzed document with Gemini

[2025-10-19 10:30:48] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:325] [route_to_judge] Routing to Gemini judge

[2025-10-19 10:30:48] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:233] [judge_analysis_gemini_node] Evaluating analysis with Gemini judge
[2025-10-19 10:30:50] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:257] [judge_analysis_gemini_node] Evaluation complete: Grade 3/5
[2025-10-19 10:30:50] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:258] [judge_analysis_gemini_node] Reasoning: The analysis captures the main theme and value adequately but lacks depth in some areas. The improvement requests are somewhat generic and could be more specific and actionable.

[2025-10-19 10:30:50] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:367] [route_after_judge] Analysis grade 3/5 is below threshold. Retrying (attempt 2/3)

[2025-10-19 10:30:50] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:125] [analyze_document_gemini_node] Analyzing document with Gemini (attempt 2)
[2025-10-19 10:30:50] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:146] [analyze_document_gemini_node] Added judge feedback to prompt for retry
[2025-10-19 10:30:53] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:160] [analyze_document_gemini_node] Successfully analyzed document with Gemini

[2025-10-19 10:30:53] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:233] [judge_analysis_gemini_node] Evaluating analysis with Gemini judge
[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:257] [judge_analysis_gemini_node] Evaluation complete: Grade 4/5
[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:258] [judge_analysis_gemini_node] Reasoning: The improved analysis provides a more comprehensive understanding of the document's theme and value. The improvement requests are now more specific and actionable, demonstrating good analysis quality.

[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:356] [route_after_judge] Analysis accepted with grade 4/5

[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:513] [run_document_analysis_pipeline] Pipeline completed successfully
[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:514] [run_document_analysis_pipeline] Total analysis attempts: 2
[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:517] [run_document_analysis_pipeline] Final evaluation grade: 4/5
[2025-10-19 10:30:55] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:518] [run_document_analysis_pipeline] Evaluation reasoning: The improved analysis provides a more comprehensive understanding...

[2025-10-19 10:30:55] [INFO] [__main__] [main.py:95] [main] Analysis results saved:
JSON: outputs/gemini_analysis_a1b2c3d4e5f6.json
Markdown: outputs/gemini_analysis_a1b2c3d4e5f6.md
```

上記のログから、以下のパイプライン実行が確認できます：
1. 文書読み込み成功（3245文字）
2. 1回目の分析実行 → 評価grade 3/5（基準未達）
3. 改善フィードバック付きで2回目の分析実行 → 評価grade 4/5（合格）
4. パイプライン完了、結果をJSON/Markdown形式で保存

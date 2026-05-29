# Chapter 4 Section 5: LLMパイプライン

## 概要

このプロジェクトは、**LangGraphを活用したLLMパイプライン**の実践的な実装例を示すサンプルコードです。複雑なタスクを複数のステージに分割し、各ステージでLLMの役割を明確に分担することで、高精度な文書分析システムを実現します。

LLM-as-a-Judge（LLMを評価者として活用する）パターンを採用し、分析結果の品質を自動評価して、必要に応じて改善フィードバックを与えながら再実行する仕組みを実装しています。OpenAI GPT-5.4とGoogle Gemini 2.5の両方に対応し、構造化出力による型安全な実装を実現しています。

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
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用（デフォルト）
uv run python -m src.main \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --document-path dataset/document_0.md

# OpenAI APIを使用
uv run python -m src.main \
  --llm-provider OPENAI \
  --model GPT_5_MINI \
  --document-path dataset/document_1.md

# 短縮オプション
uv run python -m src.main \
  -lp OPENAI \
  -m GPT_5_MINI \
  -dp dataset/document_0.md
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main \
  -lp GEMINI \
  -m GEMINI_2_5_FLASH \
  -dp dataset/document_0.md \
  --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main \
  -lp GEMINI \
  -m GEMINI_2_5_FLASH \
  -dp dataset/document_0.md \
  -od ./my_analysis
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -lp, --llm-provider [OPENAI|GEMINI]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_5|GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -dp, --document-path PATH       Path to the markdown document to analyze.
                                  [required]
  --help                          Show this message and exit.
```

### 出力例

実行すると、以下の2種類のファイルが生成されます：

#### 1. JSON出力 (`outputs/gemini_analysis_a1b2c3d4e5f6.json`)

```json
{
    "theme": "LLMの出力を構造化することで、システムに安全かつ信頼性の高い統合を実現する手法について解説しています。",
    "value": "この文書は、非構造化データの問題を解決し、LLMの出力を構造化してシステムと連携する方法を提供します。特に、医療や金融などビジネスクリティカルな場面でのLLMの活用に役立ち、自然言語処理の不確実性を排除し、予測可能性を高める実践的な指針を示しています。",
    "improvement_requests": [
        "具体的なコード例を増やして、実装の理解をより深められるようにする。",
        "構造化出力を使用したシステムでの失敗例や成功例を詳細に挙げ、実務での応用可能性を示す。",
        "各セクションの要約を追加し、読み手に理解を促す。",
        "異なるLLMモデル間での構造化出力の比較や違いについて言及する。",
        "構造化出力のコスト面の詳細な分析を追加し、採用時の注意点を補足する。"
    ]
}
```

#### 2. Markdown出力 (`outputs/gemini_analysis_a1b2c3d4e5f6.md`)

```markdown
# Document Analysis Result

## Theme
LLMの出力を構造化することで、システムに安全かつ信頼性の高い統合を実現する手法について解説しています。

## Value
この文書は、非構造化データの問題を解決し、LLMの出力を構造化してシステムと連携する方法を提供します。特に、医療や金融などビジネスクリティカルな場面でのLLMの活用に役立ち、自然言語処理の不確実性を排除し、予測可能性を高める実践的な指針を示しています。

## Improvement Requests
1. 具体的なコード例を増やして、実装の理解をより深められるようにする。
2. 構造化出力を使用したシステムでの失敗例や成功例を詳細に挙げ、実務での応用可能性を示す。
3. 各セクションの要約を追加し、読み手に理解を促す。
4. 異なるLLMモデル間での構造化出力の比較や違いについて言及する。
5. 構造化出力のコスト面の詳細な分析を追加し、採用時の注意点を補足する。

```

#### 実行ログ例

```
$ uv run python -m src.main \
  --llm-provider GEMINI \
  --model GEMINI_2_5_FLASH \
  --document-path dataset/document_0.md

[2026-02-07 08:37:06,749] [INFO] [__main__] [main.py:60] [main] LLM provider: gemini
Model: gemini-2.5-flash
Document path: dataset/document_0.md
Output directory: outputs

[2026-02-07 08:37:06,749] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:380] [run_document_analysis_pipeline] Starting document analysis pipeline for: dataset/document_0.md
[2026-02-07 08:37:06,749] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:381] [run_document_analysis_pipeline] LLM Provider: gemini, Model: gemini-2.5-flash
[2026-02-07 08:37:07,736] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:23] [read_document_node] Reading document from: dataset/document_0.md
[2026-02-07 08:37:07,738] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:29] [read_document_node] Successfully read document (4743 characters)
[2026-02-07 08:37:07,739] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:237] [route_to_llm_provider] Routing to OpenAI
[2026-02-07 08:37:07,740] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:49] [analyze_document_openai_node] Analyzing document with OpenAI (attempt 1)
[2026-02-07 08:37:17,638] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:78] [analyze_document_openai_node] Successfully analyzed document with OpenAI
[2026-02-07 08:37:17,638] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:260] [route_to_judge] Routing to OpenAI judge
[2026-02-07 08:37:17,639] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:150] [judge_analysis_openai_node] Evaluating analysis with OpenAI judge
[2026-02-07 08:37:22,229] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:167] [judge_analysis_openai_node] Evaluation complete: Grade 4/5
[2026-02-07 08:37:22,229] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:168] [judge_analysis_openai_node] Reasoning: 分析は主題を正確に捉えており、文書の価値を効果的に伝えています。改善点も具体的で実用的な案を提示しており、分析全体が良く構成されています。ただし、提案された改善点の重要性をもう少し優先順位付けして説明していると、さらに説得力が増したかもしれません。
[2026-02-07 08:37:22,229] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:284] [route_after_judge] Analysis accepted with grade 4/5
[2026-02-07 08:37:22,230] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:406] [run_document_analysis_pipeline] Pipeline completed successfully
[2026-02-07 08:37:22,230] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:407] [run_document_analysis_pipeline] Total analysis attempts: 1
[2026-02-07 08:37:22,230] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:410] [run_document_analysis_pipeline] Final evaluation grade: 4/5
[2026-02-07 08:37:22,230] [INFO] [src.service.llm_pipeline_service] [llm_pipeline_service.py:411] [run_document_analysis_pipeline] Evaluation reasoning: 分析は主題を正確に捉えており、文書の価値を効果的に伝えています。改善点も具体的で実用的な案を提示しており、分析全体が良く構成されています。 ただし、提案された改善点の重要性をもう少し優先順位付けして説明していると、さらに説得力が増したかもしれません。
[2026-02-07 08:37:22,230] [INFO] [__main__] [main.py:92] [main] Analysis results saved:
JSON: outputs/gemini_analysis_acfc8bed03d84ac19b12b4783c9b1af1.json
Markdown: outputs/gemini_analysis_acfc8bed03d84ac19b12b4783c9b1af1.md
```

# Chapter 5 Section 7: イベント駆動型AIエージェント

## 概要

本プロジェクトは、イベント駆動アーキテクチャを採用したAIエージェントシステムの実装例です。ディレクトリを監視し、新しい契約書ファイルが保存されると自動的に契約リスクコンプライアンスパイプラインを起動して、リスク評価レポートを生成します。

イベント駆動アーキテクチャにより、システム内の状態変化やアクションを「イベント」として捉え、それらを契機に各機能が非同期に動作します。これにより、エージェントの各機能を疎結合に保ち、拡張性と応答性に優れたシステムを実現しています。

## 機能

- **ファイル監視**: `watchdog`ライブラリを使用してディレクトリを監視し、新規ファイルを検知
- **イベント駆動処理**: Publish/Subscribe パターンによる疎結合なイベント処理
- **契約書リスク評価**: LangGraphを使用したパイプラインAIエージェントによる自動リスク評価
- **コンプライアンスレポート生成**: 章・条ごとの詳細なリスク分析レポートを自動生成
- **相関ID追跡**: すべてのイベントに相関IDを付与し、処理フローのトレーサビリティを確保

## プロジェクト構成

### ディレクトリ構成

```
chapter_5/section_7/
├── CLAUDE.md                    # プロジェクト設計ドキュメント
├── pyproject.toml               # プロジェクト設定・依存関係
├── contract/                    # 契約書ファイル格納ディレクトリ（監視対象）
│   ├── contract_0.md
│   ├── contract_1.md
│   └── ...
├── outputs/                     # 生成されたレポート出力先
└── src/
    ├── __init__.py
    ├── event_runner.py          # イベント駆動ランナー（エントリポイント）
    ├── config.py                # 設定
    ├── logger.py                # ロギング設定
    ├── client/
    │   └── llm_client.py        # LLMクライアント定義
    ├── model/
    │   ├── model.py             # パイプラインモデル定義
    │   └── event_model.py       # イベントモデル定義
    ├── service/
    │   ├── service.py           # パイプラインサービス
    │   └── event_handler.py     # イベントハンドラー
    ├── layer/
    │   └── contract_pipeline/   # パイプラインステージ実装
    │       ├── extraction.py    # 抽出ステージ
    │       ├── risk_scoring.py  # リスク評価ステージ
    │       └── report.py        # レポート生成ステージ
    └── prompt/
        └── prompt.py            # プロンプト定義
```

### アーキテクチャ

本システムは、ファイル監視とイベント駆動処理を組み合わせた2層構造で設計されています。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Event-Driven AI Agent                              │
│                                                                          │
│  ┌──────────────┐      ┌──────────────┐      ┌────────────────────┐     │
│  │   Watchdog   │─────▶│  Event Bus   │─────▶│  Event Handlers    │     │
│  │ (File Watch) │      │              │      │                    │     │
│  └──────────────┘      └──────────────┘      └────────────────────┘     │
│         │                     │                       │                  │
│         ▼                     ▼                       ▼                  │
│  FileCreatedEvent     Publish/Subscribe       Contract Pipeline         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

イベントフロー:
    FileCreatedEvent
          │
          ▼
    ┌─────────────────────┐
    │ FileCreatedHandler  │  (フィルタリング & 変換)
    └──────────┬──────────┘
               │
               ▼
    ContractReviewRequestedEvent
               │
               ▼
    ┌─────────────────────────────┐
    │ ContractReviewHandler       │  (パイプライン実行)
    └──────────┬──────────────────┘
               │
               ▼
    ContractReviewCompletedEvent / ContractReviewFailedEvent

契約書レビューパイプライン:
    ┌─────────────────┐
    │  Input Stage    │  (契約書ファイル読み込み)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Extraction Stage│  (章・条の構造抽出)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Risk Scoring    │  (各条項のリスク評価)
    │     Stage       │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Report Stage    │  (コンプライアンスレポート生成)
    └────────┬────────┘
             │
             ▼
           [END]
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 主要な依存ライブラリ:
  - `langgraph>=1.0.0` - パイプラインAIエージェント構築
  - `langchain-openai>=1.1.0` - OpenAI連携
  - `watchdog>=6.0.0` - ファイルシステム監視
  - `click>=8.3.0` - CLI構築
  - `pydantic>=2.12.2` - データモデル

### セットアップ

1. 環境変数を設定:

```bash
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定
```

必要な環境変数:
```
OPENAI_API_KEY=<your_openai_api_key_here>
```

2. 依存関係をインストール:

```bash
uv sync
```

### 使用方法、実行方法

ディレクトリを監視し、新規ファイルを自動的に処理します:

```bash
# contract/ ディレクトリを監視（デフォルト）
uv run python -m src.event_runner

# カスタムディレクトリを監視
uv run python -m src.event_runner -w contracts/

# カスタムモデルを使用
uv run python -m src.event_runner -w contract/ -m GPT_5_2 -od outputs

# カスタム出力ディレクトリを指定
uv run python -m src.event_runner -w contract/ -od reports/
```

CLIオプション:

| オプション | 短縮形 | デフォルト        | 説明 |
|-----------|--------|--------------|------|
| `--watch-directory` | `-w` | `data`       | 監視するディレクトリ |
| `--model` | `-m` | `GPT_5_MINI` | 使用するLLMモデル |
| `--output-directory` | `-od` | `outputs`    | レポート出力先 |

```bash
$ uv run python -m src.event_runner --help
Usage: python -m src.event_runner [OPTIONS]

  Event-Driven AI Agent Runner

  This system monitors a directory for new contract files and automatically
  triggers the contract risk compliance pipeline when new files are detected.

  Architecture:

  1. File Watcher: Monitors directory using watchdog
  2. Event Bus: Publishes FileCreatedEvent on new files
  3. FileCreatedHandler: Transforms to ContractReviewRequestedEvent
  4. ContractReviewHandler: Runs the compliance pipeline
  5. Result Events: Publishes completion/failure events

  Examples:

      # Watch data directory with defaults
      python -m src.event_runner

      # Watch custom directory     python -m src.event_runner -w contracts/

      # With custom model     python -m src.event_runner -w data/ -m gpt-4o

      # With custom output directory     python -m src.event_runner -w data/
      -od reports/

Options:
  -w, --watch-directory PATH      Directory to watch for new contract files.
  -m, --model [GPT_5_2|GPT_5|GPT_5_MINI|GPT_5_NANO]
                                  The model to use for contract review.
  -od, --output-directory PATH    Directory to save compliance reports.
  --help                          Show this message and exit.
```

### 出力例

#### 実行ログ

```bash
$ uv run python -m src.event_runner -w contract/ -m GPT_5_2 -od outputs

[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:156] [start] ======================================================================
[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:157] [start] EVENT-DRIVEN AI AGENT STARTING
[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:158] [start] ======================================================================
[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:159] [start] Watch directory: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract
[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:160] [start] Model: gpt-5.2
[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:161] [start] Output directory: outputs
[2026-02-07 09:24:16,937] [INFO] [__main__] [event_runner.py:162] [start] ======================================================================
[2026-02-07 09:24:16,937] [INFO] [src.service.event_handler] [event_handler.py:190] [register_handler] Registered handler: FileCreatedHandler
[2026-02-07 09:24:16,937] [INFO] [src.service.event_handler] [event_handler.py:190] [register_handler] Registered handler: ContractReviewHandler
[2026-02-07 09:24:16,939] [INFO] [__main__] [event_runner.py:187] [start] File watcher started. Waiting for new files...
[2026-02-07 09:24:16,939] [INFO] [__main__] [event_runner.py:188] [start] Press Ctrl+C to stop.
[2026-02-07 09:29:02,655] [INFO] [__main__] [event_runner.py:99] [on_created] New file detected: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md
[2026-02-07 09:29:02,655] [INFO] [src.service.event_handler] [event_handler.py:203] [publish] Event published: file_created [correlation_id=3400b26b...]
[2026-02-07 09:29:02,655] [INFO] [__main__] [event_runner.py:112] [event_logger_callback] EVENT LOG: {'event_id': '2a7d6968625e437a983202392e244d76', 'correlation_id': '3400b26b546c411291e889294d627afd', 'timestamp': '2026-02-07T09:29:02.655540', 'event_type': 'file_created', 'file_path': '/Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md', 'file_name': 'contract_1.md', 'file_extension': '.md'}
[2026-02-07 09:29:02,655] [INFO] [src.service.event_handler] [event_handler.py:213] [publish] Handler FileCreatedHandler processing event
[2026-02-07 09:29:02,655] [INFO] [src.service.event_handler] [event_handler.py:89] [handle] FileCreatedHandler processing: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md
[2026-02-07 09:29:02,656] [INFO] [src.service.event_handler] [event_handler.py:99] [handle] Creating ContractReviewRequestedEvent for: contract_1.md
[2026-02-07 09:29:02,656] [INFO] [src.service.event_handler] [event_handler.py:203] [publish] Event published: contract_review_requested [correlation_id=3400b26b...]
[2026-02-07 09:29:02,656] [INFO] [__main__] [event_runner.py:112] [event_logger_callback] EVENT LOG: {'event_id': 'db4617848b044dcdac92627f65d3a584', 'correlation_id': '3400b26b546c411291e889294d627afd', 'timestamp': '2026-02-07T09:29:02.656082', 'event_type': 'contract_review_requested', 'contract_file_path': '/Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md', 'model': <OpenAIModel.GPT_5_2: 'gpt-5.2'>, 'output_directory': 'outputs'}
[2026-02-07 09:29:02,656] [INFO] [src.service.event_handler] [event_handler.py:213] [publish] Handler ContractReviewHandler processing event
[2026-02-07 09:29:02,656] [INFO] [src.service.event_handler] [event_handler.py:128] [handle] ContractReviewHandler processing: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md
[2026-02-07 09:29:02,656] [INFO] [src.service.event_handler] [event_handler.py:129] [handle] Using model: gpt-5.2
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:119] [run_contract_compliance_pipeline] ================================================================================
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:120] [run_contract_compliance_pipeline] CONTRACT RISK COMPLIANCE PIPELINE
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:121] [run_contract_compliance_pipeline] Pipeline: Input -> Extraction -> Risk Scoring -> Report
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:122] [run_contract_compliance_pipeline] ================================================================================
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:123] [run_contract_compliance_pipeline] Contract file: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:124] [run_contract_compliance_pipeline] Model: gpt-5.2
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:60] [create_contract_pipeline_graph] Creating contract compliance pipeline graph...
[2026-02-07 09:29:02,656] [INFO] [src.service.service] [service.py:73] [create_contract_pipeline_graph] Contract pipeline graph created successfully
[2026-02-07 09:29:02,664] [INFO] [src.service.service] [service.py:83] [_read_contract_file] Reading contract file: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md
[2026-02-07 09:29:02,664] [INFO] [src.service.service] [service.py:130] [run_contract_compliance_pipeline] Contract ID: contract_26504683
[2026-02-07 09:29:02,666] [INFO] [PIPELINE.ExtractionAgent] [base.py:63] [_log_layer_start] ============================================================
[2026-02-07 09:29:02,666] [INFO] [PIPELINE.ExtractionAgent] [base.py:64] [_log_layer_start] PIPELINE LAYER - ExtractionAgent: Extracting contract structure
[2026-02-07 09:29:02,666] [INFO] [PIPELINE.ExtractionAgent] [base.py:65] [_log_layer_start] ============================================================
[2026-02-07 09:29:02,666] [INFO] [PIPELINE.ExtractionAgent] [extraction.py:83] [execute] Processing contract: contract_26504683
[2026-02-07 09:29:31,663] [INFO] [PIPELINE.ExtractionAgent] [base.py:89] [_invoke_structured] Received structured response from LLM
[2026-02-07 09:29:31,664] [INFO] [PIPELINE.ExtractionAgent] [extraction.py:95] [execute] Extraction complete: 14 sections
[2026-02-07 09:29:31,665] [INFO] [PIPELINE.RiskScoringAgent] [base.py:63] [_log_layer_start] ============================================================
[2026-02-07 09:29:31,665] [INFO] [PIPELINE.RiskScoringAgent] [base.py:64] [_log_layer_start] PIPELINE LAYER - RiskScoringAgent: Risk Scoring
[2026-02-07 09:29:31,665] [INFO] [PIPELINE.RiskScoringAgent] [base.py:65] [_log_layer_start] ============================================================
[2026-02-07 09:29:31,665] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:112] [execute_async] Assessing 14 sections concurrently (limit: 20)...
[2026-02-07 09:29:31,665] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第1条 目的と契約の性 質
[2026-02-07 09:29:31,666] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第2条 業務内容
[2026-02-07 09:29:31,667] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第3条 契約期間
[2026-02-07 09:29:31,668] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第4条 業務遂行責任者 および担当者
[2026-02-07 09:29:31,669] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第5条 業務の報告
[2026-02-07 09:29:31,670] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第6条 再委託の禁止
[2026-02-07 09:29:31,671] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第7条 委託料
[2026-02-07 09:29:31,671] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第8条 諸費用の負担
[2026-02-07 09:29:31,672] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第9条 成果物の提出と 確認
[2026-02-07 09:29:31,673] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第10条 知的財産権の帰属
[2026-02-07 09:29:31,674] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第11条 秘密保持
[2026-02-07 09:29:31,675] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第12条 契約の解除
[2026-02-07 09:29:31,676] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第13条 協議事項
[2026-02-07 09:29:31,676] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:78] [_assess_section_async] Assessing section: 第14条 管轄裁判所
[2026-02-07 09:29:40,860] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:40,861] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第14条 - Risk: medium
[2026-02-07 09:29:41,620] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:41,620] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第13条 - Risk: medium
[2026-02-07 09:29:42,746] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:42,746] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第6条 - Risk: medium
[2026-02-07 09:29:43,001] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:43,001] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第1条 - Risk: medium
[2026-02-07 09:29:44,353] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:44,353] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第3条 - Risk: medium
[2026-02-07 09:29:44,798] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:44,798] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第4条 - Risk: medium
[2026-02-07 09:29:44,959] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:44,959] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第5条 - Risk: medium
[2026-02-07 09:29:45,129] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:45,129] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第8条 - Risk: medium
[2026-02-07 09:29:45,176] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:45,176] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第9条 - Risk: medium
[2026-02-07 09:29:46,118] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:46,118] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第11条 - Risk: medium
[2026-02-07 09:29:47,287] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:47,287] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第12条 - Risk: high
[2026-02-07 09:29:50,488] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:50,488] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第10条 - Risk: medium
[2026-02-07 09:29:50,645] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:50,646] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第2条 - Risk: medium
[2026-02-07 09:29:51,351] [INFO] [PIPELINE.RiskScoringAgent] [base.py:124] [_ainvoke_structured] Received structured response from LLM
[2026-02-07 09:29:51,351] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:95] [_assess_section_async] Completed: 第7条 - Risk: medium
[2026-02-07 09:29:51,351] [INFO] [PIPELINE.RiskScoringAgent] [risk_scoring.py:131] [execute_async] Risk scoring complete: 43 findings, 2 high/critical
[2026-02-07 09:29:51,352] [INFO] [PIPELINE.ReportAgent] [base.py:63] [_log_layer_start] ============================================================
[2026-02-07 09:29:51,352] [INFO] [PIPELINE.ReportAgent] [base.py:64] [_log_layer_start] PIPELINE LAYER - ReportAgent: Report Generation
[2026-02-07 09:29:51,352] [INFO] [PIPELINE.ReportAgent] [base.py:65] [_log_layer_start] ============================================================
[2026-02-07 09:29:51,352] [INFO] [PIPELINE.ReportAgent] [report.py:109] [execute] Generating report for: ソフトウェア開発業務準委任契約書
[2026-02-07 09:30:31,521] [INFO] [PIPELINE.ReportAgent] [base.py:89] [_invoke_structured] Received structured response from LLM
[2026-02-07 09:30:31,521] [INFO] [PIPELINE.ReportAgent] [report.py:128] [execute] Report generated: report_1d0c12f1 - Status: needs_review
[2026-02-07 09:30:31,521] [INFO] [src.service.service] [service.py:136] [run_contract_compliance_pipeline] ================================================================================
[2026-02-07 09:30:31,521] [INFO] [src.service.service] [service.py:137] [run_contract_compliance_pipeline] COMPLIANCE REPORT GENERATED SUCCESSFULLY
[2026-02-07 09:30:31,521] [INFO] [src.service.service] [service.py:138] [run_contract_compliance_pipeline] Report ID: report_1d0c12f1
[2026-02-07 09:30:31,521] [INFO] [src.service.service] [service.py:139] [run_contract_compliance_pipeline] Overall Status: needs_review
[2026-02-07 09:30:31,521] [INFO] [src.service.service] [service.py:140] [run_contract_compliance_pipeline] Risk Score: 68/100
[2026-02-07 09:30:31,521] [INFO] [src.service.service] [service.py:141] [run_contract_compliance_pipeline] ================================================================================
[2026-02-07 09:30:31,522] [INFO] [src.service.event_handler] [event_handler.py:148] [handle] Report saved: outputs/compliance_report_report_1d0c12f1.md
[2026-02-07 09:30:31,522] [INFO] [src.service.event_handler] [event_handler.py:203] [publish] Event published: contract_review_completed [correlation_id=3400b26b...]
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:112] [event_logger_callback] EVENT LOG: {'event_id': 'd3d9ff578e0e457e9bd40b728da4a142', 'correlation_id': '3400b26b546c411291e889294d627afd', 'timestamp': '2026-02-07T09:30:31.522799', 'event_type': 'contract_review_completed', 'contract_file_path': '/Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md', 'report_id': 'report_1d0c12f1', 'report_path': 'outputs/compliance_report_report_1d0c12f1.md', 'overall_status': <ComplianceStatus.NEEDS_REVIEW: 'needs_review'>, 'risk_score': 68}
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:115] [event_logger_callback] ============================================================
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:116] [event_logger_callback] CONTRACT REVIEW COMPLETED
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:117] [event_logger_callback]   File: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_5/section_6/contract/contract_1.md
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:118] [event_logger_callback]   Report ID: report_1d0c12f1
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:119] [event_logger_callback]   Status: needs_review
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:120] [event_logger_callback]   Risk Score: 68/100
[2026-02-07 09:30:31,522] [INFO] [__main__] [event_runner.py:121] [event_logger_callback]   Report saved to: outputs/compliance_report_report_1d0c12f1.md
[2026-02-07 09:30:31,523] [INFO] [__main__] [event_runner.py:122] [event_logger_callback] ============================================================
```

#### 生成されるレポート例

```markdown
# 契約書リスクコンプライアンスレポート

**契約書**: ソフトウェア開発業務準委任契約書
**レポートID**: report_1d0c12f1
**生成日時**: 2026-02-07 09:30:31

---

## エグゼクティブサマリー

### 総合評価
- **コンプライアンス状態**: ⚠️ 要確認
- **リスクスコア**: 68/100

本契約は全体として一般的な準委任型の構成ですが、(1)委託料の確定性（別途覚書依存）、(2)解除の片務性（甲のみ中途解約）、という2点に高いリスクがあり、契約締結前の修正・補完が必要です。加えて、成果物/検収・別文書（作業指示書等）の拘束力・変更管理、秘密保持の定義/例外など運用上の不確実性が多く、紛争時の解釈ブレが想定されます。重要条項の覚書化と条文の明確化を行えば、実務運用可能性と紛争予防効果が大きく改善します。

### 主要な懸念事項
- 委託料（単価・精算方法）が「別途覚書」依存で未確定となり得て、請求・支払の確定性が不足（価格条項の高リスク）
- 解除条項が甲に片務的（中途解約権が甲のみ）で、乙の投下コスト回収不能等の重大な商業リスク・紛争リスク
- 準委任性が強調される一方で、成果物・品質基準・検収/受入・瑕疵対応の定義が弱く、期待成果の未達や是正/減額根拠が乏しい
- 業務内容・作業指示書等の別文書への委任が多いが、文書の優先順位/合意手続/変更管理が不明確でスコープクリープが起きやすい
- 秘密情報の定義や例外（法令対応・専門家/委託先への開示）が不足し、実務運用で契約違反化・情報管理の過不足が生じ得る

### 即時対応が必要な事項
- ⚠️ 単価・精算単価・工数承認フロー（期限/未承認時/端数処理等）を覚書/SOWとして先行確定し、契約との優先順位・変更手続を明記する
- ⚠️ 解除条項を是正（乙にも中途解約権、予告期間、解約精算の範囲・算定式、重大違反の即時解除等）し、片務性を解消する
- ⚠️ 成果物定義（成果物一覧）、品質基準、受入/確認手続（期限・合否基準・修正対応範囲）を明文化し、準委任下でも期待水準を固定する
- ⚠️ 秘密情報の定義・除外、第三者開示例外、秘密保持期間（情報類型に応じた延長/営業秘密は存続等）を整備する

---

## リスク分析

### 支払条件
- **検出件数**: 8件
- **主な問題点**:
  - 単価・精算単価が別途覚書等に委ねられ、未整備の場合に価格未確定となる
  - 稼働実績の算定・承認（形式、期限、未承認時、端数処理等）が不明確で請求紛争化しやすい
  - 実費精算の範囲・承諾手続が不明確で、費用負担の認識齟齬が起きやすい

### 契約解除
- **検出件数**: 6件
- **主な問題点**:
  - 中途解約権が甲のみで、権利義務が不均衡（乙の商業リスクが高い）
  - 解約時精算（進行作業、未検収分、立替費用等）の算定基準が不明確
  - 是正期間としての「相当の期間」が抽象的で運用・紛争時の不確実性がある

### 知的財産権
- **検出件数**: 4件
- **主な問題点**:
  - 権利移転が支払完了時点で、検収前利用や支払遅延時に帰属が不安定
  - 成果物範囲や第三者IP/OSS混入時の取扱いが不明確
  - 乙保有IPのライセンス範囲（改変・複製・サブライセンス・期間等）が抽象的

### 秘密保持
- **検出件数**: 4件
- **主な問題点**:
  - 秘密情報の定義欠如により、保護対象・管理範囲が不明確
  - 法令対応・専門家・委託先等への開示例外がなく実務上の支障/違反リスク
  - 秘密保持期間が一律3年で、長期価値情報（営業秘密等）の保護が不足し得る

### 紛争解決
- **検出件数**: 4件
- **主な問題点**:
  - 協議不調時の解決手段（仲裁、準拠法、手続、優先順位等）が不足し紛争長期化の恐れ
  - 専属管轄が大阪地裁固定で、当事者の実態によって負担偏在の可能性

### その他
- **検出件数**: 17件
- **主な問題点**:
  - 準委任性が強く、成果物完成義務・品質・瑕疵対応・検収基準が弱い
  - 別文書（作業指示書・月次計画等）の契約上の位置付け/優先順位/変更管理が不明確でスコープクリープが起きやすい
  - 契約期間の日付未確定、及び自動更新（通知期限1か月前）による意図しない継続リスク
  - 報告・定例会の運用要件やタイムシートの取扱いが不明確で工数増・情報管理リスク
  - 再委託の承諾基準・期限、再委託先管理/責任分担が不足し、履行・品質・漏えい時の統制が弱い

---

## セクション別評価詳細

### ✅ 目的と契約の性質
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **「準委任契約」「仕事の完成を約束しない」と明記されており、成果物の完成義務・検収基準・瑕疵対応等が契約上弱くなるため、発注者（甲）側は期待した成果が得られない場合でも是正や減額の根拠が乏しくなるリスクがある。**
  - カテゴリ: 保証
  - レベル: 🟡 中
  - 推奨対応: 甲の期待値を契約に反映するため、(1) 業務範囲・成果物（納品物）がある場合の定義、(2) 品質/性能/サービスレベル（SLA）や受入・検収基準、(3) 不具合・再実施（リワーク）・是正措置、(4) 報告義務・マイルストーン、(5) 達成できない場合の料金調整や解除条件、を別条または仕様書で具体化する。成果物が主目的なら請負（または成果完成条項）の採用も検討する。

- **「次条に定める業務」との参照のみで本条自体に目的・業務のアウトカムが記載されていないため、次条や仕様書の記載が抽象的な場合に、委託範囲・期待水準・役割分担の解釈がブレて紛争化するリスクがある。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 次条（業務内容）および仕様書に、業務範囲（含む/含まない）、前提条件、甲乙の役割分担（甲の協力義務・情報提供）、成果物の有無、判断基準（完了条件）を明確化する。定義条項に「本業務」「成果物」「完了」の定義を置くのも有効。

**備考**: 本条は準委任の位置付けを明確にしており条項として直ちに違法・不適合とはいえない一方、発注者側の成果確保・品質担保の観点では契約設計上のリスクが残る。成果型で運用する場合は、検収・SLA・是正・料金調整等の補完条項の有無が重要。

### ✅ 業務内容
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **具体的な作業内容が「作業指示書」「月次作業計画」等の別文書に委ねられており、当該文書の契約上の位置付け（優先順位、合意方法、変更手続、拘束力）が不明確なため、業務範囲・成果物・納期・検収・対価との紐付けが曖昧になりやすい。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 別文書の定義（作成者、承認者、合意成立時点）、契約との優先順位、変更管理（追加・変更時の見積/スケジュール/対価改定手続）、および別文書が未作成の場合の扱い（業務開始可否・責任分界）を明記する。

- **「その他、甲乙間で合意した関連業務」が包括的で、追加業務の範囲が広がりやすくスコープクリープ（無償対応・工数超過・納期遅延）の原因となる可能性がある。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 追加業務は書面（電子含む）での事前合意を必須とし、追加業務の定義、見積・対価・納期・優先度調整の手続（変更要求票等）を条文化する。必要に応じて「合意なき依頼は業務範囲外」と明記する。

- **業務内容が「設計・技術検証・実装・テスト・助言・コードレビュー」まで含む一方、成果物（ソースコード、設計書、検証レポート等）の明確な列挙、品質基準、受入・検収方法、完了条件が本条では定義されていないため、納品/検収を巡る紛争リスクがある。**
  - カテゴリ: 保証
  - レベル: 🟡 中
  - 推奨対応: 成果物一覧（形式・粒度・提出頻度）、品質/完了基準（Definition of Done、テスト範囲、レビュー基準等）、検収手続（検収期間・不合格時の是正・再検収）を作業指示書等に落とし込み、契約本文でそれらが必須項目であることを定める。

- **対象システム名が特定されているが、本業務における既存資産・バックグラウンドIPの扱い、開発成果の知的財産権帰属、OSS利用方針等が本条からは読み取れず、後続条項で規定がない場合にIP/ライセンス面の不確実性が残る。**
  - カテゴリ: 知的財産権
  - レベル: 🟡 中
  - 推奨対応: （別条で）成果物の権利帰属（著作権・特許等）、既存ツール/ライブラリの持込み条件、OSSコンプライアンス（ライセンス一覧・開示義務・禁止ライセンス）を明確化する。少なくとも本条に関連して、成果物の定義と権利の基本方針を参照条項として明記する。

**備考**: 本条は業務の大枠は示しているものの、具体内容を別文書に委ねる構造のため、別文書の統制（優先順位・変更手続・必須記載事項）がない場合に商業面（追加工数/費用）および運用面（検収/完了条件）の不確実性が高まりやすい。後続条項で委任/準委任・請負の性質、対価、検収、IP、責任分界が十分に規定されているかの確認が望ましい。

### ✅ 契約期間
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **契約期間が「202X年X月X日から202X年Y月Y日まで」となっており、日付が確定していないため、契約開始・終了時点が不明確となるリスクがあります。開始日や終了日の解釈を巡って、請求・成果物・責任範囲・更新可否などの紛争に発展する可能性があります。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 開始日・終了日を実日付で特定してください（例：2026年4月1日〜2027年3月31日）。未確定の場合は「両当事者が記名押印した日」等の客観的確定方法（発効日定義）を設け、期間起算点を明記してください。

- **自動更新条項により、期間満了の1ヶ月前までに書面通知がないと3ヶ月単位で同一条件更新され続けるため、解約手続の失念による意図しない契約継続・コスト発生のリスクがあります。また、通知期限が短めで運用負荷が生じる可能性があります。**
  - カテゴリ: 契約解除
  - レベル: 🟡 中
  - 推奨対応: 自動更新の有無・更新回数上限（例：最大◯回まで）や、通知期限の延長（例：2〜3ヶ月前）を検討してください。併せて「書面」の定義（電子メール等を含むか）と通知方法（宛先、到達主義/発信主義）を明確化すると運用リスクを低減できます。

- **「書面による別段の意思表示」の内容が、更新拒絶のみなのか、条件変更の申し入れも含むのかが不明確です。条件変更交渉の開始が更新阻止に当たるか等、満了・更新局面で解釈が分かれる可能性があります。**
  - カテゴリ: その他
  - レベル: 🟢 低
  - 推奨対応: 別段の意思表示の範囲を明確化してください（例：「更新しない旨の通知」または「更新条件変更の申入れは更新拒絶とはならず、合意に至らない場合は満了終了」等）。

**備考**: 本条は契約期間・更新を定める一般的条項ですが、日付未確定と自動更新運用（通知期限・方法・到達基準）の曖昧さが実務上の主要リスクです。解除条項（中途解約の可否、違約金/精算、通知期間）が別条で定められているか併せて確認すると評価精度が上がります。

### ✅ 業務遂行責任者および担当者
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **担当技術者の配置・変更に甲の「承諾」が必要で、乙側にとって人員配置の柔軟性が低く、プロジェクト継続や要員確保に支障が出るリスクがある（承諾が遅延・不合理に拒否された場合の手当がない）。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 承諾を「事前協議の上、合理的理由なく拒否しない」「〇営業日以内に回答、期限内不回答は承諾とみなす」等に修正し、承諾プロセス（評価基準、提出情報）を明確化する。

- **「やむを得ない事由」「同等のスキル」が抽象的で、変更可否や同等性の判断を巡り紛争になり得る（甲が主観的に不同意とする余地）。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 「やむを得ない事由」の例示（退職・長期病欠・配置転換・法令/安全上の制約・下請先都合等）を追加し、「同等のスキル」を資格・経験年数・同種案件実績・役割（リード/メンバー）等の客観指標で定義する。必要に応じて引継期間・引継計画の提出も規定する。

- **業務遂行責任者の「通知」のみで、責任者の権限・役割（意思決定範囲、指揮命令系統、連絡窓口、承認権限）や変更手続が定められておらず、運用上の混乱や責任所在不明確化のリスクがある。**
  - カテゴリ: その他
  - レベル: 🟢 低
  - 推奨対応: 責任者の職務（進捗・品質管理、報告、変更管理、緊急時対応等）、権限（甲への報告・協議権限、担当者への指揮命令権限）および責任者変更時の通知期限・引継義務を条文化する。

**備考**: 本条は主として運用・体制管理に関する条項で、法令違反の直接リスクは低い一方、承諾要件の強さと用語の曖昧さにより、要員変更時にスケジュール遅延・紛争化する商業的リスクが相対的に高い。甲乙いずれの立場でも、承諾の基準・期限と用語定義を明確化するとリスク低減につながる。

### ✅ 業務の報告
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **月次報告書の提出期限が「毎月末日まで」となっており、対象月の業務を同月末までに確定させて提出する運用が求められるため、実務上の作成・承認プロセスと齟齬が生じやすい（未提出・遅延による契約違反リスク）。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 提出期限を「翌月○営業日まで」等に修正し、承認・差戻し手順（提出→レビュー→修正→確定）と、遅延時の取扱い（猶予、重大な債務不履行に当たるか）を明記する。

- **定例ミーティングが「原則として週1回」とされる一方で、開催日時・所要時間・開催方法（オンライン/対面）・欠席時の扱いが未定義で、工数増大やスケジュール調整不全による業務停滞、追加費用の認識違いが発生し得る。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 開催頻度の上限（例：週1回・60分まで）、開催方法、議題・アジェンダ事前共有、議事録の作成主体、欠席・延期時のルール、追加ミーティングが発生する場合の費用/工数の取扱い（見積範囲内か別途精算か）を定める。

- **報告内容に「タイムシートを含む」とあるが、記載粒度（作業単位、プロジェクトコード等）、提出形式、保管・閲覧権限、機微情報の取扱いが不明確で、個人情報/営業秘密の過剰共有や目的外利用のリスクがある。**
  - カテゴリ: 秘密保持
  - レベル: 🟡 中
  - 推奨対応: タイムシートの必須記載項目・粒度・提出フォーマットを定義し、個人情報や機微情報を記載しない/マスキングする運用を明記する。必要に応じて秘密保持条項・個人情報取扱条項への参照（目的、管理、第三者提供禁止、保管期間）を追記する。

**備考**: 本条は業務管理上は標準的だが、提出期限と運用、定例会の追加負担、タイムシートに含まれ得る情報の管理が未整備だと紛争の火種になりやすい。重大な違法性は直ちには見当たらないためis_compliantはtrueとした。

### ✅ 再委託の禁止
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **再委託が一律に「甲の書面による事前承諾」に依存しており、承諾基準・回答期限・みなし承諾等がないため、乙側で人員不足や専門業者の活用が必要な場合でも機動的に対応できず、納期遅延や履行不能リスクが高まる可能性がある。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 承諾プロセスを明確化（例：甲は申請受領後○営業日以内に書面回答、合理的理由なく承諾を拒まない／期限内不回答は承諾とみなす等）。また、軽微な作業・専門作業（IT保守、配送補助等）や、事前に指定した協力会社は包括承諾とする旨を追加する。

- **再委託を認める場合の管理義務（秘密保持、品質、法令遵守等）や再委託先の行為に関する責任分担が本条だけでは不明確で、情報漏えい・コンプライアンス違反・品質事故等が発生した際の対応が曖昧になり得る。**
  - カテゴリ: 法令遵守
  - レベル: 🟡 中
  - 推奨対応: 再委託を例外的に認める場合の条件を追記（再委託先への本契約と同等以上の秘密保持・安全管理・法令遵守義務の課し込み、乙による監督義務、甲への事前通知事項、事故発生時の報告義務等）。あわせて、再委託先による履行について乙が責任を負う旨（または責任範囲）を明確化する。

**備考**: 再委託の事前承諾を求める条項自体は一般的で、甲の管理・品質確保の観点では標準的です。一方で、承諾手続や例外類型、再委託時の管理条項がない場合、運用面（納期・継続性）および事故対応面で不確実性が残るため、実務運用に合わせた補完が望まれます。

### ⚠️ 委託料
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 要確認

**検出されたリスク:**

- **委託料がタイム・アンド・マテリアル方式である一方、成果物・納入物の定義や検収条件、作業範囲（SOW）との紐付けが本条から読み取れず、コスト増大やスコープ拡大（スコープクリープ）時の紛争リスクがある。**
  - カテゴリ: 支払条件
  - レベル: 🟡 中
  - 推奨対応: 別紙/覚書で(1)業務範囲・前提条件・除外範囲、(2)成果物（あれば）と受入基準、(3)変更管理（追加見積・事前承認・上限超過時の停止権）を明記し、T&Mでも支払対象となる作業の範囲を特定する。

- **単価および精算単価が「別途覚書等」で定めるとされ、当該覚書が未整備/未合意の場合に価格未確定となる。支払条件の確定性が弱く、請求・支払の実務や紛争時の解釈が不安定。**
  - カテゴリ: 支払条件
  - レベル: 🟠 高
  - 推奨対応: 契約締結時点で単価表（役割別・等級別）と精算単価、適用優先順位（本契約＞覚書＞発注書等）を確定させる。未合意時の暫定単価・上限・協議期限も規定する。

- **稼働実績に基づく支払とあるが、稼働実績の算定方法（勤怠/工数表の形式、承認フロー、承認期限、未承認時の取扱い、端数処理、休憩控除、リモート時の計測等）が不明確で、請求額の争いが起こり得る。**
  - カテゴリ: 支払条件
  - レベル: 🟡 中
  - 推奨対応: 工数管理のルール（提出頻度、証憑、甲の承認期限、異議申立期間、未応答＝承認/否認の扱い、端数処理）を覚書に明記し、支払根拠を標準化する。

- **基準時間140〜180時間の精算調整について、超過/控除の計算式（例：下限割れ控除、上限超過加算）、適用単価（時間単価か人月単価換算か）、月途中参画・離任時の按分、法定労働時間や36協定等への配慮が示されていないため、精算の不一致やコンプライアンス上の懸念が残る。**
  - カテゴリ: 法令遵守
  - レベル: 🟡 中
  - 推奨対応: 精算レンジの計算式（下限/上限の控除・加算方法）、換算方法（人月⇄時間）、端数、月途中の按分、残業・深夜等が発生する場合の取扱い（必要な法令対応・事前承認）を明文化する。

- **T&Mにもかかわらず、月額報酬/時間精算の上限（キャップ）や予算超過時の停止・協議条項がなく、甲側の費用コントロールが弱い（予算超過リスク）。乙側も承認プロセス不備だと稼働が未承認となり回収リスクがある。**
  - カテゴリ: 支払条件
  - レベル: 🟡 中
  - 推奨対応: 月次の上限時間/上限金額、超過見込み時の事前通知義務、甲の追加承認がない場合の作業停止/優先度調整、請求可能範囲のルールを追加する。

**備考**: 本条はT&M精算の骨格は示すものの、単価・精算単価が別途覚書依存で確定性が弱く、工数算定/承認/計算式が不明確なため支払・運用面の紛争リスクがある。覚書（単価表・精算条件・工数承認フロー・上限管理）を契約締結時に一体化して整備するのが望ましい。

### ✅ 諸費用の負担
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **「事前に甲の承諾を得たものに限り」とあるため、承諾手続（承諾者、方法、期限）が不明確だと、乙が必要費用を立替・負担せざるを得ない状況や、事後に承諾が否認され精算拒否が生じるリスクがある。**
  - カテゴリ: 支払条件
  - レベル: 🟡 中
  - 推奨対応: 承諾プロセスを具体化（例：見積提示→甲担当者がメール/書面で承認、承認期限は提出後◯営業日、期限内に異議なき場合は承認とみなす等）。また、緊急・やむを得ない支出（出張変更等）の事後承認や上限額内での包括承認の扱いを定める。

- **「実費」の範囲が不明確で、対象費目（交通費の種別、グリーン車/タクシー、宿泊の上限単価、日当、キャンセル料、手数料、税、為替差損等）を巡って精算範囲の解釈違いが起こり得る。**
  - カテゴリ: 支払条件
  - レベル: 🟡 中
  - 推奨対応: 精算対象費目と条件を列挙し、単価・上限（例：宿泊1泊◯円まで）、領収書要否、キャンセル料負担基準、消費税の扱い等を明記する。必要に応じて別紙の経費規程を参照させる。

- **特別なソフトウェアライセンス費用を甲が負担する場合、ライセンスの契約主体（甲/乙）、名義、利用範囲、契約終了後の扱い（返却/停止/譲渡）、成果物への組込みの可否が不明確だと、利用継続の可否やライセンス違反（コンプライアンス）・追加費用発生のリスクがある。**
  - カテゴリ: 知的財産権
  - レベル: 🟡 中
  - 推奨対応: ライセンスの購入主体・名義、用途（本業務に限定）、利用期間、契約終了時の措置、サブライセンス可否、監査対応、追加購入時の承認手続を明確化する。可能なら甲が直接契約・管理する形を原則とする。

**備考**: 費用を甲が負担する旨自体は一般的で大きな違法性は見当たりませんが、承認手続と実費範囲が曖昧なため、運用・精算トラブルの商業リスクが残ります。甲乙いずれにとっても、上限・手続・証憑要件を定義することで紛争予防効果が高まります。

### ✅ 成果物の提出と確認
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **成果物の提出義務が「甲の求めに応じて随時、または月次報告時」とされており、提出タイミング・範囲（提出対象物、提出形式、提出期限）が不明確なため、甲からの随時要求が過大になり工数・納期・費用の増加や紛争につながるリスクがある。**
  - カテゴリ: その他
  - レベル: 🟡 中
  - 推奨対応: 提出対象（例：ソースコード／設計書／テスト結果等）、提出形式（例：リポジトリ/ファイル形式）、提出頻度（例：月1回まで等）、提出期限（例：要求後○営業日以内）、追加提出が発生する場合の費用・スケジュール調整（変更管理）を明記する。

- **甲の「確認」が請負の検収ではなく「完成や瑕疵の不在を保証させるものではない」とされているため、成果物の受領・承認基準が曖昧となり、後日「確認済み」か否か、どの時点で指摘可能か、修正対応の要否が争点化するリスクがある（甲側：品質確保が弱い／乙側：無限定な指摘・修正要求の懸念）。**
  - カテゴリ: 保証
  - レベル: 🟡 中
  - 推奨対応: 確認の位置づけ（進捗確認/レビュー）と、品質・瑕疵対応を別条で明確化する。例：受領・承認（検収）手続、受領後の指摘期限、重大瑕疵の定義、修補範囲・回数、追加要望は有償変更、責任範囲（契約不適合/瑕疵担保の有無・期間）を規定する。

- **甲が「疑義がある場合は乙に説明を求めることができる」とある一方、乙の説明義務の範囲（合理的な範囲/時間上限）や対応期限が定められていないため、説明対応が長期化し、乙の稼働を圧迫する／甲の確認が遅延するリスクがある。**
  - カテゴリ: その他
  - レベル: 🟢 低
  - 推奨対応: 説明要求は「合理的な範囲」に限定し、対応期限（例：要求後○営業日以内に一次回答）や、追加調査が必要な場合の取り扱い（工数見積・スケジュール調整）を定める。

**備考**: 本条は進捗管理としては有用だが、「随時提出」「確認は検収でない」という構造により、提出・レビューの運用が拡大解釈されやすい。品質保証/検収/瑕疵対応、変更管理、知財帰属（別条で規定されることが多い）との整合を確認し、手続と期限を具体化するとリスク低減につながる。

### ✅ 知的財産権の帰属
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **成果物の知的財産権が「委託料の支払い完了時点」で移転するため、検収・受領前に利用を開始した場合や支払遅延・分割払いの場合に、権利帰属が宙に浮き、利用差止め・引渡し停滞・紛争のリスクがある。**
  - カテゴリ: 知的財産権
  - レベル: 🟡 中
  - 推奨対応: 権利移転のトリガーを「検収合格（成果物の引渡し）時」または「引渡し時（支払は対抗要件/解除条件）」に見直す。少なくとも支払完了までの間、甲に対して成果物の利用に必要な暫定ライセンス（無償・取消不能・業務目的範囲）を付与する旨を追記する。分割払いの場合は各マイルストーン成果物ごとに権利移転・利用許諾を明確化する。

- **「成果物」の範囲（ソースコード、設計書、仕様書、データ、ドキュメント、派生物、改変物、学習済みモデル等）や、成果物に第三者IP・オープンソースが含まれる場合の取扱いが明確でなく、想定外に権利が移転しない/利用制限が残るリスクがある。**
  - カテゴリ: 知的財産権
  - レベル: 🟡 中
  - 推奨対応: 成果物の定義を追加し、納品物一覧（成果物目録）を添付する。第三者IP/OSS利用がある場合の事前開示、ライセンス条件、帰属、コンプライアンス（ソース開示義務の有無等）を定める。必要に応じて「成果物に含まれる第三者権利は移転対象外であり、甲には利用に必要なライセンスを付与する」等の整理を行う。

- **乙保有IPの使用許諾が「本システムを利用するために必要な範囲」と抽象的で、利用範囲（社内利用/グループ会社/委託先への再委託・サブライセンス可否、利用場所、バックアップ、改変、複製、災害時復旧、クラウド移行）や期間（永続/契約終了後）を巡り解釈相違が生じやすい。**
  - カテゴリ: 知的財産権
  - レベル: 🟡 中
  - 推奨対応: 使用許諾の条件を具体化する（許諾範囲・目的・期間・地域・再委託/サブライセンス可否・改変/複製可否・保守運用のための利用・契約終了後の取扱い）。甲側が継続運用を要するなら、少なくとも契約終了後も継続利用できる（永続・取消不能）旨や、保守委託先への利用許諾を明記する。

- **著作者人格権の不行使条項がないため、成果物が著作物に該当する場合に、将来的な改変・翻案・表示方法等について乙（著作者）から異議が出るリスクが残る。**
  - カテゴリ: 知的財産権
  - レベル: 🟡 中
  - 推奨対応: 乙および乙の従業員/再委託先が、甲および甲の指定する者に対し、成果物について著作者人格権を行使しない旨（必要に応じて範囲限定）を追加する。再委託がある場合は同等条項の取得義務も明記する。

**備考**: 本条は、成果物の権利移転と乙保有IP留保を分けて規定しており構造は標準的だが、(1)移転時期を支払完了に連動させている点、(2)成果物・第三者IP/OSSの取扱い、(3)乙保有IPライセンス条件、(4)著作者人格権不行使の欠落が、実務上の運用・紛争リスクを高め得る。法的助言ではなくリスク評価としての指摘。

### ✅ 秘密保持
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **「秘密情報」の定義がなく、何が秘密情報に該当するか不明確なため、情報管理範囲が過度に広がったり、逆に保護対象の特定ができず争いになり得る。**
  - カテゴリ: 秘密保持
  - レベル: 🟡 中
  - 推奨対応: 秘密情報の定義（例：秘密表示のある情報、口頭開示は後日書面化されたもの等）と、秘密情報に該当しない情報（公知情報、受領前から保有、正当な第三者から取得、独自開発等）を明記する。

- **第三者開示の例外（法令・裁判所/行政機関の命令、監査人・弁護士等の守秘義務者への開示、業務委託先への開示）が規定されていないため、実務上必要な開示が契約違反となるリスクがある。**
  - カテゴリ: 法令遵守
  - レベル: 🟡 中
  - 推奨対応: 法令等に基づく開示は事前（困難な場合は事後速やかに）通知の上で許容する条項、及び弁護士・会計士・金融機関・委託先等への必要最小限の開示（同等の秘密保持義務を課すことを条件）を追加する。

- **秘密保持期間が契約終了後3年に限定されており、ノウハウ・営業秘密など価値が長期に及ぶ情報について保護が不十分となる可能性がある。**
  - カテゴリ: 秘密保持
  - レベル: 🟡 中
  - 推奨対応: 情報の性質に応じて期間を延長（例：5年）する、または営業秘密に該当する情報は非公知である限り存続（無期限）とする等の二段階設計を検討する。

- **秘密情報の取扱い（目的外利用禁止、複製制限、管理義務の水準）、返還・消去、漏えい時の通知/是正、損害賠償・差止め等の救済が規定されておらず、漏えい発生時の実効性が弱い。**
  - カテゴリ: 秘密保持
  - レベル: 🟡 中
  - 推奨対応: 少なくとも①目的外使用の禁止、②合理的管理措置（アクセス制限等）、③委託先・従業員への同等義務、④終了時の返還/消去（例外：バックアップの取扱い）⑤漏えい等発生時の速やかな通知と協力、⑥差止め等の救済を追加する。

**備考**: 秘密保持条項としての骨格（第三者開示禁止・存続期間）はあるものの、定義・例外・運用（管理/返還/漏えい対応）に関する標準要素が不足しており、実務運用と紛争予防の観点で中程度のリスクがある。

### ⚠️ 契約の解除
- **リスクレベル**: 🟠 高
- **コンプライアンス**: 要確認

**検出されたリスク:**

- **中途解約権が甲のみに認められており（乙には同等の権利が明記されていない）、解除・解約の権利義務が不均衡。乙にとっては契約継続の予見可能性が低く、投下コスト回収不能等の商業リスクが高い。**
  - カテゴリ: 契約解除
  - レベル: 🟠 高
  - 推奨対応: 乙にも同等の中途解約権（例：1ヶ月前予告）を付与する、または少なくとも乙側の中途解約要件（やむを得ない事由、長期不履行等）を明記する。加えて、業務立上げ費・固定費等の回収のための解約料/最低支払（例：最低1〜2ヶ月分、未償却費用の精算）を設定する。

- **「業務実績に応じた委託料」の算定基準が不明確で、解約時の精算範囲（進行中作業、成果物未検収分、立替費用、キャンセル料、固定報酬の扱い等）を巡り紛争化しやすい。**
  - カテゴリ: 支払条件
  - レベル: 🟡 中
  - 推奨対応: 精算ルールを具体化（例：時間単価×稼働時間、マイルストーン到達基準、月額固定の按分方法、検収前成果物の取り扱い）。併せて、(i) 立替費用・第三者費用・解約に伴うキャンセル料の負担、(ii) 請求締日・支払期日、(iii) 乙の協力義務（引継ぎ）と対価を明記する。

- **第1項の解除要件における「相当の期間」が抽象的で、是正期間の長短を巡って解釈が割れうる。違反の重大性に応じた即時解除（重大違反・信用不安・反社等）も規定されていないため、実務上の機動性/予防が不足する可能性。**
  - カテゴリ: 契約解除
  - レベル: 🟡 中
  - 推奨対応: 是正期間の目安（例：10営業日、又は違反内容に応じ協議）を定める。併せて、重大な契約違反、支払遅延の一定期間継続、差押・倒産申立、反社条項違反、機密侵害等については催告不要の解除（即時解除）を追加する。

**備考**: 本条は一般的な「催告後解除」を含む一方、中途解約が甲に片務的である点が最も大きなリスク要因。準委任の趣旨に沿うとしても、精算方法（委託料・費用・未了業務）を明確化しないと解約局面での紛争・未回収リスクが残る。法的助言ではなく条項リスク評価としての所見。

### ✅ 協議事項
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **「本契約に定めのない事項」や「疑義が生じた事項」を協議で解決するとするのみで、協議不調の場合の解決手段（優先順位、決定方法、準拠法・管轄、仲裁等）が明確でないため、紛争が長期化・解決不能となるリスクがある。**
  - カテゴリ: 紛争解決
  - レベル: 🟡 中
  - 推奨対応: 協議の手続（協議開始の通知方法、協議期限、担当者/決裁権限者、議事録作成）を定め、協議不調時は「別条の紛争解決条項（管轄裁判所/仲裁）」に従う旨、または本条内に調停・仲裁・専属的合意管轄等のエスカレーションを明記する。

- **「誠意をもって」「円満に解決」といった抽象的表現は、当事者の義務内容・達成基準が不明確で、履行・不履行の判断や法的拘束力の評価が難しく、解釈の相違を招くリスクがある。**
  - カテゴリ: その他
  - レベル: 🟢 低
  - 推奨対応: 努力義務であることを明確化する（例：「誠実に協議するものとする」）とともに、必要に応じて「協議事項は書面で合意しない限り本契約を変更しない」等の文言を追加して解釈のブレを抑える。

**備考**: 一般的な協議条項で直ちに違法・不適合とは言いにくい一方、協議不調時の出口がないため実務上の紛争解決リスクが残ります。他条（準拠法・合意管轄、契約変更手続、通知条項等）の有無と整合させて補強するのが望ましいです。

### ✅ 管轄裁判所
- **リスクレベル**: 🟡 中
- **コンプライアンス**: 適合

**検出されたリスク:**

- **第一審の専属的合意管轄を大阪地方裁判所に固定しているため、当事者の所在地や業務実態によっては、移動・対応コスト増や訴訟対応の実務負担が一方当事者に偏るリスクがある。**
  - カテゴリ: 紛争解決
  - レベル: 🟡 中
  - 推奨対応: 当事者所在地・履行地との合理的関連性を確認し、偏りがある場合は「被告所在地の管轄裁判所」または「大阪地方裁判所（又は被告所在地を管轄する裁判所）」等の選択肢付き条項に修正する。オンライン期日等の活用可否も含め、訴訟対応体制・費用負担を事前整理する。

- **「本契約に関する一切の紛争」との包括表現により、契約外（不法行為等）を含む周辺紛争まで射程に入る可能性があり、想定外の紛争類型でも大阪地裁に固定される解釈リスクがある。**
  - カテゴリ: 紛争解決
  - レベル: 🟢 低
  - 推奨対応: 適用範囲を明確化するため、「本契約に起因又は関連して生じる紛争」等に整備し、必要に応じて契約外請求の扱い（含める/除外する）を当事者で合意して文言を調整する。

**備考**: 専属的合意管轄自体は一般的で直ちに違法・不適切とはいえない一方、当事者間の地理的・交渉力のバランス次第で実務負担が偏り得るため、商業上の観点から中程度のリスクと評価した。

---

## 総合的な推奨事項

1. 委託料に関する必須事項を締結前に確定：単価/精算単価、請求締め・支払期日、工数（稼働実績）の算定ルール、タイムシート様式、承認者・承認期限、未承認時の扱い、端数処理、上限（キャップ）や事前承認が必要となる追加工数条件をSOW/覚書で明文化する
2. 解除・解約の均衡化：乙にも中途解約権（合理的予告期間）を付与し、解約精算（完了分・進行中分・未検収分・立替費用・キャンセル料等）の範囲と算定式、成果物/途中成果の引渡し条件を規定する。重大違反・信用不安・反社等の即時解除条項も整備する
3. 成果物・品質・受入（確認）を定義：成果物一覧（ソースコード/設計書/試験成績等）、品質基準（レビュー/テスト要件）、提出形式、受入期限、指摘可能期間、修正対応の範囲（有償/無償境界）を明確化し、準委任下でも期待水準を固定する
4. 別文書（作業指示書・月次計画・覚書等）の優先順位と変更管理を整備：契約＞SOW＞作業指示書等の優先順位、追加/変更の合意方法（書面・電子署名・メールの可否）、変更時の費用・納期・体制の調整手続を規定する
5. 契約期間を確定日付で特定し、自動更新の運用リスクを低減：更新通知期限の延長、更新前協議条項、更新条件変更の手続を追加する
6. 秘密保持の実務適合：秘密情報の定義（表示/口頭後追い指定等）、除外（公知・受領前保有等）、第三者開示例外（法令・裁判所、弁護士/監査人、再委託先等）、目的外利用禁止、返還/消去、秘密保持期間（情報類型に応じた延長）を整備する
7. 再委託条項の運用可能化：承諾基準・回答期限・みなし承諾、再委託先への義務（秘密保持/品質/法令遵守）と乙の責任範囲（連帯/管理責任）を明確化する
8. 報告・会議体・タイムシートのルールを定義：月次報告提出期限の現実化、定例会の頻度/時間/方法/欠席時取扱い、タイムシートの粒度・閲覧権限・保管・目的外利用禁止を定める
9. 知的財産の帰属・ライセンスを明確化：成果物範囲、移転時期（検収/支払との関係）、第三者IP/OSSの申告・遵守、乙保有IPの利用範囲（グループ会社利用、委託先利用、改変、バックアップ、契約終了後の利用）を明記する

---

## 結論

総合判定は needs_review（リスクスコア68）です。高リスクの「委託料の未確定（覚書依存）」と「解除の片務性（甲のみ中途解約）」は、締結前に必ず条文修正またはSOW/覚書の同時締結で是正してください。次に、成果物・検収/受入・変更管理（別文書の優先順位）を明確化し、準委任であっても期待成果と費用・納期の紐付けを固定することが重要です。上記の即時対応事項を反映した改訂案（契約条文＋SOW/料金表＋運用ルール）を作成し、甲乙で合意のうえ締結することを次のステップとします。

```

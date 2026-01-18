# Chapter 2 Section 14: LLMによるスクリプト生成と実行

## 概要

本プロジェクトは、LLMが苦手とする数値計算や複雑なデータ処理に対して、LLM自身にPythonスクリプトを生成させて実行するプラクティスを実装したサンプルアプリケーションです。

LLMは確率的な出力を行うため、単純な算数であっても桁数が増えれば計算ミス（ハルシネーション）を起こしやすいという課題があります。本プロジェクトでは、LLMに直接的な回答を求めず、問題を解決するためのPythonスクリプトを生成させ、それをサンドボックス環境で実行するアプローチを採用しています。これにより、LLMの言語能力と従来のプログラミングによる正確な処理を融合させ、信頼性の高いタスク処理を実現します。

具体的には、契約書やレポートなどの文書を入力として受け取り、LLMがその文書構造を抽出するPythonスクリプトを自動生成し、実行結果をJSON形式で出力します。スクリプト実行時にエラーが発生した場合は、LLMによる自己修正（Self-Correction）機能により自動的にスクリプトを修正して再実行します。

## 機能

- **文書構造の自動抽出**: Markdown形式の文書からタイトル、セクション、サブセクション、メタデータを自動抽出
- **LLMによるスクリプト生成**: 文書の特性に応じた最適なPython抽出スクリプトを自動生成
- **セキュアなサンドボックス実行**: 生成されたスクリプトを安全な環境で実行（ファイルシステム・ネットワークアクセス禁止）
- **自己修正機能**: スクリプト実行エラー時にLLMが自動的にコードを修正して再試行（最大3回）
- **LLM-as-a-Judge品質評価**: 抽出結果をLLMが1〜5のスコアで評価し、低スコア時は改善提案を生成して再修正
- **構造化出力**: Anthropic API の Structured Outputs を活用した型安全な出力

## プロジェクト構成

### ディレクトリ構成.../

```
section_16/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLIエントリーポイント
│   ├── config.py            # 設定管理
│   ├── logger.py            # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py    # Anthropic APIクライアント
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py         # Pydanticデータモデル
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py        # LLMプロンプト定義
│   └── service/
│       ├── __init__.py
│       ├── document_processor.py  # 文書処理オーケストレーション
│       ├── request_llm.py         # LLMリクエスト処理
│       ├── script_executor.py     # スクリプト実行・検証
│       └── validator.py           # LLM-as-a-Judge品質評価
├── data/                     # サンプル入力文書
│   ├── contract_0.md
│   ├── report_0.md
│   └── python_blog_0.md
├── outputs/                  # 出力ファイル
├── pyproject.toml
├── .envrc.example
└── README.md
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI (main.py)                               │
│                         文書ファイル読み込み                              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Document Processor (service層)                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Step 1: sample_document()                                        │    │
│  │   - 文書タイプ識別（contract, report, manual等）                  │    │
│  │   - キーセクション特定                                            │    │
│  │   - 代表的な文のサンプリング                                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Step 2: generate_extraction_script()                             │    │
│  │   - 文書構造に適したPythonスクリプト生成                          │    │
│  │   - セキュリティ要件をプロンプトで指定                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Step 3: execute_script_with_retry()                              │    │
│  │   - スクリプト検証（禁止パターン・モジュールチェック）            │    │
│  │   - サンドボックス実行（PATH/PYTHONPATH空、タイムアウト設定）     │    │
│  │   - エラー時は correct_script() で修正して再試行（最大3回）       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Step 4: validate_extraction_result()                            │    │
│  │   - LLM-as-a-Judgeで抽出結果を1〜5のスコアで評価                 │    │
│  │   - 低スコア時は改善提案を生成しスクリプトを再修正               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            出力ファイル                                  │
│  - {filename}_{run_id}_structure.json  # 抽出された文書構造              │
│  - {filename}_{run_id}_script.py       # 生成されたPythonスクリプト      │
│  - {filename}_{run_id}_metadata.json   # 処理メタデータ                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - `anthropic>=0.74.1` - Anthropic API クライアント
  - `click>=8.3.0` - CLIフレームワーク
  - `pydantic>=2.12.2` - データバリデーション
  - `python-dotenv>=1.1.1` - 環境変数管理

### セットアップ

1. 依存関係のインストール:

```bash
# uvを使用
uv sync
```

2. 環境変数の設定:

```bash
cp .envrc.example .envrc
# .envrc を編集して ANTHROPIC_API_KEY を設定
```

```
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

### 使用方法、実行方法

```bash
# 使い方

$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

  Analyze and extract document structure using LLM-generated scripts.

Options:
  -m, --model [claude-opus-4-5|claude-haiku-4-5|claude-sonnet-4-5|claude-opus-4-1]
                                  The Anthropic model to use for analysis.
                                  [required]
  -i, --input PATH                Path to the input document (text or
                                  markdown).  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

```bash
# 基本的な使用方法
python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md

# 出力ディレクトリを指定
python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md -od outputs
```

#### CLIオプション

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|-------|------|-----------|------|
| `--model` | `-m` | Yes | - | 使用するモデル（`claude-sonnet-4-5` または `claude-opus-4-1`） |
| `--input` | `-i` | Yes | - | 入力文書ファイルのパス |
| `--output-directory` | `-od` | No | `outputs` | 出力ファイルの保存先ディレクトリ |

### 出力例

契約書（`data/contract_0.md`）を処理した場合の実行ログ:

```bash
$ python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md

[2026-01-18 15:26:24,431] [INFO] [__main__] [main.py:52] [main] Model: claude-sonnet-4-5
Input file: data/contract_0.md
Output directory: outputs
[2026-01-18 15:26:24,438] [INFO] [__main__] [main.py:60] [main] Document loaded: 1822 characters
[2026-01-18 15:26:24,438] [INFO] [src.service.document_processor] [document_processor.py:31] [extract_document_structure] Step 1: Sampling document sentences...
[2026-01-18 15:26:36,908] [INFO] [src.service.request_llm] [request_llm.py:26] [sample_document] Sampled document info: sentences=['本契約は、委託者（以下 「甲」という）と受託者（以下「乙」という）との間で、以下の条件に基づき締結される。', '甲は乙に対し、本契約に定める条件に従い、ソフトウェア開発業務（以下「 本業務」という）を委託し、乙はこれを受託する。', '乙が開発するソフトウェアの概要は以下の通りとする。', '乙は以下の成果物を甲に納品するものとする。', '本契 約の有効期間は、2024年4月1日から2024年9月30日までとする。', '甲は乙に対し、本業務の対価として、金1,500万円（消費税別）を支払うものとする。', '甲および乙は 、相手方の機密情報を厳重に管理し、本業務の遂行以外の目的に使用してはならない。', '本業務により生じた成果物に関する著作権（著作権法第27条および第28条の権利 を含む）その他一切の知的財産権は、対価の完済をもって甲に帰属するものとする。', '乙は、成果物の納品後1年間、成果物に瑕疵があった場合には、無償で修補を行うものとする。', '本契約に関する一切の紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。'] document_type='contract' key_sections=['第1条（目 的）', '第2条（業務内容）', '2.1 開発対象', '2.2 成果物', '第3条（契約期間）', '第4条（委託料）', '4.1 金額', '4.2 支払条件', '第5条（機密保持）', '5.1 機 密情報の定義', '5.2 機密保持義務', '第6条（知的財産権）', '6.1 権利の帰属', '6.2 乙の留保権利', '第7条（瑕疵担保責任）', '第8条（損害賠償）', '第9条（解除 ）', '第10条（協議事項）', '第11条（管轄裁判所）']
[2026-01-18 15:26:36,909] [INFO] [src.service.document_processor] [document_processor.py:33] [extract_document_structure] Document type identified: contract
[2026-01-18 15:26:36,909] [INFO] [src.service.document_processor] [document_processor.py:34] [extract_document_structure] Key sections found: ['第1条（目的）', '第2条（業務内容）', '2.1 開発対象', '2.2 成果物', '第3条（契約期間）', '第4条（委託料）', '4.1 金額', '4.2 支払条件', '第5条（機密保持）', '5.1 機密 情報の定義', '5.2 機密保持義務', '第6条（知的財産権）', '6.1 権利の帰属', '6.2 乙の留保権利', '第7条（瑕疵担保責任）', '第8条（損害賠償）', '第9条（解除）', '第10条（協議事項）', '第11条（管轄裁判所）']
[2026-01-18 15:26:36,909] [INFO] [src.service.document_processor] [document_processor.py:36] [extract_document_structure] Step 2: Generating extraction script...
[2026-01-18 15:26:56,941] [INFO] [src.service.request_llm] [request_llm.py:43] [generate_extraction_script] Generated script explanation: このスクリプトは 、契約書などの文書から構造情報を抽出します。標準入力からMarkdown形式の文書を読み込み、タイトル、セクション（第○条）、サブセクション（数字.数字形式）を階層 的に抽出し、さらに当事者情報や日付などのメタデータも抽出してJSON形式で標準出力に出力します。正規表現を使用して見出しレベルを判定し、ネストした構造を構築し ます。
[2026-01-18 15:26:56,941] [INFO] [src.service.document_processor] [document_processor.py:42] [extract_document_structure] Script explanation: このスクリプ トは、契約書などの文書から構造情報を抽出します。標準入力からMarkdown形式の文書を読み込み、タイトル、セクション（第○条）、サブセクション（数字.数字形式）を 階層的に抽出し、さらに当事者情報や日付などのメタデータも抽出してJSON形式で標準出力に出力します。正規表現を使用して見出しレベルを判定し、ネストした構造を構 築します。
[2026-01-18 15:26:56,941] [INFO] [src.service.document_processor] [document_processor.py:139] [_execute_script_with_retry] Step 3: Executing script (attempt 1/4)...
[2026-01-18 15:26:56,995] [WARNING] [src.service.script_executor] [script_executor.py:86] [execute_script] Script execution failed with return code 1
[2026-01-18 15:26:56,995] [WARNING] [src.service.document_processor] [document_processor.py:147] [_execute_script_with_retry] Script execution failed: Traceback (most recent call last):
  File "/var/folders/x4/1v5m360n3jbf6kh_yjjgnf4w0000gn/T/tmpdl_wwo23.py", line 115, in <module>
    extract_document_structure()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/var/folders/x4/1v5m360n3jbf6kh_yjjgnf4w0000gn/T/tmpdl_wwo23.py", line 56, in extract_document_structure
    current_section['subsections'].append(current_subsection)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
TypeError: 'NoneType' object is not subscriptable
[2026-01-18 15:26:56,995] [INFO] [src.service.document_processor] [document_processor.py:148] [_execute_script_with_retry] Attempting to correct script...
[2026-01-18 15:27:16,383] [INFO] [src.service.request_llm] [request_llm.py:61] [correct_script] Corrected script explanation: エラーの原因は、サブセクショ ン(###)が見つかった時点で、まだcurrent_sectionがNoneである可能性があったことです。文書の最初にサブセクションが現れた場合、セクション(##)が作成される前にcurrent_section['subsections']にアクセスしようとしてTypeErrorが発生していました。修正として、56行目のsubsection_matchの処理ブロック内で、current_sectionがNoneでないことを確認する条件分岐(if current_section is not None:)を追加しました。これにより、セクションが存在する場合のみサブセクションが追加されるようになります。
[2026-01-18 15:27:16,383] [INFO] [src.service.document_processor] [document_processor.py:156] [_execute_script_with_retry] Script correction: エラーの原因 は、サブセクション(###)が見つかった時点で、まだcurrent_sectionがNoneである可能性があったことです。文書の最初にサブセクションが現れた場合、セクション(##)が 作成される前にcurrent_section['subsections']にアクセスしようとしてTypeErrorが発生していました。修正として、56行目のsubsection_matchの処理ブロック内で、current_sectionがNoneでないことを確認する条件分岐(if current_section is not None:)を追加しました。これにより、セクションが存在する場合のみサブセクションが追加 されるようになります。
[2026-01-18 15:27:16,383] [INFO] [src.service.document_processor] [document_processor.py:139] [_execute_script_with_retry] Step 3: Executing script (attempt 2/4)...
[2026-01-18 15:27:16,443] [INFO] [src.service.document_processor] [document_processor.py:143] [_execute_script_with_retry] Script executed successfully!
[2026-01-18 15:27:16,443] [INFO] [src.service.document_processor] [document_processor.py:79] [extract_document_structure] Step 4: Validating extraction result (attempt 1/4)...
[2026-01-18 15:27:32,601] [INFO] [src.service.validator] [validator.py:46] [validate_extraction_result] Validation score: 2/5
[2026-01-18 15:27:32,601] [INFO] [src.service.validator] [validator.py:47] [validate_extraction_result] Reasoning: 抽出結果には重大な構造的欠陥があります。最も深刻な問題は、sections配列が完全に空であることです。文書には第1条から第11条まで11個の主要セクションが明確に存在し、さらに多数のサブセクション（2.1、2.2、4.1、4.2など）も含まれていますが、これらがまったく抽出されていません。文書の主要コンテンツである各条項の内容、業務内容の詳細、契約期間、委託料、機密保持 、知的財産権、瑕疵担保責任などの重要情報がすべて欠落しています。一方で、メタデータ部分については当事者情報（甲・乙の住所、会社名、代表者）と日付が正確に抽 出されており、この部分は適切に機能しています。タイトルと文書タイプも正確です。しかし、契約書の中核である条項構造が完全に欠落している状態では、このスクリプ トは本来の目的である「文書から構造情報を抽出する」という機能をほとんど果たせていません。セクション抽出のロジックに根本的な問題があると考えられます。
[2026-01-18 15:27:32,601] [WARNING] [src.service.validator] [validator.py:49] [validate_extraction_result] Fix proposal: セクション抽出ロジックを以下のように修正する必要があります：1) '## 第N条'パターンを正規表現で検出するロジックを追加（例：r'^##\s*第(\d+)条[（(](.+?)[）)]'）。2) '### N.N'パターンでサブセク ションを検出（例：r'^###\s*(\d+\.\d+)\s+(.+)'）。3) 各セクションの本文内容を抽出して保存。4) 階層構造を正しく構築し、サブセクションを親セクションの下に配置。5) リスト項目や表も構造化データとして抽出。現在のコードはおそらくセクションマッチングに失敗しているため、正規表現パターンとMarkdown見出しレベルの判定ロジックを見直してください。
[2026-01-18 15:27:32,601] [WARNING] [src.service.document_processor] [document_processor.py:101] [extract_document_structure] Validation score 2/5 is below threshold 3
[2026-01-18 15:27:32,601] [INFO] [src.service.document_processor] [document_processor.py:103] [extract_document_structure] Attempting to correct script based on validation feedback...
[2026-01-18 15:27:55,090] [INFO] [src.service.request_llm] [request_llm.py:80] [correct_script_from_validation] Validation-corrected script explanation: 主要な修正点：1) セクション検出の正規表現を修正し、'## 第N条（タイトル）'パターンを正確にマッチするように変更（r'^##\\s*第(\\d+)条[（(](.+?)[）)]'）。2) サブセクション検出の正規表現を修正し、'### N.N タイトル'パターンを正確にマッチ（r'^###\\s+(\\d+\.\\d+)\\s+(.+)'）。3) タイトル抽出ロジックを改善し、単一の#で始まる行のみをタイトルとして認識。4) セクションとサブセクションの保存タイミングを修正し、次のセクション/サブセクションが検出されたときに前のものを確実に保存 。5) 当事者情報の抽出ロジックを改善し、より広い範囲（最大10行先まで）を検索し、次のセクションまたは当事者情報で停止。これにより、文書内の全11条とそのサブセクションが正確に抽出され、階層構造が正しく構築されます。
[2026-01-18 15:27:55,091] [INFO] [src.service.document_processor] [document_processor.py:113] [extract_document_structure] Script corrected: 主要な修正点：1) セクション検出の正規表現を修正し、'## 第N条（タイトル）'パターンを正確にマッチするように変更（r'^##\\s*第(\\d+)条[（(](.+?)[）)]'）。2) サブセクション検出の正規表現を修正し、'### N.N タイトル'パターンを正確にマッチ（r'^###\\s+(\\d+\.\\d+)\\s+(.+)'）。3) タイトル抽出ロジックを改善し、単一の#で始まる行のみをタイトルとして認識。4) セクションとサブセクションの保存タイミングを修正し、次のセクション/サブセクションが検出されたときに前のものを確実に保存。5) 当事者情報の抽出ロジックを改善し、より広い範囲（最大10行先まで）を検索し、次のセクションまたは当事者情報で停止。これにより、文書内の全11条とそのサブセクションが正 確に抽出され、階層構造が正しく構築されます。
[2026-01-18 15:27:55,091] [INFO] [src.service.document_processor] [document_processor.py:139] [_execute_script_with_retry] Step 3: Executing script (attempt 1/4)...
[2026-01-18 15:27:55,129] [INFO] [src.service.document_processor] [document_processor.py:143] [_execute_script_with_retry] Script executed successfully!
[2026-01-18 15:27:55,129] [INFO] [src.service.document_processor] [document_processor.py:79] [extract_document_structure] Step 4: Validating extraction result (attempt 2/4)...
[2026-01-18 15:28:08,913] [INFO] [src.service.validator] [validator.py:46] [validate_extraction_result] Validation score: 4/5
[2026-01-18 15:28:08,913] [INFO] [src.service.validator] [validator.py:47] [validate_extraction_result] Reasoning: 抽出結果を詳細に評価した結果、以下の点が確認できました。

【優れている点】
1. 文書タイトル「ソフトウェア開発業務委託契約書」が正確に抽出されている
2. 全11条のセクションが完全に抽出され、欠落がない
3. 階層構造が正確に表現されている（第2条、第4条、第5条、第6条のサブセクションが適切にネストされている）
4. サブセクション（2.1/2.2、4.1/4.2、5.1/5.2、6.1/6.2）が正しくlevel 2として分類されている
5. 当事者情報（甲・乙）が正確に抽出され、役割・住所・会社名・代表者が構造化されている
6. 日付情報（2024-04-01、2024-03-15）が正確に抽出されている
7. 箇条書き項目や表形式データが適切に保持されている

【問題点】
1. 第11条のcontentフィールドに、本来は別の箇所に配置されるべき情報（区切り線以降の署名セクション、当事者の詳細情報）が含まれている。これらは第11条の本文で はなく、文書の末尾に配置される署名・押印セクションであるため、セクション内容として含めるのは構造的に不適切
2. 署名・押印セクションが独立したセクションまたはメタデータとして抽出されていない

【総合評価】
主要な構造抽出は完璧に近い精度で実行されており、全条項とサブセクションが正確に識別されている。メタデータの抽出も優れている。唯一の問題は第11条のcontentに署名セクションが含まれている点だが、これは文書全体の構造理解には大きな影響を与えない軽微な分類の問題である。契約書として必要な情報はすべて正確に抽出されてお り、実用上の問題はほとんどない。
[2026-01-18 15:28:08,913] [INFO] [src.service.document_processor] [document_processor.py:89] [extract_document_structure] Validation passed with score 4/5
[2026-01-18 15:28:08,914] [INFO] [src.service.document_processor] [document_processor.py:189] [save_extraction_results] Document structure saved to: outputs/contract_0_439362a7_structure.json
[2026-01-18 15:28:08,914] [INFO] [src.service.document_processor] [document_processor.py:195] [save_extraction_results] Generated script saved to: outputs/contract_0_439362a7_script.py
[2026-01-18 15:28:08,914] [INFO] [src.service.document_processor] [document_processor.py:209] [save_extraction_results] Metadata saved to: outputs/contract_0_439362a7_metadata.json
[2026-01-18 15:28:08,914] [INFO] [__main__] [main.py:74] [main] Document structure extraction completed successfully!
```

抽出された文書構造（`outputs/contract_0_*_structure.json`）:

```json
{
    "title": "ソフトウェア開発業務委託契約書",
    "document_type": "contract",
    "sections": [
        {
            "title": "第1条（目的）",
            "level": 2,
            "content": "甲は乙に対し、本契約に定める条件に従い、ソフトウェア開発業務（以下「本業務」という）を委託し、乙はこれを受託する。",
            "subsections": []
        },
        {
            "title": "第2条（業務内容）",
            "level": 2,
            "content": "",
            "subsections": [
                {
                    "title": "2.1 開発対象",
                    "level": 3,
                    "content": "乙が開発するソフトウェアの概要は以下の通りとする。\n- システム名称：顧客管理システム\n- 開発言語：Python 3.11以上\n- フレームワーク：FastAPI\n- データベース：PostgreSQL 15",
                    "subsections": []
                },
                {
                    "title": "2.2 成果物",
                    "level": 3,
                    "content": "乙は以下の成果物を甲に納品するものとする。\n1. ソースコード一式\n2. 設計書（基本設計書、詳細設計書）\n3. テスト仕様書およびテスト結果報告書\n4. 運用マニュアル",
                    "subsections": []
                }
            ]
        },
        {
            "title": "第3条（契約期間）",
            "level": 2,
            "content": "本契約の有効期間は、2024年4月1日から2024年9月30日までとする。ただし、期間満了の1ヶ月前までに甲乙いずれからも書面による異議がない場合は、同一条件にてさらに6ヶ月間延長されるものとし、以後も同様とする。",
            "subsections": []
        },
        {
            "title": "第4条（委託料）",
            "level": 2,
            "content": "",
            "subsections": [
                {
                    "title": "4.1 金額",
                    "level": 3,
                    "content": "甲は乙に対し、本業務の対価として、金1,500万円（消費税別）を支払うものとする。",
                    "subsections": []
                },
                {
                    "title": "4.2 支払条件",
                    "level": 3,
                    "content": "支払いは以下のスケジュールに従う。\n| 支払時期 | 金額 | 備考 |\n|---------|------|------|\n| 契約締結時 | 500万円 | 着手金 |\n| 中間検収時 | 500万円 | 基本設計完了時 |\n| 最終検収時 | 500万円 | 納品完了時 |",
                    "subsections": []
                }
            ]
        },
        {
            "title": "第5条（機密保持）",
            "level": 2,
            "content": "",
            "subsections": [
                {
                    "title": "5.1 機密情報の定義",
                    "level": 3,
                    "content": "本契約において「機密情報」とは、本業務の遂行に際して相手方から開示された技術上、営業上その他の情報であって、書面により機密である旨が明示されたもの、または口頭で開示された場合は開示後14日以内に書面で機密指定されたものをいう。",
                    "subsections": []
                },
                {
                    "title": "5.2 機密保持義務",
                    "level": 3,
                    "content": "甲および乙は、相手方の機密情報を厳重に管理し、本業務の遂行以外の目的に使用してはならない。また、相手方の事前の書面による承諾なく、第三者に開示または漏洩してはならない。",
                    "subsections": []
                }
            ]
        },
        {
            "title": "第6条（知的財産権）",
            "level": 2,
            "content": "",
            "subsections": [
                {
                    "title": "6.1 権利の帰属",
                    "level": 3,
                    "content": "本業務により生じた成果物に関する著作権（著作権法第27条および第28条の権利を含む）その他一切の知的財産権は、対価の完済をもって甲に帰属するものとする。",
                    "subsections": []
                },
                {
                    "title": "6.2 乙の留保権利",
                    "level": 3,
                    "content": "乙が本業務以前から保有していた技術、ノウハウ、およびライブラリについては、乙に権利が留保されるものとする。",
                    "subsections": []
                }
            ]
        },
        {
            "title": "第7条（瑕疵担保責任）",
            "level": 2,
            "content": "乙は、成果物の納品後1年間、成果物に瑕疵があった場合には、無償で修補を行うものとする。ただし、甲の責めに帰すべき事由による場合はこの限りでない。",
            "subsections": []
        },
        {
            "title": "第8条（損害賠償）",
            "level": 2,
            "content": "甲または乙が本契約に違反し、相手方に損害を与えた場合は、その損害を賠償する責任を負う。ただし、賠償額は本契約に定める委託料の総額を上限とする。",
            "subsections": []
        },
        {
            "title": "第9条（解除）",
            "level": 2,
            "content": "甲または乙は、相手方が以下の各号のいずれかに該当した場合、催告なく直ちに本契約を解除することができる。\n1. 本契約の条項に違反し、相当期間を定めた催告にもかかわらず是正されない場合\n2. 支払停止または支払不能の状態に陥った場合\n3. 破産手続開始、民事再生手続開始、会社更生手続開始の申立てを受け、または自ら申し立てた場合",
            "subsections": []
        },
        {
            "title": "第10条（協議事項）",
            "level": 2,
            "content": "本契約に定めのない事項、または本契約の解釈に疑義が生じた場合は、甲乙協議の上、誠意をもって解決するものとする。",
            "subsections": []
        },
        {
            "title": "第11条（管轄裁判所）",
            "level": 2,
            "content": "本契約に関する一切の紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。\n---\n本契約締結の証として、本書2通を作成し、甲乙記名押印の上、各1通を保有する。\n2024年3月15日\n**甲（委託者）**\n住所：東京都千代田区丸の内1-1-1\n会社名：株式会社サンプル商事\n代表者：代表取締役 山田 太郎\n**乙（受託者）**\n住所：東京都港区六本木2-2-2\n会社名：株式会社テック開発\n代表者：代表取締役 鈴木 花子",
            "subsections": []
        }
    ],
    "metadata": {
        "dates": [
            "2024年4月1日",
            "2024年9月30日",
            "2024年3月15日"
        ],
        "parties": [
            "株式会社サンプル商事",
            "株式会社テック開発"
        ],
        "contract_period": {
            "start": "2024年4月1日",
            "end": "2024年9月30日"
        },
        "amounts": [
            "1,500万円"
        ]
    }
}
```

LLMが生成したPythonスクリプト（`outputs/contract_0_*_script.py`）の例:

```python
import sys
import json
import re

def extract_document_structure():
    content = sys.stdin.read()
    
    lines = content.split('\n')
    
    title = ''
    document_type = 'contract'
    sections = []
    metadata = {}
    
    current_section = None
    current_subsection = None
    current_content = []
    
    parties = {}
    dates = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        # Extract title from first few lines with single #
        if i < 5 and re.match(r'^#\s+[^#]', line_stripped):
            title = re.sub(r'^#\s+', '', line_stripped)
            continue
        
        # Match section pattern: ## 第N条（タイトル）
        section_match = re.match(r'^##\s*第(\d+)条[（(](.+?)[）)]', line_stripped)
        if section_match:
            # Save previous section
            if current_section:
                if current_subsection:
                    current_subsection['content'] = '\n'.join(current_content).strip()
                    current_section['subsections'].append(current_subsection)
                    current_subsection = None
                    current_content = []
                else:
                    current_section['content'] = '\n'.join(current_content).strip()
                sections.append(current_section)
            
            # Create new section
            current_content = []
            current_section = {
                'title': f"第{section_match.group(1)}条（{section_match.group(2)}）",
                'level': 1,
                'content': '',
                'subsections': []
            }
            continue
        
        # Match subsection pattern: ### N.N タイトル
        subsection_match = re.match(r'^###\s+(\d+\.\d+)\s+(.+)', line_stripped)
        if subsection_match:
            # Save previous subsection
            if current_subsection:
                current_subsection['content'] = '\n'.join(current_content).strip()
                if current_section:
                    current_section['subsections'].append(current_subsection)
            
            # Create new subsection
            current_content = []
            current_subsection = {
                'title': f"{subsection_match.group(1)} {subsection_match.group(2)}",
                'level': 2,
                'content': '',
                'subsections': []
            }
            continue
        
        # Extract party information
        party_match = re.match(r'^\*\*([甲乙])（(.+?)）\*\*', line_stripped)
        if party_match:
            party_key = party_match.group(1)
            party_role = party_match.group(2)
            parties[party_key] = {'role': party_role, 'details': {}}
            
            # Look ahead for party details
            for j in range(i+1, min(i+10, len(lines))):
                detail_line = lines[j].strip()
                if detail_line.startswith('住所：'):
                    parties[party_key]['details']['address'] = detail_line.replace('住所：', '')
                elif detail_line.startswith('会社名：'):
                    parties[party_key]['details']['company'] = detail_line.replace('会社名：', '')
                elif detail_line.startswith('代表者：'):
                    parties[party_key]['details']['representative'] = detail_line.replace('代表者：', '')
                elif re.match(r'^\*\*[甲乙]', detail_line) or detail_line.startswith('##'):
                    break
            continue
        
        # Extract dates
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', line_stripped)
        if date_match:
            date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            if date_str not in dates:
                dates.append(date_str)
        
        # Collect content for current section or subsection
        if current_section:
            current_content.append(line_stripped)
    
    # Save final section
    if current_section:
        if current_subsection:
            current_subsection['content'] = '\n'.join(current_content).strip()
            current_section['subsections'].append(current_subsection)
        else:
            current_section['content'] = '\n'.join(current_content).strip()
        sections.append(current_section)
    
    # Build metadata
    if parties:
        metadata['parties'] = parties
    if dates:
        metadata['dates'] = dates
    
    result = {
        'title': title,
        'document_type': document_type,
        'sections': sections,
        'metadata': metadata
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    extract_document_structure()
```

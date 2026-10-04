# Chapter 2 Section 3: 非構造化データの構造化

## 概要

本プロジェクトは、LLM（大規模言語モデル）のマルチモーダル認識能力を活用して、画像形式の非構造化データから構造化データを抽出するCLIツールです。

従来、請求書やスライドなどの画像データから情報を抽出するには、OCR処理、テキスト解析、ルールベース抽出という多段階の工程が必要でした。本ツールでは、Gemini APIのマルチモーダル入力と構造化出力機能を組み合わせることで、これらの工程を単一のLLM呼び出しに置き換え、レイアウトの違いをLLMが自律的に解釈してデータを抽出します。

対応するドキュメントタイプ：
- **請求書（Invoice）**: 発行者情報、明細、税額、振込先情報などを抽出
- **スライド（Slide）**: タイトル、メッセージ、グラフデータ、図表情報を抽出

## 機能

- **自動ドキュメント分類**: 入力画像が請求書かスライドかを自動判定
- **請求書情報抽出**: 発行日、請求番号、金額、明細行、振込先情報を構造化データとして抽出
- **スライド情報抽出**: タイトル、メインメッセージ、各種グラフ・図表のデータを抽出
- **複合グラフ対応**: 棒グラフと折れ線グラフの複合グラフを個別のデータとして分離抽出
- **JSON出力**: 抽出結果をPydanticモデルに基づいたJSON形式で保存

## プロジェクト構成

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI (main.py)                              │
│  - 画像ファイルパス入力                                               │
│  - モデル選択                                                        │
│  - 出力ディレクトリ指定                                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Service Layer (request_llm.py)                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Step 1: request_identify_diagram_type()                      │   │
│  │ - 画像の種類を判定（invoice / slide）                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Step 2: extract_from_image()                                 │   │
│  │ - 判定結果に基づき適切なスキーマで情報抽出                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │  Invoice Model    │           │   Slide Model     │
        │  - issue_date     │           │  - title          │
        │  - issuer_name    │           │  - main_message   │
        │  - recipient      │           │  - diagrams[]     │
        │  - totals         │           │    - bar_chart    │
        │  - line_items[]   │           │    - line_chart   │
        │  - bank_details   │           │    - pie_chart    │
        └───────────────────┘           └───────────────────┘
                                    │
                                    ▼
                        ┌───────────────────┐
                        │   JSON Output     │
                        │   (outputs/*.json)│
                        └───────────────────┘
```

## 使い方

### 環境構成

- Python: 3.13.2以上
- 依存ライブラリ:
  - `click>=8.3.0` - CLIフレームワーク
  - `google-genai>=1.45.0` - Gemini API クライアント
  - `pydantic>=2.12.2` - データバリデーション
  - `python-dotenv>=1.1.1` - 環境変数管理

### セットアップ

1. 環境変数の設定:

```bash
# .envrc.example をコピーして .envrc を作成
cp .envrc.example .envrc

# .envrc を編集してAPIキーを設定
AWS_REGION=us-east-1
```

2. 依存関係のインストール:

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

```bash
$ uv run python -m src.main --help                           
Usage: python -m src.main [OPTIONS]

Options:
  -m, --model [CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5]
                                  The model to use for the request.
                                  [required]
  -i, --image-path PATH           The path to the input image file.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

**CLIオプション:**

| オプション | 短縮形 | 必須 | 説明 |
|-----------|-------|------|------|
| `--model` | `-m` | Yes | 使用するGeminiモデル（CLAUDE_SONNET_4_6, CLAUDE_HAIKU_4_5） |
| `--image-path` | `-i` | Yes | 入力画像ファイルのパス |
| `--output-directory` | `-od` | No | 出力ディレクトリ（デフォルト: `outputs`） |

```bash
# 請求書画像の処理
uv run python -m src.main -m CLAUDE_HAIKU_4_5 -i data/002_請求書_47491048.png

# スライド画像の処理
uv run python -m src.main -m CLAUDE_HAIKU_4_5 -i data/slide_0.png

# 出力ディレクトリを指定
uv run python -m src.main -m CLAUDE_HAIKU_4_5 -i data/003_請求書_49016461.png -od outputs/
```

### 出力例

**請求書画像からの抽出結果:**

```json
{
  "title": "目標を共有し、組織文化を醸成",
  "main_message": null,
  "description": null,
  "diagrams": [
    {
      "diagram_type": "bar_chart",
      "description": "バリュー浸透度における各項目の割合を2022年5月と2022年11月で比較した棒グラフ",
      "data_points": [
        {
          "label": "2022年5月",
          "value": 2.8,
          "unit": "%",
          "series": "そもそも知らない"
        },
        {
          "label": "2022年5月",
          "value": 12.1,
          "unit": "%",
          "series": "聞いたことはあるが内容は理解していない"
        },
        {
          "label": "2022年5月",
          "value": 36.7,
          "unit": "%",
          "series": "内容は理解しているが実践できていない"
        },
        {
          "label": "2022年5月",
          "value": 41.9,
          "unit": "%",
          "series": "一部実践できている"
        },
        {
          "label": "2022年5月",
          "value": 6.5,
          "unit": "%",
          "series": "全て実践できている"
        },
        {
          "label": "2022年11月",
          "value": 1.8,
          "unit": "%",
          "series": "そもそも知らない"
        },
        {
          "label": "2022年11月",
          "value": 6.9,
          "unit": "%",
          "series": "聞いたことはあるが内容は理解していない"
        },
        {
          "label": "2022年11月",
          "value": 26.2,
          "unit": "%",
          "series": "内容は理解しているが実践できていない"
        },
        {
          "label": "2022年11月",
          "value": 56.5,
          "unit": "%",
          "series": "一部実践できている"
        },
        {
          "label": "2022年11月",
          "value": 8.6,
          "unit": "%",
          "series": "全て実践できている"
        }
      ],
      "x_axis_label": "時期",
      "y_axis_label": "割合",
      "message": null
    },
    {
      "diagram_type": "line_chart",
      "description": "バリュー浸透度スコアの推移",
      "data_points": [
        {
          "label": "2022年5月",
          "value": 3.4,
          "unit": "Pt",
          "series": "バリュー浸透度スコア"
        },
        {
          "label": "2022年11月",
          "value": 3.6,
          "unit": "Pt",
          "series": "バリュー浸透度スコア"
        }
      ],
      "x_axis_label": "時期",
      "y_axis_label": "スコア",
      "message": "2022年5月から2022年11月にかけてバリュー浸透度スコアが0.2Pt上昇しました。"
    },
    {
      "diagram_type": "image_diagram",
      "description": "オールハンズミーティングの参加者数を示す数値表示",
      "data_points": [
        {
          "label": "平均参加者数",
          "value": 580.0,
          "unit": "名",
          "series": null
        }
      ],
      "x_axis_label": null,
      "y_axis_label": null,
      "message": "2023年5月、6月、7月の平均参加者数です。"
    },
    {
      "diagram_type": "pie_chart",
      "description": "庁内勉強会の開催カテゴリ別割合を示す円グラフ",
      "data_points": [
        {
          "label": "セキュリティ",
          "value": 22.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "クラウド",
          "value": 17.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "データ",
          "value": 13.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "会計（予算・調達）",
          "value": 8.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "準公共",
          "value": 6.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "政策・企画",
          "value": 6.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "自治体DX",
          "value": 6.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "品質管理",
          "value": 6.0,
          "unit": "%",
          "series": null
        },
        {
          "label": "その他",
          "value": 18.0,
          "unit": "%",
          "series": null
        }
      ],
      "x_axis_label": null,
      "y_axis_label": null,
      "message": "実施回数は56回です。集計期間は2022年9月から2023年8月です。"
    }
  ]
}
```

### 実行ログ

```bash
$ uv run python -m src.main -m CLAUDE_HAIKU_4_5 -i data/002_請求書_47491048.png

[2026-01-17 16:18:53,619] [INFO] [__main__] [main.py:53] [main] 
Model: global.anthropic.claude-haiku-4-5-20251001-v1:0
Input image path: data/002_請求書_47491048.png
Output directory: outputs
[2026-01-17 16:18:57,044] [INFO] [src.service.request_llm] [request_llm.py:47] [request_gemini] Processing image with model: global.anthropic.claude-haiku-4-5-20251001-v1:0
[2026-01-17 16:19:04,033] [INFO] [src.service.request_llm] [request_llm.py:25] [request_identify_diagram_type] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text='{"diagram_type": "invoice"}'
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='global.anthropic.claude-haiku-4-5-20251001-v1:0' prompt_feedback=None response_id='5zdraa6dOPSVosUP5IKAiAY' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=8,
  prompt_token_count=515,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=257
    ),
    ModalityTokenCount(
      modality=<MediaModality.IMAGE: 'IMAGE'>,
      token_count=258
    ),
  ],
  thoughts_token_count=363,
  total_token_count=886
) automatic_function_calling_history=[] parsed=Diagram(diagram_type=<DiagramType.INVOICE: 'invoice'>)
[2026-01-17 16:19:04,033] [INFO] [src.service.request_llm] [request_llm.py:50] [request_gemini] Identified diagram type: invoice
[2026-01-17 16:19:11,940] [INFO] [src.service.request_llm] [request_llm.py:42] [extract_from_image] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text='{"title":"請求書","issue_date":"2024-03-31","invoice_number":null,"payment_deadline":null,"issuer_name":"株式会社OWL","recipient":"株式会社MARU","totals":{"total_amount_excluded_tax":3670000,"total_tax_amount":367000,"total_amount_included_tax":4037000},"bank_details":{"bank_name":"三菱UFJ銀行","branch_name":"名古屋駅前支店","account_type":"普通","account_number":"5263983","account_holder":"カ)アウル"},"line_items":[{"transaction_date":null,"item_code":null,"item_name":"蛇口交換工事","quantity":2,"unit":null,"unit_price":10000,"amount":20000,"tax_type":null,"remarks":null},{"transaction_date":null,"item_code":null,"item_name":"エアコン設置工事","quantity":3,"unit":null,"unit_price":50000,"amount":150000,"tax_type":null,"remarks":null},{"transaction_date":null,"item_code":null,"item_name":"耐震工事","quantity":0,"unit":null,"unit_price":0,"amount":0,"tax_type":null,"remarks":null},{"transaction_date":null,"item_code":null,"item_name":"エントランス側","quantity":2,"unit":null,"unit_price":950000,"amount":1900000,"tax_type":null,"remarks":null},{"transaction_date":null,"item_code":null,"item_name":"エスカレーター側","quantity":2,"unit":null,"unit_price":800000,"amount":1600000,"tax_type":null,"remarks":null}]}'
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='global.anthropic.claude-haiku-4-5-20251001-v1:0' prompt_feedback=None response_id='7zdrac6zL-Wnvr0P_I7d8As' usage_metadata=GenerateContentResponseUsageMetadata(
  candidates_token_count=430,
  prompt_token_count=2391,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=2133
    ),
    ModalityTokenCount(
      modality=<MediaModality.IMAGE: 'IMAGE'>,
      token_count=258
    ),
  ],
  thoughts_token_count=1046,
  total_token_count=3867
) automatic_function_calling_history=[] parsed=Invoice(title='請求書', issue_date=datetime.date(2024, 3, 31), invoice_number=None, payment_deadline=None, issuer_name='株式会社OWL', recipient='株式会社MARU', totals=InvoiceFinancialTotals(total_amount_excluded_tax=3670000, total_tax_amount=367000, total_amount_included_tax=4037000), bank_details=InvoiceBankDetails(bank_name='三菱UFJ銀行', branch_name='名古屋駅前支店', account_type=<InvoiceBankAccountType.ORDINARY: '普通'>, account_number='5263983', account_holder='カ)アウル'), line_items=[InvoiceLineItem(transaction_date=None, item_code=None, item_name='蛇口交換工 事', quantity=2.0, unit=None, unit_price=10000.0, amount=20000, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='エアコン設置工事', quantity=3.0, unit=None, unit_price=50000.0, amount=150000, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='耐震工事', quantity=0.0, unit=None, unit_price=0.0, amount=0, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='エントランス側', quantity=2.0, unit=None, unit_price=950000.0, amount=1900000, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='エスカレーター側', quantity=2.0, unit=None, unit_price=800000.0, amount=1600000, tax_type=None, remarks=None)])
[2026-01-17 16:19:11,941] [INFO] [src.service.request_llm] [request_llm.py:53] [request_gemini] Extracted data: title='請求書' issue_date=datetime.date(2024, 3, 31) invoice_number=None payment_deadline=None issuer_name='株式会社OWL' recipient='株式会社MARU' totals=InvoiceFinancialTotals(total_amount_excluded_tax=3670000, total_tax_amount=367000, total_amount_included_tax=4037000) bank_details=InvoiceBankDetails(bank_name='三菱UFJ銀行', branch_name='名古屋駅前支店', account_type=<InvoiceBankAccountType.ORDINARY: '普通'>, account_number='5263983', account_holder='カ)アウル') line_items=[InvoiceLineItem(transaction_date=None, item_code=None, item_name='蛇口交換工事', quantity=2.0, unit=None, unit_price=10000.0, amount=20000, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='エアコン設置工事', quantity=3.0, unit=None, unit_price=50000.0, amount=150000, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='耐震工事', quantity=0.0, unit=None, unit_price=0.0, amount=0, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='エントランス側', quantity=2.0, unit=None, unit_price=950000.0, amount=1900000, tax_type=None, remarks=None), InvoiceLineItem(transaction_date=None, item_code=None, item_name='エスカレーター側', quantity=2.0, unit=None, unit_price=800000.0, amount=1600000, tax_type=None, remarks=None)]
[2026-01-17 16:19:11,943] [INFO] [__main__] [main.py:72] [main] File saved to outputs/gemini_c5aeb5f8629f4d3484b736397c77d8ae.json
```

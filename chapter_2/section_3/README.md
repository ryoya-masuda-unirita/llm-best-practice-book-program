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

### ディレクトリ構成

```
chapter_2/section_14/
├── CLAUDE.md              # プロジェクト説明ドキュメント
├── README.md              # 本ファイル
├── Makefile               # 開発用コマンド
├── pyproject.toml         # プロジェクト設定・依存関係
├── .envrc.example         # 環境変数テンプレート
├── data/                  # サンプル画像データ
│   ├── 001_請求書_47210309.png
│   ├── 002_請求書_47491048.png
│   └── 003_請求書_49016461.png
├── outputs/               # 出力ディレクトリ
└── src/
    ├── __init__.py
    ├── main.py            # CLIエントリーポイント
    ├── config.py          # 設定管理
    ├── logger.py          # ロギング設定
    ├── client/
    │   ├── __init__.py
    │   └── llm_client.py  # Gemini APIクライアント
    ├── model/
    │   ├── __init__.py
    │   └── model.py       # Pydanticデータモデル定義
    ├── prompt/
    │   ├── __init__.py
    │   └── prompt.py      # プロンプト生成
    └── service/
        ├── __init__.py
        └── request_llm.py # LLMリクエスト処理
```

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
GEMINI_API_KEY=your_gemini_api_key_here
```

2. 依存関係のインストール:

```bash
# uvを使用する場合
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

```bash
# 基本的な使い方
python -m src.main -m GEMINI_2_5_FLASH -i data/001_請求書_47210309.png

# 出力ディレクトリを指定
python -m src.main -m GEMINI_2_5_FLASH -i data/001_請求書_47210309.png -od outputs/

# 利用可能なオプション
python -m src.main --help
```

**CLIオプション:**

| オプション | 短縮形 | 必須 | 説明 |
|-----------|-------|------|------|
| `--model` | `-m` | Yes | 使用するGeminiモデル（GEMINI_2_5_PRO, GEMINI_2_5_FLASH, GEMINI_2_5_FLASH_LITE） |
| `--image-path` | `-i` | Yes | 入力画像ファイルのパス |
| `--output-directory` | `-od` | No | 出力ディレクトリ（デフォルト: `outputs`） |

### 出力例

**請求書画像からの抽出結果:**

```json
{
  "title": "請求書",
  "issue_date": "2023-09-02",
  "invoice_number": "13301681-01",
  "payment_deadline": "2023-09-30",
  "issuer_name": "株式会社フォレスト",
  "recipient": "株式会社ゲンテン",
  "totals": {
    "total_amount_excluded_tax": 1900000,
    "total_tax_amount": 190000,
    "total_amount_included_tax": 2090000
  },
  "bank_details": {
    "bank_name": "ソフトウェア関連会社",
    "branch_name": null,
    "account_type": "普通",
    "account_number": "08227000",
    "account_holder": "合同会社be BEAVE"
  },
  "line_items": [
    {
      "transaction_date": null,
      "item_code": null,
      "item_name": "概要設計",
      "quantity": 2.0,
      "unit": "人日",
      "unit_price": 40000.0,
      "amount": 80000,
      "tax_type": null,
      "remarks": null
    },
    {
      "transaction_date": null,
      "item_code": null,
      "item_name": "詳細設計",
      "quantity": 5.0,
      "unit": "人日",
      "unit_price": 40000.0,
      "amount": 200000,
      "tax_type": null,
      "remarks": null
    }
  ]
}
```

**スライド画像からの抽出結果（複合グラフの例）:**

```json
{
  "title": "2024年度 売上推移",
  "main_message": "売上は前年比120%増、成長率も堅調に推移",
  "description": "月別売上と成長率の推移を示すグラフ",
  "diagrams": [
    {
      "diagram_type": "bar_chart",
      "description": "月別売上金額",
      "data_points": [
        {"label": "1月", "value": 100, "unit": "万円", "series": "売上"},
        {"label": "2月", "value": 120, "unit": "万円", "series": "売上"}
      ],
      "x_axis_label": "月",
      "y_axis_label": "売上（万円）",
      "message": null
    },
    {
      "diagram_type": "line_chart",
      "description": "前年同月比成長率",
      "data_points": [
        {"label": "1月", "value": 15, "unit": "%", "series": "成長率"},
        {"label": "2月", "value": 18, "unit": "%", "series": "成長率"}
      ],
      "x_axis_label": "月",
      "y_axis_label": "成長率（%）",
      "message": null
    }
  ]
}
```

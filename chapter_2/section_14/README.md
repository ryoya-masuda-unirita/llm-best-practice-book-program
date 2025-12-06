# 第2章 第14項: 非構造化データの構造化

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

### 実装の詳細

#### 1. データモデル定義 (`src/model/model.py`)

Pydanticを使用して、抽出するデータの構造を厳密に定義しています。これにより、LLMの出力が期待するスキーマに準拠することを保証します。

**請求書モデル（Invoice）:**

```python
class Invoice(BaseModel):
    title: str = Field("請求書", description="文書タイトル")
    issue_date: date = Field(..., description="発行日")
    invoice_number: Optional[str] = Field(None, description="請求書番号")
    payment_deadline: Optional[date] = Field(None, description="支払い期限")
    issuer_name: str = Field(..., description="請求元情報")
    recipient: str = Field(..., description="請求先情報")
    totals: InvoiceFinancialTotals = Field(..., description="合計金額情報")
    bank_details: Optional[InvoiceBankDetails] = Field(None, description="振込先情報")
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="明細行のリスト")
```

**スライドモデル（Slide）:**

```python
class SlideDiagramType(StrEnum):
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    FLOW_CHART = "flow_chart"
    SYSTEM_DIAGRAM = "system_diagram"
    IMAGE_DIAGRAM = "image_diagram"

class SlideDiagram(BaseModel):
    diagram_type: SlideDiagramType = Field(description="図表の種類")
    description: Optional[str] = Field(default=None, description="図表の説明")
    data_points: Optional[list[ChartDataPoint]] = Field(default=None, description="グラフのデータポイントのリスト")
    x_axis_label: Optional[str] = Field(default=None, description="X軸のラベル")
    y_axis_label: Optional[str] = Field(default=None, description="Y軸のラベル")
    message: Optional[str] = Field(default=None, description="図表に関連するメッセージや説明")
```

> **ポイント**: Gemini APIの構造化出力機能では、`additionalProperties`がサポートされていないため、`dict`型の使用は避け、具体的なフィールドを持つモデルを定義する必要があります。

#### 2. LLMリクエスト処理 (`src/service/request_llm.py`)

2段階のLLM呼び出しで処理を行います：

```python
async def request_gemini(model: str, gemini_path: File) -> Invoice | Slide:
    # Step 1: ドキュメントタイプの判定
    diagram = await request_identify_diagram_type(model=model, gemini_path=gemini_path)

    # Step 2: 判定結果に基づいてデータ抽出
    result = await extract_from_image(
        model=model,
        gemini_path=gemini_path,
        diagram_type=diagram.diagram_type
    )
    return result
```

> **ポイント**: 処理を2段階に分けることで、各ステップのプロンプトをシンプルに保ち、LLMの出力精度を向上させています。

#### 3. プロンプト設計 (`src/prompt/prompt.py`)

Pydanticモデルのスキーマ情報をプロンプトに埋め込み、LLMに期待する出力形式を明示します：

```python
def make_invoice_prompt() -> tuple[str, str]:
    params = Invoice.model_json_schema()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    system_prompt = f"""あなたは請求書から情報を抽出する専門家です。

以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
- 日付は "YYYY-MM-DD" 形式で出力してください
- 金額は数値として出力してください（カンマや円記号は除く）
- 明細行（line_items）は画像に表示されているすべての項目を抽出してください
..."""
```

> **ポイント**: スライドの複合グラフ（棒グラフ＋折れ線グラフなど）は、個別のdiagramオブジェクトとして分離抽出するよう指示しています。

#### 4. Gemini APIクライアント (`src/client/llm_client.py`)

```python
class GeminiModel(StrEnum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

google_genai_client = genai.Client(api_key=config.gemini_api_key.get_secret_value())
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

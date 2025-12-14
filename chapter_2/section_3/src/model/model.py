from datetime import date
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DiagramType(StrEnum):
    INVOICE = "invoice"
    SLIDE = "slide"


class Diagram(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    diagram_type: DiagramType = Field(..., description="図表の種類")


class InvoiceBankAccountType(StrEnum):
    ORDINARY = "普通"
    CURRENT = "当座"
    SAVINGS = "貯蓄"
    OTHER = "その他"


class InvoiceTaxType(StrEnum):
    TAX_INCLUDED = "内"
    TAX_EXCLUDED = "外"
    NON_TAXABLE = "非"


class InvoiceBankDetails(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    bank_name: Optional[str] = Field(None, description="銀行名")
    branch_name: Optional[str] = Field(None, description="支店名")
    account_type: Optional[InvoiceBankAccountType] = Field(None, description="口座種別（普通/当座など）")
    account_number: Optional[str] = Field(None, description="口座番号")
    account_holder: Optional[str] = Field(None, description="口座名義")


class InvoiceLineItem(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    transaction_date: Optional[date] = Field(None, description="取引日付")
    item_code: Optional[str] = Field(None, description="品番・型番・伝票Noなど")
    item_name: str = Field(..., description="商品名・品名")
    quantity: float = Field(..., description="数量")
    unit: Optional[str] = Field(None, description="単位（本、式、個など）")
    unit_price: float = Field(..., description="単価")
    amount: int = Field(..., description="金額（通常は税抜だが、文脈による）")
    tax_type: Optional[InvoiceTaxType] = Field(None, description="税区分（内税/外税など）")
    remarks: Optional[str] = Field(None, description="備考・現場名など")


class InvoiceIssuerInfo(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    name: str = Field(..., description="請求元の会社名・氏名")
    address: Optional[str] = Field(None, description="請求元の住所")
    phone_number: Optional[str] = Field(None, description="電話番号")
    fax_number: Optional[str] = Field(None, description="FAX番号")
    registration_number: Optional[str] = Field(None, description="適格請求書発行事業者登録番号(T番号)")


class InvoiceRecipientInfo(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    name: str = Field(..., description="請求先の会社名・氏名")


class InvoiceFinancialTotals(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    total_amount_excluded_tax: Optional[int] = Field(None, description="税抜合計金額")
    total_tax_amount: Optional[int] = Field(None, description="消費税合計額")
    total_amount_included_tax: int = Field(..., description="税込合計金額（請求総額）")


class Invoice(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    title: str = Field("請求書", description="文書タイトル")
    issue_date: date = Field(..., description="発行日")
    invoice_number: Optional[str] = Field(None, description="請求書番号")
    payment_deadline: Optional[date] = Field(None, description="支払い期限")
    issuer_name: str = Field(..., description="請求元情報")
    recipient: str = Field(..., description="請求先情報")
    totals: InvoiceFinancialTotals = Field(..., description="合計金額情報")
    bank_details: Optional[InvoiceBankDetails] = Field(None, description="振込先情報")
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="明細行のリスト")


class SlideDiagramType(StrEnum):
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    FLOW_CHART = "flow_chart"
    SYSTEM_DIAGRAM = "system_diagram"
    IMAGE_DIAGRAM = "image_diagram"


class ChartDataPoint(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    label: str = Field(..., description="データポイントのラベル（例：月名、カテゴリ名）")
    value: Optional[float] = Field(default=None, description="数値データ")
    unit: Optional[str] = Field(default=None, description="単位（例：ドル、パーセント）")
    series: Optional[str] = Field(default=None, description="系列名（複数系列のグラフの場合）")


class SlideDiagram(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    diagram_type: SlideDiagramType = Field(description="図表の種類")
    description: Optional[str] = Field(default=None, description="図表の説明")
    data_points: Optional[list[ChartDataPoint]] = Field(default=None, description="グラフのデータポイントのリスト")
    x_axis_label: Optional[str] = Field(default=None, description="X軸のラベル")
    y_axis_label: Optional[str] = Field(default=None, description="Y軸のラベル")
    message: Optional[str] = Field(default=None, description="図表に関連するメッセージや説明")


class Slide(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    title: Optional[str] = Field(default=None, description="The title of the slide.")
    main_message: Optional[str] = Field(default=None, description="The main message of the slide.")
    description: Optional[str] = Field(default=None, description="The description of the slide.")
    diagrams: Optional[list[SlideDiagram]] = Field(default=None, description="The list of diagrams.")

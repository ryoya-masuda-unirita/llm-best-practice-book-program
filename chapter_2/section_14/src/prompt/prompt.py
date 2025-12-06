import json

from src.model.model import Diagram, Invoice, Slide


def make_diagram_identification_prompt() -> tuple[str, str]:
    params = Diagram.model_json_schema()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    system_prompt = f"""あなたは画像分類の専門家です。与えられた画像を分析し、その種類を特定してください。

以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
- 画像が請求書（invoice）である場合は "invoice" を返してください
- 画像がスライド（slide）である場合は "slide" を返してください
- 請求書には通常、金額、日付、発行者、請求先などの情報が含まれます
- スライドには通常、タイトル、グラフ、図表、説明文などが含まれます
"""
    user_prompt = "この画像の種類を特定してください。"
    return system_prompt, user_prompt


def make_invoice_prompt() -> tuple[str, str]:
    params = Invoice.model_json_schema()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    system_prompt = f"""あなたは請求書から情報を抽出する専門家です。与えられた請求書画像から、構造化されたデータを抽出してください。

以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
- 日付は "YYYY-MM-DD" 形式で出力してください
- 金額は数値として出力してください（カンマや円記号は除く）
- 明細行（line_items）は画像に表示されているすべての項目を抽出してください
- 読み取れない項目や存在しない項目は null として出力してください
- 税込金額（total_amount_included_tax）は必須です
- 請求元（issuer_name）と請求先（recipient）は必須です
"""
    user_prompt = "この請求書から情報を抽出してください。"
    return system_prompt, user_prompt


def make_slide_prompt() -> tuple[str, str]:
    params = Slide.model_json_schema()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    system_prompt = f"""あなたはプレゼンテーションスライドから情報を抽出する専門家です。与えられたスライド画像から、構造化されたデータを抽出してください。

以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
- スライドのタイトルを抽出してください
- 主要なメッセージ（main_message）を特定してください
- グラフや図表がある場合は、その種類を特定してください：
  - bar_chart: 棒グラフ
  - line_chart: 折れ線グラフ
  - pie_chart: 円グラフ
  - flow_chart: フローチャート・処理フロー図
  - system_diagram: システム構成図・アーキテクチャ図・ネットワーク図など
  - image_diagram: 写真・イラスト・その他の画像

重要：複合グラフの扱いについて
- 1つのグラフエリアに複数の種類のグラフが含まれている場合（例：棒グラフと折れ線グラフの複合グラフ）、それぞれを別々の diagram として分離して抽出してください
- 例：売上（棒グラフ）と成長率（折れ線グラフ）が1つのグラフに表示されている場合：
  - 1つ目の diagram: diagram_type="bar_chart" で売上データを抽出
  - 2つ目の diagram: diagram_type="line_chart" で成長率データを抽出
- 各 diagram には該当するデータポイントのみを含めてください

図表の種類ごとの抽出方法：
- グラフ（bar_chart, line_chart, pie_chart）の場合：
  - data_points にラベル、値、単位（ドル、パーセントなど）、系列名（複数系列の場合）を抽出してください
  - 軸ラベルがある場合は x_axis_label, y_axis_label に抽出してください
- フローチャート（flow_chart）の場合：
  - description に処理の流れを文章で説明してください
  - message に図の目的や要点を記載してください
- システム構成図（system_diagram）の場合：
  - description にシステムの構成要素と接続関係を文章で説明してください
  - message に図の目的や要点を記載してください
- 画像（image_diagram）の場合：
  - description に画像の内容を文章で説明してください
  - message に画像が伝えるメッセージを記載してください

- 読み取れない項目は null として出力してください
"""
    user_prompt = "このスライドから情報を抽出してください。"
    return system_prompt, user_prompt

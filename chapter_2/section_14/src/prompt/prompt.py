def make_sampling_prompt(document_content: str) -> list:
    return [
        {
            "role": "user",
            "content": f"""あなたは文書分析の専門家です。以下の文書を分析し、構造を理解するために必要な情報を抽出してください。

## タスク
1. 文書から代表的な文（5〜10文）をサンプリングしてください
2. 文書のタイプ（契約書、レポート、マニュアルなど）を特定してください
3. 文書内の主要なセクション名やヘッダーを特定してください

## 文書内容
```
{document_content}
```

## 出力形式
JSON形式で以下の構造で回答してください：
- sentences: 代表的な文のリスト（文書の構造を理解するのに役立つ文を選んでください）
- document_type: 文書のタイプ（例: "contract", "report", "manual", "article"）
- key_sections: 特定されたセクション名のリスト

重要: JSON以外のテキストを含めないでください。
""",
        },
    ]


def make_script_generation_prompt(
    document_content: str,
    sampled_info: dict,
) -> list:
    return [
        {
            "role": "user",
            "content": f"""あなたはPythonプログラミングの専門家です。文書の構造を抽出するPythonスクリプトを生成してください。

## 文書情報
- 文書タイプ: {sampled_info.get("document_type", "unknown")}
- 特定されたセクション: {sampled_info.get("key_sections", [])}
- サンプル文: {sampled_info.get("sentences", [])[:3]}

## 文書内容
```
{document_content}
```

## 要件
1. 文書の構造（タイトル、セクション、サブセクション）を抽出するPythonスクリプトを書いてください
2. スクリプトは標準入力から文書内容を受け取り、標準出力にJSON形式で結果を出力してください
3. 出力JSONは以下の構造に従ってください：
   - title: 文書のタイトル
   - document_type: 文書タイプ
   - sections: セクションのリスト（各セクションには title, level, content, subsections を含む）
   - metadata: 追加のメタデータ（日付、著者など、存在する場合）

## セキュリティ要件（重要）
- ファイルシステムへのアクセスは禁止です（open, os.path, pathlib等は使用しないでください）
- ネットワークアクセスは禁止です（requests, urllib, socket等は使用しないでください）
- 外部コマンドの実行は禁止です（subprocess, os.system等は使用しないでください）
- 使用可能なモジュール: sys, json, re のみ
- 入力は sys.stdin.read() で取得してください
- 出力は print(json.dumps(result, ensure_ascii=False, indent=2)) で行ってください

## 出力形式
JSON形式で以下の構造で回答してください：
- script: 生成したPythonスクリプト（コードブロックなしで純粋なPythonコードのみ）
- explanation: スクリプトの簡単な説明

重要: JSON以外のテキストを含めないでください。
""",
        },
    ]


def make_error_correction_prompt(
    original_script: str,
    error_message: str,
    document_content: str,
) -> list:
    return [
        {
            "role": "user",
            "content": f"""あなたはPythonプログラミングの専門家です。以下のスクリプトの実行時にエラーが発生しました。エラーを修正してください。

## 元のスクリプト
```python
{original_script}
```

## エラーメッセージ
```
{error_message}
```

## 文書内容（参考）
```
{document_content[:1000]}...
```

## セキュリティ要件（重要）
- ファイルシステムへのアクセスは禁止です
- ネットワークアクセスは禁止です
- 外部コマンドの実行は禁止です
- 使用可能なモジュール: sys, json, re のみ

## 出力形式
JSON形式で以下の構造で回答してください：
- script: 修正したPythonスクリプト（コードブロックなしで純粋なPythonコードのみ）
- explanation: 修正内容の説明

重要: JSON以外のテキストを含めないでください。
""",
        },
    ]


def make_validation_prompt(
    document_content: str,
    extraction_result: str,
    script_explanation: str,
) -> list:
    return [
        {
            "role": "user",
            "content": f"""あなたは文書構造抽出の品質評価の専門家です。以下の情報を基に、抽出結果の品質を評価してください。

## 評価対象

### 元の文書内容
```
{document_content}
```

### 抽出スクリプトの説明
{script_explanation}

### 抽出結果（JSON）
```json
{extraction_result}
```

## 評価基準

以下の基準に基づいて1〜5のスコアで評価してください：

**スコア 5（優秀）**
- 文書の構造が完全かつ正確に抽出されている
- すべての主要セクション、サブセクションが正しく特定されている
- メタデータ（タイトル、文書タイプ等）が正確
- セクションの階層関係が正しく表現されている

**スコア 4（良好）**
- 文書の構造がほぼ正確に抽出されている
- 主要セクションは正しく特定されているが、軽微な欠落がある
- メタデータはおおむね正確

**スコア 3（許容範囲）**
- 文書の主要な構造は抽出されているが、一部不正確
- いくつかのセクションが欠落または誤って分類されている
- メタデータに若干の誤りがある

**スコア 2（要改善）**
- 文書構造の抽出に重大な問題がある
- 多くのセクションが欠落または誤って分類されている
- メタデータが不正確または欠落している

**スコア 1（不十分）**
- 抽出結果が元の文書をほとんど反映していない
- 構造抽出が大幅に失敗している
- 使用不可能なレベル

## 出力形式

JSON形式で以下の構造で回答してください：
- score: 1〜5の整数スコア
- reasoning: スコアの詳細な理由（具体的な問題点や良い点を挙げてください）
- fix_proposal: スコアが3未満の場合のみ、改善提案を記載してください（3以上の場合はnull）

重要: JSON以外のテキストを含めないでください。
""",
        },
    ]


def make_validation_correction_prompt(
    original_script: str,
    validation_reasoning: str,
    fix_proposal: str,
    document_content: str,
) -> list:
    return [
        {
            "role": "user",
            "content": f"""あなたはPythonプログラミングの専門家です。以下のスクリプトによる文書構造抽出の品質が低いと評価されました。評価フィードバックに基づいてスクリプトを改善してください。

## 元のスクリプト
```python
{original_script}
```

## 品質評価の理由
{validation_reasoning}

## 改善提案
{fix_proposal}

## 文書内容（参考）
```
{document_content[:2000]}...
```

## 要件
1. 評価フィードバックと改善提案に基づいてスクリプトを修正してください
2. 文書の構造（タイトル、セクション、サブセクション）をより正確に抽出できるようにしてください
3. 出力JSONは以下の構造に従ってください：
   - title: 文書のタイトル
   - document_type: 文書タイプ
   - sections: セクションのリスト（各セクションには title, level, content, subsections を含む）
   - metadata: 追加のメタデータ（日付、著者など、存在する場合）

## セキュリティ要件（重要）
- ファイルシステムへのアクセスは禁止です
- ネットワークアクセスは禁止です
- 外部コマンドの実行は禁止です
- 使用可能なモジュール: sys, json, re のみ

## 出力形式
JSON形式で以下の構造で回答してください：
- script: 修正したPythonスクリプト（コードブロックなしで純粋なPythonコードのみ）
- explanation: 修正内容の説明

重要: JSON以外のテキストを含めないでください。
""",
        },
    ]

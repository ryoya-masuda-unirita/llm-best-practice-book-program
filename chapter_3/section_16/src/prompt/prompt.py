def make_sampling_prompt(document_content: str) -> list:
    """Create a prompt for sampling representative sentences from a document."""
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
    """Create a prompt for generating a Python script to extract document structure."""
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
    """Create a prompt for correcting a script that failed to execute."""
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

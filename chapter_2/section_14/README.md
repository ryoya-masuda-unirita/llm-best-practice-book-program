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

### 実装の詳細

#### 1. スクリプト検証とサンドボックス実行 (`src/service/script_executor.py`)

LLMが生成したスクリプトを安全に実行するため、多層的な防御策を実装しています。

```python
FORBIDDEN_PATTERNS = [
    r"\bopen\s*\(",      # ファイルアクセス禁止
    r"\bos\.",           # OSモジュール禁止
    r"\bsubprocess\b",   # 外部コマンド実行禁止
    r"\brequests\b",     # ネットワークアクセス禁止
    r"\beval\s*\(",      # 動的コード実行禁止
    r"\bexec\s*\(",
    # ... その他多数
]

ALLOWED_IMPORTS = {"sys", "json", "re"}  # 許可されたモジュールのみ
```

**ポイント**: スクリプト実行時は環境変数を空にし、外部リソースへのアクセスを完全に遮断します。

```python
result = subprocess.run(
    [sys.executable, script_path],
    input=document_content,
    capture_output=True,
    timeout=timeout,
    env={"PATH": "", "HOME": "", "PYTHONPATH": ""},  # 環境を隔離
)
```

#### 2. 自己修正ループ (`src/service/document_processor.py`)

スクリプト実行に失敗した場合、エラーメッセージをLLMにフィードバックして修正版を生成します。

```python
async def _execute_script_with_retry(
    model: AnthropicModel,
    script: str,
    document_content: str,
    max_attempts: int = DEFAULT_MAX_CORRECTION_ATTEMPTS,
) -> ScriptExecutionResult:
    """Execute a script with retry and self-correction on failure."""
    current_script = script

    for attempt in range(max_attempts + 1):
        execution_result = execute_script(current_script, document_content)

        if execution_result.success:
            return execution_result

        if attempt < max_attempts:
            # LLMにエラーをフィードバックして修正
            corrected_script = await correct_script(
                model=model,
                original_script=current_script,
                error_message=execution_result.error,
                document_content=document_content,
            )
            current_script = corrected_script.script

    return execution_result
```

#### 3. Structured Outputs によるLLMレスポンス (`src/service/request_llm.py`)

Anthropic API の Structured Outputs 機能を活用し、型安全なレスポンスを取得します。

```python
async def generate_extraction_script(
    model: AnthropicModel,
    document_content: str,
    sampled_info: dict,
) -> GeneratedScript:
    """Generate a Python script to extract document structure."""
    prompt = make_script_generation_prompt(document_content, sampled_info)
    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=GeneratedScript,  # Pydanticモデルで型を指定
    )
    return result.parsed_output
```

#### 4. LLM-as-a-Judge品質評価 (`src/service/validator.py`)

抽出結果の品質をLLMが評価し、低スコアの場合は改善提案を生成します。

```python
async def validate_extraction_result(
    model: AnthropicModel,
    extraction_result: ExtractionResult,
    document_content: str,
) -> ValidationResult:
    """Validate the extraction result using LLM-as-a-Judge."""
    prompt = make_validation_prompt(
        document_content=document_content,
        extraction_result=json.dumps(extraction_result.raw_result, ensure_ascii=False),
        script_explanation=extraction_result.script_explanation,
    )

    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=2048,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=ValidationResult,  # score, reasoning, fix_proposal
    )

    return result.parsed_output
```

**ポイント**: スコアが閾値（3）以下の場合、改善提案を基にスクリプトを再修正し、抽出精度を高めます。

#### 5. データモデル定義 (`src/model/model.py`)

抽出される文書構造はPydanticモデルで厳密に定義されています。

```python
class DocumentSection(BaseModel):
    title: str = Field(..., description="Title or heading of the section.")
    level: int = Field(..., description="Heading level (1 for top-level, 2 for subsection, etc.).")
    content: str = Field(default="", description="Content of the section.")
    subsections: list["DocumentSection"] = Field(default_factory=list)

class DocumentStructure(BaseModel):
    title: str = Field(..., description="Title of the document.")
    document_type: str = Field(..., description="Type of the document.")
    sections: list[DocumentSection] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
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
# 基本的な使用方法
python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md

# 出力ディレクトリを指定
python -m src.main -m claude-sonnet-4-5 -i data/contract_0.md -od outputs

# ヘルプを表示
python -m src.main --help
```

#### CLIオプション

| オプション | 短縮形 | 必須 | デフォルト | 説明 |
|-----------|-------|------|-----------|------|
| `--model` | `-m` | Yes | - | 使用するモデル（`claude-sonnet-4-5` または `claude-opus-4-1`） |
| `--input` | `-i` | Yes | - | 入力文書ファイルのパス |
| `--output-directory` | `-od` | No | `outputs` | 出力ファイルの保存先ディレクトリ |

### 出力例

契約書（`data/contract_0.md`）を処理した場合の実行ログ:

```
[INFO] Model: claude-sonnet-4-5
Input file: data/contract_0.md
Output directory: outputs
[INFO] Document loaded: 1822 characters
[INFO] Step 1: Sampling document sentences...
[INFO] Document type identified: contract
[INFO] Key sections found: ['第1条（目的）', '第2条（業務内容）', '2.1 開発対象', ...]
[INFO] Step 2: Generating extraction script...
[INFO] Script explanation: このスクリプトは契約書などの構造化文書からタイトル、セクション、サブセクションを抽出します...
[INFO] Step 3: Executing script (attempt 1/4)...
[INFO] Script executed successfully!
[INFO] Document structure saved to: outputs/contract_0_a25026f6_structure.json
[INFO] Generated script saved to: outputs/contract_0_a25026f6_script.py
[INFO] Metadata saved to: outputs/contract_0_a25026f6_metadata.json
[INFO] Document structure extraction completed successfully!
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
            "content": "甲は乙に対し、本契約に定める条件に従い...",
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
                    "content": "乙が開発するソフトウェアの概要は以下の通りとする...",
                    "subsections": []
                }
            ]
        }
    ],
    "metadata": {
        "contract_date": "2024-04-01",
        "contract_period": {
            "start": "2024-04-01",
            "end": "2024-09-30"
        },
        "parties": {
            "甲": {
                "address": "東京都千代田区丸の内1-1-1",
                "company": "株式会社サンプル商事",
                "representative": "代表取締役 山田 太郎"
            },
            "乙": {
                "address": "東京都港区六本木2-2-2",
                "company": "株式会社テック開発",
                "representative": "代表取締役 鈴木 花子"
            }
        }
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

    title = ""
    document_type = "contract"
    sections = []
    metadata = {}

    # Markdown見出しを解析してセクション構造を構築
    for i, line in enumerate(lines):
        h2_match = re.match(r'^##\s+(.+)$', line.strip())
        if h2_match:
            # セクション処理...

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

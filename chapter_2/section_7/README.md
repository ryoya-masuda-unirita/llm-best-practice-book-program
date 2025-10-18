# Chapter 2 Section 7: LLMでLLMを評価する（LLM-as-a-Judge）

## 概要

このプロジェクトは、**LLM-as-a-Judge**（LLMを審査員として活用する設計手法）の実装を示すサンプルコードです。LLMが生成したコンテンツを別のLLMが自動的に評価することで、品質管理の自動化と効率化を実現します。

OpenAI GPT-4o-miniとGoogle Gemini 2.5 Flashの両方に対応し、**クロスプロバイダー評価**（異なるプロバイダーで生成と評価を行う）もサポートしています。キャラクター生成という具体的なユースケースを通じて、LLM-as-a-Judgeの実践的な実装方法を学ぶことができます。

## 機能

### 基本機能
- **自動品質評価**: 生成されたすべてのキャラクターを自動的に評価
- **構造化評価結果**: JSON形式で詳細な評価結果を出力
- **3つの評価軸**: 正確性（accuracy）、網羅性（comprehensiveness）、明瞭さ（clarity）
- **スコアリング**: 1-5点の5段階評価と総合スコア算出
- **品質閾値チェック**: 設定した閾値（デフォルト3.0/5.0）を下回る場合に警告

### 高度な機能
- **クロスプロバイダー評価**: 異なるLLMプロバイダーで生成と評価を実行
- **カスタム評価基準**: プログラマティックAPIでドメイン固有の評価基準を定義可能
- **温度パラメータ制御**: 評価の一貫性を高めるため低温度（0.0）で実行
- **マルチプロバイダー対応**: OpenAIとGoogle Gemini APIの両方をサポート
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し

### システム機能
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **JSON出力**: 生成結果と評価結果をそれぞれJSON形式でファイルに保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_7/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── config.py                      # 設定管理（API キー読み込み）
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # メインエントリーポイント（CLIとLLM-as-a-Judge統合）
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                   # キャラクターデータモデル定義
│   │   └── llm_as_a_judge_model.py    # LLM-as-a-Judge評価モデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── prompt.py                  # キャラクター生成プロンプト
│   │   └── llm_as_a_judge_prompt.py   # LLM-as-a-Judge評価プロンプト
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py             # LLMリクエスト処理（統合ワークフロー）
│       └── llm_as_a_judge.py          # LLM-as-a-Judge評価サービス
├── outputs/                            # 生成結果と評価結果の保存先（自動作成）
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── README.md                           # このファイル
└── CLAUDE.md                           # コンセプト説明（日本語）
```

### アーキテクチャ

このプロジェクトは、以下の多層アーキテクチャで構成されています：

```
┌────────────────────────────────────────────────┐
│         CLI Layer (main.py)                    │
│  - コマンドライン引数解析                       │
│  - 生成と評価の統合ワークフロー                 │
│  - 出力ディレクトリ管理                         │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│      Business Logic Layer                      │
│  ┌──────────────────────────────────────────┐  │
│  │  生成サービス (request_llm.py)           │  │
│  │  - request_openai()                      │  │
│  │  - request_gemini()                      │  │
│  │  - request_with_judge() ★統合機能       │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  評価サービス (llm_as_a_judge.py)        │  │
│  │  - judge_with_openai()                   │  │
│  │  - judge_with_gemini()                   │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  プロンプト生成                           │  │
│  │  - make_prompt() (キャラクター生成)      │  │
│  │  - make_judge_prompt() (評価)            │  │
│  │  - make_custom_judge_prompt() (カスタム) │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  データモデル                             │  │
│  │  - CharacterRequest/Response             │  │
│  │  - JudgeRequest/Response                 │  │
│  │  - EvaluationCriterion                   │  │
│  └──────────────────────────────────────────┘  │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│      Infrastructure Layer                      │
│  - 設定管理 (config.py)                        │
│  - ログ管理 (logger.py)                        │
│  - LLMクライアント (llm_client.py)             │
│  - 外部API (OpenAI, Gemini)                    │
└────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. LLM-as-a-Judge データモデル (`src/model/llm_as_a_judge_model.py`)

評価に関連するデータ構造を定義します：

```python
class EvaluationScore(IntEnum):
    """評価スコア 1-5"""
    COMPLETELY_INAPPROPRIATE = 1
    POOR = 2
    ACCEPTABLE = 3
    GOOD = 4
    PERFECT = 5

class EvaluationCriterion(BaseModel):
    """個別の評価基準の結果"""
    criterion_name: str        # 評価基準名
    score: EvaluationScore     # スコア（1-5）
    reasoning: str             # スコアの理由

class JudgeRequest(BaseModel):
    """評価リクエスト"""
    question: str              # 元の質問・プロンプト
    response: str              # 評価対象の応答
    context: str | None        # オプションの参照情報（RAG評価用）

class JudgeResponse(BaseModel):
    """評価結果"""
    evaluations: list[EvaluationCriterion]  # 各基準の評価
    overall_score: float                     # 総合スコア（1.0-5.0）
    summary: str                             # 評価の要約

    def is_passing(self, threshold: float = 3.0) -> bool:
        """品質閾値をクリアしているか判定"""
        return self.overall_score >= threshold
```

**ポイント**:
- `EvaluationScore`で1-5の評価スケールを型安全に管理
- `JudgeRequest`にオプションの`context`フィールドを持たせることでRAG評価にも対応
- `is_passing()`メソッドで品質ゲーティング機能を提供

#### 2. 評価プロンプト生成 (`src/prompt/llm_as_a_judge_prompt.py`)

評価用のプロンプトを動的に生成します：

```python
def make_judge_prompt(request: JudgeRequest) -> list:
    """標準的な3基準評価プロンプトを生成"""
    params = JudgeResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    evaluation_content = f"""以下の質問と回答を評価してください。

【質問】
{request.question}

【回答】
{request.response}
"""

    if request.context:
        evaluation_content += f"""
【参照情報】
{request.context}
"""

    return [
        {
            "role": "system",
            "content": f"""あなたは優秀なレビュアーです。
提示された質問と回答を読み、以下の評価軸について1から5の5段階で評価してください。

【評価軸】
1. 正確性 (accuracy): 回答が質問に対して正確かつ事実として正しいか
2. 網羅性 (comprehensiveness): 質問に対して必要な情報が十分に含まれているか
3. 明瞭さ (clarity): 回答が理解しやすく、適切な表現で書かれているか

評価結果は以下のJSON構造で出力してください：
{param_dump}
"""
        },
        {
            "role": "user",
            "content": evaluation_content
        }
    ]
```

**ポイント**:
- 3つの標準評価基準（正確性、網羅性、明瞭さ）を定義
- モデルから自動的にスキーマ情報を抽出してプロンプトに埋め込み
- `context`がある場合は参照情報として含める（RAG評価用）

#### 3. 評価サービス (`src/service/llm_as_a_judge.py`)

OpenAIとGeminiを使った評価実装：

```python
async def judge_with_openai(
    judge_request: JudgeRequest,
    model: OpenAIModel,
) -> JudgeResponse:
    """OpenAIを使用して評価"""
    prompt = make_judge_prompt(judge_request)

    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=JudgeResponse,
        temperature=0.0,  # 一貫した評価のため低温度
    )

    return result.choices[0].message.parsed

async def judge_with_gemini(
    judge_request: JudgeRequest,
    model: GeminiModel,
) -> JudgeResponse:
    """Geminiを使用して評価"""
    prompt = make_judge_prompt(judge_request)

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=JudgeResponse,
            temperature=0.0,  # 一貫した評価のため低温度
        ),
    )

    return result.parsed
```

**特徴**:
- `temperature=0.0`で評価の一貫性を確保
- 構造化出力により確実にJSONフォーマットで評価結果を取得
- 両プロバイダーで同一のインターフェースを提供

#### 4. 統合ワークフロー (`src/service/request_llm.py`)

生成と評価を統合した関数：

```python
async def request_with_judge(
    prompt: list,
    model: OpenAIModel | GeminiModel,
    provider: str,
    judge_model: OpenAIModel | GeminiModel | None = None,
    judge_provider: str | None = None,
) -> tuple[CharacterResponse, JudgeResponse]:
    """
    キャラクター生成と評価を一括実行

    クロスプロバイダー評価をサポート：
    - judge_modelとjudge_providerを指定すると異なるプロバイダーで評価
    - 指定しない場合は生成と同じモデル/プロバイダーで評価
    """
    # ステップ1: キャラクター生成
    if provider == "openai":
        character_response = await request_openai(prompt=prompt, model=model)
    elif provider == "gemini":
        character_response = await request_gemini(prompt=prompt, model=model)

    # ステップ2: 評価リクエストの作成
    judge_request = JudgeRequest(
        question=user_prompt,
        response=character_response.model_dump_json(indent=2),
        context=None
    )

    # ステップ3: 評価実行
    if judge_provider == "openai":
        judge_response = await judge_with_openai(judge_request, judge_model)
    elif judge_provider == "gemini":
        judge_response = await judge_with_gemini(judge_request, judge_model)

    return character_response, judge_response
```

**ポイント**:
- 生成と評価を1つの関数で完結
- クロスプロバイダー評価をサポート
- 生成結果をJSON化して評価リクエストに含める

#### 5. CLI統合 (`src/main.py`)

コマンドラインから評価機能を利用：

```python
@click.command()
@click.option("--gender", "-g", ...)
@click.option("--age", "-a", ...)
@click.option("--llm-provider", "-lp", ...)
@click.option("--model", "-m", ...)
@click.option("--judge-provider", "-jp", required=False)  # オプション
@click.option("--judge-model", "-jm", required=False)     # オプション
async def main(
    gender: Gender,
    age: int,
    llm_provider: LLMProvider,
    model: str,
    judge_provider: LLMProvider | None = None,
    judge_model: str | None = None,
):
    # 常にLLM-as-a-Judgeワークフローを使用
    character_result, judge_result = await request_with_judge(
        prompt=prompt,
        model=model,
        provider=llm_provider.value,
        judge_model=judge_model,
        judge_provider=judge_provider.value if judge_provider else None,
    )

    # 両方の結果を保存
    character_result.save_as_json(character_file_path)
    judge_result.save_as_json(judge_file_path)

    # スコアチェック
    if not judge_result.is_passing():
        logger.warning("品質閾値を下回っています (3.0/5.0)")
```

**特徴**:
- すべての実行で自動的に評価を実行
- オプションで異なるプロバイダー/モデルを評価に使用可能
- 品質閾値チェックと警告機能

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

#### 基本的な使い方（同じプロバイダーで生成と評価）

```bash
# Geminiで生成し、Geminiで評価
uv run python -m src.main -g female -a 25 -lp gemini -m gemini-2.5-flash

# OpenAIで生成し、OpenAIで評価
uv run python -m src.main -g female -a 25 -lp openai -m gpt-4o-mini
```

#### クロスプロバイダー評価（推奨）

異なるプロバイダーで生成と評価を行うことで、より客観的な評価が可能になります：

```bash
# Geminiで生成、OpenAIで評価
uv run python -m src.main \
  -g female -a 25 \
  -lp gemini -m gemini-2.5-flash \
  -jp openai -jm gpt-4o-mini

# OpenAIで生成、Geminiで評価
uv run python -m src.main \
  -g male -a 40 \
  -lp openai -m gpt-4o \
  -jp gemini -jm gemini-2.5-pro
```

#### 追加指示の指定

```bash
uv run python -m src.main \
  -g female -a 30 \
  -ai "SF小説の主人公として適したキャラクターを生成してください。" \
  -lp gemini -m gemini-2.5-flash \
  -jp openai -jm gpt-4o-mini
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -g, --gender [FEMALE|MALE]      キャラクターの性別 [required]
  -a, --age INTEGER RANGE         キャラクターの年齢 [0<=x<=100; required]
  -ai, --additional-instructions TEXT
                                  追加の生成指示
  -lp, --llm-provider [OPENAI|GEMINI]
                                  生成に使用するLLMプロバイダー [required]
  -m, --model [...]               生成に使用するモデル [required]
  -od, --output-directory PATH    出力ディレクトリ
  -jp, --judge-provider [OPENAI|GEMINI]
                                  評価に使用するLLMプロバイダー（省略時は生成と同じ）
  -jm, --judge-model [...]        評価に使用するモデル（省略時は生成と同じ）
  --help                          ヘルプを表示
```

### 出力例

実行すると、2つのJSONファイルが生成されます：

#### 1. キャラクターファイル

**ファイル名**: `outputs/gemini_character_a1b2c3d4e5f6.json`

```json
{
    "first_name": "サラ",
    "last_name": "コンラッド",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "好奇心旺盛",
            "description": "未知の世界や技術に強い興味を持つ探究心の塊"
        },
        {
            "short_personality": "冷静沈着",
            "description": "危機的状況でも論理的に判断できる思考力"
        },
        {
            "short_personality": "正義感が強い",
            "description": "弱者を守り、不正を許さない強い使命感"
        }
    ]
}
```

#### 2. 評価ファイル

**ファイル名**: `outputs/openai_judge_a1b2c3d4e5f6.json`（クロスプロバイダー評価の場合）

```json
{
    "evaluations": [
        {
            "criterion_name": "accuracy",
            "score": 5,
            "reasoning": "キャラクター設定が論理的で矛盾がなく、SF小説の主人公として適切です。"
        },
        {
            "criterion_name": "comprehensiveness",
            "score": 4,
            "reasoning": "基本的な性格特性は十分ですが、背景設定があればより良いでしょう。"
        },
        {
            "criterion_name": "clarity",
            "score": 5,
            "reasoning": "各性格特性が明確に記述されており、理解しやすいです。"
        }
    ],
    "overall_score": 4.67,
    "summary": "全体的に高品質なキャラクター設定です。SF小説の主人公として適切で、個性が明確です。"
}
```

#### 実行ログ例

```
[2025-10-18 14:30:00] [INFO] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: SF小説の主人公として適したキャラクターを生成してください。

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: openai / gpt-4o-mini
Output directory: outputs

[2025-10-18 14:30:01] [INFO] Step 1: Generating character...
[2025-10-18 14:30:03] [INFO] Character generation completed.
[2025-10-18 14:30:03] [INFO] Step 2: Evaluating character with LLM-as-a-Judge...
[2025-10-18 14:30:03] [INFO] Requesting judgment from OpenAI model: gpt-4o-mini
[2025-10-18 14:30:05] [INFO] Judgment completed. Overall score: 4.67/5.0
[2025-10-18 14:30:05] [INFO] Character file saved to outputs/gemini_character_a1b2c3d4e5f6.json
[2025-10-18 14:30:05] [INFO] Judge evaluation saved to outputs/openai_judge_a1b2c3d4e5f6.json
[2025-10-18 14:30:05] [INFO] Overall evaluation score: 4.67/5.0
```

品質閾値を下回った場合の警告例：
```
[2025-10-18 14:30:05] [WARNING] The generated character did not meet the quality threshold (3.0/5.0)
```

### テスト方法

現在、このセクションにはユニットテストは含まれていません。手動テストは以下の方法で行います：

#### 1. 基本機能のテスト

```bash
# 同じプロバイダーで生成と評価
uv run python -m src.main -g female -a 25 -lp gemini -m gemini-2.5-flash -od test_outputs
```

期待される動作：
- `test_outputs`ディレクトリが作成される
- `gemini_character_XXXXXXXX.json`形式のファイルが生成される
- `gemini_judge_XXXXXXXX.json`形式のファイルが生成される
- 両方のJSONファイルが対応するスキーマに準拠している

#### 2. クロスプロバイダー評価のテスト

```bash
# Geminiで生成、OpenAIで評価
uv run python -m src.main \
  -g male -a 30 \
  -lp gemini -m gemini-2.5-flash \
  -jp openai -jm gpt-4o-mini \
  -od test_outputs
```

期待される動作：
- キャラクターファイル: `gemini_character_XXXXXXXX.json`
- 評価ファイル: `openai_judge_XXXXXXXX.json`
- 評価ファイルのプレフィックスが評価プロバイダーと一致

#### 3. 評価結果の検証

生成された評価結果が正しい構造を持っているか確認：

```bash
# jqを使用してJSONを検証
cat test_outputs/openai_judge_*.json | jq .

# Pythonで評価結果を読み込みテスト
python -c "
from src.model.llm_as_a_judge_model import JudgeResponse
import json
import glob

judge_file = glob.glob('test_outputs/*_judge_*.json')[0]
with open(judge_file) as f:
    data = json.load(f)
    judge_response = JudgeResponse(**data)
    print(f'Overall Score: {judge_response.overall_score:.2f}/5.0')
    print(f'Passing: {judge_response.is_passing()}')
    for eval in judge_response.evaluations:
        print(f'  {eval.criterion_name}: {eval.score}/5')
"
```

#### 4. 異なる組み合わせのテスト

推奨されるクロスプロバイダー組み合わせをテスト：

```bash
# パターン1: Gemini Flash → GPT-4o Mini
uv run python -m src.main -g female -a 25 -lp gemini -m gemini-2.5-flash -jp openai -jm gpt-4o-mini

# パターン2: GPT-4o → Gemini Pro
uv run python -m src.main -g male -a 40 -lp openai -m gpt-4o -jp gemini -jm gemini-2.5-pro

# パターン3: Gemini Pro → GPT-4o
uv run python -m src.main -g female -a 30 -lp gemini -m gemini-2.5-pro -jp openai -jm gpt-4o
```

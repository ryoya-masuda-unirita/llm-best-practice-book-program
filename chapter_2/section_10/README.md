# Chapter 2 Section 10: プロンプトの単体テスト

## 概要

このプロジェクトは、**プロンプトの単体テスト** の実装を示すサンプルコードです。LLM（大規模言語モデル）に与えるプロンプトの振る舞いを体系的に検証し、品質と安定性を継続的に保証するための設計プラクティスを実践します。

プロンプトの変更がシステム全体の出力に与える影響を自動的に検証する仕組みを導入することで、意図しない品質劣化（リグレッション）を早期に検出し、LLMシステムの信頼性を高めることができます。**LLM-as-a-Judge** パターンを活用し、別のLLMに出力品質を評価させることで、高度な品質検証を実現しています。

キャラクター生成のユースケースを通じて、プロンプトの構造検証、出力品質評価、リグレッション検出といった実践的なテスト手法を学ぶことができます。

## 機能

### コアの機能

- **プロンプトユニットテスト**: pytestベースの体系的なプロンプト品質検証
- **LLM-as-a-Judge**: 別のLLMを用いた自動品質評価システム
- **構造化出力**: PydanticモデルによるAPI応答形式の型安全性保証
- **マルチプロバイダー対応**: OpenAI、Google Gemini、Anthropic APIの3つのプロバイダーをサポート
- **品質スコアリング**: 5段階評価による定量的な品質測定

### テスト機能

- **構造検証テスト**: プロンプトが必須フィールドを含むことを確認
- **品質閾値テスト**: 生成結果が最低品質基準を満たすことを保証
- **リグレッション検出テスト**: プロンプト変更による品質劣化を検出
- **代表的入力テスト**: 3-5個の重要なユースケースをカバー
- **カスタム評価基準**: ドメイン固有の要件に対応した評価

### その他の機能

- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **CLIインターフェース**: Clickライブラリによる柔軟なコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **詳細なログ出力**: 実行状況の可視化
- **JSON出力**: 生成結果と評価結果をJSON形式で保存

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_8/
├── src/
│   ├── __init__.py                    # パッケージ初期化
│   ├── config.py                      # 設定管理（APIキー読み込み）
│   ├── logger.py                      # ロギング設定
│   ├── main.py                        # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py              # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                   # キャラクターモデル定義
│   │   └── llm_as_a_judge_model.py    # Judge評価モデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── prompt.py                  # キャラクター生成プロンプト
│   │   └── llm_as_a_judge_prompt.py   # Judge評価プロンプト
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py             # LLMリクエスト処理
│       └── llm_as_a_judge.py          # Judge評価サービス
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # pytestフィクスチャ定義
│   ├── test_prompt_unit_testing.py    # プロンプトユニットテスト
│   └── test_llm_as_a_judge.py         # Judge機能テスト
├── outputs/                            # 生成結果の保存先（自動作成）
├── .envrc.example                      # 環境変数設定のサンプル
├── pyproject.toml                      # プロジェクト依存関係
├── pytest.ini                          # pytest設定ファイル
├── Makefile                            # 開発用コマンド
├── README.md                           # このファイル
└── CLAUDE.md                           # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、以下の3層アーキテクチャ + テスト層で構成されています：

```
┌─────────────────────────────────────────────────┐
│         CLI Layer (main.py)                     │
│   - コマンドライン引数解析                      │
│   - 生成・評価ワークフロー制御                  │
│   - 出力ディレクトリ管理                        │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Business Logic Layer                       │
│  - プロンプト生成 (prompt.py)                   │
│  - Judge評価プロンプト (llm_as_a_judge_prompt) │
│  - LLMクライアント管理 (llm_client.py)         │
│  - リクエスト処理 (request_llm.py)             │
│  - Judge評価サービス (llm_as_a_judge.py)       │
│  - データモデル (model.py, judge_model.py)     │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      Infrastructure Layer                       │
│  - 設定管理 (config.py)                         │
│  - ログ管理 (logger.py)                         │
│  - 外部API (OpenAI, Gemini, Anthropic)          │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│      Test Layer (tests/)                        │
│  - プロンプト構造検証テスト                     │
│  - 出力品質テスト                               │
│  - リグレッション検出テスト                     │
│  - 代表的入力テスト                             │
│  - Judge機能テスト                              │
└─────────────────────────────────────────────────┘
```

### 実装の詳細

#### 1. データモデル (`src/model/`)

##### キャラクターモデル (`model.py`)

Pydanticを使用して、厳密に型付けされたデータモデルを定義します：

```python
class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"

class CharacterRequest(BaseModel):
    gender: Gender
    age: int  # 0-100
    additional_instructions: str

class CharacterResponse(BaseModel):
    first_name: str
    last_name: str
    gender: Gender
    age: int  # 0-100
    personalities: list[CharacterPersonality]  # 3つの性格特性
```

##### Judge評価モデル (`llm_as_a_judge_model.py`)

LLM-as-a-Judgeパターンの評価結果を表現するモデル：

```python
class EvaluationScore(IntEnum):
    COMPLETELY_INAPPROPRIATE = 1  # 完全に不適切
    POOR = 2                      # 不十分
    ACCEPTABLE = 3                # 許容範囲
    GOOD = 4                      # 良好
    PERFECT = 5                   # 完璧

class EvaluationCriterion(BaseModel):
    criterion_name: str    # 評価基準名
    score: EvaluationScore # スコア（1-5）
    reasoning: str         # 評価の根拠

class JudgeResponse(BaseModel):
    evaluations: list[EvaluationCriterion]  # 各基準の評価
    overall_score: float                     # 総合スコア
    summary: str                             # 評価サマリー

    def is_passing(self, threshold: float = 3.0) -> bool:
        """品質閾値を超えているかチェック"""
        return self.overall_score >= threshold
```

**ポイント**:
- 5段階評価で定量的な品質測定を実現
- `is_passing()`メソッドで品質閾値判定を簡潔に実装
- 評価の根拠（reasoning）を保持し、説明可能性を確保

#### 2. プロンプト生成 (`src/prompt/`)

##### キャラクター生成プロンプト (`prompt.py`)

```python
def make_prompt(character_request: CharacterRequest) -> list:
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    return [
        {
            "role": "system",
            "content": f"""あなたは創造的なキャラクタージェネレーターです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}
..."""
        },
        {
            "role": "user",
            "content": f"""性別: {character_request.gender.value}
年齢: {character_request.age}
追加指示: {character_request.additional_instructions}"""
        }
    ]
```

##### Judge評価プロンプト (`llm_as_a_judge_prompt.py`)

```python
def make_judge_prompt(request: JudgeRequest) -> list:
    """デフォルトの評価基準（accuracy, comprehensiveness, clarity）で評価"""
    ...

def make_custom_judge_prompt(
    request: JudgeRequest,
    criteria: list[dict]
) -> list:
    """カスタム評価基準で評価（ドメイン固有要件に対応）"""
    ...
```

**ポイント**:
- スキーマ情報をプロンプトに埋め込み、出力の一貫性を確保
- デフォルト評価基準とカスタム評価基準の両方をサポート
- 評価プロンプトもバージョン管理対象とし、品質基準を明確化

#### 3. Judge評価サービス (`src/service/llm_as_a_judge.py`)

```python
async def judge_with_openai(
    judge_request: JudgeRequest,
    model: OpenAIModel
) -> JudgeResponse:
    """OpenAI APIを使用してLLM-as-a-Judge評価を実行"""
    prompt = make_openai_judge_prompt(judge_request)

    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=JudgeResponse,
    )
    return result.output_parsed

async def judge_with_gemini(
    judge_request: JudgeRequest,
    model: GeminiModel
) -> JudgeResponse:
    """Gemini APIを使用してLLM-as-a-Judge評価を実行"""
    system_prompt, user_prompt = make_gemini_judge_prompt(judge_request)

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=JudgeResponse,
            temperature=0.0,
        ),
    )
    return result.parsed

async def judge_with_anthropic(
    judge_request: JudgeRequest,
    model: AnthropicModel
) -> JudgeResponse:
    """Anthropic APIを使用してLLM-as-a-Judge評価を実行"""
    prompt = make_anthropic_judge_prompt(judge_request)

    result = await anthropic_client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt,
        output_format=JudgeResponse,
    )
    return result.parsed_output
```

**特徴**:
- `temperature=0.0`で評価の一貫性を確保（Geminiのみ設定可能）
- 構造化出力で評価結果を確実にパース
- マルチプロバイダー対応（OpenAI、Gemini、Anthropic）で柔軟な評価環境を提供

#### 4. 統合ワークフロー (`src/service/request_llm.py`)

```python
async def request_with_judge(
    character_request: CharacterRequest,
    model: OpenAIModel | GeminiModel | AnthropicModel,
    provider: str,
    judge_model: OpenAIModel | GeminiModel | AnthropicModel | None = None,
    judge_provider: str | None = None,
) -> tuple[CharacterResponse, JudgeResponse]:
    """
    Step 1: キャラクター生成
    Step 2: LLM-as-a-Judgeによる品質評価

    Returns:
        (生成結果, 評価結果)のタプル
    """
    ...
```

**ポイント**:
- 生成と評価を1つのワークフローで実行
- 生成モデルと評価モデルを独立して指定可能
- 両方の結果を返すことで、品質検証と出力取得を同時に実現

#### 5. テスト実装 (`tests/`)

##### プロンプト構造検証テスト

```python
class TestCharacterPromptStructure:
    """プロンプトが正しい構造を持つことを検証"""

    def test_prompt_includes_required_fields(self, sample_character_request):
        """必須フィールドがプロンプトに含まれているか"""
        prompt = make_prompt(sample_character_request)
        system_content = prompt[0]["content"]

        assert "first_name" in system_content
        assert "last_name" in system_content
        assert "gender" in system_content
        assert "age" in system_content
        assert "personalities" in system_content
```

##### 品質閾値テスト

```python
class TestCharacterOutputQuality:
    """LLM-as-a-Judgeを使用した品質検証"""

    @pytest.mark.asyncio
    async def test_generated_character_meets_quality_threshold(
        self,
        sample_character_response,
        sample_judge_response
    ):
        """生成されたキャラクターが品質基準を満たすか"""
        judge_response = await judge_with_openai(...)

        assert judge_response.is_passing(threshold=3.0)
        assert judge_response.overall_score >= 4.0
```

##### リグレッション検出テスト

```python
class TestRegressionDetection:
    """プロンプト変更による品質劣化を検出"""

    @pytest.mark.asyncio
    async def test_output_contains_all_required_fields(
        self,
        sample_character_response
    ):
        """すべての必須フィールドが出力に含まれているか

        このテストが失敗した場合、プロンプトの変更により
        必須フィールドが欠落する可能性がある
        """
        response_dict = sample_character_response.model_dump()

        assert "first_name" in response_dict
        assert "last_name" in response_dict
        assert len(response_dict["personalities"]) == 3
```

##### 代表的入力テスト

```python
class TestRepresentativeInputs:
    """3-5個の代表的なユースケースをテスト"""

    @pytest.mark.asyncio
    async def test_young_female_fantasy_character(self):
        """テストケース1: 若い女性ファンタジーキャラクター"""
        request = CharacterRequest(
            gender=Gender.FEMALE,
            age=25,
            additional_instructions="Generate a wizard from a fantasy world."
        )
        prompt = make_prompt(request)
        # 検証...

    @pytest.mark.asyncio
    async def test_elderly_male_realistic_character(self):
        """テストケース2: 高齢男性現実的キャラクター"""
        ...
```

**ポイント**:
- 最初から全ケースを網羅せず、重要な3-5個からスタート
- リグレッションテストは、プロンプト変更時に失敗することで問題を検出
- モックを活用し、API呼び出しコストを削減

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1
- **開発依存ライブラリ**:
  - pytest>=8.4.2
  - pytest-asyncio>=1.2.0
  - pytest-mock>=3.15.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
pip install -e ".[dev]"  # テスト用依存関係も含む
```

### 使用方法、実行方法

#### メインプログラムの実行

キャラクター生成とLLM-as-a-Judge評価を実行します：

##### 基本的な使い方

```bash
# Gemini APIを使用
uv run python -m src.main \
    --llm-provider gemini \
    --model gemini-2.5-flash \
    --gender female \
    --age 25

# OpenAI APIを使用
uv run python -m src.main \
    --llm-provider openai \
    --model gpt-4o-mini \
    --gender male \
    --age 30

# Anthropic APIを使用
uv run python -m src.main \
    --llm-provider anthropic \
    --model claude-sonnet-4-5 \
    --gender female \
    --age 28
```

##### 追加指示を指定

```bash
uv run python -m src.main \
    -lp openai \
    -m gpt-4o-mini \
    -g female \
    -a 25 \
    --additional-instructions "Generate a wizard from a fantasy world."
```

##### 異なるモデルで評価

```bash
# gpt-4o-miniで生成し、claude-sonnet-4-5で評価
uv run python -m src.main \
    -lp openai \
    -m gpt-4o-mini \
    -g female \
    -a 25 \
    --judge-provider anthropic \
    --judge-model claude-sonnet-4-5
```

##### 出力先の指定

```bash
uv run python -m src.main \
    -lp gemini \
    -m gemini-2.5-flash \
    -g male \
    -a 40 \
    --output-directory ./custom_output
```

##### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Options:
  -g, --gender [female|male]                    The gender of the character to generate.
  -a, --age INTEGER RANGE                       The age of the character to generate.  [0<=x<=100]
  -ai, --additional-instructions TEXT           Additional instructions for character generation.
  -lp, --llm-provider [openai|gemini|anthropic] The LLM provider to use.
  -m, --model TEXT                              The model to use for the request.
  -od, --output-directory PATH                  The directory to save output files.
  -jp, --judge-provider [openai|gemini|anthropic] The LLM provider to use for judgment.
  -jm, --judge-model TEXT                       The model to use for judgment.
  --help                                        Show this message and exit.
```

#### テストの実行

プロンプトのユニットテストを実行します：

##### すべてのテストを実行

```bash
# pytestで全テストを実行
uv run pytest

# より詳細な出力
uv run pytest -v

# ローカル変数を表示
uv run pytest -vl
```

##### 特定のテストクラスを実行

```bash
# プロンプト構造検証テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterPromptStructure -v

# 品質テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterOutputQuality -v

# リグレッション検出テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestRegressionDetection -v
```

##### 特定のテスト関数を実行

```bash
# 必須フィールド検証テストのみ
uv run pytest tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_includes_required_fields -v
```

##### マーカーでフィルタリング

```bash
# 非同期テストのみ
uv run pytest -m asyncio -v

# 統合テスト（スキップされているものも実行）
uv run pytest -m integration -v

# スモークテストのみ
uv run pytest -m smoke -v
```

##### テストをスキップせずに実行

```bash
# API呼び出しを伴うテストも含めて実行（コストに注意）
uv run pytest -v -k "not test_full_generation" --tb=short
```

##### テスト結果のサマリー

```bash
# すべてのテスト結果のサマリーを表示
uv run pytest -ra
```

### 出力例

#### キャラクター生成結果

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/abc123_gemini_character.json`

```json
{
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 28,
    "personalities": [
        {
            "short_personality": "内向的な思索家",
            "description": "常に深く物事を考え、静かな場所を好む。表面的な会話よりも、哲学的な議論に心を開く。"
        },
        {
            "short_personality": "完璧主義者",
            "description": "すべてのタスクに最高の基準を求め、細部にこだわる。しばしば自分自身に対して厳しすぎることがある。"
        },
        {
            "short_personality": "忠実な友人",
            "description": "一度信頼関係を築くと、どんな困難な状況でも友人を支える。約束を何よりも大切にする。"
        }
    ]
}
```

#### Judge評価結果

**ファイル名**: `outputs/abc123_gemini_judge.json`

```json
{
    "evaluations": [
        {
            "criterion_name": "accuracy",
            "score": 4,
            "reasoning": "指定された年齢（28歳）と性別（男性）が正確に反映されている。"
        },
        {
            "criterion_name": "comprehensiveness",
            "score": 5,
            "reasoning": "名前、性別、年齢、3つの性格特性がすべて含まれており、各性格には短い説明と詳細な説明の両方が記載されている。"
        },
        {
            "criterion_name": "clarity",
            "score": 4,
            "reasoning": "各性格特性が明確に記述されており、キャラクターの個性が理解しやすい。"
        }
    ],
    "overall_score": 4.33,
    "summary": "指定された条件を満たし、キャラクターの個性が適切に表現された高品質な生成結果。"
}
```

#### 実行ログ例

```
[2025-10-18 17:30:45] [INFO] [__main__] [main.py:102] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: Generate a wizard from a fantasy world.

Generation LLM: gemini / gemini-2.0-flash-exp
Judge LLM: gemini / gemini-2.0-flash-exp
Output directory: outputs

[2025-10-18 17:30:45] [INFO] [src.service.request_llm] [request_llm.py:59] Step 1: Generating character...
[2025-10-18 17:30:47] [INFO] [src.service.request_llm] [request_llm.py:67] Character generation completed.
[2025-10-18 17:30:47] [INFO] [src.service.request_llm] [request_llm.py:70] Step 2: Evaluating character with LLM-as-a-Judge...
[2025-10-18 17:30:49] [INFO] [src.service.request_llm] [request_llm.py:96] Evaluation completed. Overall score: 4.33/5.0
[2025-10-18 17:30:49] [INFO] [__main__] [main.py:144] Character file saved to outputs/abc123_gemini_character.json
[2025-10-18 17:30:49] [INFO] [__main__] [main.py:149] Judge evaluation saved to outputs/abc123_gemini_judge.json
[2025-10-18 17:30:49] [INFO] [__main__] [main.py:151] Overall evaluation score: 4.33/5.0
```

#### テスト実行結果例

```bash
$ uv run pytest -v

============================= test session starts ==============================
platform darwin -- Python 3.13.2, pytest-8.4.2
collected 25 items

tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_request_creation PASSED    [  4%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_response_structure PASSED  [  8%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_evaluation_score_values PASSED   [ 12%]
tests/test_llm_as_a_judge.py::TestJudgePrompts::test_make_judge_prompt_structure PASSED [ 16%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_includes_required_fields PASSED [ 20%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_specifies_personality_count PASSED [ 24%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_enforces_json_format PASSED [ 28%]
tests/test_prompt_unit_testing.py::TestCharacterOutputQuality::test_generated_character_meets_quality_threshold PASSED [ 32%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_young_female_fantasy_character PASSED [ 36%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_elderly_male_realistic_character PASSED [ 40%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_output_contains_all_required_fields PASSED [ 44%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_personality_traits_have_descriptions PASSED [ 48%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_output_is_valid_json_serializable PASSED [ 52%]

============================== 25 passed in 2.45s ===============================
```

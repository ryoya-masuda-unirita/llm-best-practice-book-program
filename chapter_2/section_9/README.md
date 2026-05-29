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
OPENAI_API_KEY=<your_openai_api_key_here>
GEMINI_API_KEY=<your_gemini_api_key_here>
ANTHROPIC_API_KEY=<your_anthropic_api_key_here>
```

2. **依存関係のインストール**

```bash
# uvを使用する
uv sync --all-packages
```

### 使用方法、実行方法

#### メインプログラムの実行

キャラクター生成とLLM-as-a-Judge評価を実行します。

##### 基本的な使い方

```bash
# Gemini APIを使用
uv run python -m src.main \
    --llm-provider GEMINI \
    --model GEMINI_2_5_FLASH \
    --gender FEMALE \
    --age 25

# OpenAI APIを使用
uv run python -m src.main \
    --llm-provider OPENAI \
    --model GPT_5_MINI \
    --gender MALE \
    --age 30

# Anthropic APIを使用
uv run python -m src.main \
    --llm-provider ANTHROPIC \
    --model CLAUDE_SONNET_4_6 \
    --gender FEMALE \
    --age 28
```

##### 追加指示を指定

```bash
uv run python -m src.main \
    -lp OPENAI \
    -m GPT_5_MINI \
    -g FEMALE \
    -a 25 \
    --additional-instructions "Generate a wizard from a fantasy world."
```

##### 異なるモデルで評価

```bash
# GPT_5_MINIで生成し、CLAUDE_SONNET_4_6で評価
uv run python -m src.main \
    -lp OPENAI \
    -m GPT_5_MINI \
    -g FEMALE \
    -a 25 \
    --judge-provider ANTHROPIC \
    --judge-model CLAUDE_SONNET_4_6
```

##### 出力先の指定

```bash
uv run python -m src.main \
    -lp GEMINI \
    -m GEMINI_2_5_FLASH \
    -g MALE \
    -a 40 \
    --output-directory ./outputs
```

##### ヘルプの表示

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -g, --gender [FEMALE|MALE]      The gender of the character to generate.
                                  [required]
  -a, --age INTEGER RANGE         The age of the character to generate.
                                  [0<=x<=100; required]
  -ai, --additional-instructions TEXT
                                  Additional instructions for character
                                  generation.
  -lp, --llm-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_5|GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_4_6|CLAUDE_OPUS_4_7]
                                  The model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -jp, --judge-provider [OPENAI|GEMINI|ANTHROPIC]
                                  The LLM provider to use for judgment
                                  (defaults to same as generation provider).
  -jm, --judge-model [GPT_5_5|GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO|GEMINI_2_5_PRO|GEMINI_2_5_FLASH|GEMINI_2_5_FLASH_LITE|CLAUDE_SONNET_4_6|CLAUDE_OPUS_4_7]
                                  The model to use for judgment (defaults to
                                  same as generation model).
  --help                          Show this message and exit.
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
    "first_name": "葵",
    "last_name": "山本",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "細部にこだわる完璧主義者",
            "description": "常に物事を最良の形で仕上げようと努力し、妥協を許しません。些細なミスも見逃さず、プロジェクトや日常生活において、並外れた注意力を発揮します。この完璧主義は、時には自己への厳しい要求となり、ストレスを感じることもありますが、その結果として生まれる品質は高く評価されています。"
        },
        {
            "short_personality": "内向的で思慮深い",
            "description": "人前で目立つことを好まず、深い思考に没頭する時間を大切にします。初対面の人には控えめに映るかもしれませんが、一度心を許した相手には、独自の視点から深い洞察を共有し、真摯な意見を述べます。行動する前によく考え、リスクと可能性を慎重に分析するタイプです。"
        },
        {
            "short_personality": "控えめながらも揺るぎない芯の強さ",
            "description": "普段は穏やかで協調性がありますが、自身の信念や倫理観に関わることに関しては、決して譲らない強い意志を持っています。不当な扱いや間違いに対しては、言葉を選びながらも毅然とした態度で臨み、正しいと思うことのために行動を起こす勇気を持ち合わせています。"
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
            "reasoning": "リクエストパラメータ（性別、年齢）に忠実に従っており、生成されたキャラクターの性格描写も矛盾なく、ユニークで興味深いものとなっているため、非常に正確であると評価できます。",
            "criterion_name": "accuracy",
            "score": 5
        },
        {
            "reasoning": "質問で求められている「ユニークで興味深いフィクションのキャラクター」と「詳細な性格」の両方を十分に満たしており、必要な情報がすべて含まれています。",
            "criterion_name": "comprehensiveness",
            "score": 5
        },
        {
            "reasoning": "回答はJSON形式で構造化されており、各性格の説明も簡潔かつ明瞭で、非常に理解しやすいです。不必要な専門用語も使われていません。",
            "criterion_name": "clarity",
            "score": 5
        }
    ],
    "overall_score": 5.0,
    "summary": "質問とリクエストパラメータに完全に合致し、ユニークで詳細なキャラクターが明瞭に生成されています。すべての評価軸において完璧な回答です。"
}
```

#### 実行ログ例

```
$ uv run python -m src.main \
    --llm-provider GEMINI \
    --model GEMINI_2_5_FLASH \
    --gender FEMALE \
    --age 25
[2026-01-18 11:59:20,101] [INFO] [__main__] [main.py:106] [main] Character Generation Request:
Gender: female
Age: 25
Additional Instructions: 

Generation LLM: gemini / gemini-2.5-flash
Judge LLM: gemini / gemini-2.5-flash
Output directory: outputs
[2026-01-18 11:59:20,101] [INFO] [src.service.request_llm] [request_llm.py:80] [request_with_judge] Generating prompt...
[2026-01-18 11:59:20,101] [INFO] [src.service.request_llm] [request_llm.py:83] [request_with_judge] Generating character...
[2026-01-18 11:59:22,784] [INFO] [src.service.request_llm] [request_llm.py:42] [request_gemini] sdk_http_response=HttpResponse(
  headers=<dict len=11>
) candidates=[Candidate(
  content=Content(
    parts=[
      Part(
        text="""{
  "first_name": "エリカ",
  "last_name": "佐藤",
  "gender": "female",
  "age": 25,
  "personalities": [
    {
      "short_personality": "好奇心旺盛",
      "description": "常に新しい知識や経験を求めている。見慣れない場所を探索したり、読んだことのないジャンルの本を読んだりすることに喜びを感じる。既成概念 にとらわれず、様々な視点から物事を考察しようとする。"
    },
    {
      "short_personality": "直感的",
      "description": "論理よりも自身の直感や感情に基づいて意思決定を行うことが多い。他人の微細な感情の動きや場の雰囲気を敏感に察知し、それらを判断の材料に する。時として大胆な行動に出るが、それが良い結果をもたらすこともある。"
    },
    {
      "short_personality": "内省的",
      "description": "物事を深く考えるタイプで、自分の感情や行動、周囲の状況について一人でじっくりと向き合う時間を大切にする。そのため、時には人との交流よ りも、内なる世界との対話を優先する傾向がある。思考の過程で得た洞察は、彼女の芸術的な表現の源となる。"
    }
  ]
}"""
      ),
    ],
    role='model'
  ),
  finish_reason=<FinishReason.STOP: 'STOP'>,
  index=0
)] create_time=None model_version='gemini-2.5-flash' prompt_feedback=None response_id='ikxsaf_qKJOk0-kP0YyCkAc' usage_metadata=GenerateContentResponseUsageMetadata(
  cache_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=341
    ),
  ],
  cached_content_token_count=341,
  candidates_token_count=296,
  prompt_token_count=388,
  prompt_tokens_details=[
    ModalityTokenCount(
      modality=<MediaModality.TEXT: 'TEXT'>,
      token_count=388
    ),
  ],
  thoughts_token_count=38,
  total_token_count=722
) automatic_function_calling_history=[] parsed=CharacterResponse(first_name='エリカ', last_name='佐藤', gender=<Gender.FEMALE: 'female'>, age=25, personalities=[CharacterPersonality(short_personality='好奇心旺盛', description='常に新しい知識や経験を求めている。見慣れない場所を探索したり、読んだことのないジャ ンルの本を読んだりすることに喜びを感じる。既成概念にとらわれず、様々な視点から物事を考察しようとする。'), CharacterPersonality(short_personality='直感的', description='論理よりも自身の直感や感情に基づいて意思決定を行うことが多い。他人の微細な感情の動きや場の雰囲気を敏感に察知し、それらを判断の材料にする。時として大胆な行動に出るが、それが良い結果をもたらすこともある。'), CharacterPersonality(short_personality='内省的', description='物事を深く考えるタイプで、自 分の感情や行動、周囲の状況について一人でじっくりと向き合う時間を大切にする。そのため、時には人との交流よりも、内なる世界との対話を優先する傾向がある。思考 の過程で得た洞察は、彼女の芸術的な表現の源となる。')])
[2026-01-18 11:59:22,785] [INFO] [src.service.request_llm] [request_llm.py:93] [request_with_judge] Character generation completed.
[2026-01-18 11:59:22,785] [INFO] [src.service.request_llm] [request_llm.py:95] [request_with_judge] Evaluating character with LLM-as-a-Judge...
[2026-01-18 11:59:22,785] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:51] [judge_with_gemini] Requesting judgment from Gemini model: gemini-2.5-flash
[2026-01-18 11:59:28,394] [INFO] [src.service.llm_as_a_judge] [llm_as_a_judge.py:65] [judge_with_gemini] Judgment completed. Overall score: 5.00/5.0
[2026-01-18 11:59:28,394] [INFO] [src.service.request_llm] [request_llm.py:128] [request_with_judge] Evaluation completed. Overall score: 5.00/5.0
[2026-01-18 11:59:28,394] [INFO] [__main__] [main.py:151] [main] Character file saved to outputs/432b62990b884887ae8b6c931f4bc7af_gemini_character.json
[2026-01-18 11:59:28,394] [INFO] [__main__] [main.py:157] [main] Judge evaluation saved to outputs/432b62990b884887ae8b6c931f4bc7af_gemini_judge.json
[2026-01-18 11:59:28,394] [INFO] [__main__] [main.py:158] [main] Overall evaluation score: 5.00/5.0
```

#### テスト実行結果例

```bash
$ uv run pytest -ra
=================================================================== test session starts ===================================================================
platform darwin -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0 -- /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_9
configfile: pytest.ini
testpaths: tests
plugins: mock-3.15.1, asyncio-1.2.0, anyio-4.11.0, langsmith-0.4.37
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 34 items                                                                                                                                        

tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_request_creation PASSED                                                                   [  2%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_request_with_context PASSED                                                               [  5%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_response_structure PASSED                                                                 [  8%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_evaluation_score_range PASSED                                                                   [ 11%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_response_is_passing_above_threshold PASSED                                                [ 14%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_response_is_passing_below_threshold PASSED                                                [ 17%]
tests/test_llm_as_a_judge.py::TestJudgeModels::test_judge_response_save_as_json PASSED                                                              [ 20%]
tests/test_llm_as_a_judge.py::TestJudgePrompts::test_make_judge_prompt_structure PASSED                                                             [ 23%]
tests/test_llm_as_a_judge.py::TestJudgePrompts::test_make_judge_prompt_contains_criteria PASSED                                                     [ 26%]
tests/test_llm_as_a_judge.py::TestJudgePrompts::test_make_judge_prompt_includes_question PASSED                                                     [ 29%]
tests/test_llm_as_a_judge.py::TestJudgePrompts::test_make_custom_judge_prompt PASSED                                                                [ 32%]
tests/test_llm_as_a_judge.py::TestJudgeService::test_judge_with_openai PASSED                                                                       [ 35%]
tests/test_llm_as_a_judge.py::TestJudgeService::test_judge_with_gemini PASSED                                                                       [ 38%]
tests/test_llm_as_a_judge.py::TestJudgeService::test_judge_evaluation_criteria_count PASSED                                                         [ 41%]
tests/test_llm_as_a_judge.py::TestJudgeService::test_judge_overall_score_calculation PASSED                                                         [ 44%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_includes_required_fields PASSED                                        [ 47%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_specifies_personality_count PASSED                                     [ 50%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_enforces_json_format PASSED                                            [ 52%]
tests/test_prompt_unit_testing.py::TestCharacterPromptStructure::test_prompt_includes_request_parameters PASSED                                     [ 55%]
tests/test_prompt_unit_testing.py::TestCharacterOutputQuality::test_generated_character_meets_quality_threshold PASSED                              [ 58%]
tests/test_prompt_unit_testing.py::TestCharacterOutputQuality::test_low_quality_output_detected PASSED                                              [ 61%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_young_female_fantasy_character PASSED                                             [ 64%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_elderly_male_realistic_character PASSED                                           [ 67%]
tests/test_prompt_unit_testing.py::TestRepresentativeInputs::test_young_adult_no_additional_instructions PASSED                                     [ 70%]
tests/test_prompt_unit_testing.py::TestCustomJudgeCriteria::test_fantasy_character_creativity PASSED                                                [ 73%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_output_contains_all_required_fields PASSED                                         [ 76%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_personality_traits_have_descriptions PASSED                                        [ 79%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_output_is_valid_json_serializable PASSED                                           [ 82%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_generated_names_are_not_empty PASSED                                               [ 85%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_age_matches_requested_age PASSED                                                   [ 88%]
tests/test_prompt_unit_testing.py::TestRegressionDetection::test_gender_matches_requested_gender PASSED                                             [ 91%]
tests/test_prompt_unit_testing.py::TestEndToEndWithJudge::test_full_generation_and_evaluation_workflow PASSED                                       [ 94%]
tests/test_prompt_unit_testing.py::TestEndToEndWithJudge::test_elderly_male_realistic_character_workflow PASSED                                     [ 97%]
tests/test_prompt_unit_testing.py::TestEndToEndWithJudge::test_minimal_instructions_workflow PASSED                                                 [100%]

=================================================================== 34 passed in 49.96s ===================================================================
/Users/shibuiyusuke/.pyenv/versions/3.13.2/lib/python3.13/asyncio/selector_events.py:869: ResourceWarning: unclosed transport <_SelectorSocketTransport closing fd=20>
  _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
ResourceWarning: Enable tracemalloc to get the object allocation traceback
/Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/.venv/lib/python3.13/site-packages/_pytest/unraisableexception.py:33: ResourceWarning: unclosed <socket.socket fd=23, family=2, type=1, proto=6, laddr=('192.168.3.7', 57407)>
  gc.collect()
ResourceWarning: Enable tracemalloc to get the object allocation traceback
/Users/shibuiyusuke/.pyenv/versions/3.13.2/lib/python3.13/asyncio/selector_events.py:869: ResourceWarning: unclosed transport <_SelectorSocketTransport closing fd=23>
  _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
ResourceWarning: Enable tracemalloc to get the object allocation traceback
/Users/shibuiyusuke/.pyenv/versions/3.13.2/lib/python3.13/asyncio/selector_events.py:869: ResourceWarning: unclosed transport <_SelectorSocketTransport closing fd=21>
  _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
ResourceWarning: Enable tracemalloc to get the object allocation traceback
/Users/shibuiyusuke/.pyenv/versions/3.13.2/lib/python3.13/asyncio/selector_events.py:869: ResourceWarning: unclosed transport <_SelectorSocketTransport closing fd=22>
  _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
ResourceWarning: Enable tracemalloc to get the object allocation traceback
```

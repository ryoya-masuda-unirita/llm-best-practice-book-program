# Chapter 2 Section 12: プロンプトを再利用するために分析する

LLMアプリケーションにおけるプロンプトを体系的に記録・分析し、再利用可能な知見として蓄積するシステムの実装例です。

## 概要

キャラクター生成を実例として、プロンプトのログ記録、評価、テンプレート化、分析の一連のワークフローを示します。

### 主な機能

1. **プロンプトログの記録**: すべてのLLM実行を詳細なメタデータと共に記録
2. **評価基準の定義**: タスクごとの成功/失敗の判定基準を設定
3. **テンプレートの自動生成**: 成功したプロンプトから再利用可能なテンプレートを作成
4. **アンチパターンの追跡**: 失敗パターンを記録し、将来の過ちを防ぐ
5. **検索とカタログ**: タグやカテゴリによるテンプレート検索
6. **分析とレポート**: プロンプトのパフォーマンス分析と改善提案
7. **コスト追跡**: API使用量とコストの分析


## アーキテクチャ

```
src/
├── model/                          # データモデル
│   ├── model.py                    # キャラクタージェネレーションのモデル
│   ├── prompt_log.py              # ログエントリ、評価基準、メタデータ
│   └── prompt_template.py         # テンプレートとアンチパターン
│
├── service/                        # ビジネスロジック
│   ├── prompt_storage.py          # ストレージ層(ファイルベース)
│   ├── prompt_analyzer.py         # 評価とパターン抽出
│   ├── prompt_catalog.py          # テンプレート検索・管理
│   ├── prompt_analytics.py        # 分析とレポート生成
│   ├── prompt_service.py          # 統合APIサービス
│   ├── template_engine.py         # Jinja2テンプレートエンジン
│   └── request_llm.py             # LLMリクエスト処理
│
├── client/                         # LLMクライアント
│   └── llm_client.py              # OpenAI APIクライアント
│
├── prompt/                         # プロンプト定義
│   └── prompt.py                  # プロンプト構造
│
├── examples/                       # 使用例
│   ├── basic_example.py           # 基本的な使い方
│   ├── integration_example.py     # 既存システムとの統合例
│   └── advanced_example.py        # 高度な分析とレポート生成
│
├── main.py                         # メインCLI
├── config.py                       # 設定管理
└── logger.py                       # ロギング設定

templates/                          # プロンプトテンプレート
├── character_generation.yaml      # キャラクター生成
├── email_casual.yaml              # カジュアルメール
├── email_formal.yaml              # フォーマルメール
└── product_description.yaml       # 商品説明

variables/                          # 変数ファイル
├── character_artist.yaml
├── character_detective.yaml
├── warrior.yaml
├── email_campaign_summer.yaml
├── email_campaign_winter.yaml
├── product_apparel.yaml
└── product_electronics.yaml
```

### ワークフロー

このシステムは、以下の継続的改善サイクルを実装しています：

```
1. 実行 (Execute)
   ↓
   プロンプトをLLMに送信し、応答を受け取る

2. 記録 (Log)
   ↓
   プロンプト、応答、メタデータを記録

3. 評価 (Evaluate)
   ↓
   事前定義された基準で結果を評価

4. 分析 (Analyze)
   ↓
   パターンを抽出し、成功/失敗を分類

5. 学習 (Learn)
   ↓
   成功 → テンプレート化
   失敗 → アンチパターン記録

6. 再利用 (Reuse)
   ↓
   テンプレートを検索・適用
   アンチパターンを回避

7. 最適化 (Optimize)
   ↓
   分析結果に基づき改善
   → 1に戻る
```

## 使い方

### インストール

```bash
# 依存関係のインストール
uv sync
```

#### 環境変数を設定:

```bash
cp .envrc.example .envrc
```

`.envrc` を編集し、OpenAIのAPIキーを設定:

```bash
OPENAI_API_KEY=<your_openai_api_key_here>
```

### 基本的な使用方法

```bash
$ uv run python -m src.main --help
Usage: python -m src.main [OPTIONS]

Options:
  -m, --model [GPT_5_4|GPT_5_4_MINI|GPT_5_4_NANO|GPT_5_2|GPT_5_1|GPT_5|GPT_5_MINI|GPT_5_NANO]
                                  The OpenAI model to use for the request.
                                  [required]
  -od, --output-directory PATH    The directory to save output files.
  -t, --template PATH             Template file path (relative to project root
                                  or absolute). Default:
                                  templates/character_generation.yaml
  -v, --variables PATH            Variables file path (relative to project
                                  root or absolute). If not specified, uses
                                  default values.
  --help                          Show this message and exit.
```

#### 実行コマンド

```bash
# デフォルト設定で実行
uv run python -m src.main -m GPT_5_4_MINI

# 特定の変数ファイルを使用
uv run python -m src.main -m GPT_5_4 -v variables/character_artist.yaml

# テンプレートと変数を両方指定
uv run python -m src.main -m GPT_5_4 -t templates/character_generation.yaml -v variables/warrior.yaml
```

#### 実行例

- テンプレートの利用例

```bash
$ uv run python -m src.main -m GPT_5_4 -t templates/character_generation.yaml -v variables/warrior.yaml
[2026-01-18 14:59:16,520] [INFO] [__main__] [main.py:87] [main] Model: gpt-5.4
Output directory: outputs
Template: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/templates/character_generation.yaml
Variables: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/variables/warrior.yaml
[2026-01-18 14:59:16,526] [INFO] [src.service.request_llm] [request_llm.py:146] [render_prompt_from_template] Using template: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/templates/character_generation.yaml
[2026-01-18 14:59:16,526] [INFO] [src.service.request_llm] [request_llm.py:147] [render_prompt_from_template] Variables: gender=male, age=25
[2026-01-18 14:59:20,386] [INFO] [__main__] [main.py:109] [main] File saved to outputs/openai_d0655efadf694c06ba76f508c3990bc5.json
```

- 出力ファイル例

```json
{
    "first_name": "葵",
    "last_name": "佐倉",
    "gender": "female",
    "age": 28,
    "personalities": [
        {
            "short_personality": "感受性が豊か",
            "description": "色や光、音や匂いの微細な変化に心を動かされやすく、その瞬間の感覚をキャンバスに留めようとする。人の表情や沈黙からも物語を読み取り、絵画のテーマに変えることで自己表現と他者理解を同時に果たす。"
        },
        {
            "short_personality": "情熱的",
            "description": "制作に対しては全身全霊で向き合い、集中すると時間や生活リズムを忘れて没頭する。愛情も怒りも創作エネルギーに変える傾向があり、作品には強い感情の温度が宿る。目標や信念に対しては妥協を嫌う。"
        },
        {
            "short_personality": "自由奔放で繊細",
            "description": "規則や慣習に縛られない生き方を好み、旅や即興的な制作を通して新しい表現を探求する。一方で批判や失敗には深く傷つきやすく、繊細な自己防衛本能から時に孤立を選ぶ。自由さと脆さを併せ持ち、それが独特の魅力と作品の深みを生む。"
        }
    ]
}
```

- Prompt logging & template creation 例

```bash

================================================================================
BASIC EXAMPLE: Prompt Logging and Template Creation
================================================================================

[2026-01-18 15:03:25,916] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:03:25,916] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:03:25,916] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:03:25,916] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:03:25,916] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService

Step 1: Executing prompt with character generation template...
--------------------------------------------------------------------------------
[2026-01-18 15:03:25,917] [INFO] [src.service.request_llm] [request_llm.py:146] [render_prompt_from_template] Using template: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/templates/character_generation.yaml
[2026-01-18 15:03:25,917] [INFO] [src.service.request_llm] [request_llm.py:147] [render_prompt_from_template] Variables: gender=male, age=25
✓ Generated character: Kael Thorne
  Gender: male
  Age: 25
  Personality: Brave

Step 2: Logging prompt execution...
--------------------------------------------------------------------------------
[2026-01-18 15:03:35,584] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 80e321095eba4a38acace8fbcf80296d
[2026-01-18 15:03:35,585] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 80e321095eba4a38acace8fbcf80296d
✓ Logged execution with ID: 80e321095eba4a38acace8fbcf80296d

Step 3: Evaluating the prompt result...
--------------------------------------------------------------------------------
[2026-01-18 15:03:35,587] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 80e321095eba4a38acace8fbcf80296d
[2026-01-18 15:03:35,587] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 80e321095eba4a38acace8fbcf80296d: success (score: 0.9566666666666667)
✓ Evaluation completed
  Overall score: 95.67%
  Status: success

Step 4: Creating reusable template from successful prompt...
--------------------------------------------------------------------------------
[2026-01-18 15:03:35,589] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: warrior_character_template (ID: 718852da1939421a9edf55c3c264f654)
[2026-01-18 15:03:35,589] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:116] [create_template_from_log] Created template 'warrior_character_template' of 718852da1939421a9edf55c3c264f654 from log 80e321095eba4a38acace8fbcf80296d
✓ Created template: warrior_character_template
  Template ID: 718852da1939421a9edf55c3c264f654
  Category: character_generation
  Success rate: 100.0%
  Tags: rpg, fantasy, character, warrior

Step 5: Searching for related templates...
--------------------------------------------------------------------------------
[2026-01-18 15:03:35,620] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:66] [search_templates] Search found 4 templates
✓ Found 4 template(s) matching criteria:
  - warrior_character_template (success rate: 100.0%)
  - warrior_character_template (success rate: 100.0%)
  - warrior_character_template (success rate: 100.0%)
  - warrior_character_template (success rate: 100.0%)

Step 6: Viewing catalog summary...
--------------------------------------------------------------------------------
✓ Catalog Summary:
  Total templates: 13
  Total anti-patterns: 3
  Total template uses: 28
  Average success rate: 94.9%

================================================================================
Basic workflow completed successfully!
================================================================================


================================================================================
BONUS: Template Reuse Demonstration
================================================================================

[2026-01-18 15:03:35,629] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:03:35,629] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:03:35,630] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:03:35,630] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:03:35,630] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService
✓ Found 3 recommended template(s):

1. warrior_character_template
   Description: Template for generating warrior-type RPG characters with consistent quality
   Success rate: 100.0%
   Average score: 0.96
   Required variables: gender, age
   Recommended models: gpt-5.4-mini
   Recommended temperature: 1.0

2. warrior_character_template
   Description: Template for generating warrior-type RPG characters with consistent quality
   Success rate: 100.0%
   Average score: 0.96
   Required variables: gender, age
   Recommended models: gpt-5.4-mini
   Recommended temperature: 1.0

3. warrior_character_template
   Description: Template for generating warrior-type RPG characters with consistent quality
   Success rate: 100.0%
   Average score: 0.96
   Required variables: gender, age
   Recommended models: gpt-5.4-mini
   Recommended temperature: 1.0

✓ Exported template 'warrior_character_template' for team sharing:
   Use cases: RPG character generation for fantasy game

================================================================================
Template reuse demonstration completed!
================================================================================


💡 Key Takeaways:
   1. Every prompt execution is logged with rich metadata
   2. Results are evaluated based on predefined criteria
   3. Successful prompts become reusable templates
   4. Templates can be searched and shared across the team
   5. This creates a knowledge base that improves over time
```

- Integration例

```bash
$ uv run python -m src.examples.integration_example
[2026-01-18 15:06:55,387] [INFO] [__main__] [integration_example.py:191] [log_configuration] Model: gpt-5.4
Output directory: outputs
Template: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/templates/character_generation.yaml
Variables: default
Logging: enabled
Auto-evaluate: disabled
[2026-01-18 15:06:55,387] [INFO] [src.service.request_llm] [request_llm.py:146] [render_prompt_from_template] Using template: /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/templates/character_generation.yaml
[2026-01-18 15:06:55,387] [INFO] [src.service.request_llm] [request_llm.py:147] [render_prompt_from_template] Variables: gender=male, age=25
[2026-01-18 15:06:58,781] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:06:58,781] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:06:58,781] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:06:58,781] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:06:58,781] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService
[2026-01-18 15:06:58,782] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: d97d157e170141b2865a11f059e8942e
[2026-01-18 15:06:58,782] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: d97d157e170141b2865a11f059e8942e
[2026-01-18 15:06:58,782] [INFO] [__main__] [integration_example.py:91] [log_execution] Logged execution: d97d157e170141b2865a11f059e8942e
[2026-01-18 15:06:58,782] [INFO] [__main__] [integration_example.py:205] [save_result] File saved to outputs/openai_c6943619d8554ebfbab162441997e06f.json

================================================================================
CHARACTER GENERATION RESULT
================================================================================
Name: Leo Venture
Gender: male
Age: 25
Personality: Adventurous
Description: Leo thrives on the thrill of adventure, always seeking out new experiences and uncharted territories...
================================================================================

✓ Execution logged: d97d157e170141b2865a11f059e8942e
```

- Complete Prompt Analysis and Continuous Improvement

```bash
$ uv run python -m src.examples.advanced_example   

================================================================================
ADVANCED EXAMPLE: Simulating 15 Agent Operations
================================================================================

[2026-01-18 15:08:31,787] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:31,787] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:31,788] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:08:31,788] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:08:31,788] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService
Running autonomous agent operations...
--------------------------------------------------------------------------------
[2026-01-18 15:08:31,788] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 59f4588c89e243c8bfeb3e063b60f727
[2026-01-18 15:08:31,788] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 59f4588c89e243c8bfeb3e063b60f727
[2026-01-18 15:08:31,790] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 59f4588c89e243c8bfeb3e063b60f727
[2026-01-18 15:08:31,790] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 59f4588c89e243c8bfeb3e063b60f727: success (score: 0.9135453113178529)
✓ Operation 1/15: PROD-004 - SUCCESS
[2026-01-18 15:08:31,892] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: ac04760456104f51a49d36e9474270f8
[2026-01-18 15:08:31,892] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: ac04760456104f51a49d36e9474270f8
[2026-01-18 15:08:31,894] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: ac04760456104f51a49d36e9474270f8
[2026-01-18 15:08:31,894] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log ac04760456104f51a49d36e9474270f8: failure (score: 0.28950046872533314)
✗ Operation 2/15: PROD-004 - FAILED
[2026-01-18 15:08:31,995] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 91603c67ee8b45baab7f98fdd3064333
[2026-01-18 15:08:31,996] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 91603c67ee8b45baab7f98fdd3064333
[2026-01-18 15:08:31,997] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 91603c67ee8b45baab7f98fdd3064333
[2026-01-18 15:08:31,997] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 91603c67ee8b45baab7f98fdd3064333: success (score: 0.9569941582902337)
✓ Operation 3/15: PROD-003 - SUCCESS
[2026-01-18 15:08:32,099] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 83b79ea6a7d04428a471caaf0393ea30
[2026-01-18 15:08:32,099] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 83b79ea6a7d04428a471caaf0393ea30
[2026-01-18 15:08:32,103] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 83b79ea6a7d04428a471caaf0393ea30
[2026-01-18 15:08:32,103] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 83b79ea6a7d04428a471caaf0393ea30: failure (score: 0.2386312032097476)
✗ Operation 4/15: PROD-005 - FAILED
[2026-01-18 15:08:32,204] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: cf5d7833adf04075949117f65b7291ab
[2026-01-18 15:08:32,204] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: cf5d7833adf04075949117f65b7291ab
[2026-01-18 15:08:32,206] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: cf5d7833adf04075949117f65b7291ab
[2026-01-18 15:08:32,206] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log cf5d7833adf04075949117f65b7291ab: success (score: 0.8821409275824084)
✓ Operation 5/15: PROD-002 - SUCCESS
[2026-01-18 15:08:32,309] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 407af06dd9b949de8ab8b76868760cec
[2026-01-18 15:08:32,309] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 407af06dd9b949de8ab8b76868760cec
[2026-01-18 15:08:32,311] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 407af06dd9b949de8ab8b76868760cec
[2026-01-18 15:08:32,311] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 407af06dd9b949de8ab8b76868760cec: success (score: 0.8865167198434561)
✓ Operation 6/15: PROD-004 - SUCCESS
[2026-01-18 15:08:32,413] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 4a03392ae2d94c9fa9f948f3d47d069c
[2026-01-18 15:08:32,413] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 4a03392ae2d94c9fa9f948f3d47d069c
[2026-01-18 15:08:32,415] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 4a03392ae2d94c9fa9f948f3d47d069c
[2026-01-18 15:08:32,415] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 4a03392ae2d94c9fa9f948f3d47d069c: success (score: 0.9255077965018407)
✓ Operation 7/15: PROD-001 - SUCCESS
[2026-01-18 15:08:32,517] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: eceaeff1f6084be9ba518953c45ed2f7
[2026-01-18 15:08:32,517] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: eceaeff1f6084be9ba518953c45ed2f7
[2026-01-18 15:08:32,518] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: eceaeff1f6084be9ba518953c45ed2f7
[2026-01-18 15:08:32,519] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log eceaeff1f6084be9ba518953c45ed2f7: failure (score: 0.2945617820590804)
✗ Operation 8/15: PROD-005 - FAILED
[2026-01-18 15:08:32,620] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 4785727152cd4a7f81e05bc90b7ebc95
[2026-01-18 15:08:32,620] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 4785727152cd4a7f81e05bc90b7ebc95
[2026-01-18 15:08:32,623] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 4785727152cd4a7f81e05bc90b7ebc95
[2026-01-18 15:08:32,623] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 4785727152cd4a7f81e05bc90b7ebc95: success (score: 0.868569868986313)
✓ Operation 9/15: PROD-001 - SUCCESS
[2026-01-18 15:08:32,724] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 22a909ae6f2d493ab10b651bd18be474
[2026-01-18 15:08:32,724] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 22a909ae6f2d493ab10b651bd18be474
[2026-01-18 15:08:32,730] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 22a909ae6f2d493ab10b651bd18be474
[2026-01-18 15:08:32,730] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 22a909ae6f2d493ab10b651bd18be474: success (score: 0.9557925912596615)
✓ Operation 10/15: PROD-005 - SUCCESS
[2026-01-18 15:08:32,831] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 98b5bd79f4244ad7a30f97ba04822243
[2026-01-18 15:08:32,831] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 98b5bd79f4244ad7a30f97ba04822243
[2026-01-18 15:08:32,833] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 98b5bd79f4244ad7a30f97ba04822243
[2026-01-18 15:08:32,833] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 98b5bd79f4244ad7a30f97ba04822243: failure (score: 0.2523567587884007)
✗ Operation 11/15: PROD-003 - FAILED
[2026-01-18 15:08:32,934] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: b168127887e54fdaba8d2880c3f5e5a4
[2026-01-18 15:08:32,934] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: b168127887e54fdaba8d2880c3f5e5a4
[2026-01-18 15:08:32,936] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: b168127887e54fdaba8d2880c3f5e5a4
[2026-01-18 15:08:32,936] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log b168127887e54fdaba8d2880c3f5e5a4: success (score: 0.91106496213293)
✓ Operation 12/15: PROD-004 - SUCCESS
[2026-01-18 15:08:33,037] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: e9c42039079742258cc12283b4cae9cc
[2026-01-18 15:08:33,037] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: e9c42039079742258cc12283b4cae9cc
[2026-01-18 15:08:33,039] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: e9c42039079742258cc12283b4cae9cc
[2026-01-18 15:08:33,039] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log e9c42039079742258cc12283b4cae9cc: success (score: 0.9448153839422299)
✓ Operation 13/15: PROD-004 - SUCCESS
[2026-01-18 15:08:33,140] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: fac4ef6423864158b4f75dcdc80e1fa5
[2026-01-18 15:08:33,140] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: fac4ef6423864158b4f75dcdc80e1fa5
[2026-01-18 15:08:33,147] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: fac4ef6423864158b4f75dcdc80e1fa5
[2026-01-18 15:08:33,147] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log fac4ef6423864158b4f75dcdc80e1fa5: failure (score: 0.26805003905071784)
✗ Operation 14/15: PROD-003 - FAILED
[2026-01-18 15:08:33,250] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 22ec7604f3a6431ab0f6b441a762ddcb
[2026-01-18 15:08:33,250] [INFO] [src.service.prompt_service] [prompt_service.py:93] [log_prompt_execution] Logged prompt execution: 22ec7604f3a6431ab0f6b441a762ddcb
[2026-01-18 15:08:33,253] [DEBUG] [src.service.prompt_storage] [prompt_storage.py:60] [save_log] Saved prompt log: 22ec7604f3a6431ab0f6b441a762ddcb
[2026-01-18 15:08:33,253] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:61] [evaluate_log] Evaluated log 22ec7604f3a6431ab0f6b441a762ddcb: failure (score: 0.2730879098465671)
✗ Operation 15/15: PROD-003 - FAILED

✓ Completed 15 operations:
  Successes: 9
  Failures: 6
  Success rate: 60.0%

================================================================================
STEP 2: Analyzing Patterns and Creating Templates
================================================================================

[2026-01-18 15:08:33,354] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,354] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,355] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:08:33,355] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:08:33,355] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService
Creating templates from successful patterns...
--------------------------------------------------------------------------------
[2026-01-18 15:08:33,362] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v1 (ID: dddd6c7c6d3548b0a930525ddec6053f)
[2026-01-18 15:08:33,362] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:116] [create_template_from_log] Created template 'inventory_demand_analysis_v1' of dddd6c7c6d3548b0a930525ddec6053f from log 59f4588c89e243c8bfeb3e063b60f727
✓ Created template: inventory_demand_analysis_v1
  Template ID: dddd6c7c6d3548b0a930525ddec6053f
  Recommended temperature: 0.3
[2026-01-18 15:08:33,365] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v2 (ID: 51d40c00581d4531b106c09f1fa0d302)
[2026-01-18 15:08:33,365] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:116] [create_template_from_log] Created template 'inventory_demand_analysis_v2' of 51d40c00581d4531b106c09f1fa0d302 from log 91603c67ee8b45baab7f98fdd3064333
✓ Created template: inventory_demand_analysis_v2
  Template ID: 51d40c00581d4531b106c09f1fa0d302
  Recommended temperature: 0.3
[2026-01-18 15:08:33,366] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v3 (ID: e2864bd45e604d1aa295eb1ea74e921e)
[2026-01-18 15:08:33,366] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:116] [create_template_from_log] Created template 'inventory_demand_analysis_v3' of e2864bd45e604d1aa295eb1ea74e921e from log cf5d7833adf04075949117f65b7291ab
✓ Created template: inventory_demand_analysis_v3
  Template ID: e2864bd45e604d1aa295eb1ea74e921e
  Recommended temperature: 0.3

Identifying anti-patterns from failures...
--------------------------------------------------------------------------------
[2026-01-18 15:08:33,367] [INFO] [src.service.prompt_storage] [prompt_storage.py:251] [save_antipattern] Saved anti-pattern: insufficient_data_pattern (ID: 4017c053864b44f29611e368d8f9a7f2)
[2026-01-18 15:08:33,367] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:210] [create_antipattern_from_log] Created anti-pattern 'insufficient_data_pattern' of 4017c053864b44f29611e368d8f9a7f2 from failed log ac04760456104f51a49d36e9474270f8
✓ Created anti-pattern: insufficient_data_pattern
  Pattern ID: 4017c053864b44f29611e368d8f9a7f2
  Severity: high
  Recommended fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.
[2026-01-18 15:08:33,367] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,367] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,368] [INFO] [src.service.prompt_storage] [prompt_storage.py:251] [save_antipattern] Saved anti-pattern: insufficient_data_pattern (ID: 4017c053864b44f29611e368d8f9a7f2)
[2026-01-18 15:08:33,368] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:239] [update_antipattern_occurrence] Updated anti-pattern 4017c053864b44f29611e368d8f9a7f2: occurrences=2
[2026-01-18 15:08:33,368] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,368] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_storage] [prompt_storage.py:251] [save_antipattern] Saved anti-pattern: insufficient_data_pattern (ID: 4017c053864b44f29611e368d8f9a7f2)
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:239] [update_antipattern_occurrence] Updated anti-pattern 4017c053864b44f29611e368d8f9a7f2: occurrences=3
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_storage] [prompt_storage.py:251] [save_antipattern] Saved anti-pattern: insufficient_data_pattern (ID: 4017c053864b44f29611e368d8f9a7f2)
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:239] [update_antipattern_occurrence] Updated anti-pattern 4017c053864b44f29611e368d8f9a7f2: occurrences=4
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,369] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,370] [INFO] [src.service.prompt_storage] [prompt_storage.py:251] [save_antipattern] Saved anti-pattern: insufficient_data_pattern (ID: 4017c053864b44f29611e368d8f9a7f2)
[2026-01-18 15:08:33,370] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:239] [update_antipattern_occurrence] Updated anti-pattern 4017c053864b44f29611e368d8f9a7f2: occurrences=5
[2026-01-18 15:08:33,370] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,370] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_storage] [prompt_storage.py:251] [save_antipattern] Saved anti-pattern: insufficient_data_pattern (ID: 4017c053864b44f29611e368d8f9a7f2)
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:239] [update_antipattern_occurrence] Updated anti-pattern 4017c053864b44f29611e368d8f9a7f2: occurrences=6
  Total occurrences recorded: 6

================================================================================
STEP 3: Generating Analytics and Insights
================================================================================

[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,371] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
Performance Summary:
--------------------------------------------------------------------------------
✓ Storage Statistics:
  Total logs: 70
  Total templates: 16
  Total anti-patterns: 4

✓ Success Rates by Category:
  character_generation: 80.0%
  data_extraction: 66.7%

✓ Model Performance:
  gpt-5.4:
    Total uses: 1
    Success rate: 0.0%
  gpt-5.4-mini:
    Total uses: 64
    Success rate: 68.8%
    Average score: 0.71
    Avg execution time: 1246ms
  gpt-5-mini:
    Total uses: 5
    Success rate: 80.0%
    Average score: 0.88

Cost Analysis:
--------------------------------------------------------------------------------
✓ Total API cost: $0.0079
  Input tokens: 3,240
  Output tokens: 12,376

  Cost by category:
    data_extraction: $0.0079

Template Usage Report:
--------------------------------------------------------------------------------
✓ Top templates by usage:
  1. inventory_demand_analysis_v3
     Uses: 6 | Success rate: 100.0%
     Average score: 0.87
  2. inventory_demand_analysis_v3
     Uses: 6 | Success rate: 66.7%
     Average score: 0.73
  3. inventory_demand_analysis_v2
     Uses: 6 | Success rate: 66.7%
     Average score: 0.69
  4. inventory_demand_analysis_v2
     Uses: 1 | Success rate: 100.0%
     Average score: 0.96
  5. warrior_character_template
     Uses: 1 | Success rate: 100.0%
     Average score: 0.96

Anti-Pattern Report:
--------------------------------------------------------------------------------
✓ Critical anti-patterns:
  1. insufficient_data_pattern
     Severity: high | Occurrences: 6
     Fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.
  2. insufficient_data_pattern
     Severity: high | Occurrences: 5
     Fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.
  3. insufficient_data_pattern
     Severity: high | Occurrences: 5
     Fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.
  4. insufficient_data_pattern
     Severity: high | Occurrences: 4
     Fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.

Improvement Suggestions:
--------------------------------------------------------------------------------
✓ Found 3 suggestion(s):

  1. [HIGH] frequent_antipattern
     Anti-pattern 'insufficient_data_pattern' has occurred 6 times. Recommended fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.

  2. [HIGH] frequent_antipattern
     Anti-pattern 'insufficient_data_pattern' has occurred 5 times. Recommended fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.

  3. [HIGH] frequent_antipattern
     Anti-pattern 'insufficient_data_pattern' has occurred 5 times. Recommended fix: Ensure at least 60 days of historical data before requesting demand forecasts. If unavailable, use rule-based fallback or request more data collection.

Success Rate Analysis:
--------------------------------------------------------------------------------
✓ Overall success rate: 73.3%

⚠  Categories needing attention:
   data_extraction: 66.7% - Consider reviewing prompts in this category

================================================================================
STEP 4: Template Optimization Demonstration
================================================================================

[2026-01-18 15:08:33,785] [INFO] [src.service.prompt_storage] [prompt_storage.py:39] [__init__] Initialized PromptStorage at /Users/shibuiyusuke/llm-best-practice-book/llm-best-practice-book-program/chapter_2/section_12/prompt_storage
[2026-01-18 15:08:33,785] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:30] [__init__] Initialized PromptAnalyzer
[2026-01-18 15:08:33,785] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:29] [__init__] Initialized PromptCatalog
[2026-01-18 15:08:33,785] [INFO] [src.service.prompt_analytics] [prompt_analytics.py:28] [__init__] Initialized PromptAnalytics
[2026-01-18 15:08:33,785] [INFO] [src.service.prompt_service] [prompt_service.py:53] [__init__] Initialized PromptManagementService
[2026-01-18 15:08:33,788] [INFO] [src.service.prompt_catalog] [prompt_catalog.py:66] [search_templates] Search found 12 templates
Optimizing template: inventory_demand_analysis_v2
--------------------------------------------------------------------------------
Initial stats:
  Success count: 1
  Failure count: 0
  Success rate: 100.0%
  Average score: 0.96

Simulating template usage with feedback...
[2026-01-18 15:08:33,789] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v2 (ID: 51d40c00581d4531b106c09f1fa0d302)
[2026-01-18 15:08:33,789] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:162] [update_template_stats] Updated template 51d40c00581d4531b106c09f1fa0d302: success_rate=100.00%
[2026-01-18 15:08:33,795] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v2 (ID: 51d40c00581d4531b106c09f1fa0d302)
[2026-01-18 15:08:33,795] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:162] [update_template_stats] Updated template 51d40c00581d4531b106c09f1fa0d302: success_rate=100.00%
[2026-01-18 15:08:33,797] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v2 (ID: 51d40c00581d4531b106c09f1fa0d302)
[2026-01-18 15:08:33,797] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:162] [update_template_stats] Updated template 51d40c00581d4531b106c09f1fa0d302: success_rate=75.00%
[2026-01-18 15:08:33,799] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v2 (ID: 51d40c00581d4531b106c09f1fa0d302)
[2026-01-18 15:08:33,799] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:162] [update_template_stats] Updated template 51d40c00581d4531b106c09f1fa0d302: success_rate=80.00%
[2026-01-18 15:08:33,800] [INFO] [src.service.prompt_storage] [prompt_storage.py:157] [save_template] Saved template: inventory_demand_analysis_v2 (ID: 51d40c00581d4531b106c09f1fa0d302)
[2026-01-18 15:08:33,800] [INFO] [src.service.prompt_analyzer] [prompt_analyzer.py:162] [update_template_stats] Updated template 51d40c00581d4531b106c09f1fa0d302: success_rate=83.33%

Updated stats after 5 uses:
  Success count: 5
  Failure count: 1
  Success rate: 83.3%
  Average score: 0.80

✓ Template performance is being tracked and can inform future optimizations

================================================================================
ADVANCED WORKFLOW COMPLETED
================================================================================


💡 Key Insights from Advanced Example:
   1. Autonomous agents can log all prompts for systematic analysis
   2. Both successes and failures provide valuable learning opportunities
   3. Templates emerge from successful patterns and improve over time
   4. Anti-patterns prevent repeating mistakes and reduce wasted API calls
   5. Analytics provide actionable insights for cost optimization
   6. Continuous feedback loop drives systematic improvement

📊 Business Impact:
   - Reduced API costs by avoiding known failure patterns
   - Improved response quality through template optimization
   - Faster development with reusable, proven prompt patterns
   - Data-driven decisions based on actual performance metrics
```

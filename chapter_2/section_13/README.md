# プロンプト分析・再利用システム

LLMアプリケーションにおけるプロンプトを体系的に記録・分析し、再利用可能な知見として蓄積するシステムの実装例です。

## 概要

このプロジェクトは、「第10項　プロンプトを再利用するために分析する」で解説されているベストプラクティスを実装したものです。キャラクター生成を実例として、プロンプトのログ記録、評価、テンプレート化、分析の一連のワークフローを示します。

### 主な機能

1. **プロンプトログの記録**: すべてのLLM実行を詳細なメタデータと共に記録
2. **評価基準の定義**: タスクごとの成功/失敗の判定基準を設定
3. **テンプレートの自動生成**: 成功したプロンプトから再利用可能なテンプレートを作成
4. **アンチパターンの追跡**: 失敗パターンを記録し、将来の過ちを防ぐ
5. **検索とカタログ**: タグやカテゴリによるテンプレート検索
6. **分析とレポート**: プロンプトのパフォーマンス分析と改善提案
7. **コスト追跡**: API使用量とコストの分析

## 使い方

### インストール

```bash
# 依存関係のインストール
uv sync

# 環境変数の設定
cp .envrc.example .envrc
# .envrcを編集してAPIキーを設定
```

### 基本的な使用方法

#### 1. シンプルなキャラクター生成

```bash
# デフォルト設定で実行
uv run python -m src.main -m gpt-4o-mini

# 特定の変数ファイルを使用
uv run python -m src.main -m gpt-4o -v variables/character_artist.yaml

# テンプレートと変数を両方指定
uv run python -m src.main -m gpt-4o -t templates/character_generation.yaml -v variables/warrior.yaml
```

#### 2. 実践的なサンプル実行

```bash
# 基本的なワークフロー（ログ記録、評価、テンプレート作成）
uv run python -m src.examples.basic_example

# 既存システムとの統合例（プロンプトロギング機能の追加）
uv run python -m src.examples.integration_example

# 高度な分析とレポート生成の例
uv run python -m src.examples.advanced_example
```

#### 3. プロンプトロギング付き実行

```bash
# ロギングを有効にして実行
uv run python -m src.examples.integration_example -m gpt-4o-mini

# 自動評価を有効化
uv run python -m src.examples.integration_example -m gpt-4o-mini --auto-evaluate

# 統計情報を表示
uv run python -m src.examples.integration_example -m gpt-4o-mini --show-stats

# ロギングを無効化（通常のキャラクター生成のみ）
uv run python -m src.examples.integration_example -m gpt-4o-mini --no-logging
```

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

## テンプレートと変数の分離

このシステムの重要な設計原則は、**プロンプトテンプレート**と**変数**を分離することです:

### テンプレート (`templates/`)
- プロンプトの構造を定義
- システムプロンプトとユーザープロンプト
- Jinja2テンプレート形式で変数を参照

### 変数 (`variables/`)
- テンプレートに注入する具体的な値
- YAMLフォーマット
- 異なるユースケースやテストケースごとに作成

### メリット

1. **再利用性**: 同じテンプレートを異なる変数で使用
2. **バージョン管理**: テンプレートとデータを分離して管理
3. **テスト**: 様々なパラメータの組み合わせを簡単にテスト
4. **コラボレーション**: チームでテンプレートを共有

## プロンプト管理API

### 基本的な使用例

```python
from src.service.prompt_service import PromptManagementService
from src.model.prompt_log import (
    EvaluationCriteria,
    EvaluationStatus,
    PromptCategory,
    PromptMetadata,
)

# サービスの初期化
service = PromptManagementService()

# メタデータの作成
metadata = PromptMetadata(
    model_name="gpt-4o",
    temperature=0.7,
    use_case="text_classification",
    category=PromptCategory.CLASSIFICATION,
    tags=["sentiment", "review"],
)

# プロンプト実行のログ記録
log_id = service.log_prompt_execution(
    prompt_text="Classify the sentiment...",
    messages=[{"role": "user", "content": "..."}],
    response_text="Positive",
    metadata=metadata,
)

# 評価
evaluation = EvaluationCriteria(
    accuracy=1.0,
    completeness=1.0,
    relevance=1.0,
    task_completed=True,
)

service.evaluate_prompt(
    log_id=log_id,
    evaluation=evaluation,
    status=EvaluationStatus.SUCCESS,
)
```

### テンプレートの作成

```python
# 成功したプロンプトからテンプレート作成
template = service.create_template_from_success(
    log_id=log_id,
    template_name="sentiment_classification",
    description="Classify sentiment of product reviews",
    required_variables=["review_text"],
    optional_variables=["output_format"],
)

# テンプレート検索
templates = service.search_templates(
    category=PromptCategory.CLASSIFICATION,
    tags=["sentiment"],
    min_success_rate=0.8,
)
```

### アンチパターンの追跡

```python
# 失敗したプロンプトからアンチパターン作成
antipattern = service.create_antipattern_from_failure(
    log_id=failed_log_id,
    pattern_name="vague_context",
    failure_reason="Prompt lacks specific context",
    recommended_fix="Always provide clear context and examples",
    severity="high",
)
```

### 分析とレポート

```python
# パフォーマンスサマリー
summary = service.get_performance_summary()

# カテゴリ別成功率
success_rates = service.get_success_rates()

# 改善提案
suggestions = service.get_improvement_suggestions()

# コスト分析
costs = service.get_cost_analysis()
```

## 実装例の説明

### 1. 基本例 (basic_example.py)

プロンプトログ記録から再利用可能なテンプレート作成までの基本的なワークフローを実演します：

- キャラクター生成プロンプトの実行
- 実行結果のログ記録とメタデータ保存
- 評価基準に基づく結果の評価
- 成功したプロンプトからのテンプレート作成
- カタログ検索と統計表示

### 2. 統合例 (integration_example.py)

既存のCLIアプリケーションにプロンプトロギング機能を非侵襲的に追加する方法を示します：

- 既存コードへの最小限の変更でロギング機能を追加
- オプションフラグによるロギングの有効/無効切り替え
- 自動評価機能の実装
- 統計情報とコスト分析の表示

### 3. 高度な例 (advanced_example.py)

自律型AIエージェントを想定した、包括的なプロンプト管理システムを実演します：

- 複数のプロンプト実行をシミュレート（成功と失敗の両方）
- 成功パターンからの複数テンプレート生成
- 失敗パターンからのアンチパターン作成
- 詳細な分析レポートと改善提案の生成
- コスト分析と最適化の提案
- テンプレートパフォーマンスの追跡

## データ構造

### ストレージ構造

```
prompt_storage/
├── logs/                       # プロンプトログ
│   ├── 2025-01-15/            # 日付ごとに整理
│   │   ├── abc123.json
│   │   └── def456.json
│   └── 2025-01-16/
│
├── templates/                  # 再利用可能なテンプレート
│   ├── template_001.json
│   └── template_002.json
│
└── antipatterns/              # 失敗パターン（アンチパターン）
    ├── pattern_001.json
    └── pattern_002.json
```

### 主要なデータモデル

#### PromptLog
- プロンプトの実行履歴を記録
- メタデータ（モデル、温度、トークン数、コストなど）
- 評価結果（正確性、完全性、関連性など）
- 実行時間とパフォーマンス指標

#### PromptTemplate
- 成功したプロンプトから生成されたテンプレート
- 必須変数とオプション変数の定義
- 推奨されるモデルとパラメータ
- 成功率とスコアの追跡

#### AntiPattern
- 失敗したプロンプトから学習したパターン
- 失敗の原因と推奨される修正方法
- 深刻度と発生頻度の追跡

## ワークフロー

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

## 主要機能の詳細

### プロンプトログ記録

すべてのLLM実行を以下の情報と共に記録：

- **プロンプトテキスト**: 送信したプロンプトの全文
- **メッセージ**: システムプロンプトとユーザープロンプト
- **応答**: LLMからの応答
- **メタデータ**:
  - モデル名とバージョン
  - パラメータ（temperature、max_tokensなど）
  - 実行時間
  - トークン数（入力/出力）
  - コスト
  - ユースケースとカテゴリ
  - タグ

### 評価システム

多面的な評価基準：

- **accuracy**: 出力の正確性（0.0-1.0）
- **completeness**: 要求された情報の網羅性（0.0-1.0）
- **relevance**: 目的への関連性（0.0-1.0）
- **task_completed**: タスク完了フラグ（boolean）
- **user_feedback**: ユーザーからのフィードバック（boolean）
- **error_count**: エラー発生回数

### テンプレート管理

成功したプロンプトからテンプレートを自動生成：

- 変数の自動抽出
- 推奨パラメータの記録
- 成功率の追跡
- 平均スコアの計算
- 使用履歴の記録

### 分析とレポート

包括的な分析機能：

- **パフォーマンスサマリー**: 全体的な成功率とスコア
- **カテゴリ別成功率**: タスクタイプごとの分析
- **モデル別パフォーマンス**: モデルごとの比較
- **コスト分析**: トークン使用量とコスト追跡
- **改善提案**: データに基づく具体的な改善案
- **テンプレート使用レポート**: 人気のテンプレートと効果測定
- **アンチパターンレポート**: 頻出する失敗パターンの特定

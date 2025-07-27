# 構造化プロンプトテンプレートシステム

このプロジェクトは、LLMベストプラクティス本の第2章第6項で説明されている、LLMアプリケーションにおけるプロンプトの構造的テンプレート化のベストプラクティスを実装したものです。外部YAMLテンプレートと変数ファイルを通じて、プロンプトロジックをビジネスロジックから分離する方法を示しています。

## 概要

このプロジェクトは、構造化プロンプトテンプレートを使用して詳細な性格を持つフィクションキャラクターを生成するキャラクター生成システムを実装しています。Pythonコードにプロンプトをハードコーディングする代わりに、以下を使用しています：

- **YAMLテンプレート** - プロンプト構造とコンテンツ用
- **変数ファイル** - 異なるシナリオと設定用
- **Jinja2テンプレート** - 動的コンテンツ注入用
- **スキーマ検証** - テンプレート一貫性用
- **CLI統合** - 簡単なテンプレートと変数管理用

## 主要機能

### 🎯 テンプレート管理
- `templates/`ディレクトリの外部YAMLテンプレートファイル
- 複数のテンプレートタイプ（デフォルト、クリエイティブ、シンプル）
- テンプレートのバージョン管理とメタデータ
- Jinja2による動的コンテンツ生成

### 📝 変数ファイルシステム
- `variables/`ディレクトリのYAML変数ファイル
- 事前設定されたシナリオ（ファンタジー、SF、年齢グループ）
- ファイルベース設定によるCLIパラメータのオーバーライド
- 非エンジニア向けフレンドリーフォーマット

### 🔧 CLIインターフェース
- 利用可能なテンプレートと変数ファイルの一覧表示
- 特定のテンプレートでのキャラクター生成
- テンプレート情報と変数の検査
- 複数のLLMプロバイダーサポート（OpenAI、Gemini）

### 🛡️ 検証とエラーハンドリング
- テンプレートスキーマ検証
- 変数の型チェックとデフォルト値
- レガシープロンプトへの graceful fallback
- 包括的なエラーレポート

## プロジェクト構造

```
src/
├── main.py              # コマンドグループ付きCLIエントリーポイント
├── template_engine.py   # Jinja2付きコアテンプレートエンジン
├── prompt.py           # テンプレート統合付きプロンプト生成
├── model.py            # キャラクターデータ用Pydanticモデル
├── llms.py             # LLMクライアント設定
├── config.py           # 環境設定
└── logger.py           # 集中ログ

templates/              # YAMLプロンプトテンプレート
├── character_generation.yaml    # デフォルトキャラクターテンプレート
├── creative_character.yaml      # クリエイティブ/ファンタジーテンプレート
└── simple_character.yaml        # シンプル/親しみやすいテンプレート

variables/              # YAML変数ファイル
├── character_generation_default.yaml
├── character_generation_conservative.yaml
├── creative_character_fantasy.yaml
├── creative_character_scifi.yaml
├── simple_character_teenager.yaml
└── simple_character_elderly.yaml

outputs/                # 生成されたキャラクターJSONファイル
```

## クイックスタート

### インストール

```bash
# 依存関係のインストール
uv sync

# 環境変数の設定
cp .envrc.example .envrc
# .envrcをAPIキーで編集
```

### 基本的な使用方法

```bash
# 利用可能なテンプレートの一覧表示
uv run python -m src.main list-templates

# 利用可能な変数ファイルの一覧表示
uv run python -m src.main list-variables

# デフォルトテンプレートと変数でキャラクター生成
uv run python -m src.main generate \
  --template character_generation \
  --variable-file variables/character_generation_default.yaml

# ファンタジーキャラクターの生成
uv run python -m src.main generate \
  --template creative_character \
  --variable-file variables/creative_character_fantasy.yaml

# GeminiではなくOpenAIを使用
uv run python -m src.main generate \
  --template simple_character \
  --variable-file variables/simple_character_teenager.yaml \
  --llm-provider OPENAI
```

### テンプレート情報

```bash
# テンプレート詳細の表示
uv run python -m src.main template-info --template character_generation

# 出力にはテンプレート変数、型、説明が表示される
```

## テンプレートシステムアーキテクチャ

### テンプレート構造

各YAMLテンプレートには以下が含まれます：

```yaml
name: "template_name"
description: "テンプレートの説明"
version: "1.0"

variables:
  variable_name:
    type: string
    description: "変数の説明"
    required: true/false
    default: "デフォルト値"

system_prompt: |
  {{ variable_name }} プレースホルダー付きのシステムプロンプト

user_prompt: |
  条件付きロジック付きのユーザープロンプト:
  {% if condition %}
  追加コンテンツ
  {% endif %}
```

### 変数ファイル形式

```yaml
# 変数設定を説明するコメント
variable_name: "値"
another_variable: "別の値"
```

### テンプレートエンジン機能

- **Jinja2統合**: 条件文、ループ、フィルターを含む完全なテンプレート機能
- **変数検証**: 型チェックと必須フィールドの強制
- **動的ローディング**: ランタイムテンプレートと変数ファイルの発見
- **エラーハンドリング**: 失敗時のレガシープロンプトへの graceful fallback
- **スキーマ注入**: Pydanticモデルスキーマの自動注入

## 利用可能なテンプレート

### character_generation
**デフォルトキャラクター生成テンプレート**
- 変数: `target_language`, `creativity_level`
- 用途: 一般的なキャラクター作成
- 変数ファイル: `character_generation_default.yaml`, `character_generation_conservative.yaml`

### creative_character
**ファンタジー/SF設定用クリエイティブキャラクターテンプレート**
- 変数: `fantasy_setting`, `character_background`
- 用途: ファンタジーゲーム、創作文芸、世界観構築
- 変数ファイル: `creative_character_fantasy.yaml`, `creative_character_scifi.yaml`

### simple_character
**親しみやすい性格用シンプルキャラクターテンプレート**
- 変数: `age_range`, `personality_focus`
- 用途: リアリスティックフィクション、教育コンテンツ
- 変数ファイル: `simple_character_teenager.yaml`, `simple_character_elderly.yaml`

## 開発コマンド

```bash
# コード品質
uv run ruff check src/          # コードのlint
uv run ruff format src/         # コードのフォーマット
uv run mypy src/               # 型チェック

# テンプレートのテスト
uv run python -m src.main list-templates
uv run python -m src.main template-info --template character_generation
uv run python -m src.main list-variables
```

## 環境設定

必要なAPIキーで`.envrc`ファイルを作成：

```bash
export GEMINI_API_KEY="your_gemini_api_key"
export OPENAI_API_KEY="your_openai_api_key"
export LOG_LEVEL="INFO"
```

## 実証されたベストプラクティス

### 🔄 関心の分離
- プロンプトコンテンツをビジネスロジックから分離
- テンプレート構造を変数データから分離
- 一貫したスキーマでの複数出力形式（JSON）

### 📁 外部ファイル管理
- バージョン管理されたテンプレートと変数
- 非エンジニアが編集可能なYAML形式
- Git-friendlyな差分追跡

### 🎛️ 設定管理
- 環境固有の変数ファイル
- CLIパラメータのオーバーライド
- デフォルト値の処理

### 🔍 検証とテスト
- テンプレートのスキーマ検証
- 変数の型チェック
- テンプレートレンダリングの検証

### 🚀 運用の卓越性
- 包括的なログ記録
- フォールバック付きエラーハンドリング
- 運用のためのCLIツール

## 高度な使用方法

### カスタムテンプレートの作成

1. `templates/`ディレクトリに新しいYAMLファイルを作成
2. 変数付きテンプレート構造を定義
3. `variables/`に対応する変数ファイルを作成
4. `template-info`コマンドでテスト

### カスタム変数ファイル

1. `variables/`ディレクトリにYAMLファイルを作成
2. 命名規則に従う: `{template}_{scenario}.yaml`
3. 対象テンプレートに必要なすべての変数を含める
4. `generate`コマンドでテスト

### システムの拡張

- テンプレートYAMLに新しいテンプレート変数を追加
- `main.py`に新しいCLIコマンドを実装
- カスタムフィルターでテンプレートエンジンを拡張
- `llms.py`に新しいLLMプロバイダーを追加

## 出力

生成されたキャラクターは`outputs/`ディレクトリにJSONファイルとして保存され、形式は以下のとおりです：
```
{llm_provider}_{template}_{variable_file}_{uuid}.json
```

出力構造の例：
```json
{
  "first_name": "Elara",
  "last_name": "Umbril",
  "gender": "female",
  "age": 62,
  "personalities": [
    {
      "short_personality": "Enigmatic & Distant",
      "description": "詳細な性格の説明..."
    }
  ]
}
```

## このアプローチの利点

### 開発者向け
- ✅ メンテナブルで再利用可能なプロンプトコード
- ✅ 異なるプロンプトの簡単なA/Bテスト
- ✅ プロンプト変更のバージョン管理
- ✅ コード重複の削減

### 非エンジニア向け
- ✅ コード変更なしでのプロンプト編集
- ✅ 変数ファイルでの新しいシナリオ作成
- ✅ YAMLを通じたプロンプト構造の理解
- ✅ 迅速な実験と反復

### 運用チーム向け
- ✅ ランタイムテンプレート切り替え
- ✅ 設定駆動の動作
- ✅ モニタリングとログ統合
- ✅ ロールバック機能

この実装は、構造化プロンプトテンプレートがLLMアプリケーション開発を、硬直的でコード重視のアプローチから、技術者と非技術者の両方がプロンプトの改善と実験に貢献できる柔軟で設定駆動のシステムにどのように変革できるかを実証しています。
# Chapter 2 Section 9: プロンプトを構造的にテンプレート化する

## 概要

このプロジェクトは、**構造化されたテンプレート化プロンプト（Structured Template Prompting）** の実装を示すサンプルコードです。プロンプトをソースコードから分離し、YAML形式のテンプレートファイルとして管理することで、再利用性、保守性、可読性を飛躍的に向上させます。Jinja2テンプレートエンジンを活用して動的に変数を注入し、最終的なプロンプトを生成します。

キャラクター生成、商品説明文作成、メール文面生成といった複数のユースケースを通じて、プロンプトテンプレート化のベストプラクティスを学ぶことができます。

## 機能

- **テンプレートベースのプロンプト管理**: YAMLファイルでプロンプト構造を定義
- **動的変数注入**: Jinja2を使用した柔軟な変数置換とロジック（条件分岐、ループなど）
- **テンプレートバリデーション**: 必須変数の存在チェックによる実行時エラーの防止
- **複数テンプレートのサポート**: キャラクター生成、商品説明、メールなど多様なユースケース
- **変数ファイル管理**: テンプレートとデータを完全に分離した設計
- **OpenAI API対応**: OpenAI APIをサポート
- **型安全な構造化出力**: Pydanticモデルによる厳密な型検証
- **包括的なテストスイート**: TemplateEngineとプロンプト生成の網羅的テスト
- **CLIインターフェース**: 使いやすいコマンドラインツール
- **Makefileサポート**: 一般的なタスクを簡単に実行

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_6/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py       # LLM APIリクエスト処理
│       └── template_engine.py   # テンプレートエンジン実装
├── templates/                    # プロンプトテンプレートファイル
│   ├── character_generation.yaml # キャラクター生成テンプレート
│   ├── product_description.yaml  # 商品説明文テンプレート
│   ├── email_formal.yaml         # フォーマルメールテンプレート
│   └── email_casual.yaml         # カジュアルメールテンプレート
├── variables/                    # テンプレート変数定義ファイル
│   ├── character_artist.yaml     # 芸術家キャラクター変数
│   ├── character_detective.yaml  # 探偵キャラクター変数
│   ├── product_electronics.yaml  # 家電商品変数
│   ├── product_apparel.yaml      # アパレル商品変数
│   ├── email_campaign_summer.yaml # サマーキャンペーン変数
│   └── email_campaign_winter.yaml # ウィンターキャンペーン変数
├── tests/                        # テストファイル
│   ├── __init__.py
│   ├── conftest.py              # pytest設定とフィクスチャ
│   ├── test_template_engine.py  # TemplateEngineのテスト
│   └── test_prompt.py           # プロンプト生成のテスト
├── outputs/                      # 生成結果の保存先（自動作成）
├── .envrc.example                # 環境変数設定のサンプル
├── pyproject.toml                # プロジェクト依存関係
├── Makefile                      # タスク自動化
├── README.md                     # このファイル
└── CLAUDE.md                     # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、テンプレート駆動型の4層アーキテクチャで構成されています：

```
┌───────────────────────────────────────────────┐
│         CLI Layer (main.py)                   │
│     - コマンドライン引数解析                   │
│     - 出力ディレクトリ管理                     │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│      Business Logic Layer                     │
│  - プロンプト生成 (prompt.py)                 │
│  - LLMリクエスト処理 (request_llm.py)         │
│  - データモデル (model.py)                    │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│      Template Layer                           │
│  - テンプレートエンジン (template_engine.py)  │
│  - YAMLテンプレート (templates/)              │
│  - 変数定義 (variables/)                      │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│      Infrastructure Layer                     │
│  - 設定管理 (config.py)                       │
│  - ログ管理 (logger.py)                       │
│  - 外部API (OpenAI)                           │
└───────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - click>=8.3.0 (CLIインターフェース)
  - jinja2>=3.1.6 (テンプレートエンジン)
  - openai>=2.4.0 (OpenAI API)
  - pydantic>=2.12.2 (データモデル)
  - python-dotenv>=1.1.1 (環境変数管理)
  - pyyaml>=6.0.3 (YAMLパーサー)

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# または make コマンド
make install

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# OpenAI APIを使用
uv run python -m src.main --model gpt-4o

# Makefileを使用
make run-openai
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main -m gpt-4o-mini -od ./custom_output

# 短縮オプション
uv run python -m src.main -m gpt-4o -od ./my_characters
```

#### ヘルプの表示

```bash
uv run python -m src.main --help
```

**出力例**:
```
Usage: python -m src.main [OPTIONS]

Options:
  -m, --model TEXT                The OpenAI model to use for the request.  [required]
  -od, --output-directory PATH    The directory to save output files.
  --help                          Show this message and exit.
```

#### Makefileコマンド一覧

```bash
# ヘルプを表示
make help

# テストを実行
make test               # 全テスト実行
make pytest             # ユニットテストのみ
make pytest-cov         # カバレッジレポート付き
make test-templates     # テンプレートテストのみ

# コード品質チェック
make lint               # リンター実行
make fmt                # コードフォーマット
make fix                # リントとフォーマットを両方実行
make mypy               # 型チェック

# LLM実行
make run-openai         # OpenAI APIで実行
```

### 出力例

実行すると、以下のような構造化されたJSONファイルが生成されます：

**ファイル名**: `outputs/openai_c5339cd3f7b240b3b6e7b113eeacd216.json`

```json
{
    "first_name": "蒼",
    "last_name": "雨宮",
    "gender": "male",
    "age": 25,
    "personalities": [
        {
            "short_personality": "冒険心旺盛",
            "description": "新しい場所や経験を求め、常に未知への挑戦を楽しむ。好奇心が強く、リスクを恐れず行動する。"
        },
        {
            "short_personality": "社交的",
            "description": "初対面の人とも打ち解けやすく、会話を楽しむ。多様なバックグラウンドを持つ人々との交流を大切にする。"
        },
        {
            "short_personality": "楽観的",
            "description": "困難な状況でもポジティブな側面を見つけ、前向きに対処する。失敗を学びの機会と捉える。"
        }
    ]
}
```

**実行ログ例**:
```
[2025-01-18 10:30:45] [INFO] [__main__] [main.py:53] [main] LLM provider: openai
Model: gpt-4o
Output directory: outputs
[2025-01-18 10:30:47] [INFO] [__main__] [main.py:74] [main] File saved to outputs/openai_c5339cd3f7b240b3b6e7b113eeacd216.json
```

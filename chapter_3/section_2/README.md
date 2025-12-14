# Chapter 3 Section 2: LLMリクエストのタイムアウトとフォールバック

## 概要

このプロジェクトは、**本番環境で求められるLLM APIリクエストの復元力（レジリエンス）とフォールバック戦略**を実装したサンプルコードです。プライマリLLMプロバイダーの障害やタイムアウトが発生した場合でも、サービスを継続的に提供するための多段階フォールバックシステムを実現します。

Section 1とSection 2で学んだ基本的なLLM実装をベースに、**プロダクションレディなエラーハンドリング、キャッシング、代替プロバイダー切り替え**などの実用的なパターンを追加しています。

フィクションのキャラクター情報生成を通じて、API障害時でも安定したサービス提供を実現する方法を学ぶことができます。

## 機能

### 1. 3段階フォールバックシステム

プライマリプロバイダーの障害時に自動的に代替手段へ切り替える多段階システム：

1. **プライマリプロバイダーリクエスト** - 設定されたタイムアウト内でリクエストを試行
2. **パラメーターキャッシュ/セマンティックキャッシュ** - 過去のリクエストのキャッシュを検索
3. **代替プロバイダー** - 別のLLMプロバイダー（OpenAI ⇄ Gemini）に自動切り替え

### 2. 2種類のレスポンスキャッシング

**パラメーターキャッシュ（CacheManager）:**
- **SHA256ベースのキャッシュキー生成** - プロンプト、モデルを元にハッシュ化
- **完全一致検索** - 同じプロンプトとモデルの組み合わせで高速ヒット
- **TTL（Time-To-Live）サポート** - キャッシュの有効期限管理（デフォルト: 1時間）
- **JSONファイルベースストレージ** - `.cache/` ディレクトリに保存

**セマンティックキャッシュ（SemanticCacheManager）:**
- **埋め込みベースの類似検索** - プロンプトの意味的な類似性でキャッシュヒット
- **コサイン類似度** - 設定可能な類似度閾値（デフォルト: 0.95）
- **類似プロンプトの再利用** - 完全一致でなくても類似したリクエストでキャッシュを活用

**共通機能:**
- **期限切れエントリの自動クリーンアップ** - 無効なキャッシュの自動削除
- **ベースクラスによる共通機能** - BaseCacheManagerで重複コードを削減

### 3. 設定可能なタイムアウト管理

- **デフォルトタイムアウト**: 10秒（環境変数またはCLIで設定可能）
- **リクエスト毎のタイムアウト上書き** - 柔軟な制御が可能
- **タイムアウト追跡** - 監視用の統計情報を記録

### 4. 統計情報とモニタリング

包括的なメトリクスの追跡：
- 総リクエスト数
- プライマリプロバイダー成功率
- パラメーターキャッシュヒット率
- セマンティックキャッシュヒット率
- 代替プロバイダー使用率
- タイムアウトおよびエラーカウント
- フォールバック率と失敗率

### 5. デュアルLLMプロバイダーサポート

- **OpenAI**: GPT-4o-miniによる構造化出力
- **Gemini**: Gemini-2.5-flashによるJSONスキーマ検証
- **クロスプロバイダーフォールバック**: OpenAI失敗時にGeminiへ、またはその逆

### 6. その他の機能

- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **型安全性**: Pydanticによる厳密な型検証とバリデーション
- **CLIインターフェース**: Clickライブラリを使用した使いやすいコマンドラインツール
- **環境変数管理**: python-dotenvによる安全なAPIキー管理
- **詳細なログ出力**: 実行状況とフォールバック戦略の可視化
- **JSON出力**: 生成結果をJSON形式でファイルに保存
- **データクラスによる型安全性**: RequestContextとFallbackResultで明確なデータ構造

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_3/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー、タイムアウト、TTL）
│   ├── logger.py                # ロギング設定
│   ├── main.py                  # メインエントリーポイント
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # LLMクライアント初期化（OpenAI/Gemini）
│   │   └── llm_request_wrapper.py  # フォールバックロジックを含むリクエストラッパー
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── cache_manager.py     # TTL付きレスポンスキャッシング（パラメーター/セマンティック）
│       ├── fallback_coordinator.py  # フォールバック戦略の統括
│       └── template_response.py # テンプレート応答生成
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytestフィクスチャ
│   ├── test_cache_manager.py    # キャッシュマネージャーのテスト
│   └── test_fallback_coordinator.py # フォールバックコーディネーターのテスト
├── .cache/                      # パラメーターキャッシュストレージ（.gitignore）
├── .semantic_cache/             # セマンティックキャッシュストレージ（.gitignore）
├── outputs/                     # 生成結果の保存先（自動作成）
├── .envrc.example               # 環境変数設定のサンプル
├── pyproject.toml               # プロジェクト依存関係
├── README.md                    # このファイル
└── CLAUDE.md                    # プロジェクト状態レポート（英語）
```

### アーキテクチャ

このプロジェクトは、以下の4層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────┐
│         CLI Layer (main.py)                 │
│     - コマンドライン引数解析                 │
│     - 出力ディレクトリ管理                   │
│     - フォールバック有効/無効制御             │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Request Wrapper Layer                  │
│  - リクエストラッパー (llm_request_wrapper)  │
│  - OpenAI/Geminiリクエストの統一I/F         │
│  - リクエストロジックの共通化                │
│  - プロバイダー間の切り替え                  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Fallback Coordination Layer            │
│  - フォールバック統括 (fallback_coordinator)│
│  - タイムアウト管理                          │
│  - 3段階フォールバック戦略実行               │
│  - 統計情報の追跡                            │
│  - 戦略パターンによるディスパッチ            │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Service Layer                          │
│  - キャッシュマネージャー (cache_manager)   │
│    • BaseCacheManager (基底クラス)         │
│    • CacheManager (パラメーターキャッシュ)  │
│    • SemanticCacheManager (セマンティック)  │
│  - プロンプト生成 (prompt.py)               │
│  - データモデル (model.py)                  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Infrastructure Layer                   │
│  - 設定管理 (config.py)                     │
│  - ログ管理 (logger.py)                     │
│  - 外部API (OpenAI, Gemini)                 │
│  - ファイルシステム（キャッシュ、出力）      │
└─────────────────────────────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - **コア**:
    - click>=8.3.0 - CLIフレームワーク
    - google-genai>=1.45.0 - Google Gemini APIクライアント
    - openai>=2.4.0 - OpenAI APIクライアント
    - pydantic>=2.12.2 - データ検証とスキーマ
    - python-dotenv>=1.1.1 - 環境変数管理
  - **開発**:
    - pytest>=8.4.2 - テストフレームワーク
    - pytest-asyncio>=1.2.0 - 非同期テストサポート
    - pytest-mock>=3.15.1 - モッキングサポート

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX

# オプション設定（デフォルト値で問題なければ省略可）
LLM_REQUEST_TIMEOUT=10.0    # リクエストタイムアウト（秒）
CACHE_TTL=3600              # キャッシュTTL（秒、デフォルト: 1時間）
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# 開発依存関係も含める場合
uv sync --all-extras
```

### 使用方法、実行方法

#### 基本的な使い方

```bash
# Gemini APIを使用（デフォルト、フォールバック有効）
uv run python -m src.main

# OpenAI APIを使用（フォールバック有効）
uv run python -m src.main --llm-provider OPENAI

# 短縮オプション
uv run python -m src.main -lp OPENAI
```

#### タイムアウトの設定

```bash
# カスタムタイムアウトを指定（5秒）
uv run python -m src.main --timeout 5

# 短縮オプション
uv run python -m src.main -t 5

# 非常に短いタイムアウト（3秒）でフォールバック動作をテスト
uv run python -m src.main -t 3
```

#### フォールバックの制御

```bash
# フォールバックを無効化（プライマリプロバイダーのみ使用）
uv run python -m src.main --disable-fallback

# 短縮オプション
uv run python -m src.main -df

# デバッグ用: OpenAIのみ、フォールバックなし、短いタイムアウト
uv run python -m src.main -lp OPENAI -df -t 5
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main -od ./my_characters
```

#### 複合オプション

```bash
# すべてのオプションを組み合わせ
uv run python -m src.main -lp OPENAI -od ./outputs -t 15 -df

# 本番環境向け設定例（長めのタイムアウト）
uv run python -m src.main -lp GEMINI -t 30

# 開発/テスト環境向け設定例（短いタイムアウトでフォールバックをテスト）
uv run python -m src.main -lp GEMINI -t 2
```

### 出力例

#### 正常実行時（プライマリプロバイダー成功）

**ファイル名**: `outputs/gemini_a1b2c3d4e5f6.json`

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

**実行ログ例**:
```
[2025-11-17 10:30:45] [INFO] Attempting primary request with gemini (timeout: 10.0s)
[2025-11-17 10:30:47] [INFO] Primary request succeeded with gemini
[2025-11-17 10:30:47] [INFO] Cached response: f0f84bef45c8...
[2025-11-17 10:30:47] [INFO] File saved to outputs/gemini_a1b2c3d4e5f6.json
[2025-11-17 10:30:47] [INFO] === Fallback Statistics ===
[2025-11-17 10:30:47] [INFO] Total Requests: 1
[2025-11-17 10:30:47] [INFO] Primary Success: 1 (100.0%)
[2025-11-17 10:30:47] [INFO] Parameter Cache Hits: 0 (0.0%)
[2025-11-17 10:30:47] [INFO] Semantic Cache Hits: 0 (0.0%)
[2025-11-17 10:30:47] [INFO] Total Cache Hit Rate: 0.0%
[2025-11-17 10:30:47] [INFO] Alternative Provider: 0
[2025-11-17 10:30:47] [INFO] Fallback Failures: 0 (0.0%)
[2025-11-17 10:30:47] [INFO] Timeouts: 0
[2025-11-17 10:30:47] [INFO] Errors: 0
[2025-11-17 10:30:47] [INFO] Fallback Rate: 0.0%
[2025-11-17 10:30:47] [INFO] ===========================
```

#### フォールバック実行時（パラメーターキャッシュヒット）

**実行ログ例**:
```
[2025-11-17 10:32:10] [WARNING] Primary request timed out after 3.0s. Initiating fallback strategy: parameter_cache
[2025-11-17 10:32:10] [INFO] Cache hit: 7a8b9c0d1e2f... (age: 120.5s)
[2025-11-17 10:32:10] [INFO] Fallback: Using parameter cache response (exact match)
[2025-11-17 10:32:10] [INFO] Response obtained via fallback strategy: parameter_cache
[2025-11-17 10:32:10] [WARNING] Primary provider failed due to: timeout
```

#### セマンティックキャッシュヒット時

**実行ログ例**:
```
[2025-11-17 10:33:15] [WARNING] Primary request timed out after 3.0s. Initiating fallback strategy: semantic_cache
[2025-11-17 10:33:15] [INFO] Semantic cache hit: 8b9c0d1e2f3a... (similarity: 0.967, threshold: 0.950)
[2025-11-17 10:33:15] [INFO] Fallback: Using semantic cache response (similar prompt)
[2025-11-17 10:33:15] [INFO] Response obtained via fallback strategy: semantic_cache
```

#### 代替プロバイダー使用時

**実行ログ例**:
```
[2025-11-17 10:35:22] [WARNING] Primary request failed with error: Connection error. Initiating fallback strategy: alternative_provider
[2025-11-17 10:35:22] [INFO] Fallback: Attempting alternative provider (timeout: 10.0s)
[2025-11-17 10:35:24] [INFO] Fallback: Alternative provider succeeded
[2025-11-17 10:35:24] [INFO] Cached response: e7f8g9h0i1j2...
[2025-11-17 10:35:24] [INFO] Response obtained via fallback strategy: alternative_provider
[2025-11-17 10:35:24] [WARNING] Primary provider failed due to: error
```

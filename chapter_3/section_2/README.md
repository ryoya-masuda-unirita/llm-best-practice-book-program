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

- **OpenAI**: GPT-5.4-miniによる構造化出力
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
AWS_REGION=us-east-1

# オプション設定（デフォルト値で問題なければ省略可）
LLM_REQUEST_TIMEOUT=10.0    # リクエストタイムアウト（秒）
CACHE_TTL=3600              # キャッシュTTL（秒、デフォルト: 1時間）
```

2. **依存関係のインストール**

```bash
# uvを使用
uv sync
```

### 使用方法、実行方法

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
  -lp, --llm-provider [OPENAI|GEMINI]
                                  The LLM provider to use.  [required]
  -m, --model [GPT_5_5|GPT_5_4|CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5]
                                  The model to use for the request.
                                  [required]
  -fs, --fallback-strategy [PRIMARY|PARAMETER_CACHE|SEMANTIC_CACHE|ALTERNATIVE_PROVIDER]
                                  The fallback strategy to use.  [required]
  -am, --alternative-model [GPT_5_5|GPT_5_4|CLAUDE_SONNET_4_6|CLAUDE_HAIKU_4_5]
                                  The alternative model to use for fallback
                                  requests.  [required]
  -od, --output-directory PATH    The directory to save output files.
  -t, --timeout FLOAT             Request timeout in seconds (default: 10.0s
                                  from config)  [required]
  -df, --disable-fallback         Disable fallback mechanisms (use only
                                  primary provider)
  --help                          Show this message and exit.
```

#### 基本的な使い方

```bash
# Gemini APIを使用（プライマリリクエストのみ）
uv run python -m src.main \
  --gender FEMALE \
  --age 25 \
  --llm-provider ANTHROPIC \
  --model CLAUDE_HAIKU_4_5 \
  --fallback-strategy PRIMARY \
  --alternative-model GPT_5_4 \
  --timeout 10

# OpenAI APIを使用（プライマリリクエストのみ）
uv run python -m src.main \
  --gender MALE \
  --age 30 \
  --llm-provider OPENAI \
  --model GPT_5_4 \
  --fallback-strategy PRIMARY \
  --alternative-model CLAUDE_HAIKU_4_5 \
  --timeout 10

# 短縮オプション
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 -fs PRIMARY -am GPT_5_4 -t 10
```

#### フォールバック戦略の設定

```bash
# パラメーターキャッシュをフォールバックに使用
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  --fallback-strategy PARAMETER_CACHE \
  --alternative-model GPT_5_4 \
  --timeout 10

# セマンティックキャッシュをフォールバックに使用
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  --fallback-strategy SEMANTIC_CACHE \
  --alternative-model GPT_5_4 \
  --timeout 10

# 代替プロバイダーをフォールバックに使用（OpenAI → Gemini）
uv run python -m src.main \
  -g MALE -a 28 -lp OPENAI -m GPT_5_4 \
  --fallback-strategy ALTERNATIVE_PROVIDER \
  --alternative-model CLAUDE_HAIKU_4_5 \
  --timeout 5
```

#### タイムアウトの設定

```bash
# カスタムタイムアウトを指定（5秒）
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -fs PRIMARY -am GPT_5_4 \
  --timeout 5

# 非常に短いタイムアウト（3秒）でフォールバック動作をテスト
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -fs PARAMETER_CACHE -am GPT_5_4 \
  -t 3
```

#### フォールバックの無効化

```bash
# フォールバックを無効化（プライマリプロバイダーのみ使用）
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -fs PRIMARY -am GPT_5_4 -t 10 \
  --disable-fallback

# デバッグ用: OpenAIのみ、フォールバックなし、短いタイムアウト
uv run python -m src.main \
  -g MALE -a 30 -lp OPENAI -m GPT_5_4 \
  -fs PRIMARY -am CLAUDE_HAIKU_4_5 -t 5 -df
```

#### 出力先の指定

```bash
# カスタム出力ディレクトリを指定
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -fs PRIMARY -am GPT_5_4 -t 10 \
  --output-directory ./custom_output

# 短縮オプション
uv run python -m src.main \
  -g MALE -a 28 -lp OPENAI -m GPT_5_4 \
  -fs PRIMARY -am CLAUDE_HAIKU_4_5 -t 10 \
  -od ./my_characters
```

#### 追加指示の使用

```bash
# キャラクターに追加指示を与える
uv run python -m src.main \
  -g FEMALE -a 22 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -fs PRIMARY -am GPT_5_4 -t 10 \
  --additional-instructions "魔法使いの見習いという設定で"
```

#### 複合オプション

```bash
# 本番環境向け設定例（長めのタイムアウト、代替プロバイダーフォールバック）
uv run python -m src.main \
  -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -fs ALTERNATIVE_PROVIDER \
  -am GPT_5_4 \
  -t 30 \
  -od ./outputs

# 開発/テスト環境向け設定例（短いタイムアウトでキャッシュフォールバックをテスト）
uv run python -m src.main \
  -g MALE -a 28 -lp OPENAI -m GPT_5_4 \
  -fs SEMANTIC_CACHE \
  -am CLAUDE_HAIKU_4_5 \
  -t 2
```

### 出力例

#### 正常実行時（プライマリプロバイダー成功）

**ファイル名**: `outputs/gemini_a1b2c3d4e5f6.json`

```json
{
    "first_name": "紗和",
    "last_name": "風間",
    "gender": "female",
    "age": 25,
    "personalities": [
        {
            "short_personality": "探究心旺盛で発明好き",
            "description": "幼少期から壊れたおもちゃを分解しては新しい使い方を考えるなど、常に「どうして」「どうすれば」を問い続ける性格。限られた素材から機能的なプロトタイプを作り上げる即興力と、仮説を何度も検証する粘り強さを持つ。問題の本質を見抜き、既存の道具やアイデアを組み合わせて斬新な解決策を提示することを好む。"
        },
        {
            "short_personality": "強い共感性と保護欲",
            "description": "他人の感情に敏感で、表情や声の僅かな変化から心の状態を読み取る能力に長けている。友人や見知らぬ人が困っていれば手を差し伸べ、具体的な助け（手作りの道具や時間を割くこと）で支えることをためらわない。一方で他人の問題を背負い込みやすく、境界線を引くことを学ぶ途中にあるため時折疲弊する。"
        },
        {
            "short_personality": "理想主義で反骨精神",
            "description": "不正や不合理を見過ごせない強い正義感を持ち、既存のルールや慣習に疑問を投げかけることを恐れない。技術や道具を使って透明性や公平性を高めることに情熱を燃やし、小さなコミュニティでの改善運動を自ら企画・実行する。頑固で衝動的な面もあるが、その情熱が周囲を巻き込んで現実的な変化を生む原動力となる。"
        }
    ]
}
```

**実行ログ例**:
```bash
$ uv run python -m src.main \
  --gender FEMALE \
  --age 25 \
  --llm-provider ANTHROPIC \
  --model CLAUDE_HAIKU_4_5 \
  --fallback-strategy PRIMARY \
  --alternative-model GPT_5_4 \
  --timeout 10
[2026-01-18 15:57:03,753] [INFO] [__main__] [main.py:126] [main] Starting character generation with the following parameters:
Gender: female
Age: 25
Additional instruction: 

LLM Parameters:
LLM provider: gemini
Model: global.anthropic.claude-haiku-4-5-20251001-v1:0
Fallback strategy: primary
Alternative model: openai.gpt-5.4
Output directory: outputs
Timeout: 10.0s
Fallback enabled: True
[2026-01-18 15:57:03,753] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:107] [_try_primary_request] Attempting primary request with gemini (timeout: 10.0s)
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:110] [_try_primary_request] Primary request succeeded with gemini
[2026-01-18 15:57:06,379] [DEBUG] [src.service.cache_manager] [cache_manager.py:152] [set] Cached response: 3266657fba01d24177cb086fc68d434618d120c158b04927ba7dd40b0f90199f
[2026-01-18 15:57:06,379] [INFO] [__main__] [main.py:207] [main] Response obtained via fallback strategy: primary
[2026-01-18 15:57:06,379] [INFO] [__main__] [main.py:214] [main] File saved to outputs/gemini_f1dfd6a2c45b40ff85f7e61d28e79fa7.json
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:277] [log_stats] === Fallback Statistics ===
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:278] [log_stats] Total Requests: 1
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:279] [log_stats] Primary Success: 1 (100.0%)
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:280] [log_stats] Parameter Cache Hits: 0 (0.0%)
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:281] [log_stats] Semantic Cache Hits: 0 (0.0%)
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:282] [log_stats] Total Cache Hit Rate: 0.0%
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:283] [log_stats] Alternative Provider: 0
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:284] [log_stats] Fallback Failures: 0 (0.0%)
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:285] [log_stats] Timeouts: 0
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:286] [log_stats] Errors: 0
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:287] [log_stats] Fallback Rate: 0.0%
[2026-01-18 15:57:06,379] [INFO] [src.service.fallback_coordinator] [fallback_coordinator.py:288] [log_stats] ===========================
```

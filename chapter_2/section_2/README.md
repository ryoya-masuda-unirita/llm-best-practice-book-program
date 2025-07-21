# LLMを使用したキャラクター生成ツール

## 概要

このプロジェクトは、LLM（大規模言語モデル）を使用してフィクションのキャラクターを生成するツールです。OpenAIとGeminiの両方のLLMプロバイダーをサポートし、構造化ログ機能を備えています。

## 主要な機能

### 1. キャラクター生成

- **詳細な性格特性**を持つフィクションキャラクターの生成
- **複数のLLMプロバイダー**（OpenAI、Gemini）のサポート
- **JSON形式**での一貫した出力

### 2. 構造化ログエントリ

- **JSON形式**での一貫したログ記録
- **時系列ベース**のディレクトリ構造（`./logs/2025/07/21/14/26/43/`）
- **プロンプト専用ストレージ**での秘匿性維持

### 3. プライバシー保護

- **PII自動マスキング**（メール、電話番号、クレジットカード、SSN）
- **設定可能**なマスキングの有効/無効

### 4. 非同期処理

- **バックグラウンド**でのプロンプト保存
- **レスポンス性能**への影響を最小化

## 使用方法

### 基本的な使用

```bash
# キャラクター生成の実行（デフォルトはGemini）
python -m src.main --llm-provider gemini --user-id user123

# OpenAIを使用する場合
python -m src.main --llm-provider openai --user-id user123
```

### プログラムでの使用例

```python
import asyncio
from src.logger import llm_logger
from src.model import LLMProvider

# LLMリクエストのログ記録
async def log_request():
    prompt_id = await llm_logger.log_llm_request(
        model="gemini-2.5-flash",
        provider=LLMProvider.GEMINI,
        input_text="プロンプトテキスト",
        output_text="生成されたキャラクター情報",
        temperature=2.0,
        latency_ms=1500,
        status_code=200,
        user_id="user123",
        metadata={"token_count": 755}
    )
    return prompt_id

# 非同期関数の実行
prompt_id = asyncio.run(log_request())
```

### アプリケーションでの統合例

```bash
# 既存のアプリケーションを実行（構造化ログ付き）
python -m src.main --llm-provider gemini --user-id user123

# 出力例:
# Result saved to: outputs/gemini_05bd53e6d6b24f738065f1e7aeb8920f.json
# Structured log prompt_id: cc9396b6-c588-4c4b-ae53-da8315e90c45
# Check ./logs/ and ./prompt_storage/ directories for structured logs
```

## 生成されるファイル構造

### 出力ファイル
```
./outputs/
└── gemini_05bd53e6d6b24f738065f1e7aeb8920f.json
```

### 構造化ログ
```
./logs/
└── 2025/
    └── 07/
        └── 21/
            └── 14/
                └── 26/
                    └── 43/
                        └── llm-log-20250721-142643.jsonl
```

### プロンプトストレージ
```
./prompt_storage/
└── 2025/
    └── 07/
        └── 21/
            └── 14/
                └── 26/
                    └── 43/
                        └── prompt-cc9396b6-c588-4c4b-ae53-da8315e90c45.json
```

## ログフィールド

| フィールド名 | 説明 |
|-------------|------|
| `timestamp` | ログの記録時刻 |
| `prompt_id` | プロンプトの一意識別子 |
| `user_id` | ユーザー識別子 |
| `model` | 使用したLLMモデル名 |
| `temperature` | 生成時の温度パラメータ |
| `input_text` | 入力プロンプト |
| `output_text` | LLMの出力 |
| `latency_ms` | 応答時間（ミリ秒） |
| `status_code` | API呼び出しのステータス |
| `provider` | LLMプロバイダー |
| `metadata` | 追加のメタデータ |

## 設定オプション

### ロガー設定

```python
from src.logger import LLMStructuredLogger

logger = LLMStructuredLogger(
    logs_base_dir="./custom_logs",           # ログディレクトリ
    prompts_base_dir="./custom_prompts",     # プロンプトディレクトリ
    enable_privacy_masking=True,             # プライバシーマスキング
    log_to_console=True                      # コンソール出力
)
```

### API設定

環境変数または.envrcファイルで以下の設定が必要です：

```
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## 分析とモニタリング

### ログ分析例

```bash
# 特定時間帯のログを確認
cat ./logs/2025/07/21/14/26/43/llm-log-20250721-142643.jsonl | jq '.'

# エラー率の計算
cat ./logs/2025/07/21/14/26/43/llm-log-20250721-142643.jsonl | jq -r 'select(.status_code >= 400) | .status_code' | wc -l

# 平均レスポンス時間
cat ./logs/2025/07/21/14/26/43/llm-log-20250721-142643.jsonl | jq -r '.latency_ms' | awk '{sum+=$1} END {print sum/NR}'
```

### 外部ツールとの連携

このログ形式は以下のツールと連携可能：
- **Datadog** - ログ集約・可視化
- **CloudWatch** - AWS環境での監視
- **Elasticsearch** - 検索・分析
- **BigQuery** - 大規模データ分析

## セキュリティ考慮事項

1. **アクセス制御**: プロンプトストレージへの適切な権限設定
2. **データ保持**: TTL設定による自動削除
3. **暗号化**: 機密データの暗号化保存（必要に応じて）
4. **マスキング**: PII情報の自動マスキング

## トラブルシューティング

### 一般的な問題

1. **ディレクトリ権限エラー**
   ```bash
   chmod 755 ./logs ./prompt_storage ./outputs
   ```

2. **非同期処理のエラー**
   - イベントループが適切に実行されているか確認
   - `asyncio.run()` を使用してメイン関数を実行

3. **ログファイルサイズ**
   - 大量のログでディスク容量を確認
   - ログローテーション設定を検討

4. **API認証エラー**
   - 環境変数が正しく設定されているか確認
   - API鍵の有効期限と権限を確認
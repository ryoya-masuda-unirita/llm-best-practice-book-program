# LLM API Gateway - 実装詳細

## 実装概要

このプロジェクトは、CLAUDE.mdで説明されているLLM APIゲートウェイパターンを完全実装したものです。以下の主要コンポーネントで構成されています。

## アーキテクチャコンポーネント

### 1. 認証・認可 (`auth.py`)

**目的**: ゲートウェイへのアクセスを制御し、APIキーをクライアントから隠蔽

**主要機能**:
- Bearer トークンによる認証
- トークンの検証とクライアント識別
- 不正アクセスの防止

**使用例**:
```python
from src.api_gateway.auth import verify_api_token

@app.post("/v1/generate")
async def generate(
    request: GatewayRequest,
    client_id: str = Depends(verify_api_token)
):
    # client_idは認証済みクライアントの識別子
    pass
```

### 2. APIキーマネージャー (`api_key_manager.py`)

**目的**: LLMプロバイダのAPIキーを一元管理

**主要機能**:
- 各プロバイダのAPIキーを安全に管理
- キーの取得と検証
- プロバイダサポート状況の確認

**利点**:
- APIキーの分散を防止
- キーローテーションが容易（設定ファイルのみ変更）
- セキュリティリスクの最小化

**実装**:
```python
from src.api_gateway.api_key_manager import api_key_manager

# プロバイダのAPIキーを取得
api_key = api_key_manager.get_api_key("openai")

# サポート確認
if api_key_manager.is_provider_supported("gemini"):
    # Geminiを使用
    pass
```

### 3. リトライハンドラー (`retry_handler.py`)

**目的**: 一時的な障害に対する堅牢な処理

**主要機能**:
- 指数バックオフによる自動リトライ
- タイムアウト制御
- 詳細なリトライログ

**動作例**:
```
Attempt 1: Failed → Wait 2^0 = 1s
Attempt 2: Failed → Wait 2^1 = 2s
Attempt 3: Failed → Wait 2^2 = 4s
Attempt 4: Success
```

**実装**:
```python
from src.api_gateway.retry_handler import retry_handler

result = await retry_handler.execute_with_retry(
    some_async_function,
    arg1,
    arg2,
    kwarg1=value
)
```

### 4. 監視・ログ (`monitoring.py`)

**目的**: 全てのリクエストを追跡し、可視化

**主要機能**:
- ユニークなリクエストIDの生成
- リクエスト/レスポンスのログ記録
- キャッシュヒット/ミスの追跡
- エラー発生時の詳細ログ

**ログフォーマット例**:
```
[REQUEST] id=abc123... | provider=openai | model=gpt-4o | client=client_dev
[RESPONSE] id=abc123... | status=SUCCESS | time=245.67ms | cache=FRESH
[CACHE HIT] id=def456... | provider=gemini | model=gemini-2.5-flash
[ERROR] id=ghi789... | type=TimeoutError | message=Request timeout
```

### 5. ミドルウェア (`middleware.py`)

**目的**: リクエスト/レスポンスのライフサイクル全体を追跡

**主要機能**:
- 全リクエストの処理時間計測
- カスタムヘッダーの追加
- エラーハンドリング

**追加されるヘッダー**:
- `X-Processing-Time-Ms`: 処理時間（ミリ秒）
- `X-Gateway-Version`: ゲートウェイのバージョン

### 6. ゲートウェイサービス (`gateway_service.py`)

**目的**: LLM APIへのリクエストを中継するコアロジック

**主要機能**:
- プロバイダごとのクライアント管理
- レスポンスキャッシング
- リクエストのルーティング
- エラーハンドリング

**処理フロー**:
```
1. リクエスト受信
2. キャッシュチェック
   ├─ キャッシュヒット → すぐに返却
   └─ キャッシュミス → 次へ
3. プロバイダ検証
4. リトライ付きでAPI呼び出し
5. レスポンスをキャッシュ
6. クライアントに返却
```

### 7. ゲートウェイサーバー (`gateway_server.py`)

**目的**: FastAPIアプリケーションとしてゲートウェイを提供

**エンドポイント**:
- `GET /health`: ヘルスチェック
- `POST /v1/generate`: LLM生成リクエスト

**セキュリティ機能**:
- 全エンドポイントで認証が必須
- グローバルエラーハンドラー
- 詳細なエラーレスポンス

### 8. サンプルクライアント (`example_client.py`)

**目的**: ゲートウェイの使用方法を示す実装例

**提供機能**:
- ゲートウェイへの接続
- 認証トークンの管理
- エラーハンドリング

## データモデル (`models.py`)

### GatewayRequest
```python
{
    "provider": "openai",
    "model": "gpt-4o-mini",
    "prompt": [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7,
    "api_token": "your-token"
}
```

### GatewayResponse
```python
{
    "content": "Hello! How can I help you?",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "processing_time_ms": 245.67,
    "request_id": "abc-123-def-456",
    "cached": false
}
```

## 設定管理

### 環境変数 (.env)

```bash
# プロバイダAPIキー（ゲートウェイのみが使用）
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key

# ゲートウェイ認証
GATEWAY_API_TOKEN=secure_token

# リトライ設定
GATEWAY_MAX_RETRIES=3
GATEWAY_RETRY_BACKOFF=2.0
GATEWAY_TIMEOUT=30.0

# キャッシュ設定
GATEWAY_ENABLE_CACHE=true
GATEWAY_CACHE_TTL=300
```

## デプロイメント

### ローカル開発

```bash
# ゲートウェイ起動
make run-api-gateway

# クライアント例を実行
make run-gateway-client
```

### Docker

```bash
# イメージビルド
docker-compose build

# サービス起動
docker-compose up -d

# ログ確認
docker-compose logs -f gateway
```

## 使用シナリオ

### シナリオ1: マイクロサービスからの利用

```python
# 商品推薦サービス
async def recommend_products(user_id: str):
    response = await gateway_client.generate(
        provider="openai",
        model="gpt-4o-mini",
        prompt=build_recommendation_prompt(user_id)
    )
    return parse_recommendations(response['content'])

# チャットボットサービス
async def chat_response(message: str):
    response = await gateway_client.generate(
        provider="gemini",
        model="gemini-2.5-flash",
        prompt=build_chat_prompt(message)
    )
    return response['content']
```

**利点**:
- 両サービスともAPIキーを持つ必要がない
- 同じリトライロジックの恩恵を受ける
- 利用状況が一元的に記録される

### シナリオ2: フロントエンドからの利用

```javascript
// ブラウザ上のJavaScript
async function generateText(prompt) {
    const response = await fetch('https://api.yourcompany.com/gateway/v1/generate', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer user-session-token',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            provider: 'openai',
            model: 'gpt-4o-mini',
            prompt: prompt,
            api_token: 'user-session-token'
        })
    });

    return await response.json();
}
```

**利点**:
- APIキーがブラウザに露出しない
- セッショントークンで認証
- 不正利用の防止

## 監視とデバッグ

### ログの見方

```
# 正常なリクエスト
[REQUEST] id=abc123... | provider=openai | model=gpt-4o | client=client_dev
[CACHE MISS] id=abc123... | provider=openai | model=gpt-4o
[RESPONSE] id=abc123... | status=SUCCESS | time=245.67ms | cache=FRESH

# キャッシュヒット
[REQUEST] id=def456... | provider=openai | model=gpt-4o | client=client_dev
[CACHE HIT] id=def456... | provider=openai | model=gpt-4o
[RESPONSE] id=def456... | status=SUCCESS | time=0ms | cache=CACHED

# エラー
[REQUEST] id=ghi789... | provider=openai | model=gpt-4o | client=client_dev
[ERROR] id=ghi789... | type=TimeoutError | message=Request timeout
[RESPONSE] id=ghi789... | status=FAILURE | time=30000ms | error=Request timeout
```

## パフォーマンス最適化

### キャッシュの効果

```
# キャッシュなし
Average response time: 250ms
API calls per day: 10,000
Cost per day: $10

# キャッシュあり（30%ヒット率）
Average response time: 175ms (30% faster)
API calls per day: 7,000 (30% reduction)
Cost per day: $7 (30% cheaper)
```

### リトライの効果

```
# リトライなし
Success rate: 95%
Failed requests: 500/10,000

# リトライあり（3回まで）
Success rate: 99.8%
Failed requests: 20/10,000
```

## セキュリティベストプラクティス

1. **APIトークンの管理**
   - 本番環境では強固なトークンを使用
   - 定期的なトークンローテーション
   - トークンの暗号化保存

2. **レート制限**
   - クライアントごとの制限実装を推奨
   - 異常な使用パターンの検出

3. **監査ログ**
   - 全てのリクエストを記録
   - 定期的なログ分析
   - 異常検知アラート

## トラブルシューティング

### よくある問題

**Q: ゲートウェイが起動しない**
```bash
# 環境変数の確認
cat .env | grep GATEWAY

# ポートの使用確認
lsof -i :8080
```

**Q: 認証エラーが発生する**
```bash
# トークンの確認
curl -H "Authorization: Bearer your-token" http://localhost:8080/health
```

**Q: キャッシュが効かない**
```bash
# 設定確認
echo $GATEWAY_ENABLE_CACHE
echo $GATEWAY_CACHE_TTL
```

## まとめ

この実装は、CLAUDE.mdで提案されたLLM APIゲートウェイパターンの完全な実装例です。

**実装した主要機能**:
1. ✅ 集約化されたAPIキー管理
2. ✅ 認証・認可機能
3. ✅ 指数バックオフを用いたリトライロジック
4. ✅ 構造化ログと監視
5. ✅ リクエスト/レスポンス追跡
6. ✅ レスポンスキャッシング
7. ✅ 複数プロバイダ対応
8. ✅ Docker対応

**得られるメリット**:
- セキュリティの向上
- 運用コストの削減
- 開発効率の向上
- システム全体の可視化
- プロバイダ切り替えの柔軟性

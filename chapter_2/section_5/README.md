# LLM ストリーミングと構造化ログ

このプロジェクトは、System.md 設計文書で定義されている LLM ストリーミングシステム用の構造化ログを実装しています。実装には HTTP クライアント操作に **httpx** を使用し、リアルタイムストリーミングには適切な **Server-Sent Events (SSE)** を使用しています。

## 機能

### 構造化ログ
- 標準化されたフィールドを持つ JSON 形式のログ
- ストリーム固有のメタデータ（stream_id、user_id、session_id）
- LLM プロバイダーの追跡
- パフォーマンスメトリクス（所要時間、トークン数）
- コンテキスト付きのエラー追跡

### ストリーミング実装
- 適切な SSE 形式を備えた FastAPI ベースのサーバー
- OpenAI と Gemini ストリーミング API のサポート
- SSE 解析機能を備えた httpx ベースの非同期クライアント
- イベント駆動型アーキテクチャによるリアルタイムトークン配信

### モニタリングとヘルスチェック
- ストリームメトリクスの収集と分析
- プロバイダーのパフォーマンス統計
- 劣化検出機能を備えたヘルスモニタリング
- 自動データクリーンアップ

## プロジェクト構造

```
src/
   logger.py           # ストリーミング固有のヘルパーを備えた構造化ログ
   streaming_server.py # ストリーミングエンドポイントを備えた FastAPI サーバー
   streaming_client.py # ストリームを消費するためのクライアント
   monitoring.py       # メトリクスとヘルスモニタリング
   config.py          # 設定管理
   llms.py            # LLM クライアント初期化
   model.py           # データモデル
   prompt.py          # プロンプト生成
   main.py            # オリジナルの CLI インターフェース
```

## 使用方法

### ストリーミングサーバーの起動:
```bash
python -m src.streaming_server
```

### ストリーミングクライアントの使用 (CLI):
```bash
python -m src.streaming_client --provider openai --user-id user123 --session-id session456
```

### Web ベースの SSE クライアント:
1. サーバーを起動
2. ブラウザで `http://localhost:8000` にアクセス
3. インタラクティブな Web インターフェースを使用して SSE ストリーミングをテスト

### システムのモニタリング:
- ヘルス: `GET /health`
- メトリクス: `GET /metrics`
- プロバイダー統計: `GET /metrics/{provider}`

## ログ形式

構造化ログは以下のフィールドを持つ JSON 形式で出力されます:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "src.streaming_server",
  "message": "Stream started",
  "stream_id": "abc123",
  "user_id": "user123", 
  "session_id": "session456",
  "llm_provider": "openai",
  "event_type": "stream_start"
}
```

## 記録される主要イベント

- `stream_start`: メタデータを含むストリーム開始
- `token_received`: 個々のトークン配信（DEBUG レベル）
- `stream_complete`: メトリクスを含むストリーム完了
- `stream_error`: コンテキスト付きのエラー状態
- `health_check`: システムヘルスステータス
- `monitoring_*`: メトリクスとクリーンアップイベント

## SSE イベント形式

サーバーは以下の形式で適切な Server-Sent Events を発行します:

```
event: stream-start
data: <stream_id>

event: token
data: <token_content>

event: stream-end
data: {"duration": 5.23, "tokens": 142}

event: error
data: {"error": "Error message", "type": "error_type"}
```

## 技術スタック

- **バックエンド**: SSE 用の StreamingResponse を備えた FastAPI
- **HTTP クライアント**: httpx (aiohttp の代替) 
- **ログ**: ストリームコンテキストを持つ構造化 JSON ログ
- **モニタリング**: カスタムメトリクス収集とヘルスチェック
- **フロントエンド**: バニラ HTML/JavaScript SSE クライアント

## 環境変数

- `LOG_LEVEL`: ログレベル (DEBUG, INFO, WARNING, ERROR)
- `OPENAI_API_KEY`: OpenAI API キー
- `GEMINI_API_KEY`: Google Gemini API キー
# Chapter 4 Section 3: LLMサービスインターフェイスの分離

## 概要

本プロジェクトは、**インターフェイス分離の原則（Interface Segregation Principle: ISP）** を適用したLLM APIサービスの実装例です。Anthropic Claude APIを使用し、テキスト生成とテキスト分類という2つの機能を、それぞれ独立したサービスインターフェイスとして定義することで、保守性と拡張性に優れたシステムを実現しています。

単一の巨大なLLMサービスクラスではなく、機能ごとに分離されたインターフェイスを採用することで、各コンポーネントは必要な機能にのみ依存できます。これにより、テストの簡素化、安全な機能拡張、そしてユーザープランに基づく柔軟なアクセス制御が可能になります。

## 機能

- **インターフェイス分離**: 機能ごとに独立したサービスインターフェイスを定義（ITextGenerationService、ITextClassificationService）
- **依存性注入コンテナ**: ServiceContainerによる集中的なサービス管理
- **プランベースのモデル制限**: ユーザープラン（Free/Standard）に応じた利用可能モデルの制御
- **構造化出力**: Pydanticモデルを活用した型安全なLLM応答
- **RESTful API**: FastAPIによる2つの独立したエンドポイント（/generate、/classify）
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **ログ出力**: 詳細なログ機能による実行状況の可視化
- **Docker対応**: コンテナ化による簡単なデプロイメント

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_3/
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（APIキー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   └── llm_server.py        # FastAPI アプリケーション
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # Anthropicクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticデータモデル定義
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成ロジック
│   └── service/
│       ├── __init__.py
│       ├── interfaces.py        # サービスインターフェイス定義（ISP）
│       ├── container.py         # 依存性注入コンテナ
│       ├── text_generation_service.py    # テキスト生成サービス実装
│       └── text_classification_service.py # テキスト分類サービス実装
├── .env.example                 # 環境変数設定のサンプル
├── docker-compose.yml           # Docker Compose設定
├── Dockerfile.web               # Webサーバー用Dockerfile
├── Makefile                     # 開発用コマンド定義
├── pyproject.toml               # プロジェクト依存関係
└── README.md                    # このファイル
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│  ┌─────────────────┐              ┌─────────────────────────┐  │
│  │  POST /generate │              │    POST /classify       │  │
│  └────────┬────────┘              └───────────┬─────────────┘  │
└───────────┼───────────────────────────────────┼─────────────────┘
            │                                   │
            ▼                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                      ServiceContainer (DI)                        │
│  ┌────────────────────────────┐  ┌────────────────────────────┐  │
│  │ get_text_generation_service│  │get_text_classification_service│
│  └─────────────┬──────────────┘  └──────────────┬─────────────┘  │
└────────────────┼────────────────────────────────┼─────────────────┘
                 │                                │
                 ▼                                ▼
┌────────────────────────────┐    ┌────────────────────────────────┐
│ ITextGenerationService     │    │ ITextClassificationService     │
│ (Abstract Interface)       │    │ (Abstract Interface)           │
└─────────────┬──────────────┘    └──────────────┬─────────────────┘
              │                                  │
              ▼                                  ▼
┌────────────────────────────┐    ┌────────────────────────────────┐
│ TextGenerationService      │    │ TextClassificationService      │
│ (Concrete Implementation)  │    │ (Concrete Implementation)      │
└─────────────┬──────────────┘    └──────────────┬─────────────────┘
              │                                  │
              └──────────────┬───────────────────┘
                             ▼
                 ┌───────────────────────┐
                 │   Anthropic Client    │
                 │   (AsyncAnthropic)    │
                 └───────────────────────┘
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - anthropic>=0.74.1
  - fastapi>=0.119.0
  - uvicorn>=0.37.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
cp .env.example .envrc

# .envrcを編集してAPIキーを設定
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

2. **依存関係のインストール**

```bash
uv sync
```

### 使用方法、実行方法

#### 開発サーバーの起動

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

#### Docker を使用した起動

```bash
make docker-build
make docker-up
make docker-logs   # ログの確認
make docker-down   # コンテナの停止
```

### API の使用例

#### 1. ヘルスチェック

```bash
$ curl http://localhost:8000/health | jq .

  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    51  100    51    0     0  10450      0 --:--:-- --:--:-- --:--:-- 12750
{
  "status": "healthy",
  "timestamp": 1769324595.5410314
}
```

#### 2. キャラクター生成（Free Plan）

```bash
$ curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "user_plan": "free",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "冒険家で勇敢な性格にしてください"
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1619  100  1395  100   224    139     22  0:00:10  0:00:10 --:--:--   290
{
  "character": {
    "first_name": "Akira",
    "last_name": "Nakamura",
    "gender": "female",
    "age": 25,
    "personalities": [
      {
        "short_personality": "勇敢で恐れ知らず",
        "description": "どんな危険な状況でも怯むことなく立ち向かう勇気を持っています。未知の領域への探検や困難な挑戦を前にしても、冷静さを保ちながら果敢に行動します。彼女の勇敢さは無謀さではなく、計算されたリスクテイクと強い意志に基づいています。"                                             
      },
      {
        "short_personality": "好奇心旺盛で探究心が強い",
        "description": "世界中の未踏の地や古代遺跡、失われた文明に対して尽きることのない興味を持っています。新しい文化や言語を学ぶことに情熱を注ぎ、常に次の冒険先を探しています。この探究心が彼女を世界各地の危険な場所へと駆り立てる原動力となっています。"                                       
      },
      {
        "short_personality": "独立心が強く自立している",
        "description": "他人に頼ることなく自分の力で問題を解決することを好みます。幼少期から一人で旅をしてきた経験から、サバイバルスキルや判断力を磨いてきました。チームワークも大切にしますが、最終的には自分自身の直感と能力を信じて行動します。"                                                 
      }
    ]
  },
  "model": "claude-sonnet-4-5",
  "processing_time_ms": 10019.26589012146
}
```

#### 3. テキスト分類

```bash
$ curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "user_plan": "free",
    "text": "この製品は素晴らしい！期待以上の品質でした。",
    "categories": ["ポジティブ", "ネガティブ", "中立"]
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   568  100   355  100   213     72     43  0:00:04  0:00:04 --:--:--   115
{
  "category": "ポジティブ",
  "model": "claude-sonnet-4-5",
  "processing_time_ms": 4895.140171051025,
  "classification_result": {
    "reasoning": "「素晴らしい」「期待以上の品質」という明確な肯定的表現が使用されており、製品に対する高い満足度が示されています。",
    "category": "ポジティブ",
    "confidence": "high"
  }
}
```

#### 4. プラン制限のエラー例

Free Planユーザーが上位モデルを使用しようとした場合：

```bash
$ curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus-4",
    "user_plan": "free",
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": null
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   274  100   102  100   172  17273  29127 --:--:-- --:--:-- --:--:-- 54800
{
  "detail": "Model 'claude-opus-4' is not available for free plan. Available models: claude-sonnet-4-5"
}
```

### 出力例

#### コンソールログ出力

```
[2025-10-25 10:30:45] [INFO] [src.service.text_generation_service] Generating character using Anthropic model: claude-sonnet-4-5
[2025-10-25 10:30:47] [INFO] [src.api.llm_server] Successfully generated character using claude-sonnet-4-5 for free plan in 1234.56ms

[2025-10-25 10:31:12] [INFO] [src.service.text_classification_service] Classifying text using Anthropic model: claude-sonnet-4-5
[2025-10-25 10:31:13] [INFO] [src.service.text_classification_service] Classification result: ポジティブ (confidence: high) - 「素晴らしい」などの肯定的表現が含まれているため
[2025-10-25 10:31:13] [INFO] [src.api.llm_server] Successfully classified text using claude-sonnet-4-5 for free plan in 789.12ms. Result: ポジティブ
```

#### プラン制限の警告ログ

```
[2025-10-25 10:32:00] [WARNING] [src.api.llm_server] Validation error: Model 'claude-opus-4' is not available for free plan. Available models: claude-sonnet-4-5
```

# Chapter 4 Section 1: 状態変化と読み取りの責任分離（LLMシステムのCQRS）

## 概要

このプロジェクトは、**CQRS（Command Query Responsibility Segregation）パターン**を用いたLLMシステムの実装サンプルです。状態を変更する処理（Command）とデータを読み取る処理（Query）を明確に分離することで、高スループットと低レイテンシを両立させるアーキテクチャを実現します。

キャラクター生成システムを通じて、大規模なLLMアプリケーションにおける知識ベースの管理手法を学ぶことができます。生成されたキャラクター情報は、Gemini Embedding APIを使用してベクトル化され、ChromaDBに非同期で保存されます。ユーザーは保存された知識ベースに対して、セマンティック検索を用いて高速に情報を取得できます。

## 機能

### コア機能
- **CQRS実装**: Command（書き込み）とQuery（読み取り）の完全な責任分離
- **非同期知識登録**: バックグラウンドでの高スループット書き込み処理
- **同期知識検索**: 低レイテンシの検索API
- **カスタムEmbedding**: Gemini APIによる高品質なベクトル生成（768次元）
- **ベクトルデータベース**: ChromaDBを使用したセマンティック検索

### LLM統合
- **Gemini対応**: Google Gemini（2.5 Pro, 2.5 Flash, 2.5 Flash Lite）をサポート
- **構造化出力**: Pydanticモデルによる型安全なLLM応答
- **自動知識保存**: キャラクター生成時に自動的に知識ベースへ保存

### インフラストラクチャ
- **Docker Compose対応**: ChromaDB、LLMサーバー、知識ベースサーバーの統合デプロイ
- **永続化**: Docker volumeによるデータ永続化
- **ヘルスチェック**: サービス間の依存関係管理と健全性監視
- **環境切り替え**: ローカル開発とDocker環境のシームレスな切り替え

## プロジェクト構成

### ディレクトリ構成

```
chapter_3/section_5/
├── src/
│   ├── __init__.py                 # パッケージ初期化、共有ThreadPoolExecutor
│   ├── config.py                   # 設定管理（APIキー読み込み）
│   ├── logger.py                   # ロギング設定
│   ├── api/
│   │   ├── __init__.py
│   │   ├── llm_server.py           # LLM APIサーバー（Port 8000）
│   │   └── knowledge_server.py     # 知識ベースAPIサーバー（Port 8001）
│   ├── client/
│   │   ├── __init__.py
│   │   ├── llm_client.py           # Gemini APIクライアント初期化
│   │   └── chromadb_client.py      # ChromaDBクライアント（ローカル/リモート対応）
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py                # LLMデータモデル定義
│   │   └── knowledge.py            # 知識ベース用データモデル（Command/Query）
│   ├── service/
│   │   ├── __init__.py
│   │   ├── request_llm.py          # LLMリクエストハンドラ
│   │   ├── embedding_service.py    # Gemini Embedding生成サービス
│   │   ├── knowledge_command.py    # Commandサイド（非同期書き込み）
│   │   └── knowledge_query.py      # Queryサイド（同期読み取り）
│   └── prompt/
│       ├── __init__.py
│       └── prompt.py               # プロンプト生成ロジック
├── data/
│   └── chromadb/                   # ローカル開発時のChromaDBデータ（自動作成）
├── docker-compose.yml              # Docker Compose設定
├── pyproject.toml                  # プロジェクト依存関係
└── README.md                       # このファイル
```

### アーキテクチャ

このプロジェクトは、CQRSパターンに基づく3層アーキテクチャで構成されています：

```
┌─────────────────────────────────────────────────────────────┐
│                     ユーザーリクエスト                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────┴────────────┐
       │                        │
       ▼                        ▼
┌─────────────┐        ┌─────────────────┐
│ LLMサーバー  │        │知識ベースサーバー│
│  Port 8000  │        │   Port 8001     │
│             │        │                 │
│キャラクター  │        │  ┌───────────┐  │
│    生成     │        │  │ Command   │  │
│  (Gemini)   │        │  │  (書込)   │  │
│             │        │  │  非同期   │  │
└──────┬──────┘        │  └─────┬─────┘  │
       │               │        │        │
       │ バックグラウンド│        │        │
       │   タスク      │◄───────┘        │
       │               │                 │
       │               │  ┌───────────┐  │
       │               │  │  Query    │  │
       │               │  │  (読取)   │  │
       │               │  │   同期    │  │
       │               │  └─────┬─────┘  │
       └───────────────┴────────┴─────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    ChromaDB     │
              │  Vector Store   │
              │  Port 8002      │
              └─────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Gemini API     │
              │  Embedding/LLM  │
              └─────────────────┘
```

**処理フロー**:

1. **キャラクター生成（LLMサーバー）**
   - ユーザーがキャラクター生成をリクエスト
   - Gemini を使用してキャラクター情報を生成
   - レスポンスを即座にユーザーに返却
   - バックグラウンドでCommand処理を実行

2. **Command処理（非同期書き込み）**
   - キャラクター情報からテキスト表現を生成
   - Gemini Embedding APIでベクトル化（768次元）
   - ChromaDBにベクトルとメタデータを保存
   - 高スループット、結果整合性

3. **Query処理（同期読み取り）**
   - ユーザーが検索クエリを送信
   - Gemini Embedding APIでクエリをベクトル化
   - ChromaDBでベクトル類似度検索を実行
   - 類似度スコア付きで結果を返却
   - 低レイテンシ、即座に応答

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **Docker**: 20.10以上（Docker Compose使用時）
- **依存ライブラリ**:
  - chromadb >= 1.3.0
  - fastapi >= 0.119.0
  - google-genai >= 1.45.0
  - pydantic >= 2.12.2
  - uvicorn >= 0.37.0

### セットアップ

#### Docker Compose

1. **環境変数の設定**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **サービスの起動**

```bash
# すべてのサービスを起動
docker-compose up -d

# サービスの状態確認
docker-compose ps
```

3. **ヘルスチェック**

```bash
# LLMサーバー
curl http://localhost:8000/health

# 知識ベースサーバー
curl http://localhost:8001/health
```

### 使用方法、実行方法

#### 1. キャラクターの生成（自動的に知識ベースに保存）

```bash
$ curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "character_request": {
      "gender": "female",
      "age": 25,
      "additional_instructions": "勇敢な戦士キャラクターを作成してください"
    }
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1126  100   916  100   210    275     63  0:00:03  0:00:03 --:--:--   338
{
  "character": {
    "first_name": "エルミナ",
    "last_name": "ストームハート",
    "gender": "female",
    "age": 25,
    "personalities": [
      {
        "short_personality": "勇敢",
        "description": "どんな困難や危険にも臆することなく立ち向かう生来の勇気を持っている。常に最前線に立ち、仲間や弱き者を守るために自らの命を顧みない。"                                                                                                                                         
      },
      {
        "short_personality": "決断力がある",
        "description": "一度決めた目標は決して諦めず、粘り強く達成しようと努力する。逆境に直面しても、不屈の精神で道を切り開き、困難を乗り越える。"                                                                                                                                                 
      },
      {
        "short_personality": "忠実",
        "description": "仲間や大義に対して揺るぎない忠誠心を持つ。信頼する者には献身的であり、裏切りを決して許さない。彼らのためにどんな犠牲も厭わない。"                                                                                                                                           
      }
    ]
  },
  "model": "gemini-2.5-flash",
  "processing_time_ms": 3317.896842956543
}
```

**処理フロー**:
1. キャラクターが即座に生成され、レスポンスが返却される
2. バックグラウンドでGemini Embedding APIでベクトル化（768次元）
3. ChromaDBにベクトルとメタデータが保存される

#### 2. 知識ベースの検索

```bash
$ curl -X POST "http://localhost:8001/query/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "勇敢な戦士",
    "limit": 5
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1291  100  1234  100    57   2719    125 --:--:-- --:--:-- --:--:--  2843
{
  "results": [
    {
      "id": "0ad2c003-4899-41ac-a1cb-18ce824a5260",
      "character_request": {
        "gender": "female",
        "age": 25,
        "additional_instructions": "勇敢な戦士キャラクターを作成してください"
      },
      "character_response": {
        "first_name": "エルミナ",
        "last_name": "ストームハート",
        "gender": "female",
        "age": 25,
        "personalities": [
          {
            "short_personality": "勇敢",
            "description": "どんな困難や危険にも臆することなく立ち向かう生来の勇気を持っている。常に最前線に立ち、仲間や弱き者を守るために自らの命を顧みない。"                                                                                                                                     
          },
          {
            "short_personality": "決断力がある",
            "description": "一度決めた目標は決して諦めず、粘り強く達成しようと努力する。逆境に直面しても、不屈の精神で道を切り開き、困難を乗り越える。"                                                                                                                                             
          },
          {
            "short_personality": "忠実",
            "description": "仲間や大義に対して揺るぎない忠誠心を持つ。信頼する者には献身的であり、裏切りを決して許さない。彼らのためにどんな犠牲も厭わない。"                                                                                                                                       
          }
        ]
      },
      "model": "gemini-2.5-flash",
      "processing_time_ms": 3317.896842956543,
      "similarity_score": 0.70917124,
      "created_at": 1769323983.9810076
    }
  ],
  "total_count": 1,
  "query_time_ms": 444.03672218322754
}
```

#### 3. 統計情報の取得

```bash
$ curl http://localhost:8001/query/stats | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    93  100    93    0     0   4696      0 --:--:-- --:--:-- --:--:--  4894
{
  "total_items": 1,
  "models_distribution": {
    "gemini-2.5-flash": 1
  },
  "timestamp": 1769324039.6702378
}
```

#### 4. 直接知識を登録（Command API）

```bash
$ curl -X POST "http://localhost:8001/command/register" \
  -H "Content-Type: application/json" \
  -d '{
    "character_request": {
      "gender": "male",
      "age": 30,
      "additional_instructions": "冷静沈着"
    },
    "character_response": {
      "first_name": "太郎",
      "last_name": "山田",
      "gender": "male",
      "age": 30,
      "personalities": [
        {"short_personality": "冷静", "description": "どんな状況でも冷静さを保つ"},
        {"short_personality": "論理的", "description": "論理的思考を重視する"},
        {"short_personality": "誠実", "description": "約束を必ず守る"}
      ]
    },
    "model": "gemini-2.5-flash",
    "prompt": [],
    "processing_time_ms": 1000.0
  }' | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   778  100   126  100   652  24667   124k --:--:-- --:--:-- --:--:--  151k
{
  "job_id": "f534eedf-5ecf-4fef-8b29-f0d8432164b3",
  "status": "accepted",
  "message": "Knowledge registration queued for processing"
}
```

### 出力例

#### キャラクター生成のログ

```
[2025-10-29 10:30:45] [INFO] [llm_server] Generating character with gemini/gemini-2.5-flash
[2025-10-29 10:30:47] [INFO] [llm_server] Successfully generated character in 1250.50ms
[2025-10-29 10:30:47] [INFO] [llm_server] Queued knowledge registration for background processing
```

#### Command処理（非同期）のログ

```
[2025-10-29 10:30:47] [INFO] [knowledge_command] Accepting knowledge registration command with job_id: a1b2c3d4-...
[2025-10-29 10:30:47] [INFO] [knowledge_command] Generating Gemini embedding for job_id: a1b2c3d4-...
[2025-10-29 10:30:48] [INFO] [knowledge_command] Successfully stored knowledge with job_id: a1b2c3d4-... (embedding dim: 768)
```

#### Query処理（同期）のログ

```
[2025-10-29 10:31:00] [INFO] [knowledge_query] Searching knowledge base with query: 勇敢な戦士...
[2025-10-29 10:31:00] [INFO] [knowledge_query] Search completed in 45.20ms, found 3 results
```

# LLMを使用した基本的なキャラクター生成ツール

## 概要

このプロジェクトは、LLM（大規模言語モデル）を使用してフィクションのキャラクターを生成する基本的なツールです。OpenAIとGeminiの両方のLLMプロバイダーをサポートし、構造化されたJSON形式で出力を提供します。

## 主要な機能

### 1. キャラクター生成

- **詳細な性格特性**を持つフィクションキャラクターの生成
- **複数のLLMプロバイダー**（OpenAI、Gemini）のサポート
- **JSON形式**での一貫した出力

### 2. LLMプロバイダー

- **OpenAI**: GPT-4o-miniモデルを使用
- **Gemini**: Gemini-2.5-Flashモデルを使用

### 3. 構造化データ

- **Pydanticモデル**を使用した型安全な応答処理
- **検証済み出力**で一貫したデータ構造を保証

## 使用方法

### 基本的な使用

```bash
# キャラクター生成の実行（デフォルトはGemini）
python -m src.main

# OpenAIを使用する場合
python -m src.main --llm-provider openai
```

### コマンドラインオプション

```bash
# ヘルプの表示
python -m src.main --help

# 利用可能なオプション:
# --llm-provider, -lp [openai|gemini]  使用するLLMプロバイダー（デフォルト: gemini）
```

## 出力例

生成されたキャラクターデータは`outputs`ディレクトリに保存されます。ファイル名は使用したプロバイダーと一意のIDを含みます（例：`gemini_213aae3ccf6648b392c6ee51f0a3bfeb.json`）。

出力JSONの例：

```json
{
  "first_name": "太郎",
  "last_name": "山田",
  "gender": "male",
  "age": 28,
  "personalities": [
    {
      "short_personality": "冒険好き",
      "description": "新しい場所や経験を常に求めている。未知の領域に足を踏み入れることに喜びを感じる。"
    },
    {
      "short_personality": "分析的",
      "description": "物事を論理的に考え、詳細に分析することを好む。問題解決において体系的なアプローチを取る。"
    },
    {
      "short_personality": "忠実",
      "description": "友人や家族に対して非常に忠実で、困っている人を助けることを厭わない。信頼関係を何よりも大切にする。"
    }
  ]
}
```

## 設定

環境変数または.envファイルで以下の設定が必要です：

```
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## 技術的詳細

### キャラクターモデル

キャラクターデータは以下のフィールドを含みます：

- `first_name`: キャラクターの名
- `last_name`: キャラクターの姓
- `gender`: 性別（"male"または"female"）
- `age`: 年齢（0〜100の整数）
- `personalities`: 性格特性のリスト（3つの特性）
  - `short_personality`: 性格の短い説明
  - `description`: 性格の詳細な説明

### プロンプト設計

システムプロンプトは以下の指示を含みます：

1. 創造的なキャラクタージェネレーターとして機能する
2. 詳細な情報を持つフィクションのキャラクターを生成する
3. 指定された構造に厳密に従ったJSONオブジェクトで応答する
4. 応答は有効なJSONであること
5. すべての必須フィールドが含まれていること
6. 性別は「female」または「male」のいずれかであること
7. 年齢は0から100の間であること
8. 正確に3つの性格特性が提供されていること

## アーキテクチャ

### 主要コンポーネント

- **main.py**: メインのエントリーポイント、LLMプロバイダーの選択と実行を管理
- **model.py**: Pydanticを使用したデータモデルの定義
- **prompt.py**: LLMへのプロンプトの生成
- **llms.py**: OpenAIとGeminiのクライアント設定
- **config.py**: 環境変数と設定の管理
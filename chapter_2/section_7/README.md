# キャラクタージェネレーター

このプロジェクトは、大規模言語モデル（LLM）を使用して、詳細な情報を持つフィクションのキャラクターを生成するツールです。OpenAIとGoogle Geminiの両方のLLMプロバイダーをサポートしており、生成されたキャラクターの品質を評価するためのLLM-as-a-Judge機能も備えています。

## 機能

- OpenAIまたはGoogle Geminiを使用したキャラクター生成
- 生成されたキャラクターのLLMによる評価（オプション）
- コマンドラインインターフェース
- 結果のJSON形式での保存
- 非同期API呼び出しによる高パフォーマンス

## 必要条件

- Python 3.13.2以上
- 以下のAPIキー：
  - OpenAI API（OpenAIプロバイダーを使用する場合）
  - Google Gemini API（Geminiプロバイダーを使用する場合）

## インストール

1. リポジトリをクローンします：

```bash
git clone <repository-url>
cd chapter_2/section_7
```

2. 依存関係をインストールします：

```bash
pip install -e .
```

3. `.env`ファイルを作成し、APIキーを設定します：

```
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## 使用方法

コマンドラインから以下のコマンドを実行します：

```bash
python -m src.main [オプション]
```

### オプション

- `--llm-provider`, `-lp`: キャラクター生成に使用するLLMプロバイダー（`openai`または`gemini`、デフォルトは`gemini`）
- `--judge-provider`, `-jp`: 評価に使用するLLMプロバイダー（`openai`または`gemini`、デフォルトは`gemini`）
- `--enable-judge`, `--judge`: 生成後にLLM-as-a-Judge評価を有効にする（フラグ、デフォルトは無効）

### 例

```bash
# Geminiを使用してキャラクターを生成
python -m src.main

# OpenAIを使用してキャラクターを生成
python -m src.main --llm-provider openai

# Geminiを使用してキャラクターを生成し、OpenAIを使用して評価
python -m src.main --enable-judge --judge-provider openai
```

## 出力

生成されたキャラクターと評価結果（有効な場合）は、`outputs`ディレクトリにJSON形式で保存されます。出力ファイル名は使用されたLLMプロバイダーと一意のIDに基づいています。

### キャラクター出力形式

```json
{
  "first_name": "名前",
  "last_name": "苗字",
  "gender": "female",
  "age": 25,
  "personalities": [
    {
      "short_personality": "短い性格特性の説明1",
      "description": "詳細な性格特性の説明1"
    },
    {
      "short_personality": "短い性格特性の説明2",
      "description": "詳細な性格特性の説明2"
    },
    {
      "short_personality": "短い性格特性の説明3",
      "description": "詳細な性格特性の説明3"
    }
  ]
}
```

※ `gender`は"female"または"male"、`age`は0〜100の範囲の値になります。

### 評価出力形式

評価が有効な場合、出力には以下の評価結果も含まれます：

```json
{
  "accuracy_score": 4,
  "completeness_score": 5,
  "clarity_score": 3,
  "average_score": 4.0,
  "feedback": "評価フィードバック"
}
```

※ 各スコアは0〜5の範囲の値になります。

## プロジェクト構造

- `src/main.py`: メインエントリーポイントとコマンドラインインターフェース
- `src/model.py`: データモデルの定義
- `src/prompt.py`: LLMプロンプトの生成
- `src/judge.py`: キャラクター評価ロジック
- `src/llms.py`: LLMプロバイダーとの統合
- `src/config.py`: 設定管理
- `outputs/`: 生成されたキャラクターと評価結果

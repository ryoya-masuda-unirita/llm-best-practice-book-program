# Chapter 2 Section 9: LLMを安定して使うために自由度を下げる

## 概要

このプロジェクトは、**ユーザー入力の自由度を制限することでLLMアプリケーションの安定性を向上させる**という重要な設計原則を実践的に学ぶためのサンプルコードです。**Streamlit**を使用したインタラクティブなWebアプリケーションを通じて、自由形式の入力と構造化されたフォーム入力を比較し、それぞれのトレードオフを体験できます。

LLMは柔軟性が高い一方で、その柔軟性がアプリケーションの予測不可能性やエラーの原因となることがあります。本セクションでは、**CharacterRequest**モデルを導入してユーザー入力を構造化し、内部的なプロンプト生成の柔軟性を維持しながら、外部からの入力を適切に制約する方法を示します。

OpenAI GPT-5/4.1/4oシリーズとGoogle Gemini 2.5シリーズの両方に対応し、複数のモデルを選択できるようになっています。

## 機能

### 主要機能

- **2つのインターフェース比較**:
  - **自由形式タブ**: ユーザーが任意のテキストを入力（柔軟性高・安定性低）
  - **構造化フォームタブ**: 制約されたフィールドで入力（柔軟性低・安定性高）
- **モデル選択サイドバー**: OpenAI/Geminiの複数モデルから選択可能
- **リアルタイム生成**: 入力後すぐにキャラクター情報を生成
- **2つの出力形式**:
  - JSON形式（技術者向け）
  - フォーマット済みプロフィール（一般ユーザー向け）
- **内部プロンプト表示**: システムが実際に送信したプロンプトを確認可能
- **教育的メッセージング**: 各インターフェースのトレードオフを説明

### 技術的機能

- **リクエスト/レスポンスパターン**: 入力（CharacterRequest）と出力（CharacterResponse）を明確に分離
- **構造化プロンプト生成**: ユーザー入力をバリデーション済みの構造化データからプロンプトに変換
- **型安全性**: Pydanticによる厳密な型検証
- **非同期処理**: async/awaitパターンによる効率的なAPI呼び出し
- **環境変数管理**: 安全なAPIキー管理
- **詳細なログ出力**: 実行状況の可視化

## プロジェクト構成

### ディレクトリ構成

```
chapter_2/section_9/
├── app.py                       # Streamlitアプリケーション（本セクション独自）
├── src/
│   ├── __init__.py              # パッケージ初期化
│   ├── config.py                # 設定管理（API キー読み込み）
│   ├── logger.py                # ロギング設定
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLMクライアント初期化
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py             # Pydanticモデル（CharacterRequest追加）
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # プロンプト生成（リクエストベース）
│   └── service/
│       ├── __init__.py
│       └── request_llm.py       # LLM呼び出しサービス
├── outputs/                     # 生成結果の保存先（自動作成）
├── .envrc.example               # 環境変数設定のサンプル
├── pyproject.toml               # プロジェクト依存関係（streamlit含む）
├── Makefile                     # ビルド・lint コマンド
├── README.md                    # このファイル
└── CLAUDE.md                    # プロジェクト状態レポート
```

### アーキテクチャ

このプロジェクトは、Section 1の基本アーキテクチャを拡張し、**リクエスト層**を追加した4層構造になっています：

```
┌─────────────────────────────────────────┐
│      Presentation Layer                 │
│  - Streamlit Web UI (app.py)            │  ← 新規追加
│  - ユーザー入力の収集と表示             │
│  - インタラクティブな比較デモ           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Request Layer                      │  ← 新規追加
│  - CharacterRequest (model.py)          │
│  - 入力バリデーションと構造化           │
│  - ドメインモデルへの変換               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Business Logic Layer               │
│  - プロンプト生成 (prompt.py)           │
│  - LLM呼び出し (request_llm.py)         │
│  - CharacterResponse (model.py)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Infrastructure Layer               │
│  - 設定管理 (config.py)                 │
│  - ログ管理 (logger.py)                 │
│  - LLMクライアント (llm_client.py)      │
│  - 外部API (OpenAI, Gemini)             │
└─────────────────────────────────────────┘
```

**Section 1との主な違い**:
- **Presentation Layer**: Streamlit Web UIを追加し、2つのインターフェース（自由形式 vs 構造化）を比較
- **Request Layer**: CharacterRequestモデルで入力を構造化・バリデーション
- **Interactive Demo**: ユーザーが実際に体験しながら設計原則を学べる教育的インターフェース

### 実装の詳細

#### 1. リクエストモデル (`src/model/model.py`)

**新規追加**: ユーザー入力を構造化するためのモデル

```python
class CharacterRequest(BaseModel):
    """キャラクター生成リクエストを表すモデル（ユーザー入力の構造化）"""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="forbid",
    )

    gender: Gender = Field(..., description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    additional_instructions: str | None = Field(
        default=None,
        description="Additional instructions for character generation.",
    )
```

**ポイント**:
- `gender`: 列挙型で選択肢を制限（FEMALE/MALE のみ）
- `age`: 0-100の範囲に制約（`ge=0, le=100`）
- `additional_instructions`: オプションで追加の自由記述を許可
- `frozen=True`により不変オブジェクトを保証
- `extra="forbid"`で予期しないフィールドを拒否

#### 2. レスポンスモデル (`src/model/model.py`)

Section 1から継承したCharacterResponseモデル（変更なし）：

```python
class CharacterResponse(BaseModel):
    """LLMからのレスポンスを表すモデル（構造化出力）"""

    first_name: str
    last_name: str
    gender: Gender
    age: int  # 0-100
    personalities: list[CharacterPersonality]  # 正確に3つの性格特性
```

#### 3. 構造化プロンプト生成 (`src/prompt/prompt.py`)

CharacterRequestから動的にプロンプトを生成：

```python
def make_prompt(character_request: CharacterRequest) -> list:
    """CharacterRequestからプロンプトを生成"""
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    return [
        {
            "role": "system",
            "content": f"""あなたは創造的なキャラクタージェネレーターです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

【重要な制約】
- personalitiesは正確に3つの要素を含む配列である必要があります
- short_personalityは5文字以下の簡潔な表現にしてください
- descriptionは詳細な説明文にしてください""",
        },
        {
            "role": "user",
            "content": f"""フィクションの架空の人物のキャラクター情報を生成してください。

性別は「{character_request.gender.value}」、年齢は「{character_request.age}」歳です。
{character_request.additional_instructions or ""}""",
        },
    ]
```

**ポイント**:
- リクエストの構造化データ（性別・年齢）をプロンプトに埋め込み
- 追加指示は任意で含める
- システムプロンプトでレスポンススキーマを明示
- ユーザープロンプトで具体的な要求を伝達

#### 4. Streamlitアプリケーション (`app.py`)

**タブ1: 自由形式インターフェース**

```python
with tab1:
    st.header("🎲 自由形式プロンプト入力")
    st.info("""
    このインターフェースでは、任意のテキストプロンプトを入力できます。
    柔軟性は高いですが、予期しない結果や不安定な動作のリスクがあります。
    """)

    free_text = st.text_area(
        "プロンプトを自由に入力してください",
        placeholder="例: 30歳の女性キャラクターを作成してください",
        height=150,
    )

    if st.button("生成", key="free_form_button"):
        # 自由形式の入力を処理
        # エラーハンドリングの難しさを示す
```

**タブ2: 構造化フォームインターフェース**

```python
with tab2:
    st.header("📋 構造化フォーム入力")
    st.success("""
    このインターフェースでは、明確に定義されたフィールドに入力します。
    予測可能で安定した結果が得られ、エラーハンドリングも容易です。
    """)

    # 構造化された入力フィールド
    col1, col2 = st.columns(2)
    with col1:
        gender = st.selectbox(
            "性別",
            options=[Gender.FEMALE, Gender.MALE],
            format_func=lambda x: {"female": "女性", "male": "男性"}[x.value],
        )

    with col2:
        age = st.number_input(
            "年齢",
            min_value=0,
            max_value=100,
            value=25,
            step=1,
        )

    additional_instructions = st.text_area(
        "追加の指示（任意）",
        placeholder="例: ファンタジー世界の魔法使いにしてください",
        height=100,
    )

    if st.button("生成", key="structured_button"):
        # CharacterRequestを作成してバリデーション
        character_request = CharacterRequest(
            gender=gender,
            age=age,
            additional_instructions=additional_instructions or None,
        )
        # 構造化されたデータから安全にプロンプトを生成
```

**モデル選択サイドバー**:

```python
with st.sidebar:
    st.header("⚙️ モデル設定")

    llm_provider = st.selectbox(
        "LLMプロバイダー",
        options=[LLMProvider.OPENAI, LLMProvider.GEMINI],
    )

    # プロバイダーに応じたモデル選択
    if llm_provider == LLMProvider.OPENAI:
        model = st.selectbox("モデル", options=list(OpenAIModel))
    else:
        model = st.selectbox("モデル", options=list(GeminiModel))
```

#### 5. サービス層 (`src/service/request_llm.py`)

プロンプトとモデルを受け取り、LLMを呼び出す：

```python
async def request_openai(
    prompt: list, model: OpenAIModel
) -> CharacterResponse:
    """OpenAI APIでキャラクター生成"""
    result = await openai_client.beta.chat.completions.parse(
        model=model.value,
        messages=prompt,
        response_format=CharacterResponse,
        temperature=1.0,
    )
    return result.choices[0].message.parsed


async def request_gemini(
    prompt: list, model: GeminiModel
) -> CharacterResponse:
    """Gemini APIでキャラクター生成"""
    result = await google_genai_client.aio.models.generate_content(
        model=model.value,
        contents=prompt[-1]["content"],
        config=GenerateContentConfig(
            system_instruction=prompt[0]["content"],
            response_mime_type="application/json",
            response_schema=CharacterResponse,
            temperature=2.0,
        ),
    )
    return result.parsed
```

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - **streamlit>=1.50.0** ← Section 9独自の追加
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### セットアップ

1. **環境変数ファイルの作成**

```bash
# .envrc.exampleをコピーして.envrcを作成
cp .envrc.example .envrc

# エディタで.envrcを開き、APIキーを設定
# .envrc
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

2. **依存関係のインストール**

```bash
# uvを使用する場合（推奨）
uv sync

# pipを使用する場合
pip install -e .
```

### 使用方法、実行方法

#### Streamlit Webアプリケーション

```bash
# Webアプリケーションを起動
streamlit run app.py
```

ブラウザが自動的に開き（通常は `http://localhost:8501`）、以下の操作が可能になります：

1. **サイドバーでモデルを選択**
   - LLMプロバイダー（OpenAI/Gemini）を選択
   - 使用するモデルを選択

2. **タブ1（自由形式）で試す**
   - テキストエリアに任意のプロンプトを入力
   - 「生成」ボタンをクリック
   - 結果とプロンプトを確認

3. **タブ2（構造化フォーム）で試す**
   - 性別をドロップダウンから選択
   - 年齢を数値入力（0-100）
   - 必要に応じて追加指示を入力
   - 「生成」ボタンをクリック
   - 結果とプロンプトを確認

4. **2つのアプローチを比較**
   - 使いやすさ
   - 結果の安定性
   - エラーハンドリングの容易さ

#### 利用可能なモデル

**OpenAI**:
- `gpt-5`
- `gpt-5-mini`
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4o-2024-11-20`
- `gpt-4o-2024-08-06`

**Gemini**:
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

### 出力例

**構造化フォームでの入力**:
- 性別: 男性
- 年齢: 28
- 追加指示: "サイバーパンク世界のハッカーにしてください"

**生成結果（フォーマット済み）**:
```
📋 キャラクタープロフィール

👤 基本情報
名前: 蒼 雨宮
性別: male
年齢: 28歳

🎭 性格特性

1. 孤独な天才
   常に一人で作業することを好み、複雑なシステムを解読する能力に長けている。
   社会的なスキルは低いが、デジタル世界では無敵の存在。

2. 反骨精神
   権威や大企業に対して強い不信感を持ち、情報の自由を信じている。
   正義感が強く、弱者を守るために自らのスキルを使う。

3. 完璧主義
   すべてのコードに最高の基準を求め、セキュリティホールを決して許さない。
   細部へのこだわりが時に強迫観念となることもある。
```

**内部プロンプト（展開可能セクション）**:
```json
[
  {
    "role": "system",
    "content": "あなたは創造的なキャラクタージェネレーターです。\n以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：\n\n..."
  },
  {
    "role": "user",
    "content": "フィクションの架空の人物のキャラクター情報を生成してください。\n\n性別は「male」、年齢は「28」歳です。\nサイバーパンク世界のハッカーにしてください"
  }
]
```

### テスト方法

```bash
# アプリケーションを起動
streamlit run app.py
```

**テストシナリオ**:

**シナリオ1: 自由形式タブのテスト**
1. タブ1「自由形式プロンプト入力」を開く
2. テキストエリアに以下を入力: "20歳の男性キャラクターを作成してください"
3. 「生成」ボタンをクリック
4. 期待される動作:
   - JSON出力とフォーマット済みプロフィールが表示される
   - 「送信されたプロンプトを表示」セクションでプロンプトが確認できる
   - 性別がmale、年齢が20に近い値になる

**シナリオ2: 構造化フォームタブのテスト**
1. タブ2「構造化フォーム入力」を開く
2. 性別: 女性を選択
3. 年齢: 45を入力
4. 追加の指示: "歴史小説の主人公にしてください"を入力
5. 「生成」ボタンをクリック
6. 期待される動作:
   - JSON出力で`"gender": "female"`、`"age": 45`が確認できる
   - personalitiesが正確に3つ含まれる
   - 歴史的な要素を含むキャラクターが生成される

**シナリオ3: モデル切り替えテスト**
1. サイドバーでLLMプロバイダーを「gemini」に変更
2. モデルを「gemini-2.5-flash」に選択
3. 構造化フォームで任意の値を入力して生成
4. サイドバーでLLMプロバイダーを「openai」に変更
5. モデルを「gpt-4o-mini」に選択
6. 同じ値で再度生成
7. 期待される動作:
   - どちらのモデルでも正しくCharacterResponseスキーマに準拠したJSONが生成される

**シナリオ4: バリデーションテスト**
1. 構造化フォームタブで年齢に101を入力しようとする
2. 期待される動作:
   - 数値入力フィールドが最大値100を超えないように制限される

**シナリオ5: インターフェース比較テスト**

同じ要求を自由形式と構造化フォームで試して比較：

1. **自由形式タブで入力**:
   - 「25歳の女性で、明るくて社交的な性格のキャラクターを作ってください」

2. **構造化フォームタブで入力**:
   - 性別: 女性
   - 年齢: 25
   - 追加指示: "明るくて社交的な性格にしてください"

3. **比較観点**:
   - **入力の容易さ**: フォームの方が選択肢が明確で入力しやすい
   - **エラーの可能性**: 自由形式では年齢を書き忘れる可能性がある
   - **結果の一貫性**: フォームの方が指定した年齢・性別が確実に反映される
   - **プロンプトの品質**: どちらも内部プロンプトを確認して構造を理解できる

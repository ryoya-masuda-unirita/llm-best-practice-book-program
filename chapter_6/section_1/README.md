# Chapter 6 Section 1: LLMを安定して使うために自由度を下げる

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
chapter_2/section_10/
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
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    gender: Gender = Field(..., description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    additional_instructions: Optional[str] = Field(
        ...,
        description="Additional instructions for character generation.",
    )
```

**ポイント**:
- `gender`: 列挙型で選択肢を制限（FEMALE/MALE のみ）
- `age`: 0-100の範囲に制約（`ge=0, le=100`）
- `additional_instructions`: 必須フィールドだが空文字列やNoneを許可
- `frozen=True`により不変オブジェクトを保証
- `extra="ignore"`で予期しないフィールドを無視

#### 2. レスポンスモデル (`src/model/model.py`)

Section 1から継承したCharacterResponseモデル：

```python
class CharacterPersonality(BaseModel):
    """キャラクターの性格特性を表すモデル"""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    short_personality: str = Field(
        ..., description="A short description of the character's personality."
    )
    description: str = Field(
        ..., description="A description of the character's personality traits and behaviors."
    )


class CharacterResponse(BaseModel):
    """LLMからのレスポンスを表すモデル（構造化出力）"""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    first_name: str = Field(..., description="The first name of the character.")
    last_name: str = Field(..., description="The last name of the character.")
    gender: Gender = Field(Gender.MALE, description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    personalities: list[CharacterPersonality] = Field(
        ..., description="The three most important personality traits of the character."
    )
```

#### 3. 構造化プロンプト生成 (`src/prompt/prompt.py`)

CharacterRequestから動的にプロンプトを生成する関数を、OpenAIとGemini用にそれぞれ提供：

**OpenAI用プロンプト生成**:

```python
def make_openai_prompt(character_request: CharacterRequest) -> list:
    """OpenAI用のプロンプトを生成"""
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    return [
        {
            "role": "system",
            "content": f"""あなたは創造的なキャラクタージェネレーターです。
あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
1. 応答は有効なJSONであること
2. すべてのフィールドが含まれていること
3. 性別は指定された値であること
4. 年齢は指定された値であること
5. 正確に3つの性格特性が提供されていること
6. JSON構造の外に説明や追加のテキストを含めないこと""",
        },
        {
            "role": "user",
            "content": f"""ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。
性別は「{character_request.gender.value}」、年齢は「{character_request.age}」歳です。
{character_request.additional_instructions}""",
        },
    ]
```

**Gemini用プロンプト生成**:

```python
def make_gemini_prompt(character_request: CharacterRequest) -> tuple[str, str]:
    """Gemini用のプロンプトを生成（システムプロンプトとユーザープロンプトを分離）"""
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)

    system_prompt = f"""あなたは創造的なキャラクタージェネレーターです。
あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
1. 応答は有効なJSONであること
2. すべてのフィールドが含まれていること
3. 性別は指定された値であること
4. 年齢は指定された値であること
5. 正確に3つの性格特性が提供されていること
6. JSON構造の外に説明や追加のテキストを含めないこと"""

    user_prompt = f"""ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。
性別は「{character_request.gender.value}」、年齢は「{character_request.age}」歳です。
{character_request.additional_instructions}"""

    return system_prompt, user_prompt
```

**ポイント**:
- リクエストの構造化データ（性別・年齢）をプロンプトに埋め込み
- 追加指示をプロンプトに含める
- システムプロンプトでレスポンススキーマを明示
- OpenAIはメッセージリスト、Geminiはタプル形式で返す

#### 4. Streamlitアプリケーション (`app.py`)

**タブ1: 自由形式インターフェース**

```python
def render_freeform_tab(provider: LLMProvider, model: str) -> None:
    st.header("自由形式プロンプトインターフェース")
    st.markdown("""
    任意のプロンプトを入力してください。システムはキャラクターを生成しようとしますが、
    結果が一貫しなかったり、期待した形式と一致しない場合があります。
    """)

    free_prompt = st.text_area(
        "プロンプトを入力:",
        placeholder="例: かっこいいキャラクターを作ってください",
        height=150,
        key="free_prompt",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        free_submit = st.button("生成", type="primary", key="free_submit")

    if free_submit and free_prompt:
        with st.spinner("キャラクターを生成中..."):
            try:
                # 自由形式の入力をCharacterRequestに変換（デフォルト値を使用）
                request = create_freeform_request(free_prompt)
                result = call_llm(provider, model, request)
                display_character_result(result)
            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")
```

**タブ2: 構造化フォームインターフェース**

```python
def render_structured_form_tab(provider: LLMProvider, model: str) -> None:
    st.header("構造化フォームインターフェース")
    st.markdown("""
    以下のフォームに入力してください。システムが内部で最適化されたプロンプトを構築し、
    一貫性のある予測可能な結果を保証します。
    """)

    with st.form("character_form"):
        col1, col2 = st.columns(2)

        with col1:
            gender = st.selectbox(
                "性別 *",
                options=[Gender.MALE, Gender.FEMALE],
                format_func=lambda x: "男性" if x == Gender.MALE else "女性",
            )

        with col2:
            age = st.number_input("年齢 *", min_value=0, max_value=100, value=25, step=1)

        additional_instructions = st.text_area(
            "追加指示（任意）",
            placeholder="例: ファンタジー世界の戦士にしてください",
            height=100,
        )

        submitted = st.form_submit_button("キャラクターを生成", type="primary")

        if submitted:
            with st.spinner("構造化プロンプトでキャラクターを生成中..."):
                try:
                    # CharacterRequestを作成
                    request = CharacterRequest(
                        gender=gender,
                        age=age,
                        additional_instructions=additional_instructions or "",
                    )

                    # LLMを呼び出し
                    result = call_llm(provider, model, request)

                    # 結果を表示
                    display_character_result(result)

                    # 内部プロンプトを表示
                    display_internal_prompt(provider, request)

                except Exception as e:
                    st.error(f"❌ エラー: {str(e)}")
```

**モデル選択サイドバー**:

```python
def render_sidebar() -> tuple[LLMProvider, str]:
    with st.sidebar:
        st.header("⚙️ LLM設定")
        provider = st.selectbox(
            "プロバイダーを選択",
            options=[LLMProvider.OPENAI, LLMProvider.GEMINI],
            format_func=lambda x: x.value.upper(),
        )

        if provider == LLMProvider.OPENAI:
            model = st.selectbox(
                "モデルを選択",
                options=OpenAIModel.list_str(),
                index=OpenAIModel.list_str().index(OpenAIModel.GPT_4O_MINI),
            )
        else:
            model = st.selectbox(
                "モデルを選択",
                options=GeminiModel.list_str(),
                index=GeminiModel.list_str().index(GeminiModel.GEMINI_2_5_FLASH),
            )

        st.divider()
        st.markdown("""
### 💡 主な違い

**自由形式:**
- ✅ 最大限の柔軟性
- ❌ 一貫性のない結果
- ❌ セキュリティリスク
- ❌ ユーザーの混乱

**構造化:**
- ✅ 予測可能な出力
- ✅ より良いUX
- ✅ リスク軽減
- ❌ 柔軟性が低い
""")

    return provider, model
```

#### 5. サービス層 (`src/service/request_llm.py`)

CharacterRequestとモデル名を受け取り、LLMを呼び出す：

```python
async def request_openai(
    character_request: CharacterRequest, model: OpenAIModel
) -> CharacterResponse:
    """OpenAI APIでキャラクター生成"""
    prompt = make_openai_prompt(character_request)
    result = await openai_client.responses.parse(
        model=model,
        input=prompt,
        text_format=CharacterResponse,
    )
    logger.info(result)
    return result.output_parsed


async def request_gemini(
    character_request: CharacterRequest, model: GeminiModel
) -> CharacterResponse:
    """Gemini APIでキャラクター生成"""
    system_prompt, user_prompt = make_gemini_prompt(character_request)
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=CharacterResponse,
        ),
    )
    logger.info(result)
    return result.parsed
```

**ポイント**:
- CharacterRequestを直接受け取り、内部でプロンプトを生成
- OpenAIは新しい`responses.parse()` APIを使用
- Geminiは`aio.models.generate_content()`で非同期生成
- どちらもCharacterResponseスキーマに基づいて構造化出力を取得

## 使い方

### 環境構成

- **Python**: 3.13.2以上
- **依存ライブラリ**:
  - **streamlit>=1.50.0** ← Section 10独自の追加
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
- `gpt-5-nano`
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4.1-nano`
- `gpt-4o`
- `gpt-4o-mini`

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

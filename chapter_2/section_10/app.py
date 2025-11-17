"""
Streamlit app demonstrating free-form vs structured LLM interfaces.

This app showcases the concept from CLAUDE.md:
- Free-form: High flexibility but less predictable
- Structured: Reduced flexibility but more stable and user-friendly
"""

import asyncio

import streamlit as st
from src.client.llm_client import GeminiModel, LLMProvider, OpenAIModel
from src.model.model import CharacterRequest, Gender
from src.prompt.prompt import make_prompt
from src.service.request_llm import request_gemini, request_openai

# Page config
st.set_page_config(
    page_title="LLMインターフェース比較",
    page_icon="🎭",
    layout="wide",
)

# Title
st.title("🎭 キャラクター生成 - インターフェース比較")
st.markdown(
    """
このデモでは、LLMインターフェースの2つのアプローチを比較します：
- **自由形式**: ユーザーが自分でプロンプトを書く（柔軟だが予測不可能）
- **構造化**: ユーザーがフォームに入力する（制約があるが安定）
"""
)

# Sidebar for LLM selection
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
    st.markdown(
        """
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
"""
    )

# Create tabs
tab1, tab2 = st.tabs(["🆓 自由形式プロンプト", "📋 構造化フォーム"])

# Tab 1: Free-form Prompt
with tab1:
    st.header("自由形式プロンプトインターフェース")
    st.markdown(
        """
任意のプロンプトを入力してください。システムはキャラクターを生成しようとしますが、
結果が一貫しなかったり、期待した形式と一致しない場合があります。
"""
    )

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
                # Create a simple prompt structure for free-form input
                messages = [
                    {
                        "role": "system",
                        "content": """あなたはキャラクタージェネレーターです。ユーザーの入力に基づいてキャラクターを生成してください。
以下の構造のJSONオブジェクトのみを返してください：
{
    "first_name": "文字列",
    "last_name": "文字列",
    "gender": "male" または "female",
    "age": 数値 (0-100),
    "personalities": [
        {"short_personality": "文字列", "description": "文字列"},
        {"short_personality": "文字列", "description": "文字列"},
        {"short_personality": "文字列", "description": "文字列"}
    ]
}""",
                    },
                    {"role": "user", "content": free_prompt},
                ]

                # Call LLM
                if provider == LLMProvider.OPENAI:
                    result = asyncio.run(request_openai(messages, model))
                else:
                    result = asyncio.run(request_gemini(messages, model))

                # Display result
                st.success("✅ キャラクターが正常に生成されました！")

                col_left, col_right = st.columns(2)

                with col_left:
                    st.subheader("📊 構造化された出力")
                    st.json(result.model_dump())

                with col_right:
                    st.subheader("👤 キャラクタープロフィール")
                    st.markdown(f"**名前:** {result.first_name} {result.last_name}")
                    st.markdown(f"**性別:** {result.gender.value.capitalize()}")
                    st.markdown(f"**年齢:** {result.age}")
                    st.markdown("**性格:**")
                    for i, p in enumerate(result.personalities, 1):
                        st.markdown(f"{i}. **{p.short_personality}**")
                        st.markdown(f"   _{p.description}_")

            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")
                st.markdown(
                    """
**自由形式プロンプトが問題となる理由:**
- ユーザーが十分な情報を提供しない可能性がある
- 出力形式が期待と一致しない可能性がある
- エラーを適切に処理することが難しい
"""
                )

    if not free_submit or not free_prompt:
        st.info("👆 上記にプロンプトを入力して「生成」をクリックすると結果が表示されます")

# Tab 2: Structured Form
with tab2:
    st.header("構造化フォームインターフェース")
    st.markdown(
        """
以下のフォームに入力してください。システムが内部で最適化されたプロンプトを構築し、
一貫性のある予測可能な結果を保証します。
"""
    )

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
                    # Create CharacterRequest
                    request = CharacterRequest(
                        gender=gender,
                        age=age,
                        additional_instructions=additional_instructions or "",
                    )

                    # Generate prompt using the structured function
                    messages = make_prompt(request)

                    # Call LLM
                    if provider == LLMProvider.OPENAI:
                        result = asyncio.run(request_openai(messages, model))
                    else:
                        # For Gemini, we need to handle it differently
                        result = asyncio.run(request_gemini(messages, model))

                    # Display result
                    st.success("✅ キャラクターが正常に生成されました！")

                    col_left, col_right = st.columns(2)

                    with col_left:
                        st.subheader("📊 構造化された出力")
                        st.json(result.model_dump())

                    with col_right:
                        st.subheader("👤 キャラクタープロフィール")
                        st.markdown(f"**名前:** {result.first_name} {result.last_name}")
                        st.markdown(f"**性別:** {'男性' if result.gender == Gender.MALE else '女性'}")
                        st.markdown(f"**年齢:** {result.age}")
                        st.markdown("**性格:**")
                        for i, p in enumerate(result.personalities, 1):
                            st.markdown(f"{i}. **{p.short_personality}**")
                            st.markdown(f"   _{p.description}_")

                    # Show the internal prompt
                    with st.expander("🔍 内部プロンプトを表示"):
                        st.markdown("**LLMに送信されたプロンプト:**")
                        for msg in messages:
                            st.markdown(f"**{msg['role'].upper()}:**")
                            st.code(msg["content"], language="text")

                except Exception as e:
                    st.error(f"❌ エラー: {str(e)}")
                    st.markdown("構造化フォームにより、より良いエラーハンドリングが保証されます。")

# Footer
st.divider()
st.markdown(
    """
### 📚 詳しく学ぶ

このデモは**第2章 第9項: LLMを安定して使うために自由度を下げる**に基づいています

**重要なポイント:**
1. 構造化されたインターフェースは、特定のタスクに対してより良いUXを提供する
2. ユーザー入力を制約しながら、内部でLLMの柔軟性を維持できる
3. パラメーターベースのフォームは、混乱を減らし、出力の一貫性を向上させる
"""
)

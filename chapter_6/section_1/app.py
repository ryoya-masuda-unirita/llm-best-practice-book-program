"""
Streamlit app demonstrating free-form vs structured LLM interfaces.

This app showcases the concept from CLAUDE.md:
- Free-form: High flexibility but less predictable
- Structured: Reduced flexibility but more stable and user-friendly
"""

import asyncio

import streamlit as st
from src.client.llm_client import AnthropicModel, LLMProvider, OpenAIModel
from src.model.model import CharacterRequest, CharacterResponse, Gender
from src.prompt.prompt import make_anthropic_prompt, make_openai_prompt
from src.service.request_llm import request_anthropic, request_openai


def configure_page() -> None:
    st.set_page_config(
        page_title="LLMインターフェース比較",
        page_icon="🎭",
        layout="wide",
    )


def render_header() -> None:
    st.title("🎭 キャラクター生成 - インターフェース比較")
    st.markdown(
        """
このデモでは、LLMインターフェースの2つのアプローチを比較します：
- **自由形式**: ユーザーが自分でプロンプトを書く（柔軟だが予測不可能）
- **構造化**: ユーザーがフォームに入力する（制約があるが安定）
"""
    )


def render_sidebar() -> tuple[LLMProvider, str]:
    with st.sidebar:
        st.header("⚙️ LLM設定")
        provider = st.selectbox(
            "プロバイダーを選択",
            options=[LLMProvider.OPENAI, LLMProvider.ANTHROPIC],
            format_func=lambda x: x.value.upper(),
        )

        if provider == LLMProvider.OPENAI:
            model = st.selectbox(
                "モデルを選択",
                options=OpenAIModel.list_str(),
                index=OpenAIModel.list_str().index(OpenAIModel.GPT_5_4),
            )
        else:
            model = st.selectbox(
                "モデルを選択",
                options=AnthropicModel.list_str(),
                index=AnthropicModel.list_str().index(AnthropicModel.CLAUDE_HAIKU_4_5),
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

    return provider, model


def call_llm(provider: LLMProvider, model: str, character_request: CharacterRequest) -> CharacterResponse:
    if provider == LLMProvider.OPENAI:
        return asyncio.run(request_openai(character_request, model))
    else:
        return asyncio.run(request_anthropic(character_request, model))


def display_character_result(result: CharacterResponse) -> None:
    st.success("✅ キャラクターが正常に生成されました！")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 構造化された出力")
        st.json(result.model_dump())

    with col_right:
        st.subheader("👤 キャラクタープロフィール")
        st.markdown(f"**名前:** {result.first_name} {result.last_name}")
        gender_display = "男性" if result.gender == Gender.MALE else "女性"
        st.markdown(f"**性別:** {gender_display}")
        st.markdown(f"**年齢:** {result.age}")
        st.markdown("**性格:**")
        for i, p in enumerate(result.personalities, 1):
            st.markdown(f"{i}. **{p.short_personality}**")
            st.markdown(f"   _{p.description}_")


def create_freeform_request(user_prompt: str) -> CharacterRequest:
    """Use default values and put the user's free text into additional_instructions."""
    return CharacterRequest(
        gender=Gender.MALE,
        age=25,
        additional_instructions=user_prompt,
    )


def render_freeform_tab(provider: LLMProvider, model: str) -> None:
    st.header("自由形式プロンプトインターフェース")
    st.markdown(
        """
年齢と性別を含めて入力してください。
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
                request = create_freeform_request(free_prompt)
                result = call_llm(provider, model, request)
                display_character_result(result)

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


def display_internal_prompt(provider: LLMProvider, character_request: CharacterRequest) -> None:
    with st.expander("🔍 内部プロンプトを表示"):
        st.markdown("**LLMに送信されたプロンプト:**")
        if provider == LLMProvider.OPENAI:
            messages = make_openai_prompt(character_request)
            for msg in messages:
                st.markdown(f"**{msg['role'].upper()}:**")
                st.code(msg["content"], language="text")
        else:
            system_prompt, user_prompt = make_anthropic_prompt(character_request)
            st.markdown("**SYSTEM:**")
            st.code(system_prompt, language="text")
            st.markdown("**USER:**")
            st.code(user_prompt, language="text")


def render_structured_form_tab(provider: LLMProvider, model: str) -> None:
    st.header("構造化フォームインターフェース")
    st.markdown(
        """
以下のフォームに入力してください。
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
                    request = CharacterRequest(
                        gender=gender,
                        age=age,
                        additional_instructions=additional_instructions or "",
                    )
                    result = call_llm(provider, model, request)
                    display_character_result(result)
                    display_internal_prompt(provider, request)

                except Exception as e:
                    st.error(f"❌ エラー: {str(e)}")
                    st.markdown("構造化フォームにより、より良いエラーハンドリングが保証されます。")


def render_footer() -> None:
    st.divider()
    st.markdown(
        """
### 📚 詳しく学ぶ

このデモは**第6章 第1項: LLMを安定して使うために自由度を下げる**に基づいています

**重要なポイント:**
1. 構造化されたインターフェースは、特定のタスクに対してより良いUXを提供する
2. ユーザー入力を制約しながら、内部でLLMの柔軟性を維持できる
3. パラメーターベースのフォームは、混乱を減らし、出力の一貫性を向上させる
"""
    )


def main() -> None:
    configure_page()
    render_header()
    provider, model = render_sidebar()

    tab1, tab2 = st.tabs(["🆓 自由形式プロンプト", "📋 構造化フォーム"])

    with tab1:
        render_freeform_tab(provider, model)

    with tab2:
        render_structured_form_tab(provider, model)

    render_footer()


if __name__ == "__main__":
    main()

import json

from src.model.model import CharacterRequest, CharacterResponse


def _build_system_text(character_request: CharacterRequest) -> str:
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return f"""あなたは創造的なキャラクタージェネレーターです。
あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
1. 応答は有効なJSONであること
2. すべてのフィールドが含まれていること
3. 性別は指定された値であること
4. 年齢は指定された値であること
5. 正確に3つの性格特性が提供されていること
6. JSON構造の外に説明や追加のテキストを含めないこと
"""


def _build_user_text(character_request: CharacterRequest) -> str:
    return f"""ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。
性別は「{character_request.gender.value}」、年齢は「{character_request.age}」歳です。
{character_request.additional_instructions}
"""


def make_openai_prompt(character_request: CharacterRequest) -> list[dict]:
    return [
        {"role": "system", "content": _build_system_text(character_request)},
        {"role": "user", "content": _build_user_text(character_request)},
    ]


def make_gemini_prompt(character_request: CharacterRequest) -> tuple[str, str]:
    return _build_system_text(character_request), _build_user_text(character_request)


def make_anthropic_prompt(character_request: CharacterRequest) -> tuple[str, list[dict]]:
    system_text = _build_system_text(character_request)
    messages = [{"role": "user", "content": _build_user_text(character_request)}]
    return system_text, messages

import json

from src.client.llm_client import LLMProvider
from src.model.model import CharacterRequest, CharacterResponse


def make_openai_prompt(character: CharacterRequest) -> list:
    data = character.to_str_dict()
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
2. JSON構造の外に説明や追加のテキストを含めないこと

リクエストパラメータ：
{data}
""",
        },
        {
            "role": "user",
            "content": "ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。",
        },
    ]


def make_gemini_prompt(character: CharacterRequest) -> tuple[str, str]:
    data = character.to_str_dict()
    data = character.to_str_dict()
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    system_prompt = f"""あなたは創造的なキャラクタージェネレーターです。
あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
1. 応答は有効なJSONであること
2. JSON構造の外に説明や追加のテキストを含めないこと

リクエストパラメータ：
{data}
"""
    user_prompt = "ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。"
    return system_prompt, user_prompt


def make_anthropic_prompt(character: CharacterRequest) -> list:
    data = character.to_str_dict()
    params = CharacterResponse.detailed_model()
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return [
        {
            "role": "user",
            "content": f"""あなたは創造的なキャラクタージェネレーターです。
あなたの任務は、詳細な情報を持つフィクションのキャラクターを生成することです。
以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

{param_dump}

以下を確認してください：
1. 応答は有効なJSONであること
2. JSON構造の外に説明や追加のテキストを含めないこと

リクエストパラメータ：
{data}

ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。
""",
        },
    ]


def make_prompt(character: CharacterRequest, provider: LLMProvider) -> list | tuple[str, str]:
    if provider == LLMProvider.OPENAI:
        return make_openai_prompt(character)
    elif provider == LLMProvider.GEMINI:
        return make_gemini_prompt(character)
    elif provider == LLMProvider.ANTHROPIC:
        return make_anthropic_prompt(character)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

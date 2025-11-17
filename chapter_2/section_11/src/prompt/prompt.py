import json

from src.model.model import CharacterResponse


def make_prompt() -> list:
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
3. 性別は「female」または「male」のいずれかであること
4. 年齢は0から100の間であること
5. 正確に3つの性格特性が提供されていること
6. JSON構造の外に説明や追加のテキストを含めないこと
""",
        },
        {
            "role": "user",
            "content": "ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。",
        },
    ]

import json
from typing import Any, Dict, Optional

from src.logger import make_logger
from src.model import CharacterResponse
from src.template_engine import template_engine

logger = make_logger(__name__)


def make_prompt(template_name: str = "character_generation", **kwargs) -> list:
    """Generate prompt using template system with fallback to legacy method.

    Args:
        template_name: Name of the template to use
        **kwargs: Additional variables for template rendering

    Returns:
        List of message dictionaries for LLM API
    """
    try:
        # Prepare template variables
        variables = {
            "schema_format": json.dumps(CharacterResponse.detailed_model(), indent=2, ensure_ascii=False),
            **kwargs,
        }

        # Use template engine
        messages = template_engine.render_template(template_name, variables)
        logger.info(f"Generated prompt using template: {template_name}")
        return messages

    except Exception as e:
        logger.warning(f"Failed to use template '{template_name}': {e}. Falling back to legacy prompt.")
        return _make_legacy_prompt()


def _make_legacy_prompt() -> list:
    """Legacy prompt generation method as fallback."""
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


def get_template_info(template_name: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific template.

    Args:
        template_name: Name of the template

    Returns:
        Template information dictionary or None if not found
    """
    template = template_engine.get_template(template_name)
    if not template:
        return None

    return {
        "name": template.name,
        "description": template.description,
        "version": template.version,
        "variables": {
            name: {"type": var.type, "description": var.description, "required": var.required, "default": var.default}
            for name, var in template.variables.items()
        },
    }

"""Prompt templates for parallel world article generation."""

import json
from typing import Literal

from src.model.parallel_world_model import ArticleHalf, ArticleOutline, ArticleReview


def make_outline_generation_prompt(theme: str, language: Literal["en", "ja"]) -> list[dict[str, str]]:
    """
    Create a prompt for generating article outline.

    Args:
        theme: The article theme
        language: Target language ("en" or "ja")

    Returns:
        List of message dictionaries for the LLM
    """
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleOutline.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an expert article writer and content strategist.
Your task is to create a comprehensive outline for an article {lang_instruction}.

The outline should include:
1. **Title**: A compelling and descriptive article title
2. **Summary**: A brief 2-3 sentence summary of what the article will cover
3. **Structure**: A logical section structure with 3-10 section headers

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- All content must be written {lang_instruction}
- The outline should be comprehensive yet focused
- Section headers should be clear and descriptive
- Ensure logical flow from one section to the next
"""

    user_prompt = f"""Please create an article outline on the following theme:

Theme: {theme}

Create an engaging and well-structured outline that would result in a high-quality article.
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def make_outline_generation_system_instruction(theme: str, language: Literal["en", "ja"]) -> tuple[str, str]:
    """
    Create system instruction for outline generation (for Gemini).

    Args:
        theme: The article theme
        language: Target language ("en" or "ja")

    Returns:
        Tuple of (system_instruction, user_content)
    """
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleOutline.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an expert article writer and content strategist.
Your task is to create a comprehensive outline for an article {lang_instruction}.

The outline should include:
1. **Title**: A compelling and descriptive article title
2. **Summary**: A brief 2-3 sentence summary of what the article will cover
3. **Structure**: A logical section structure with 3-10 section headers

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- All content must be written {lang_instruction}
- The outline should be comprehensive yet focused
- Section headers should be clear and descriptive
- Ensure logical flow from one section to the next
"""

    user_content = f"""Please create an article outline on the following theme:

Theme: {theme}

Create an engaging and well-structured outline that would result in a high-quality article.
"""

    return system_instruction, user_content


def make_first_half_generation_prompt(outline: ArticleOutline, language: Literal["en", "ja"]) -> list[dict[str, str]]:
    """
    Create a prompt for generating the first half of an article.

    Args:
        outline: The article outline
        language: Target language ("en" or "ja")

    Returns:
        List of message dictionaries for the LLM
    """
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleHalf.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an expert article writer.
Your task is to write the FIRST HALF of an article {lang_instruction} based on the provided outline.

The first half should:
- Cover approximately the first 50% of the outlined sections
- Be well-written, engaging, and informative
- Use proper markdown formatting
- Create a smooth narrative flow
- Set up context for the second half

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Content must be in markdown format
- All content must be written {lang_instruction}
- Write approximately 400-800 words
- End at a natural transition point for the second half
"""

    outline_md = outline.to_markdown()

    user_prompt = f"""Please write the FIRST HALF of an article based on this outline:

{outline_md}

Write engaging, informative content that covers roughly the first half of the outlined structure.
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def make_first_half_generation_system_instruction(
    outline: ArticleOutline, language: Literal["en", "ja"]
) -> tuple[str, str]:
    """
    Create system instruction for first half generation (for Gemini).

    Args:
        outline: The article outline
        language: Target language ("en" or "ja")

    Returns:
        Tuple of (system_instruction, user_content)
    """
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleHalf.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an expert article writer.
Your task is to write the FIRST HALF of an article {lang_instruction} based on the provided outline.

The first half should:
- Cover approximately the first 50% of the outlined sections
- Be well-written, engaging, and informative
- Use proper markdown formatting
- Create a smooth narrative flow
- Set up context for the second half

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Content must be in markdown format
- All content must be written {lang_instruction}
- Write approximately 400-800 words
- End at a natural transition point for the second half
"""

    outline_md = outline.to_markdown()

    user_content = f"""Please write the FIRST HALF of an article based on this outline:

{outline_md}

Write engaging, informative content that covers roughly the first half of the outlined structure.
"""

    return system_instruction, user_content


def make_second_half_generation_prompt(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
) -> list[dict[str, str]]:
    """
    Create a prompt for generating the second half of an article.

    Args:
        outline: The article outline
        first_half: The first half content
        language: Target language ("en" or "ja")

    Returns:
        List of message dictionaries for the LLM
    """
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleHalf.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an expert article writer.
Your task is to write the SECOND HALF of an article {lang_instruction} based on the outline and the already-written first half.

The second half should:
- Continue seamlessly from where the first half ended
- Cover the remaining sections from the outline
- Be well-written, engaging, and informative
- Use proper markdown formatting
- Provide a strong conclusion

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Content must be in markdown format
- All content must be written {lang_instruction}
- Write approximately 400-800 words
- Ensure smooth transition from the first half
- Provide a satisfying conclusion
"""

    outline_md = outline.to_markdown()

    user_prompt = f"""Please write the SECOND HALF of an article to complete it.

**Article Outline:**
{outline_md}

**First Half (already written):**
{first_half}

Write the second half that completes the article, covering the remaining sections and providing a strong conclusion.
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def make_second_half_generation_system_instruction(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
) -> tuple[str, str]:
    """
    Create system instruction for second half generation (for Gemini).

    Args:
        outline: The article outline
        first_half: The first half content
        language: Target language ("en" or "ja")

    Returns:
        Tuple of (system_instruction, user_content)
    """
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleHalf.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an expert article writer.
Your task is to write the SECOND HALF of an article {lang_instruction} based on the outline and the already-written first half.

The second half should:
- Continue seamlessly from where the first half ended
- Cover the remaining sections from the outline
- Be well-written, engaging, and informative
- Use proper markdown formatting
- Provide a strong conclusion

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Content must be in markdown format
- All content must be written {lang_instruction}
- Write approximately 400-800 words
- Ensure smooth transition from the first half
- Provide a satisfying conclusion
"""

    outline_md = outline.to_markdown()

    user_content = f"""Please write the SECOND HALF of an article to complete it.

**Article Outline:**
{outline_md}

**First Half (already written):**
{first_half}

Write the second half that completes the article, covering the remaining sections and providing a strong conclusion.
"""

    return system_instruction, user_content


def make_article_review_prompt(
    theme: str,
    outline: ArticleOutline,
    full_article: str,
    language: Literal["en", "ja"],
) -> list[dict[str, str]]:
    """
    Create a prompt for reviewing a complete article (LLM-as-a-Judge).

    Args:
        theme: The original article theme
        outline: The article outline
        full_article: The complete article content
        language: Article language

    Returns:
        List of message dictionaries for the LLM judge
    """
    schema_fields = {}
    for field_name, field_info in ArticleReview.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_prompt = f"""You are an expert article reviewer and quality evaluator.
Your task is to evaluate the quality of an article based on the original theme and outline.

Evaluation Criteria:
1. **Content Quality (30%)**: Is the content accurate, informative, and valuable?
2. **Structure & Flow (25%)**: Does the article follow the outline? Is the flow logical and smooth?
3. **Writing Quality (20%)**: Is the writing clear, engaging, and well-crafted?
4. **Completeness (15%)**: Does the article adequately cover the theme and all outlined sections?
5. **Language Quality (10%)**: Is the language appropriate, consistent, and error-free?

Grading Scale:
- **5 (Excellent)**: Outstanding article that exceeds expectations in all criteria
- **4 (Good)**: High-quality article with minor areas for improvement
- **3 (Acceptable)**: Adequate article but with noticeable gaps or weaknesses
- **2 (Poor)**: Significant issues that detract from the article's value
- **1 (Very Poor)**: Fails to meet basic quality standards

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Grade must be an integer between 1 and 5
- Reasoning must be 3-5 sentences explaining the grade
- Provide 2-4 specific strengths
- Provide 2-4 specific weaknesses (if any)
- Be objective and constructive in your evaluation
"""

    outline_md = outline.to_markdown()

    user_prompt = f"""Please review and evaluate this article.

**Original Theme:**
{theme}

**Intended Outline:**
{outline_md}

**Complete Article:**
{full_article}

Provide your evaluation following the specified JSON structure.
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def make_article_review_system_instruction(
    theme: str,
    outline: ArticleOutline,
    full_article: str,
    language: Literal["en", "ja"],
) -> tuple[str, str]:
    """
    Create system instruction for article review (for Gemini).

    Args:
        theme: The original article theme
        outline: The article outline
        full_article: The complete article content
        language: Article language

    Returns:
        Tuple of (system_instruction, user_content)
    """
    schema_fields = {}
    for field_name, field_info in ArticleReview.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an expert article reviewer and quality evaluator.
Your task is to evaluate the quality of an article based on the original theme and outline.

Evaluation Criteria:
1. **Content Quality (30%)**: Is the content accurate, informative, and valuable?
2. **Structure & Flow (25%)**: Does the article follow the outline? Is the flow logical and smooth?
3. **Writing Quality (20%)**: Is the writing clear, engaging, and well-crafted?
4. **Completeness (15%)**: Does the article adequately cover the theme and all outlined sections?
5. **Language Quality (10%)**: Is the language appropriate, consistent, and error-free?

Grading Scale:
- **5 (Excellent)**: Outstanding article that exceeds expectations in all criteria
- **4 (Good)**: High-quality article with minor areas for improvement
- **3 (Acceptable)**: Adequate article but with noticeable gaps or weaknesses
- **2 (Poor)**: Significant issues that detract from the article's value
- **1 (Very Poor)**: Fails to meet basic quality standards

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Grade must be an integer between 1 and 5
- Reasoning must be 3-5 sentences explaining the grade
- Provide 2-4 specific strengths
- Provide 2-4 specific weaknesses (if any)
- Be objective and constructive in your evaluation
"""

    outline_md = outline.to_markdown()

    user_content = f"""Please review and evaluate this article.

**Original Theme:**
{theme}

**Intended Outline:**
{outline_md}

**Complete Article:**
{full_article}

Provide your evaluation following the specified JSON structure.
"""

    return system_instruction, user_content

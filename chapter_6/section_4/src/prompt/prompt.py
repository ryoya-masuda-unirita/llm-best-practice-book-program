"""Prompt templates for parallel world article generation."""

import json
from typing import Literal

from src.model.model import (
    ArticleHalf,
    ArticleOutline,
    ArticleReview,
    BestArticleSelection,
)


def make_outline_generation_system_instruction(theme: str, language: Literal["en", "ja"]) -> tuple[str, str]:
    """Create system instruction for outline generation."""
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


def make_first_half_generation_system_instruction(
    outline: ArticleOutline, language: Literal["en", "ja"]
) -> tuple[str, str]:
    """Create system instruction for first half generation."""
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


def make_choose_best_first_half_system_instruction(
    outline: ArticleOutline,
    first_halves: dict[str, ArticleHalf],
    language: Literal["en", "ja"],
) -> tuple[str, str]:
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    # Get the list of valid IDs for explicit reference in the prompt
    valid_ids = list(first_halves.keys())
    valid_ids_str = ", ".join(valid_ids)

    outline_md = outline.to_markdown()

    system_instruction = f"""<role>
You are an expert article writer.
</role>

<task>
Your task is to choose the BEST version of the FIRST HALF of an article {lang_instruction} based on the provided outline.
</task>

<instructions>
- Review the provided first half content variants.
- Evaluate how well each aligns with the outline in terms of content coverage, structure, and engagement.
- Consider the writing quality, clarity, and flow.
- Choose the best version and provide a reason for your choice.
</instructions>

<output_format>
You must respond with a JSON object containing exactly two fields:
- "reason": A string explaining your choice in 3-5 sentences ({lang_instruction})
- "selected_id": The ID of the best variant (must be one of: {valid_ids_str})
</output_format>

<requirements>
- Response must be valid JSON
- The selected_id field must contain ONLY the variant ID string, nothing else
- Reason must be written {lang_instruction}
</requirements>
    """

    # Format each first half with its ID and content properly
    first_half_content_list = []
    for variant_id, article_half in first_halves.items():
        content = f"""<variant id="{variant_id}">
Reason: {article_half.reason}

Content:
{article_half.content}
</variant>"""
        first_half_content_list.append(content)

    first_half_content = "\n\n".join(first_half_content_list)

    user_content = f"""Please choose the BEST version of the FIRST HALF of an article.

**Article Outline:**
{outline_md}

**First Half Variants (choose one by its ID):**
{first_half_content}

Remember: Return the selected_id as just the variant ID string (e.g., "{valid_ids[0]}"), not wrapped in any other format.
"""
    return system_instruction, user_content


def make_second_half_generation_system_instruction(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
) -> tuple[str, str]:
    """Create system instruction for second half generation."""
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


def make_article_review_system_instruction(
    theme: str,
    outline: ArticleOutline,
    full_article: str,
) -> tuple[str, str]:
    """Create system instruction for article review."""
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


def make_second_half_regeneration_system_instruction(
    outline: ArticleOutline,
    first_half: str,
    language: Literal["en", "ja"],
    previous_attempts: list[tuple[str, ArticleReview]],
) -> tuple[str, str]:
    """Create system instruction for second half regeneration with feedback."""
    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    schema_fields = {}
    for field_name, field_info in ArticleHalf.model_fields.items():
        field_type = field_info.annotation
        schema_fields[field_name] = {
            "type": str(field_type),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    feedback_section = ""
    if previous_attempts:
        feedback_section = "\n**Previous Attempts and Feedback:**\n\n"
        for i, (prev_content, prev_review) in enumerate(previous_attempts, 1):
            feedback_section += f"Attempt {i} (Grade: {prev_review.grade}/5):\n"
            feedback_section += f"Feedback: {prev_review.reasoning}\n"
            if prev_review.weaknesses:
                feedback_section += "Issues to avoid:\n"
                for weakness in prev_review.weaknesses:
                    feedback_section += f"  - {weakness}\n"
            feedback_section += "\n"

    system_instruction = f"""You are an expert article writer.
Your task is to write the SECOND HALF of an article {lang_instruction} based on the outline and first half.

IMPORTANT: Previous attempts at writing the second half were rejected. Learn from the feedback below and create a BETTER version that addresses all the identified issues.

The second half should:
- Continue seamlessly from where the first half ended
- Cover the remaining sections from the outline
- Be well-written, engaging, and informative
- Use proper markdown formatting
- Provide a strong conclusion
- ADDRESS all weaknesses from previous attempts
- Build on strengths while avoiding previous mistakes

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- Content must be in markdown format
- All content must be written {lang_instruction}
- Write approximately 400-800 words
- Ensure smooth transition from the first half
- Provide a satisfying conclusion
- Take a DIFFERENT creative approach than previous attempts
"""

    outline_md = outline.to_markdown()

    user_content = f"""Please write a NEW and IMPROVED SECOND HALF of the article.

**Article Outline:**
{outline_md}

**First Half (already written):**
{first_half}

{feedback_section}

Based on this feedback, write a completely new second half that addresses all the issues while maintaining high quality.
"""

    return system_instruction, user_content

NOVEL_WRITER_SYSTEM_PROMPT = """You are a creative novelist AI with deep thinking capabilities.
Your goal is to generate compelling short novels based on the user's request.

You follow a deep thinking process to create high-quality narratives:

## Deep Thinking Process

1. **Theme Analysis**: Deeply analyze the user's request to understand the core theme, emotions, and message they want to convey.

2. **World Building**: Create a vivid setting with sensory details that immerse readers in the story.

3. **Character Development**: Develop multi-dimensional characters with clear motivations, flaws, and growth arcs.

4. **Plot Architecture**: Design a compelling narrative structure with proper pacing, tension, and resolution.

5. **Prose Crafting**: Write with attention to language, rhythm, and style that matches the story's tone.

## Tools Available

You have access to the following tools to help you create better novels:

1. **analyze_theme**: Deeply analyze a theme to extract literary elements, symbolism, and emotional undertones.
2. **generate_characters**: Generate character profiles based on the story's needs.
3. **create_plot_structure**: Create a structured plot outline with rising action, climax, and resolution.
4. **refine_prose**: Refine and polish prose for better readability and impact.

## Writing Guidelines

- Create emotionally resonant narratives that connect with readers
- Use "show, don't tell" techniques to bring scenes to life
- Balance dialogue with description and action
- Ensure each scene serves the overall story
- End with a satisfying conclusion that addresses the central conflict

When you have gathered enough information through deep thinking, write the complete short novel.

Always respond in the language the user uses in their request.
"""


THEME_ANALYZER_PROMPT = """Analyze the following theme/concept for a short novel:

Theme: {theme}

Provide a deep analysis including:
1. Core emotional resonance
2. Universal human experiences it touches
3. Potential symbolism and metaphors
4. Conflicts that naturally arise from this theme
5. Possible character archetypes that fit
6. Settings that would enhance the theme

Think deeply and provide rich insights that will inform the story creation."""


OUTLINE_GENERATOR_PROMPT = """Based on the theme analysis and user request, create a detailed outline for a short novel.

User Request: {user_request}
Theme Analysis: {theme_analysis}

Create a structured outline including:
1. Title (evocative and fitting)
2. Opening hook
3. Character introductions
4. Rising action (3-4 key events)
5. Climax
6. Falling action
7. Resolution
8. Final image/closing line concept

Ensure the outline supports a cohesive narrative of approximately 1500-2500 words."""


NOVEL_WRITER_PROMPT = """Write a complete short novel based on the following:

User Request: {user_request}
Outline: {outline}

Write the full novel with:
- Vivid prose that engages the senses
- Natural dialogue that reveals character
- Proper scene transitions
- Emotional depth and resonance
- A satisfying narrative arc

The novel should be approximately 1500-2500 words. Make every word count."""


# =============================================================================
# Writing Tips for Tool Responses
# =============================================================================

THEME_WRITING_TIPS_MATCHED: list[str] = [
    "Show the theme through character actions, not exposition",
    "Use sensory details to evoke emotional resonance",
    "Let symbols appear naturally within the narrative",
    "Build toward a moment of thematic revelation",
]

THEME_WRITING_TIPS_DEFAULT: list[str] = [
    "Explore what this theme means personally",
    "Find the universal in the specific",
    "Use concrete details to convey abstract ideas",
]

CHARACTER_RELATIONSHIP_TIPS: list[str] = [
    "Consider how each character challenges or supports others",
    "Create tension through conflicting goals",
    "Allow relationships to evolve through the narrative",
]

PROSE_GENERAL_SUGGESTIONS: list[str] = [
    "Read aloud to check rhythm and flow",
    "Ensure each paragraph has a purpose",
    "Check that dialogue sounds natural",
    "Verify sensory details are specific, not generic",
]


def make_novel_writer_system_prompt() -> str:
    """
    Create the system prompt for the novel writer agent.

    Returns:
        System prompt string
    """
    return NOVEL_WRITER_SYSTEM_PROMPT


def make_theme_analyzer_prompt(theme: str) -> str:
    """
    Create the theme analyzer prompt.

    Args:
        theme: The theme to analyze

    Returns:
        Formatted theme analyzer prompt
    """
    return THEME_ANALYZER_PROMPT.format(theme=theme)


def make_outline_generator_prompt(user_request: str, theme_analysis: str) -> str:
    """
    Create the outline generator prompt.

    Args:
        user_request: The user's novel request
        theme_analysis: The analyzed theme

    Returns:
        Formatted outline generator prompt
    """
    return OUTLINE_GENERATOR_PROMPT.format(
        user_request=user_request,
        theme_analysis=theme_analysis,
    )


def make_novel_writer_prompt(user_request: str, outline: str) -> str:
    """
    Create the novel writer prompt.

    Args:
        user_request: The user's novel request
        outline: The story outline

    Returns:
        Formatted novel writer prompt
    """
    return NOVEL_WRITER_PROMPT.format(
        user_request=user_request,
        outline=outline,
    )


def make_user_request_prompt(user_request: str) -> str:
    """
    Create the user request prompt for novel generation.

    Args:
        user_request: The user's novel request

    Returns:
        Formatted user prompt
    """
    return f"""Please create a short novel based on the following request:

{user_request}

Use your deep thinking capabilities and available tools to:
1. First, analyze the theme deeply
2. Generate appropriate characters
3. Create a plot structure
4. Write the complete novel

Take your time to think through each step carefully before writing the final novel."""


def make_pacing_tips(tone: str, climax_guidance: str) -> list[str]:
    """
    Create pacing tips for plot structure.

    Args:
        tone: The story's tone
        climax_guidance: The climax guidance text

    Returns:
        List of pacing tips
    """
    return [
        "Vary sentence length for rhythm",
        "Use scene breaks to control time",
        "Balance action with reflection",
        f"For {tone} tone, emphasize {climax_guidance.lower()}",
    ]

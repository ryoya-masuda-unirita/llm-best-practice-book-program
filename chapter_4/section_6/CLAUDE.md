# Chapter 4 Section 6: Article Generation System with Parallel World Pattern

## Overview

This project implements an **AI Agent article generation system** utilizing the **Parallel World Pattern**. It combines multiple parallel LLM sessions with Human-in-the-Loop decision-making and LLM-as-a-Judge evaluation to generate high-quality article content.

The Parallel World Pattern is a workflow technique in AI agent systems where multiple different execution paths (parallel worlds) are generated simultaneously, and the optimal result is selected from among them. This approach ensures content diversity while maintaining quality and controllability through strategic human intervention at key decision points.

**Key Innovation**: This system demonstrates how to balance automation with human oversight by creating multiple article variants in parallel, evaluating them systematically with LLM-as-a-Judge, and incorporating human feedback in a review loop for continuous quality improvement.

## Features

### Core Capabilities

- **Parallel World Article Generation**: Generate multiple article variations simultaneously
- **Human-in-the-Loop**: User intervention at critical decision points
- **LLM-as-a-Judge**: Automated article quality evaluation and review
- **Feedback Loop**: Regeneration based on feedback from rejected articles
- **Multi-Provider Support**: Compatible with both OpenAI and Google Gemini APIs
- **Bilingual Support**: Generate articles in English or Japanese

### Workflow Phases

The system orchestrates a sophisticated 9-phase pipeline:

1. **Phase 1**: Generate multiple outline variants in parallel (Parallel World Branching Point #1)
2. **Phase 2**: User selects preferred outline (Human-in-the-Loop #1)
3. **Phase 3**: Generate first half of article based on selected outline
4. **Phase 4**: Generate multiple second half variants in parallel (Parallel World Branching Point #2)
5. **Phase 5**: Review all complete articles with LLM-as-a-Judge
6. **Phase 6**: User selects final article (Human-in-the-Loop #2)
7. **Phase 7**: User approves or rejects article (Human-in-the-Loop #3)
8. **Phase 8**: If rejected, regenerate second halves with feedback (loop back to Phase 5)
9. **Phase 9**: Save approved article and all variants

### Technical Features

- **Async Parallel Processing**: Efficient parallel LLM calls using asyncio
- **Type Safety**: Strict type validation with Pydantic
- **Structured Outputs**: Leverages LLM API structured output capabilities
- **Interactive CLI**: User-friendly command-line interface with Click
- **Auto Mode**: Fully automated execution with `--auto-select` flag
- **Multi-Format Output**: Save in both JSON and Markdown formats
- **Variant Preservation**: Save all generated variants for comparison

## Project Structure

### Directory Layout

```
chapter_4/section_6/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration management (API keys)
│   ├── logger.py                # Logging configuration
│   ├── main.py                  # Main entry point (CLI commands)
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLM client initialization (OpenAI, Gemini)
│   ├── model/
│   │   ├── __init__.py
│   │   └── parallel_world_model.py  # Pydantic data model definitions
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── parallel_world_prompt.py # Prompt generation logic
│   └── service/
│       ├── __init__.py
│       ├── generation_service.py    # LLM generation and pipeline nodes
│       ├── runner_service.py        # Workflow orchestration
│       └── helper.py                # UI display and file saving helpers
├── outputs/                      # Generated results (auto-created)
│   └── parallel_world_article_<uuid>/
│       ├── parallel_world_article_<uuid>.json  # Selected article (JSON)
│       ├── parallel_world_article_<uuid>.md    # Selected article (Markdown)
│       └── all_variants/         # All candidate variants
│           ├── variant_1_grade_5.md
│           ├── variant_2_grade_4.md
│           └── variant_3_grade_3.md
├── pyproject.toml                # Project dependencies
├── README.md                     # Project documentation
└── CLAUDE.md                     # This file
```

### Architecture

This project follows a three-layer architecture pattern:

```
┌──────────────────────────────────────────────────────────┐
│              CLI Layer (main.py)                         │
│   - Command-line argument parsing                        │
│   - User input and interaction                           │
│   - Output directory management                          │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│         Orchestration Layer (runner_service.py)          │
│   - Workflow phase management                            │
│   - Human-in-the-Loop control                            │
│   - Review loop orchestration                            │
│   - File saving and output management                    │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│       AI Agent Pipeline Layer (generation_service.py)    │
│   - LLM generation functions (outline, halves, review)   │
│   - Pipeline nodes (parallel generation, review, regen)  │
│   - Parallel World branching and merging logic           │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────┐
│            Infrastructure Layer                          │
│   - LLM clients (llm_client.py)                          │
│   - Prompt generation (parallel_world_prompt.py)         │
│   - Data models (parallel_world_model.py)                │
│   - Configuration (config.py)                            │
│   - Logging (logger.py)                                  │
└──────────────────────────────────────────────────────────┘
```

**Key Architectural Principles**:
- **Separation of Concerns**: Each layer has clear responsibilities
- **State Management**: Explicit state passing through pipeline nodes
- **Async-First**: All I/O operations use async/await patterns
- **Type Safety**: Pydantic models ensure data consistency

### Implementation Details

#### 1. Data Models (`src/model/parallel_world_model.py`)

Type-safe data models using Pydantic for the entire workflow:

```python
class ArticleOutline(BaseModel):
    """Article outline structure"""
    reason: str                    # Reason for choosing this outline
    title: str                     # Article title
    summary: str                   # Article summary (2-3 sentences)
    structure: list[str]           # Section headers (3-10 items)

class ArticleHalf(BaseModel):
    """First or second half of article"""
    reason: str                    # Reason for content approach
    content: str                   # Article content in markdown format

class ArticleReview(BaseModel):
    """LLM-as-a-Judge article review"""
    reasoning: str                 # Detailed reasoning (3-5 sentences)
    grade: int                     # 1 (very poor) to 5 (excellent)
    strengths: list[str]           # Article strengths (2-4 items)
    weaknesses: list[str]          # Article weaknesses (2-4 items)

    def is_acceptable(self) -> bool:
        """Check if quality is acceptable (grade >= 4)"""
        return self.grade >= 4

class ParallelSession(BaseModel):
    """Represents a single parallel world session"""
    session_id: str                # Unique session ID
    parent_session_id: str | None  # Parent session ID (if forked)
    outline: ArticleOutline | None
    first_half: str | None
    second_half: str | None
    review: ArticleReview | None
    metadata: dict                 # Additional metadata
    created_at: str               # Creation timestamp

class CompletedArticle(BaseModel):
    """Complete article with all components"""
    session_id: str
    outline: ArticleOutline
    first_half: str
    second_half: str
    review: ArticleReview | None
    language: Literal["en", "ja"]
    created_at: str

    def get_full_content(self) -> str:
        """Get complete article content"""
        return f"{self.first_half}\n\n{self.second_half}"

class ParallelWorldState(TypedDict):
    """State management for parallel world pipeline"""
    theme: str
    language: Literal["en", "ja"]
    # Phase 1: Multiple outlines generated in parallel
    outline_sessions: list[ParallelSession]
    # Phase 2: User selects one outline
    selected_outline_session_id: str | None
    # Phase 3: First half generated
    first_half_session: ParallelSession | None
    # Phase 4: Multiple second halves in parallel
    second_half_sessions: list[ParallelSession]
    # Phase 5: Reviews for each complete article
    reviewed_sessions: list[ParallelSession]
    # Phase 6: User selects best article
    final_selected_session_id: str | None
    # Phase 7-8: Human approval and feedback loop
    human_approved: bool | None
    rejected_session_ids: list[str]
    review_loop_iteration: int
    # Pipeline metadata
    llm_provider: str
    model: str
    error: str | None
    num_outline_variants: int
    num_second_half_variants: int
```

**Key Features**:
- `ParallelSession` represents each parallel world branch
- `ParallelWorldState` manages entire pipeline state
- Proper separation of TypedDict (state) and BaseModel (data)
- Immutable configurations with `frozen=True`

#### 2. Prompt Generation (`src/prompt/parallel_world_prompt.py`)

Dynamic prompt generation for each phase:

```python
def make_outline_generation_system_instruction(
    theme: str,
    language: Literal["en", "ja"]
) -> tuple[str, str]:
    """Create system instruction for outline generation"""

    lang_instruction = "in English" if language == "en" else "in Japanese (日本語)"

    # Automatically extract schema from Pydantic model
    schema_fields = {}
    for field_name, field_info in ArticleOutline.model_fields.items():
        schema_fields[field_name] = {
            "type": str(field_info.annotation),
            "description": field_info.description,
        }

    schema_json = json.dumps(schema_fields, indent=2, ensure_ascii=False)

    system_instruction = f"""You are an expert article writer and content strategist.
Your task is to create a comprehensive outline for an article {lang_instruction}.

The outline should include:
1. **Title**: A compelling and descriptive article title
2. **Summary**: A brief 2-3 sentence summary
3. **Structure**: A logical section structure with 3-10 headers

Please respond strictly following this JSON structure:

{schema_json}

Requirements:
- Response must be valid JSON
- All content must be written {lang_instruction}
- Ensure logical flow from one section to the next
"""

    user_content = f"""Please create an article outline on the following theme:

Theme: {theme}

Create an engaging and well-structured outline that would result in a high-quality article.
"""

    return system_instruction, user_content
```

**Main Prompt Functions**:
- `make_outline_generation_system_instruction()`: Outline generation
- `make_first_half_generation_system_instruction()`: First half generation
- `make_second_half_generation_system_instruction()`: Second half generation
- `make_second_half_regeneration_system_instruction()`: Regeneration with feedback
- `make_article_review_system_instruction()`: LLM-as-a-Judge review
- `make_choose_best_first_half_system_instruction()`: Select best first half variant

**Key Points**:
- Schema automatically extracted from Pydantic models
- Language-specific instructions (English/Japanese)
- Special prompts for feedback loop regeneration

#### 3. LLM Generation Service (`src/service/generation_service.py`)

Implements generation functions and pipeline nodes for both OpenAI and Gemini:

##### Basic LLM Generation Functions

```python
async def _generate_with_openai(
    prompt: list[dict[str, str]],
    response_format: type,
    model: str,
) -> Any:
    """Generic OpenAI structured output helper"""
    result = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=prompt,
        response_format=response_format,  # Pydantic model
    )
    return result.choices[0].message.parsed

async def _generate_with_gemini(
    system_instruction: str,
    user_content: str,
    response_schema: type,
    model: str,
) -> Any:
    """Generic Gemini structured output helper"""
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,  # Pydantic model
        ),
    )
    return result.parsed
```

##### Pipeline Nodes (Parallel Generation)

```python
async def generate_multiple_outlines_node(
    state: ParallelWorldState,
) -> ParallelWorldState:
    """Generate multiple article outlines in parallel (Parallel World Branching #1)"""

    logger.info(f"Generating {state['num_outline_variants']} parallel outline variants")

    # Create parallel tasks
    tasks = [
        generate_outline(
            state["theme"],
            state["language"],
            state["model"],
            LLMProvider(state["llm_provider"]),
        )
        for _ in range(state["num_outline_variants"])
    ]

    # Execute in parallel
    outlines = await asyncio.gather(*tasks)

    # Create ParallelSession for each outline
    outline_sessions = []
    for i, outline in enumerate(outlines):
        if outline:
            session = ParallelSession(
                outline=outline,
                metadata={"variant_number": i + 1, "phase": "outline_generation"},
            )
            outline_sessions.append(session)
            logger.info(f"Generated outline variant {i + 1}: {outline.title}")

    if not outline_sessions:
        return return_error_state(state, "Failed to generate any outlines")

    return {
        **state,
        "outline_sessions": outline_sessions,
        "error": None,
    }
```

##### Feedback Loop Regeneration

```python
async def regenerate_second_halves_after_rejection_node(
    state: ParallelWorldState,
) -> ParallelWorldState:
    """Regenerate second halves after human rejection (using feedback)"""

    logger.info("Regenerating second half variants based on previous feedback...")

    first_half_session = state.get("first_half_session")
    if not first_half_session or not first_half_session.outline or not first_half_session.first_half:
        return return_error_state(state, "No first half session for regeneration")

    # Collect feedback from rejected sessions
    rejected_ids = state.get("rejected_session_ids", [])
    reviewed_sessions = state.get("reviewed_sessions", [])

    previous_attempts: list[tuple[str, ArticleReview]] = []
    for session in reviewed_sessions:
        if session.session_id in rejected_ids and session.second_half and session.review:
            previous_attempts.append((session.second_half, session.review))

    logger.info(f"Using feedback from {len(previous_attempts)} previous attempt(s)")

    # Generate new second halves in parallel with feedback
    tasks = [
        regenerate_second_half(
            first_half_session.outline,
            first_half_session.first_half,
            state["language"],
            state["model"],
            LLMProvider(state["llm_provider"]),
            previous_attempts,  # Feedback from failed attempts
        )
        for _ in range(state["num_second_half_variants"])
    ]
    second_halves = await asyncio.gather(*tasks)

    # Create new sessions
    new_second_half_sessions = []
    for i, second_half in enumerate(second_halves):
        if second_half:
            session = ParallelSession(
                parent_session_id=first_half_session.session_id,
                outline=first_half_session.outline,
                first_half=first_half_session.first_half,
                second_half=second_half,
                metadata={
                    "variant_number": i + 1,
                    "phase": "second_half_regenerated",
                    "iteration": state.get("review_loop_iteration", 0),
                },
            )
            new_second_half_sessions.append(session)

    return {
        **state,
        "second_half_sessions": new_second_half_sessions,
        "error": None,
    }
```

**Key Points**:
- `asyncio.gather()` for efficient parallel execution
- State management pattern (receive state, return updated state)
- Comprehensive error handling and logging
- Feedback incorporation in regeneration

#### 4. Workflow Orchestration (`src/service/runner_service.py`)

Manages overall workflow phases and controls Human-in-the-Loop and review loops:

```python
async def run_parallel_world_article_generation(
    theme: str,
    language: Literal["en", "ja"],
    llm_provider: LLMProvider,
    model: str,
    output_directory: str,
    num_outline_variants: int,
    num_second_half_variants: int,
    auto_select: bool,
) -> CompletedArticle | None:
    """Run complete Parallel World article generation workflow"""

    # Initialize state
    state: ParallelWorldState = {
        "theme": theme,
        "language": language,
        "outline_sessions": [],
        "selected_outline_session_id": None,
        "first_half_session": None,
        "second_half_sessions": [],
        "reviewed_sessions": [],
        "final_selected_session_id": None,
        "human_approved": None,
        "rejected_session_ids": [],
        "review_loop_iteration": 0,
        "llm_provider": llm_provider.value,
        "model": model,
        "error": None,
        "num_outline_variants": num_outline_variants,
        "num_second_half_variants": num_second_half_variants,
    }

    # Phase 1: Generate Multiple Outlines
    state = await generate_outlines(state)
    if state.get("error"):
        return None

    # Phase 2: Human Selects Outline
    state = await select_outline(state, auto_select)
    if state.get("error"):
        return None

    # Phase 3: Generate First Half
    state = await generate_first_half(state)
    if state.get("error"):
        return None

    # Phase 4: Generate Multiple Second Halves
    state = await generate_second_halves(state)
    if state.get("error"):
        return None

    # Phase 5: Review All Articles
    state = await review_articles(state)
    if state.get("error"):
        return None

    # Phase 6-8: Review Loop (select, approve/reject, regenerate)
    state, final_article, approved, iteration = await review_loop(
        state, auto_select, max_iterations=5
    )

    if not final_article:
        return None

    # Phase 9: Save Final Article
    save_article(state, final_article, output_directory, iteration)

    return final_article
```

**Review Loop Implementation**:

```python
async def review_loop(
    state: ParallelWorldState,
    auto_select: bool,
    max_iterations: int = 5,
) -> tuple[ParallelWorldState, CompletedArticle | None, bool, int]:
    """Phase 6-8: Review loop - select, approve/reject, regenerate"""

    iteration = 0
    human_approved = False
    final_article = None

    while not human_approved and iteration < max_iterations:
        iteration += 1

        # Phase 6: Select final article
        state, completed_article = select_final_article(state, auto_select, iteration)

        if not completed_article:
            return state, None, False, iteration

        # Phase 7: Get human approval
        state, human_approved = approve_article(state, completed_article, auto_select)

        if human_approved:
            final_article = completed_article
            break

        # Phase 8: Regenerate if rejected (loop back to Phase 5)
        state = await regenerate_and_review(state, iteration)

        if state.get("error"):
            return state, None, False, iteration

    # Handle max iterations reached
    if not human_approved:
        click.echo(f"\n⚠️  Maximum iterations ({max_iterations}) reached without approval")
        click.echo("Saving the last selected article...")
        if not final_article:
            final_article = completed_article

    return state, final_article, human_approved, iteration
```

**Key Points**:
- Each phase implemented as independent function
- Clear separation of Human-in-the-Loop decision points
- Feedback loop for quality improvement
- Maximum iteration limit prevents infinite loops

#### 5. CLI Interface (`src/main.py`)

Interactive command-line tool using Click library:

```python
@click.command()
@click.option("--theme", "-t", type=str, required=True, help="Article theme/topic.")
@click.option("--language", "-l", type=click.Choice(["en", "ja"]), required=True)
@click.option("--llm-provider", "-lp", type=click.Choice([...]), required=True)
@click.option("--model", "-m", type=click.Choice([...]), required=True)
@click.option("--output-directory", "-od", type=click.Path(), default="outputs")
@click.option("--num-outline-variants", "-no", type=int, default=3)
@click.option("--num-second-half-variants", "-ns", type=int, default=3)
@click.option("--auto-select", "-a", is_flag=True)
@async_cmd
async def main(
    theme: str,
    language: str,
    llm_provider: str,
    model: str,
    output_directory: str = "outputs",
    num_outline_variants: int = 3,
    num_second_half_variants: int = 3,
    auto_select: bool = False,
) -> None:
    """Generate an article using parallel world pattern with human-in-the-loop."""

    # Convert to enum
    llm_provider_enum = LLMProvider(llm_provider.lower())

    # Validate provider and model combination
    if llm_provider_enum == LLMProvider.OPENAI and model.lower() not in OpenAIModel.list_str():
        raise ValueError(f"Invalid model '{model}' for provider '{llm_provider_enum.value}'.")

    # Create output directory
    os.makedirs(output_directory, exist_ok=True)

    # Run workflow
    await run_parallel_world_article_generation(
        theme=theme,
        language=language,
        llm_provider=llm_provider_enum,
        model=model.lower(),
        output_directory=output_directory,
        num_outline_variants=num_outline_variants,
        num_second_half_variants=num_second_half_variants,
        auto_select=auto_select,
    )
```

#### 6. LLM Clients (`src/client/llm_client.py`)

Initialize clients for both OpenAI and Gemini:

```python
class LLMProvider(StrEnum):
    """Enum for LLM providers"""
    OPENAI = "openai"
    GEMINI = "gemini"

class OpenAIModel(StrEnum):
    """Available OpenAI models"""
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

    @staticmethod
    def list_str() -> list[str]:
        return [model.value for model in OpenAIModel]

class GeminiModel(StrEnum):
    """Available Gemini models"""
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    @staticmethod
    def list_str() -> list[str]:
        return [model.value for model in GeminiModel]

# Initialize clients
google_genai_client = genai.Client(api_key=config.gemini_api_key)
openai_client = AsyncOpenAI(api_key=config.openai_api_key)
```

## Usage

### Environment Requirements

- **Python**: 3.13.2 or higher
- **Dependencies**:
  - click>=8.3.0
  - google-genai>=1.45.0
  - openai>=2.4.0
  - pydantic>=2.12.2
  - python-dotenv>=1.1.1

### Setup

1. **Create environment variables file**

```bash
# Create .envrc file
cat > .envrc << EOF
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
export GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
EOF

# If using direnv
direnv allow

# Or manually export
source .envrc
```

2. **Install dependencies**

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

### Basic Usage

#### Generate article with Gemini (default)

```bash
# English article with Gemini
uv run python -m src.main \
  --theme "The Future of Artificial Intelligence" \
  --language en \
  --llm-provider gemini \
  --model gemini-2.5-flash

# Japanese article with OpenAI
uv run python -m src.main \
  --theme "人工知能の未来" \
  --language ja \
  --llm-provider openai \
  --model gpt-4o
```

#### Advanced configuration

```bash
# Custom settings
uv run python -m src.main \
  -t "Quantum Computing Breakthrough" \
  -l en \
  -lp openai \
  -m gpt-4o \
  -od ./my_articles \
  -no 5 \
  -ns 4

# Option explanations:
# -t, --theme: Article theme/topic
# -l, --language: Language (en or ja)
# -lp, --llm-provider: LLM provider (openai or gemini)
# -m, --model: Model to use
# -od, --output-directory: Output directory
# -no, --num-outline-variants: Number of outline variants (default: 3)
# -ns, --num-second-half-variants: Number of second half variants (default: 3)
```

#### Auto mode (no human interaction)

```bash
# Fully automated execution
uv run python -m src.main \
  -t "Climate Change Solutions" \
  -l en \
  -lp gemini \
  -m gemini-2.5-flash \
  -a

# -a, --auto-select flag behavior:
# - Phase 2: Auto-select first outline
# - Phase 6: Auto-select highest graded article
# - Phase 7: Auto-approve if Grade >= 4, else auto-reject
```

#### Display help

```bash
uv run python -m src.main --help
```

**Output**:
```
Usage: python -m src.main [OPTIONS]

  Generate an article using parallel world pattern with human-in-the-loop.

  This tool implements the parallel world pattern described in CLAUDE.md:
  1. Generate multiple outline variants in parallel
  2. User selects the best outline (human-in-the-loop)
  3. Generate first half based on selected outline
  4. Generate multiple second half variants in parallel
  5. Review all variants using LLM-as-a-Judge
  6. User selects the best complete article (human-in-the-loop)

Options:
  -t, --theme TEXT                Article theme/topic.  [required]
  -l, --language [en|ja]          Article language (en: English, ja:
                                  Japanese).  [required]
  -lp, --llm-provider [openai|gemini]
                                  The LLM provider to use (openai or gemini).
                                  [required]
  -m, --model [gpt-4o|gemini-2.5-flash|...]
                                  The model to use.  [required]
  -od, --output-directory PATH    The directory to save output files.
  -no, --num-outline-variants INTEGER
                                  Number of outline variants to generate
                                  (default: 3).
  -ns, --num-second-half-variants INTEGER
                                  Number of second half variants to generate
                                  (default: 3).
  -a, --auto-select               Automatically select best options without
                                  human interaction.
  --help                          Show this message and exit.
```

### Output Examples

#### Workflow Execution Output

```
╔════════════════════════════════════════════════════════════════════════════╗
║         Parallel World Article Generation - Human-in-the-Loop             ║
╚════════════════════════════════════════════════════════════════════════════╝

Configuration:
  Theme: The Future of Artificial Intelligence
  Language: en
  LLM Provider: gemini
  Model: gemini-2.5-flash
  Outline Variants: 3
  Second Half Variants: 3
  Mode: Interactive

================================================================================

🌍 PHASE 1: Generating Multiple Outline Variants (Parallel World Branching)
Creating 3 different article outlines in parallel...
✅ Generated 3 outline variants

================================================================================

👤 PHASE 2: Human-in-the-Loop - Select Your Preferred Outline

[Variant 1]
Reason: This outline provides a comprehensive yet approachable overview...
Title: The Dawn of Thinking Machines: Navigating the Future of AI
Summary: Artificial Intelligence is rapidly evolving from science fiction...
Structure:
  1. Introduction: The AI Revolution
  2. Current State of AI Technology
  3. Breakthrough Applications in Healthcare
  4. AI in Education and Creative Fields
  5. Ethical Considerations and Challenges
  6. The Road Ahead: 2025-2035
  7. Conclusion: Embracing the AI Future

[Variant 2]
Reason: Focuses on practical implications and real-world impact...
Title: AI Unleashed: How Intelligent Systems Are Reshaping Our World
Summary: From autonomous vehicles to medical diagnosis...
Structure:
  1. The AI Awakening
  2. AI in Daily Life: Current Applications
  3. Industry Transformation
  4. The Promise and Peril
  5. Preparing for the AI Era

[Variant 3]
Reason: Emphasizes the human element in AI development...
Title: Human + AI: Building a Collaborative Future
Summary: The future of AI isn't about replacement but augmentation...
Structure:
  1. Introduction: Beyond the Hype
  2. AI as Human Augmentation
  3. Success Stories Across Industries
  4. Addressing the Challenges
  5. A Vision for Tomorrow

Select an outline (1-3): 1
✅ Selected: The Dawn of Thinking Machines: Navigating the Future of AI

================================================================================

📝 PHASE 3: Generating First Half of Article
✅ Generated first half (2847 characters)

Preview:
# Introduction: The AI Revolution

The artificial intelligence landscape in 2025 represents a pivotal moment...

## Current State of AI Technology

Today's AI systems have evolved beyond simple pattern recognition...

================================================================================

🌍 PHASE 4: Generating Multiple Second Half Variants (Parallel World Branching)
Creating 3 different endings in parallel...
✅ Generated 3 second half variants

================================================================================

⚖️  PHASE 5: Reviewing All Articles with LLM-as-a-Judge
✅ Reviewed 3 complete articles

================================================================================

👤 PHASE 6: Human-in-the-Loop - Select Your Preferred Article (Iteration 1)

[Article Variant 1] - Grade: 5/5
Reasoning: This article excellently balances technical depth with accessibility...
Strengths:
  ✓ Clear, engaging writing that maintains reader interest throughout
  ✓ Comprehensive coverage of AI applications across multiple domains
  ✓ Well-structured flow from current state to future predictions
  ✓ Thoughtful discussion of ethical considerations and challenges
Weaknesses:
  (No significant weaknesses identified)

Second Half Preview:
## The Road Ahead: 2025-2035

Looking forward, the next decade promises transformative advances...

[Article Variant 2] - Grade: 4/5
Reasoning: Strong article with good technical content, though slightly less engaging...
Strengths:
  ✓ Accurate technical information
  ✓ Good coverage of practical applications
  ✓ Clear structure
Weaknesses:
  ✗ Could be more engaging in writing style
  ✗ Some sections feel slightly rushed

Second Half Preview:
## Ethical Considerations and Challenges

As AI systems become more powerful...

[Article Variant 3] - Grade: 3/5
Reasoning: Adequate but lacks depth in several areas...
Strengths:
  ✓ Good introduction
  ✓ Covers basic concepts well
Weaknesses:
  ✗ Lacks depth in technical discussions
  ✗ Limited coverage of future implications
  ✗ Some sections feel incomplete

Second Half Preview:
## Conclusion: Embracing the AI Future

In conclusion, AI represents both opportunity...

Select final article (1-3): 1

================================================================================

✅ PHASE 7: Human-in-the-Loop - Approve or Reject Article

📝 Selected Article Preview:
Title: The Dawn of Thinking Machines: Navigating the Future of AI
Grade: 5/5
Review: This article excellently balances technical depth with accessibility...

✅ Do you approve this article? (yes/no): yes

✅ Article approved! Proceeding to save...

================================================================================

💾 Saving Final Article

✅ Article Generation Complete!

Selected Article Details:
  Title: The Dawn of Thinking Machines: Navigating the Future of AI
  Grade: 5/5
  Total Length: 5482 characters
  Review Loop Iterations: 1

Files saved:
  📄 JSON: outputs/parallel_world_article_a1b2c3d4.../parallel_world_article_a1b2c3d4....json
  📝 Markdown: outputs/parallel_world_article_a1b2c3d4.../parallel_world_article_a1b2c3d4....md

Session Metadata:
  Session ID: a1b2c3d4e5f6...
  Created: 2025-10-26T10:30:45.123456
  Outline variants generated: 3
  Second half variants generated: 3

📁 All variants saved to: outputs/parallel_world_article_a1b2c3d4.../all_variants

================================================================================

🎉 Parallel World Article Generation Complete!
```

#### Generated Files

**Directory Structure**:
```
outputs/parallel_world_article_a1b2c3d4e5f6.../
├── parallel_world_article_a1b2c3d4e5f6....json     # Selected article (JSON)
├── parallel_world_article_a1b2c3d4e5f6....md       # Selected article (Markdown)
└── all_variants/                                   # All candidates
    ├── variant_1_grade_5.md
    ├── variant_2_grade_4.md
    └── variant_3_grade_3.md
```

**JSON Output Example** (`parallel_world_article_<uuid>.json`):

```json
{
    "session_id": "a1b2c3d4e5f6...",
    "outline": {
        "reason": "This outline provides a comprehensive yet approachable overview...",
        "title": "The Dawn of Thinking Machines: Navigating the Future of AI",
        "summary": "Artificial Intelligence is rapidly evolving from science fiction...",
        "structure": [
            "Introduction: The AI Revolution",
            "Current State of AI Technology",
            "Breakthrough Applications in Healthcare",
            "AI in Education and Creative Fields",
            "Ethical Considerations and Challenges",
            "The Road Ahead: 2025-2035",
            "Conclusion: Embracing the AI Future"
        ]
    },
    "first_half": "# Introduction: The AI Revolution\n\nThe artificial intelligence landscape...",
    "second_half": "## The Road Ahead: 2025-2035\n\nLooking forward, the next decade...",
    "review": {
        "reasoning": "This article excellently balances technical depth with accessibility...",
        "grade": 5,
        "strengths": [
            "Clear, engaging writing that maintains reader interest throughout",
            "Comprehensive coverage of AI applications across multiple domains",
            "Well-structured flow from current state to future predictions",
            "Thoughtful discussion of ethical considerations and challenges"
        ],
        "weaknesses": []
    },
    "language": "en",
    "created_at": "2025-10-26T10:30:45.123456"
}
```

**Markdown Output Example** (`parallel_world_article_<uuid>.md`):

```markdown
# The Dawn of Thinking Machines: Navigating the Future of AI

# Introduction: The AI Revolution

The artificial intelligence landscape in 2025 represents a pivotal moment...

## Current State of AI Technology

Today's AI systems have evolved beyond simple pattern recognition...

## Breakthrough Applications in Healthcare

One of the most promising frontiers for AI lies in healthcare...

[... article content continues ...]

## Conclusion: Embracing the AI Future

As we stand at this crossroads, the future of AI depends on...

---

# Article Review

## Review Grade: 5/5

### Reasoning
This article excellently balances technical depth with accessibility, providing readers with both a comprehensive overview of current AI capabilities and thoughtful projections about future developments. The writing is engaging throughout, and the structure effectively guides readers from foundational concepts to advanced implications.

### Strengths
- Clear, engaging writing that maintains reader interest throughout
- Comprehensive coverage of AI applications across multiple domains
- Well-structured flow from current state to future predictions
- Thoughtful discussion of ethical considerations and challenges

### Weaknesses
No significant weaknesses identified.
```

### Testing

While this project doesn't include automated unit tests, you can perform manual testing:

#### 1. Basic Functionality Test (Interactive Mode)

```bash
# Test OpenAI API (English)
uv run python -m src.main \
  -t "Test Article Theme" \
  -l en \
  -lp openai \
  -m gpt-4o-mini \
  -od test_outputs \
  -no 2 \
  -ns 2

# Test Gemini API (Japanese)
uv run python -m src.main \
  -t "テスト記事のテーマ" \
  -l ja \
  -lp gemini \
  -m gemini-2.5-flash \
  -od test_outputs \
  -no 2 \
  -ns 2
```

**Expected Behavior**:
- Phase 1 displays 2 outline candidates
- User can select an outline
- Phase 3 generates first half with preview
- Phase 4 generates 2 second half candidates
- Phase 5 reviews all candidates
- Phase 6 allows user to select final article
- Phase 7 allows user to approve/reject
- Results saved to `test_outputs/parallel_world_article_<uuid>/`

#### 2. Auto Mode Test

```bash
# Fully automated execution
uv run python -m src.main \
  -t "Automated Test Theme" \
  -l en \
  -lp gemini \
  -m gemini-2.5-flash \
  -od test_outputs_auto \
  -no 3 \
  -ns 3 \
  -a
```

**Expected Behavior**:
- All phases execute without user input
- Phase 2 auto-selects first outline
- Phase 6 auto-selects highest graded article
- Phase 7 auto-approves if Grade >= 4
- Results automatically saved

#### 3. Feedback Loop Test

```bash
# Test regeneration with feedback
uv run python -m src.main \
  -t "Complex Technical Topic" \
  -l en \
  -lp openai \
  -m gpt-4o-mini \
  -od test_outputs_loop \
  -no 2 \
  -ns 2
```

**Test Steps**:
1. Phase 6: Intentionally select low-grade article (Grade <= 3)
2. Phase 7: Select "no" to reject
3. Phase 8: Verify regeneration occurs
4. Confirm Phases 5-7 execute again
5. Verify maximum 5 iterations limit

#### 4. Output Validation

```bash
# Validate generated JSON
cat test_outputs/parallel_world_article_*/parallel_world_article_*.json | jq .

# Python structure validation
python -c "
from src.model.parallel_world_model import CompletedArticle
import json
import glob

# Load latest output file
files = glob.glob('test_outputs/*/parallel_world_article_*.json')
latest_file = max(files, key=lambda x: x)

with open(latest_file) as f:
    data = json.load(f)
    article = CompletedArticle(**data)
    print(f'✅ Valid Article: {article.outline.title}')
    print(f'   Grade: {article.review.grade if article.review else \"N/A\"}/5')
    print(f'   Length: {len(article.get_full_content())} characters')
"

# Check all variants
ls -lh test_outputs/*/all_variants/

# View variant content
cat test_outputs/*/all_variants/variant_1_grade_*.md
```

#### 5. Error Handling Test

```bash
# Test with invalid API key (error handling check)
OPENAI_API_KEY=invalid uv run python -m src.main \
  -t "Error Test" \
  -l en \
  -lp openai \
  -m gpt-4o

# Test with invalid model name
uv run python -m src.main \
  -t "Error Test" \
  -l en \
  -lp openai \
  -m invalid-model
```

**Expected Behavior**:
- Appropriate error messages displayed
- Program exits gracefully with error state
- No crashes or unhandled exceptions

## Design Patterns and Implementation Features

### 1. Parallel World Pattern Implementation

The core Parallel World Pattern consists of:

**Branching Points**:
- **Branching #1 (Phase 1)**: Generate multiple outline variants in parallel
- **Branching #2 (Phase 4)**: Generate multiple second half variants in parallel

**Selection Points**:
- **Selection #1 (Phase 2)**: User selects outline (Human-in-the-Loop)
- **Selection #2 (Phase 6)**: User selects final article (Human-in-the-Loop)

**Feedback Loop**:
- **Phases 7-8**: Feed rejected article reviews back into next generation

**Key Benefits**:
- **Diversity**: Multiple creative directions explored simultaneously
- **Quality**: Best result selected from multiple candidates
- **Control**: Human oversight at critical decision points
- **Learning**: Feedback improves subsequent generations

### 2. Human-in-the-Loop Integration

Three critical decision points with user intervention:

1. **Outline Selection (Phase 2)**: Determines article direction and structure
2. **Final Article Selection (Phase 6)**: Chooses optimal variant from candidates
3. **Article Approval/Rejection (Phase 7)**: Quality threshold enforcement

Auto mode (`--auto-select`) allows LLM-based decisions to replace human intervention for automated workflows.

### 3. LLM-as-a-Judge Integration

Uses LLM itself as objective quality evaluator:

**Evaluation Criteria**:
- **Content Quality (30%)**: Accuracy, informativeness, value
- **Structure & Flow (25%)**: Adherence to outline, logical flow
- **Writing Quality (20%)**: Clarity, engagement, craftsmanship
- **Completeness (15%)**: Coverage of theme and sections
- **Language Quality (10%)**: Appropriateness, consistency, error-free

**Grading Scale**:
- **5 (Excellent)**: Outstanding, exceeds expectations
- **4 (Good)**: High quality with minor improvements
- **3 (Acceptable)**: Adequate but with noticeable gaps
- **2 (Poor)**: Significant issues
- **1 (Very Poor)**: Fails basic standards

**Feedback Components**:
- Detailed reasoning (3-5 sentences)
- Specific strengths (2-4 items)
- Specific weaknesses (2-4 items if any)

### 4. State Management Pattern

Explicit state management using `ParallelWorldState` TypedDict:

**Key Principles**:
- Each phase's results stored in state object
- Immutable state updates: `{**state, "key": value}`
- Each node function follows `state -> state` pure function pattern
- Error states explicitly tracked in state object

**Benefits**:
- Predictable state transitions
- Easy debugging and testing
- Clear data flow through pipeline
- Enables state persistence/resumption

### 5. Async Parallel Processing

Efficient parallel execution using `asyncio.gather()`:

```python
# Generate 3 outlines in parallel
tasks = [generate_outline(...) for _ in range(3)]
outlines = await asyncio.gather(*tasks)
```

**Performance Benefits**:
- Simultaneous LLM API calls
- Reduced total execution time
- Efficient resource utilization
- Non-blocking I/O operations

### 6. Type Safety and Validation

Comprehensive Pydantic usage:

**Features**:
- All data models inherit from BaseModel
- Runtime type validation
- Structured outputs directly from LLM
- Automatic serialization/deserialization
- Field-level validation with constraints

**Benefits**:
- Catch errors at model boundary
- Self-documenting data structures
- IDE autocomplete support
- Consistent data formats

## Troubleshooting

### Common Issues and Solutions

#### 1. API Key Errors

**Problem**: `KeyError: 'OPENAI_API_KEY'` or `KeyError: 'GEMINI_API_KEY'`

**Solution**:
```bash
# Check if environment variables are set
echo $OPENAI_API_KEY
echo $GEMINI_API_KEY

# Create .envrc file with keys
cat > .envrc << EOF
export OPENAI_API_KEY=your-key-here
export GEMINI_API_KEY=your-key-here
EOF

source .envrc
```

#### 2. Model Name Errors

**Problem**: `Invalid model 'xxx' for provider 'openai'`

**Solution**:
```bash
# Check available models
uv run python -m src.main --help

# For OpenAI: gpt-4o, gpt-4o-mini, gpt-4.1, etc.
# For Gemini: gemini-2.5-flash, gemini-2.5-pro, etc.
```

#### 3. Output Directory Permission Errors

**Problem**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
# Specify writable directory
uv run python -m src.main ... -od ~/my_articles

# Or fix permissions
chmod 755 outputs/
```

#### 4. Generation Failures Mid-Pipeline

**Problem**: Error occurs during execution

**Solutions**:
- Check logs for error messages
- API rate limits: Wait and retry
- Reduce variant counts: `-no 2 -ns 2`
- Verify API key validity
- Check network connectivity

#### 5. Low-Quality Outputs

**Problem**: Articles consistently receive low grades

**Solutions**:
- Use more capable models (gpt-4o instead of gpt-4o-mini)
- Increase variant counts for more options
- Refine theme to be more specific
- Use feedback loop to improve (reject low-grade articles)

## Summary

This project demonstrates a practical implementation of the Parallel World Pattern, showcasing:

1. **Parallel Generation & Selection**: Workflow that generates multiple candidates and selects optimal ones
2. **Human-in-the-Loop**: Strategic human decision-making at critical points
3. **LLM-as-a-Judge**: Leveraging LLM as quality evaluator
4. **Feedback Loop**: Learning from failures to improve subsequent generations
5. **Type-Safe Implementation**: Robust data modeling with Pydantic
6. **Async Parallel Processing**: Efficient LLM API calls with asyncio

By combining these techniques, the system achieves high-quality content generation while maintaining user control and flexibility.

## Advanced Use Cases

### 1. Batch Article Generation

```bash
# Generate multiple articles on different themes
for theme in "AI Ethics" "Quantum Computing" "Climate Tech"; do
  uv run python -m src.main \
    -t "$theme" \
    -l en \
    -lp gemini \
    -m gemini-2.5-flash \
    -a \
    -od "outputs/$theme"
done
```

### 2. A/B Testing Article Styles

```bash
# Generate variants with different LLM providers
uv run python -m src.main -t "Topic" -l en -lp openai -m gpt-4o -od outputs/openai
uv run python -m src.main -t "Topic" -l en -lp gemini -m gemini-2.5-pro -od outputs/gemini
```

### 3. Quality-Focused Generation

```bash
# Maximum variants for best quality
uv run python -m src.main \
  -t "Critical Topic" \
  -l en \
  -lp openai \
  -m gpt-4o \
  -no 7 \
  -ns 5
```

## Future Enhancements

Potential improvements to consider:

1. **Automated Testing**: Add pytest unit and integration tests
2. **State Persistence**: Save/resume pipeline state
3. **Custom Evaluation Criteria**: User-defined review metrics
4. **Multi-Language Support**: Extend beyond English/Japanese
5. **Template System**: Customizable article templates
6. **Streaming Output**: Real-time generation display
7. **Cost Tracking**: Monitor API usage and costs
8. **Parallel Phase Execution**: Run independent phases concurrently

## License

This project is part of the LLM Best Practice Book educational materials.

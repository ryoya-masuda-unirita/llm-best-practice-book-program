# Chapter 4 Section 4: Hierarchical AI Agent - Personalized Learning Platform

## Overview

This project implements a **Hierarchical (Multi-Layer) AI Agent** pattern for a personalized learning platform. The system uses a 4-layer architecture to autonomously create customized learning plans based on learner goals and constraints.

The hierarchical approach separates concerns across different abstraction levels, similar to organizational structures:
- **Strategy Layer (戦略・プランニング層)**: Defines learning objectives and roadmaps
- **Tactics Layer (戦術・マネジメント層)**: Designs weekly/daily curricula
- **Execution Layer (実行層)**: Generates content and quizzes
- **Reflection Layer (自己評価・省察層)**: Evaluates quality and goal alignment

Reference: See `REFERENCE.md` for architectural principles.

## Architecture

```
+----------------------------------------------------------+
|                    CLI Layer (main.py)                    |
|              - Command-line argument parsing              |
|              - Profile loading and validation             |
+---------------------------+------------------------------+
                            |
                            v
+---------------------------+------------------------------+
|              LangGraph State Machine                      |
|                 (llm_pipeline_service.py)                 |
+---------------------------+------------------------------+
                            |
                            v
         ┌─────────────────────────────────┐
         │    1. STRATEGY LAYER            │
         │    (戦略・プランニング層)         │
         │    - Goal interpretation        │
         │    - Roadmap creation           │
         │    - Blueprint for lower layers │
         └──────────────┬──────────────────┘
                        │
                        v
         ┌─────────────────────────────────┐
         │    2. TACTICS LAYER             │
         │    (戦術・マネジメント層)         │
         │    - Task decomposition         │
         │    - Weekly/Daily planning      │
         │    - Task assignment            │
         └──────────────┬──────────────────┘
                        │
                        v
         ┌─────────────────────────────────┐
         │    3. EXECUTION LAYER           │◄───┐
         │    (実行層)                      │    │
         │    - Content generation         │    │ Loop
         │    - Quiz creation              │    │
         └──────────────┬──────────────────┘    │
                        │                       │
                        ▼                       │
                 ┌──────┴──────┐                │
                 │ More tasks? │────────────────┘
                 └──────┬──────┘
                        │ No
                        v
         ┌─────────────────────────────────┐
         │    4. REFLECTION LAYER          │
         │    (自己評価・省察層)            │
         │    - Quality evaluation         │
         │    - Goal alignment check       │
         │    - Improvement recommendations│
         └──────────────┬──────────────────┘
                        │
                        v
                      [END]
```

### Directory Structure

```
chapter_4/section_4/
|-- src/
|   |-- __init__.py              # Package initialization
|   |-- config.py                # Configuration (API keys)
|   |-- logger.py                # Logging utilities
|   |-- main.py                  # CLI entry point
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py        # OpenAI client setup
|   |-- layer/                   # 4-Layer Agent Implementation
|   |   |-- __init__.py          # Layer package exports
|   |   |-- base.py              # BaseAgent abstract class
|   |   |-- strategy.py          # Strategy Layer (戦略・プランニング層)
|   |   |-- tactics.py           # Tactics Layer (戦術・マネジメント層)
|   |   |-- execution.py         # Execution Layer (実行層)
|   |   +-- reflection.py        # Reflection Layer (自己評価・省察層)
|   |-- model/
|   |   |-- __init__.py
|   |   +-- llm_pipeline_model.py  # Pydantic data models
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- llm_pipeline_prompt.py # Agent prompts per layer
|   +-- service/
|       |-- __init__.py
|       +-- llm_pipeline_service.py  # LangGraph orchestration
|-- outputs/                     # Generated learning plans
|-- .envrc.example               # Environment variable template
|-- pyproject.toml               # Project dependencies
|-- Makefile                     # Development commands
|-- REFERENCE.md                 # Architectural principles reference
+-- CLAUDE.md                    # This file
```

## Key Components

### 4-Layer Agent Architecture

| Layer      | Module              | Responsibility                                      |
|------------|---------------------|-----------------------------------------------------|
| Strategy   | `layer/strategy.py` | Analyze goals, create learning roadmap (blueprint)  |
| Tactics    | `layer/tactics.py`  | Design weekly/daily curriculum, assign tasks        |
| Execution  | `layer/execution.py`| Generate content and quizzes (ContentAgent, QuizAgent) |
| Reflection | `layer/reflection.py`| Evaluate quality, check goal alignment, recommend adjustments |

### Layer Responsibilities (REFERENCE.md)

1. **Strategy Layer (戦略・プランニング層)**
   - Interprets ambiguous user goals
   - Sets overall architecture and direction
   - Creates blueprints for lower layers
   - Does NOT involve itself in implementation details

2. **Tactics Layer (戦術・マネジメント層)**
   - Transforms strategy into executable sub-tasks
   - Creates ToDo lists for execution layer
   - Manages progress aggregation
   - Acts as middle-management bridge

3. **Execution Layer (実行層)**
   - Performs concrete tasks faithfully
   - Operates external tools (LLM for content generation)
   - Specialists: ContentAgent, QuizAgent
   - Does NOT make strategic decisions

4. **Reflection Layer (自己評価・省察層)**
   - Independent quality auditor
   - Monitors execution outputs
   - Evaluates goal alignment
   - Requests plan corrections when needed
   - Prevents runaway execution in wrong directions

### Data Models (llm_pipeline_model.py)

**Strategy Layer Models:**
- `LearningModule`, `LearningRoadmap`, `StrategyOutput`

**Tactics Layer Models:**
- `DailyTask`, `WeeklyPlan`, `TacticsOutput`

**Execution Layer Models:**
- `LearningContent`, `Quiz`, `QuizQuestion`, `LearningSession`

**Reflection Layer Models:**
- `ProgressMetrics`, `ProgressReport`

**Session & State Models:**
- `LearnerProfile`, `PersonalizedLearningPlan`, `HierarchicalAgentState`

### State Machine Flow

```
strategy -> tactics -> execution (loop) -> reflection -> END
```

## Dependencies

| Package           | Purpose                            |
|-------------------|------------------------------------|
| langchain-openai  | OpenAI integration for LangChain   |
| langgraph         | State machine for agent workflows  |
| openai            | OpenAI API client                  |
| pydantic          | Data validation and modeling       |
| click             | CLI framework                      |
| python-dotenv     | Environment variable management    |

## Usage

### Setup

1. Create environment file:
```bash
cp .envrc.example .envrc
# Edit .envrc and set your API key:
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

2. Install dependencies:
```bash
uv sync
```

### Run

```bash
# Basic usage with learning goal
uv run python -m src.main -g "3 months to learn Python programming" -h 10 -d 12

# Using a profile JSON file
uv run python -m src.main -p example/learner_profile.json

# Specify current knowledge
uv run python -m src.main -g "Learn data analysis" -k "Excel basics,Statistics"

# Use a specific model
uv run python -m src.main -g "Learn SQL" -m gpt-4o-mini
```

### CLI Options

| Option                  | Short | Description                           | Default   |
|-------------------------|-------|---------------------------------------|-----------|
| --model                 | -m    | OpenAI model to use                   | gpt-4o    |
| --output-directory      | -od   | Directory for output files            | outputs   |
| --profile-file          | -p    | JSON file with learner profile        | None      |
| --goal                  | -g    | Learning goal description             | None      |
| --hours-per-week        | -h    | Available study hours per week        | 10        |
| --duration-weeks        | -d    | Target duration in weeks              | 12        |
| --current-knowledge     | -k    | Comma-separated current skills        | ""        |

### Example Profile JSON

```json
{
  "learner_id": "learner_001",
  "learning_goal": "3 months to become proficient in data analysis",
  "current_knowledge": ["Excel basics", "Statistics fundamentals"],
  "available_hours_per_week": 10,
  "preferred_content_types": ["video", "exercise"],
  "target_duration_weeks": 12
}
```

## Development Commands

```bash
make lint    # Run ruff linter with auto-fix
make fmt     # Format code with ruff
make fix     # Run both lint and format
make mypy    # Type checking with mypy
```

## Implementation Notes

### 4-Layer Hierarchical Agent Flow

1. **Strategy Layer**: Analyzes learner profile, determines skill levels, creates module-based roadmap as a blueprint
2. **Tactics Layer**: Transforms roadmap into weekly themes and daily tasks, creates ToDo lists for execution
3. **Execution Loop**: Iterates through tasks generating content and quizzes (max 5 sessions for first week)
4. **Reflection Layer**: Evaluates output quality, checks goal alignment, provides recommendations

### Key Design Principles (from REFERENCE.md)

- **Separation of Concerns**: Each layer has a distinct abstraction level and responsibility
- **Clear Interfaces**: Layers communicate via structured JSON data (not natural language)
- **Independent Audit**: Reflection layer operates independently to evaluate execution outputs
- **Bottom-up Development**: Start with execution layer components, add higher layers incrementally

### JSON Response Handling

The base agent includes robust JSON parsing with:
- Multiple extraction strategies (raw JSON, markdown code blocks, brace matching)
- Truncated JSON repair (closing unclosed brackets/braces)
- Retry logic with configurable attempts (MAX_RETRIES=3)

### Skill Levels

- beginner: No prior knowledge
- elementary: Basic concepts understood
- intermediate: Can work independently on basic tasks
- upper_intermediate: Can handle complex tasks
- advanced: Expert level, can teach others

### Content Types

- video: Video content
- article: Text-based articles
- interactive: Interactive tutorials
- exercise: Practice exercises
- project: Project-based learning

## Trade-offs and Considerations

As noted in REFERENCE.md:

- **Latency**: Multi-layer processing increases response time
- **Complexity**: Layer interfaces and state management add design complexity
- **Rigidity Risk**: Upper layer decisions may override valuable insights from execution
- **Error Propagation**: Strategy mistakes affect all downstream layers

## Output

The system generates a markdown file containing:
- Learner profile summary
- Strategy overview (domain, levels, duration)
- Learning roadmap with milestones
- Module descriptions
- Weekly curriculum details
- Sample learning sessions with quizzes
- Progress report with recommendations from reflection layer

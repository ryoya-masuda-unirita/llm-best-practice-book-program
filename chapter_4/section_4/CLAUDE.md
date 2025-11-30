# Chapter 4 Section 4: Hierarchical AI Agent - Personalized Learning Platform

## Overview

This project implements a **Hierarchical AI Agent** pattern for a personalized learning platform. The system uses a three-layer architecture (Strategy, Tactics, Execution) to autonomously create customized learning plans based on learner goals and constraints.

The hierarchical approach separates concerns across different abstraction levels:
- **Strategy Layer**: Defines learning objectives and roadmaps
- **Tactics Layer**: Designs weekly/daily curricula
- **Execution Layer**: Generates content, quizzes, and monitors progress

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
            +---------------+---------------+
            |               |               |
            v               v               v
    +-------+-------+  +----+----+  +-------+-------+
    | Strategy      |  | Tactics |  | Execution     |
    | Agent         |->| Agent   |->| Agents        |
    | (Roadmap)     |  | (Plan)  |  | (Content/Quiz)|
    +---------------+  +---------+  +---------------+
            |               |               |
            +---------------+---------------+
                            |
                            v
                    +-------+-------+
                    | Progress      |
                    | Agent         |
                    | (Report)      |
                    +---------------+
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
|   |-- model/
|   |   |-- __init__.py
|   |   +-- llm_pipeline_model.py  # Pydantic data models
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- llm_pipeline_prompt.py # Agent prompts
|   +-- service/
|       |-- __init__.py
|       +-- llm_pipeline_service.py  # LangGraph pipeline
|-- outputs/                     # Generated learning plans
|-- .envrc.example               # Environment variable template
|-- pyproject.toml               # Project dependencies
|-- Makefile                     # Development commands
+-- CLAUDE.md                    # This file
```

## Key Components

### Agent Layers

| Layer     | Agent           | Responsibility                              |
|-----------|-----------------|---------------------------------------------|
| Strategy  | strategy_agent  | Analyze goals, create learning roadmap      |
| Tactics   | tactics_agent   | Design weekly/daily curriculum plans        |
| Execution | content_agent   | Generate learning content for tasks         |
| Execution | quiz_agent      | Create assessment quizzes                   |
| Progress  | progress_agent  | Monitor learning progress, create reports   |

### Data Models (llm_pipeline_model.py)

- **LearnerProfile**: Learner's goal, knowledge, time constraints
- **LearningRoadmap**: Strategic learning path with modules
- **WeeklyPlan / DailyTask**: Detailed curriculum structure
- **LearningContent**: Generated educational content
- **Quiz / QuizQuestion**: Assessment materials
- **ProgressReport**: Learning progress metrics

### State Machine (HierarchicalAgentState)

The LangGraph state machine flows through:
1. `strategy` -> `tactics` -> `execution` (loop) -> `progress` -> END

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

### Hierarchical Agent Flow

1. **Strategy Agent**: Analyzes learner profile, determines skill levels, creates module-based roadmap
2. **Tactics Agent**: Breaks roadmap into weekly themes and daily tasks
3. **Execution Loop**: Iterates through tasks generating content and quizzes (max 5 sessions for first week)
4. **Progress Agent**: Evaluates initial progress and provides recommendations

### JSON Response Handling

The service includes robust JSON parsing with:
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

## Output

The system generates a markdown file containing:
- Learner profile summary
- Strategy overview (domain, levels, duration)
- Learning roadmap with milestones
- Module descriptions
- Weekly curriculum details
- Sample learning sessions with quizzes
- Progress report with recommendations

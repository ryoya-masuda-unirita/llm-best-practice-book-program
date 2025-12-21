# Learning AI Agent - Training Plan Generator

## Overview

A learning AI agent that generates personalized 1-week training plans. The system accumulates user feedback and learning history as external memory (JSON files), dynamically injecting learned patterns into prompts for increasingly personalized recommendations.

## Architecture

```
+------------------------------------------------------------------+
|                    Pattern Analyzer Agent                         |
|              (Extracts patterns from user feedback)               |
+---------------------------------+--------------------------------+
                                  |
                                  | Injects learned patterns
                                  v
+------------------------------------------------------------------+
|                Training Plan Generator Agent                      |
|           (Generates plans using learned patterns)                |
+------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------+
|                         User Memory                               |
|       (Stores profile, history, feedback, learned patterns)       |
|                     memory/{user_id}_{timestamp}.json             |
+------------------------------------------------------------------+
```

### Learning Feedback Loop

1. **Inference and Recording**: Agent generates training plan, user feedback is saved to memory
2. **Pattern Extraction**: Accumulated feedback is analyzed to learn user preferences
3. **Adaptive Generation**: Learned patterns are injected into prompts for personalized plans

## Directory Structure

```
chapter_5/section_5/
|-- src/
|   |-- __init__.py
|   |-- config.py                # Configuration (API keys)
|   |-- logger.py                # Logging setup
|   |-- main.py                  # CLI entry point
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py        # OpenAI model definitions
|   |-- model/
|   |   |-- __init__.py
|   |   +-- model.py             # Pydantic data models
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- prompt.py            # Prompt templates
|   +-- service/
|       |-- __init__.py
|       |-- memory_service.py    # Memory persistence operations
|       +-- service.py           # Agent implementation
|-- memory/                      # User memory storage directory
|   +-- {user_id}_{timestamp}.json
|-- example/
|   +-- profile.json             # Sample user profile
|-- outputs/                     # Generated plans (auto-created)
|-- .envrc.example               # Environment variable template
|-- pyproject.toml               # Dependencies
|-- Makefile                     # Build commands
+-- CLAUDE.md                    # This file
```

## Key Components

### Data Models (`src/model/model.py`)

| Model | Purpose |
|-------|---------|
| `UserProfile` | User's learning goal, skill level, available time |
| `TrainingPlan` | 1-week training plan with daily tasks and assessment |
| `DailyPlan` / `DailyTask` | Daily plans and individual tasks |
| `TrainingFeedback` | User feedback on completed training |
| `LearnedPattern` | Patterns extracted from feedback |
| `UserMemory` | Complete user memory (profile, history, patterns) |
| `LearningProgress` | Learning progress statistics |

### Service Functions (`src/service/service.py`)

| Function | Purpose |
|----------|---------|
| `run_training_plan_generation()` | Main workflow - complete plan generation |
| `generate_training_plan()` | Generate training plan with pattern injection |
| `analyze_feedback_patterns()` | Extract patterns from feedback |
| `create_user_profile()` | Create user profile |

### Memory Service (`src/service/memory_service.py`)

| Function | Purpose |
|----------|---------|
| `save_memory()` | Save memory to JSON file |
| `load_memory()` | Load latest memory for user |
| `create_new_memory()` | Create new memory instance |
| `add_feedback_to_memory()` | Add feedback and save |
| `list_user_memories()` | List all users and memory files |

### Prompt Templates (`src/prompt/prompt.py`)

| Template | Purpose |
|----------|---------|
| `TRAINING_PLAN_SYSTEM_PROMPT` | System prompt for plan generation |
| `TRAINING_PLAN_USER_PROMPT_TEMPLATE` | User prompt for plan generation |
| `PATTERN_ANALYZER_SYSTEM_PROMPT` | System prompt for pattern analysis |
| `LEARNED_CONTEXT_TEMPLATE` | Template for injecting learned patterns |

## Usage

### Setup

```bash
# Set environment variables
cp .envrc.example .envrc
# Edit .envrc to set OPENAI_API_KEY

# Install dependencies
uv sync
```

### CLI Commands

#### Generate Plan

```bash
# New user with command-line options
uv run python -m src.main generate -g "Learn Python programming" -h 10 -s beginner

# Use profile file
uv run python -m src.main generate -p example/profile.json

# Existing user (loads from memory)
uv run python -m src.main generate -u user_example
```

#### Submit Feedback

```bash
uv run python -m src.main feedback -u user_example -r good -d just_right
uv run python -m src.main feedback -u user_example -r excellent -d challenging -ft "Great content!"
```

#### List Users

```bash
uv run python -m src.main list
```

#### Show User Details

```bash
uv run python -m src.main show -u user_example --show-plans --show-patterns
```

### CLI Options

#### generate command

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | OpenAI model to use |
| `--output-dir` | `-o` | Output directory |
| `--profile-file` | `-p` | Path to profile JSON file |
| `--user-id` | `-u` | User ID (loads existing memory) |
| `--goal` | `-g` | Learning goal |
| `--hours-per-week` | `-h` | Weekly available hours |
| `--skill-level` | `-s` | Skill level (beginner/intermediate/advanced) |
| `--learning-pace` | `-lp` | Learning pace (slow/moderate/fast) |
| `--skip-analysis` | | Skip pattern analysis |

#### feedback command

| Option | Short | Description |
|--------|-------|-------------|
| `--user-id` | `-u` | User ID (required) |
| `--plan-id` | `-pid` | Plan ID (uses latest if not specified) |
| `--rating` | `-r` | Overall rating (required) |
| `--difficulty` | `-d` | Difficulty rating (required) |
| `--improvement-suggestions` | `-is` | Suggestions (comma-separated) |
| `--free-text` | `-ft` | Free text feedback |

## Memory Structure

### File Naming Convention

```
memory/{user_id}_{timestamp}.json
```

Example: `memory/user_example_20241221_143052.json`

The latest file contains the most up-to-date memory.

### Memory JSON Schema

```json
{
  "user_id": "user_example",
  "created_at": "2024-12-21T14:30:52",
  "updated_at": "2024-12-21T15:45:30",
  "profile": {
    "user_id": "user_example",
    "learning_goal": "Learn Python programming",
    "skill_level": "beginner",
    "available_hours_per_week": 10
  },
  "training_history": [
    {
      "plan": { ... },
      "feedback": { ... }
    }
  ],
  "learned_patterns": [
    {
      "pattern_type": "preference",
      "description": "Prefers video content",
      "confidence_score": 0.8
    }
  ],
  "progress": {
    "total_weeks_completed": 3,
    "total_tasks_completed": 42,
    "average_completion_rate": 0.85
  }
}
```

## Learning Mechanism

### Pattern Extraction

Pattern analysis runs when 2+ feedback entries exist:

1. **preference**: Content type and learning style preferences
2. **difficulty**: Difficulty-related patterns
3. **pace**: Learning pace patterns
4. **content**: Specific content patterns
5. **time**: Time allocation patterns

### Prompt Injection

Patterns with confidence_score >= 0.6 are injected into prompts:

```
## Insights from Past Learning

### User Preferences
- Prefers video content
- Prefers short learning units (under 30 minutes)

### Difficulty Information
- Slightly easier difficulty is appropriate

### Specific Recommendations
- Include more video content
- Set each task under 30 minutes
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `langchain-openai` | OpenAI LLM integration |
| `openai` | OpenAI API client |
| `pydantic` | Data validation and models |
| `click` | CLI framework |
| `python-dotenv` | Environment variable loading |

## Development Commands

```bash
# Install dependencies
uv sync

# Show help
uv run python -m src.main --help

# Generate plan
uv run python -m src.main generate -p example/profile.json

# Run tests
uv run pytest

# Lint code
make lint

# Format code
make fmt

# Run both lint and format
make fix

# Type check
make mypy
```

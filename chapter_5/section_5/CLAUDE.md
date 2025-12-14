# Learning AI Agent - Personalized Learning Platform

## Overview

This project implements a **Learning AI Agent** pattern - a design where AI agents learn from accumulated experiences (user feedback, interaction history) and continuously improve their behavior and output quality. Unlike static prompt-based systems, this platform builds a feedback loop that enables the system to adapt and grow through operation.

The system generates personalized learning plans using a hierarchical multi-agent architecture built with LangGraph. It features a learning feedback loop that analyzes past experiences to extract patterns and inject them into agent prompts for improved output quality.

## Architecture

```
+------------------------------------------------------------------+
|                       Learning Agent                              |
|            (Analyzes past experiences, extracts patterns)         |
+---------------------------------+--------------------------------+
                                  |
                                  | Injects learned patterns
                                  v
+------------------------------------------------------------------+
|  +------------+   +------------+   +------------+   +---------+  |
|  |  Strategy  |-->|  Tactics   |-->| Execution  |-->| Progress|  |
|  |   Agent    |   |   Agent    |   |   Agent    |   |  Agent  |  |
|  | (Roadmap)  |   | (Weekly/   |   | (Content/  |   | (Track) |  |
|  |            |   |  Daily)    |   |  Quiz)     |   |         |  |
|  +------------+   +------------+   +-----+------+   +---------+  |
|                                          |                       |
|                                          | Loop for sessions     |
|                                          v                       |
+------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------+
|                      Experience Store                             |
|    (Accumulates experiences, stores patterns, tracks feedback)    |
+------------------------------------------------------------------+
```

### Agent Flow

1. **Learning Agent**: Analyzes accumulated experiences before plan generation
2. **Strategy Agent**: Creates learning roadmap based on learner profile
3. **Tactics Agent**: Designs weekly/daily curriculum from roadmap
4. **Execution Agent**: Generates learning content and quizzes (loops for multiple sessions)
5. **Progress Agent**: Creates progress report and recommendations

### Directory Structure

```
chapter_4/section_5/
|-- src/
|   |-- __init__.py              # Package init
|   |-- config.py                # Configuration (API keys)
|   |-- logger.py                # Logging setup
|   |-- main.py                  # CLI entry point
|   |-- client/
|   |   |-- __init__.py
|   |   +-- llm_client.py        # OpenAI model definitions
|   |-- model/
|   |   |-- __init__.py
|   |   +-- llm_pipeline_model.py  # Pydantic data models
|   |-- prompt/
|   |   |-- __init__.py
|   |   +-- llm_pipeline_prompt.py # Prompt templates
|   +-- service/
|       |-- __init__.py
|       +-- llm_pipeline_service.py # Agent implementations
|-- example/
|   |-- learner_profile.json     # Sample learner profile
|   +-- experience_store.json    # Sample experience store
|-- outputs/                     # Generated plans (auto-created)
|-- .envrc.example               # Environment variables template
|-- pyproject.toml               # Project dependencies
|-- Makefile                     # Build commands
+-- README.md                    # Documentation
```

## Key Components

### Data Models (`src/model/llm_pipeline_model.py`)

| Model | Purpose |
|-------|---------|
| `LearnerProfile` | Learner information (goal, knowledge, availability) |
| `StrategyOutput` | Learning roadmap with modules and milestones |
| `TacticsOutput` | Weekly/daily curriculum plans |
| `LearningContent` | Generated learning content |
| `Quiz` / `QuizQuestion` | Assessment quizzes |
| `ExperienceRecord` | Single experience (input, output, feedback) |
| `ExperienceStore` | Accumulated experiences and learned patterns |
| `ExperiencePattern` | Pattern extracted from multiple experiences |
| `HierarchicalAgentState` | LangGraph state for agent workflow |

### Service Functions (`src/service/llm_pipeline_service.py`)

| Function | Purpose |
|----------|---------|
| `run_personalized_learning()` | Main entry - runs complete pipeline |
| `learning_agent()` | Analyzes experiences, extracts patterns |
| `run_learning_cycle()` | Runs learning analysis for all agent types |
| `strategy_agent()` | Creates learning roadmap |
| `tactics_agent()` | Designs curriculum |
| `content_agent()` | Generates learning content |
| `quiz_agent()` | Creates assessment quizzes |
| `progress_agent()` | Generates progress reports |
| `record_experience()` | Records new experience to store |
| `get_learned_context_for_agent()` | Gets formatted patterns for prompt injection |

### Prompt Templates (`src/prompt/llm_pipeline_prompt.py`)

Each agent has system and user prompt templates:
- `STRATEGY_AGENT_SYSTEM_PROMPT` - Learning strategy design
- `TACTICS_AGENT_SYSTEM_PROMPT` - Curriculum planning
- `CONTENT_AGENT_SYSTEM_PROMPT` - Content generation
- `QUIZ_AGENT_SYSTEM_PROMPT` - Quiz creation
- `PROGRESS_AGENT_SYSTEM_PROMPT` - Progress monitoring
- `LEARNING_AGENT_SYSTEM_PROMPT` - Experience analysis
- `LEARNED_PATTERNS_INJECTION_TEMPLATE` - Pattern injection format

## Dependencies

| Package | Purpose |
|---------|---------|
| `langchain-openai` | OpenAI LLM integration |
| `langgraph` | State graph for agent workflow |
| `openai` | OpenAI API client |
| `pydantic` | Data validation and models |
| `click` | CLI framework |
| `python-dotenv` | Environment variable loading |

## Usage

### Setup

1. Copy environment template and set API key:
```bash
cp .envrc.example .envrc
# Edit .envrc and set OPENAI_API_KEY
```

2. Install dependencies:
```bash
uv sync
```

### Run

Basic usage with command-line options:
```bash
uv run python -m src.main -g "Learn Python programming in 3 months" -h 10 -d 12
```

Using a profile file:
```bash
uv run python -m src.main -p example/learner_profile.json
```

With experience-based learning:
```bash
uv run python -m src.main -p example/learner_profile.json -e example/experience_store.json
```

Save experiences for future learning:
```bash
uv run python -m src.main -p example/learner_profile.json -se outputs/experience_store.json
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | OpenAI model to use (default: gpt-5-mini) |
| `--output-directory` | `-od` | Output directory (default: outputs) |
| `--profile-file` | `-p` | Path to learner profile JSON |
| `--goal` | `-g` | Learning goal text |
| `--hours-per-week` | `-h` | Available study hours per week |
| `--duration-weeks` | `-d` | Target duration in weeks |
| `--current-knowledge` | `-k` | Current knowledge (comma-separated) |
| `--experience-store` | `-e` | Path to load experience store |
| `--save-experience-store` | `-se` | Path to save updated experience store |
| `--skip-learning` | | Skip learning cycle |

## Development Commands

```bash
# Install dependencies
uv sync

# Run the platform
uv run python -m src.main --help

# Run with profile
uv run python -m src.main -p example/learner_profile.json

# Run tests
uv run pytest
```

## Implementation Notes

### Learning Feedback Loop

The learning feedback loop works as follows:

1. **Experience Recording**: Each agent's input/output is recorded with optional user feedback
2. **Pattern Extraction**: Learning agent analyzes experiences (min 3 required)
3. **Pattern Injection**: Extracted patterns are injected into agent prompts
4. **Continuous Improvement**: System improves as more experiences accumulate

### Experience Store Structure

```json
{
  "store_id": "store_001",
  "experiences": [...],
  "learned_patterns": [...],
  "total_positive_feedback": 5,
  "total_negative_feedback": 1
}
```

### Pattern Injection

Learned patterns are injected into agent system prompts:
- Positive patterns: Things that worked well
- Negative patterns: Things to avoid
- Improvement notes: Specific recommendations

### Safety Mechanisms

- Minimum 3 experiences required before learning cycle runs
- Confidence scores (0-1) for each pattern
- Fallback to base prompts when no patterns available
- Retry logic with exponential backoff for API calls

### State Management

LangGraph `StateGraph` manages workflow:
- `HierarchicalAgentState` TypedDict holds all state
- Conditional edges control execution flow
- Maximum 5 sessions per execution to limit API calls

# Weather-Based Outfit Recommender with MCP

## Overview

A CLI application that provides outfit recommendations based on real-time weather data. Uses the Model Context Protocol (MCP) to connect LLMs (OpenAI, Google Gemini, Anthropic Claude) to the US National Weather Service API.

**Key Features**:
- Multi-provider LLM support (OpenAI, Gemini, Anthropic)
- Real-time weather data via MCP tool integration
- Structured JSON output with Pydantic validation
- Two MCP patterns: Manual (OpenAI/Anthropic) vs Native (Gemini)

## Architecture

```
User Input (coordinates)
        |
        v
+-------------------+
|   CLI (main.py)   |
+-------------------+
        |
        v
+------------------------+
| Service (request_llm)  |
+------------------------+
        |
        +---> MCP Client Session
        |           |
        |           v
        |    +------------------+
        |    | MCP Weather Tool |
        |    | (weather_server) |
        |    +------------------+
        |           |
        |           v
        |    NWS Weather API
        |           |
        v           v
+------------------------+
|   LLM Provider API     |
| (OpenAI/Gemini/Claude) |
+------------------------+
        |
        v
+------------------------+
| Structured Output      |
| (OutfitResponse)       |
+------------------------+
        |
        v
JSON File + Console Output
```

### Directory Structure

```
chapter_3/section_10/
|-- src/
|   |-- main.py              # CLI entry point (Click-based)
|   |-- config.py            # Environment config (API keys)
|   |-- logger.py            # Logging configuration
|   |-- client/
|   |   |-- llm_client.py    # LLM provider clients and model enums
|   |-- model/
|   |   |-- model.py         # Pydantic models (OutfitResponse, etc.)
|   |-- prompt/
|   |   |-- prompt.py        # Prompt templates for each provider
|   |-- service/
|       |-- request_llm.py   # Business logic for LLM requests
|-- tool_server/
|   |-- weather_server.py    # MCP server with weather tools
|-- outputs/                 # Generated outfit JSON files
|-- .envrc.example           # Environment variable template
|-- pyproject.toml           # Project dependencies
|-- Makefile                 # Development commands
```

## Key Components

### LLM Providers (`src/client/llm_client.py`)

| Provider   | Models                                          | MCP Pattern    |
|------------|------------------------------------------------|----------------|
| OpenAI     | gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano | Manual         |
| Gemini     | gemini-2.5-pro, gemini-2.5-flash               | Native         |
| Anthropic  | claude-sonnet-4-6, claude-opus-4-6             | Manual         |

### Data Models (`src/model/model.py`)

- `WeatherCondition`: Temperature, wind, forecast summary
- `ClothingRecommendation`: Clothing type, item, reason
- `OutfitResponse`: Location, weather, 3+ recommendations, advice

### MCP Server (`tool_server/weather_server.py`)

Tools exposed via FastMCP:
- `get_forecast(latitude, longitude)`: Fetch weather forecast from NWS API
- `get_alerts(state)`: Get weather alerts for US state (available but unused)

## Dependencies

| Package       | Purpose                                |
|---------------|----------------------------------------|
| openai        | OpenAI API client (v2.4.0+)            |
| google-genai  | Google Gemini API client (v1.45.0+)    |
| anthropic     | Anthropic Claude API client            |
| mcp[cli]      | Model Context Protocol implementation  |
| pydantic      | Data validation and structured output  |
| click         | CLI framework                          |
| httpx         | Async HTTP client for NWS API          |

## Usage

### Setup

```bash
# Install dependencies
uv sync

# Configure environment variables
cp .envrc.example .envrc
# Edit .envrc with your API keys:
# - OPENAI_API_KEY
# - GEMINI_API_KEY
# - ANTHROPIC_API_KEY

# Load environment
direnv allow
```

### Run

```bash
# Basic usage with Gemini
uv run python -m src.main -lp GEMINI -m gemini-2.5-flash -lat 39.7456 -lon -97.0892

# With OpenAI
uv run python -m src.main -lp OPENAI -m gpt-5.4-mini -lat 39.7456 -lon -97.0892

# With Anthropic Claude
uv run python -m src.main -lp ANTHROPIC -m claude-sonnet-4-6 -lat 39.7456 -lon -97.0892

# Custom output directory
uv run python -m src.main -lp GEMINI -m gemini-2.5-flash -lat 39.7456 -lon -97.0892 -od ./my_outputs
```

### CLI Options

| Option              | Short | Required | Description                        |
|---------------------|-------|----------|------------------------------------|
| --llm-provider      | -lp   | Yes      | OPENAI, GEMINI, or ANTHROPIC       |
| --model             | -m    | Yes      | Model name (provider-specific)     |
| --latitude          | -lat  | Yes      | Latitude (US coordinates only)     |
| --longitude         | -lon  | Yes      | Longitude (US coordinates only)    |
| --output-directory  | -od   | No       | Output dir (default: outputs)      |

## Development Commands

```bash
# Lint code
make lint

# Format code
make fmt

# Lint + format
make fix

# Type check
make mypy
```

## Implementation Notes

### MCP Integration Patterns

**Manual Pattern (OpenAI/Anthropic)**:
1. Initialize MCP session
2. Explicitly call `get_forecast` tool
3. Extract weather data from response
4. Pass weather data to LLM prompt
5. Use structured output parsing

**Native Pattern (Gemini)**:
1. Initialize MCP session
2. Pass session as `tools=[session]` to LLM
3. LLM autonomously decides to call tools
4. Parse JSON from text response (no structured output with tools)

### Geographic Constraints

- **US coordinates only**: NWS API serves only US territories
- Non-US coordinates return clear error with example coordinates
- Example: Kansas, USA - lat=39.7456, lon=-97.0892

### Structured Output

- All providers return `OutfitResponse` Pydantic model
- Minimum 3 outfit recommendations enforced
- Frozen models prevent accidental mutation
- JSON files saved with UUID-based naming

### Error Handling

- Provider/model validation at CLI level
- Geographic constraint validation with actionable messages
- JSON parsing errors with detailed logging
- HTTP timeout handling (30s for NWS API)

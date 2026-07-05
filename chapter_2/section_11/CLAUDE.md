# Chapter 2 Section 11: Connecting LLMs to External Tools with MCP

## What This Section Demonstrates

This section connects LLMs to a real external data source through the **Model Context Protocol (MCP)**: a FastMCP server exposes US National Weather Service (NWS) forecast tools, and the app asks an LLM (OpenAI / Gemini / Anthropic) to recommend an outfit based on live weather for given coordinates.

It deliberately demonstrates **two integration patterns** side by side:
- **Manual pattern (OpenAI / Anthropic)** — the app itself calls the MCP tool (`session.call_tool("get_forecast", ...)`), then feeds the result into a normal structured-output request. Deterministic tool usage, full control.
- **Native pattern (Gemini)** — the MCP `ClientSession` is passed directly as a tool (`tools=[session]`) and the model decides when to call it. Less code, but you give up structured output (tool use and `response_schema` can't be combined), so the response must be parsed from text.

Apply MCP when tools should be reusable across applications and agents — the same weather server works unchanged with Claude Desktop, other MCP hosts, or any of the three providers here.

## Practice Rules

1. **Implement tools as an MCP server with FastMCP**: decorate plain async functions with `@mcp.tool()`; the docstring and type hints become the tool schema.
2. **Launch the tool server over stdio from the client** (`StdioServerParameters(command="uv", args=[...])`) and always `await session.initialize()` before calling tools.
3. **Choose the integration pattern consciously.** Manual (fetch tool result → include in prompt → structured output) when you know which tool is needed and want typed output; native (`tools=[session]`) when the model should decide, accepting text parsing.
4. **Return errors from tools as readable strings, never exceptions** — MCP tool results flow into prompts; "Unable to fetch forecast data" is actionable to the model and detectable by the app.
5. **Detect external-service constraints and convert them to user-actionable errors.** NWS covers US coordinates only; the service layer detects failure markers and raises a message that names the constraint and gives a working example.
6. **When forced to parse text (native pattern), extract JSON defensively**: try ` ```json ` fences, then bare fences, then brace matching — and validate with the Pydantic model at the end regardless.

## Architecture

```
CLI (src/main.py)  --lat/--lon, provider, model
        │
        ▼
Service (src/service/request_llm.py)
  ├─ OpenAI/Anthropic (manual):
  │    stdio_client → ClientSession.call_tool("get_forecast")
  │    → weather text → prompt → structured output → OutfitResponse
  └─ Gemini (native):
       GenerateContentConfig(tools=[session])  ← model decides to call MCP tool
       → text response → defensive JSON extraction → OutfitResponse
        │
        ▼ (stdio, spawned subprocess)
tool_server/weather_server.py  (FastMCP "weather")
  ├─ get_forecast(latitude, longitude)   → NWS /points + /forecast
  └─ get_alerts(state)                   → NWS /alerts/active/area/{state}  (available, unused by the app)
```

### Directory Structure

```
chapter_2/section_11/
├── tool_server/weather_server.py   # FastMCP server: get_forecast / get_alerts
├── src/
│   ├── main.py                     # CLI: provider/model/coordinates
│   ├── service/request_llm.py      # manual + native MCP integration per provider
│   ├── prompt/prompt.py            # outfit prompts (weather embedded or tool-driven)
│   ├── model/model.py              # WeatherCondition / ClothingRecommendation / OutfitResponse
│   ├── client/llm_client.py        # 3-provider clients + model enums
│   └── config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Tool definition is just a decorated function (`tool_server/weather_server.py`)

```python
mcp = FastMCP("weather")

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    points_data = await make_nws_request(f"{NWS_API_BASE}/points/{latitude},{longitude}")
    if not points_data:
        return "Unable to fetch forecast data for this location."   # error as string
    ...
```

### 2. Manual pattern — app-controlled tool call (`src/service/request_llm.py`)

```python
MCP_SERVER_PARAMS = StdioServerParameters(command="uv", args=["run", "python", "tool_server/weather_server.py"])

async def _fetch_weather_data_via_mcp(latitude, longitude, provider_name) -> str:
    async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_forecast",
                                             arguments={"latitude": latitude, "longitude": longitude})
            weather_data = result.content[0].text
    if "Unable to fetch" in weather_data:
        raise ValueError(_make_us_only_error_message(latitude, longitude))
    return weather_data
```

The weather text then goes into a normal structured-output request → typed `OutfitResponse`.

### 3. Native pattern — session as a tool (Gemini, `src/service/request_llm.py`)

```python
result = await google_genai_client.aio.models.generate_content(
    model=model,
    contents=user_prompt,
    config=GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[session],            # the MCP session itself; model decides to call
    ),
)
# tool use and response_schema cannot be combined → parse result.text
```

### 4. Defensive JSON extraction when structured output is unavailable

```python
if "```json" in response_text:      # fenced json block
    ...
elif "```" in response_text:        # generic fence
    ...
elif "{" in response_text:          # brace matching
    json_text = response_text[response_text.find("{"):response_text.rfind("}") + 1]
outfit_data = json.loads(json_text)
return OutfitResponse(**outfit_data)   # Pydantic validation is still the last gate
```

### 5. Constraint-aware error message

```python
def _make_us_only_error_message(latitude: float, longitude: float) -> str:
    return ("天気予報データの取得に失敗しました。\n"
            "このツールは米国国立気象局(NWS)のAPIを使用しているため、米国内の座標のみ対応しています。\n"
            f"指定された座標: 緯度={latitude}, 経度={longitude}\n"
            "米国内の座標を使用してください（例: Kansas, USA - lat=39.7456, lon=-97.0892）")
```

## Data Models

| Model | Purpose |
|-------|---------|
| `WeatherCondition` | Temperature, wind, forecast summary |
| `ClothingRecommendation` | Clothing type, item, reason |
| `OutfitResponse` | Location, weather, recommendations, advice |
| `LLMProvider` / model enums | Provider & model selection (OpenAI: manual / Gemini: native / Anthropic: manual) |

## Setup & Run

> **Constraint: the NWS API covers US locations only.** Always use US coordinates; non-US coordinates fail with a guided error message.

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example (Kansas, USA)
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 39.7456 -lon -97.0892

# Manual-pattern providers
uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6 -lat 39.7456 -lon -97.0892
```

The MCP server is spawned automatically as a stdio subprocess — no separate server startup needed.

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--llm-provider` | `-lp` | Yes | `OPENAI` / `GEMINI` / `ANTHROPIC` |
| `--model` | `-m` | Yes | Model enum name for the provider |
| `--latitude` | `-lat` | Yes | Latitude (US only) |
| `--longitude` | `-lon` | Yes | Longitude (US only) |
| `--output-directory` | `-od` | No | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Manual vs native trade-off**: manual costs one extra orchestration step but keeps structured output and makes tool usage deterministic (always exactly one forecast call). Native lets the model chain tools as it sees fit but forfeits `response_schema` on Gemini — hence the JSON-extraction fallback chain. Prefer manual when the tool sequence is known.
- **The stdio lifecycle** (`stdio_client` context manager) starts and stops the tool-server subprocess per request here; long-running apps should hold the session open across requests.
- **Tool docstrings are the API contract for the model** — `get_forecast`'s docstring/args are all the model ever sees; write them like user-facing docs.
- **Validation still ends at Pydantic** even in the native pattern: text extraction can produce structurally valid but semantically empty JSON (e.g. null temperature), which is caught and converted into the US-only guidance error.

## How to Apply This Practice to Your Own Project

1. Wrap your external API as a FastMCP server: one `@mcp.tool()` function per capability, errors returned as descriptive strings, docstrings written for the model.
2. Connect via `stdio_client(StdioServerParameters(...))` + `ClientSession`; initialize before first call.
3. Pick the pattern per use case: known tool sequence → manual call + structured output; model-driven tool choice → native integration + defensive text parsing.
4. Encode external-service constraints (region limits, rate limits, auth scopes) as detectable failure markers and user-actionable error messages.
5. Keep the tool server free of LLM/provider code — that's what makes it reusable across MCP hosts (Claude Desktop, agents, other apps).

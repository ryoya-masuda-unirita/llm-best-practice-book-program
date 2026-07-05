# Chapter 2 Section 1: Structured Output — Type-Safe LLM Responses with Pydantic

## What This Section Demonstrates

This section is the reference implementation for **structured output**: making an LLM return a machine-parseable object that is validated against a schema, instead of free-form text. A single Pydantic model (`CharacterResponse`) serves as the one source of truth for the output shape, and each provider's native structured-output API (OpenAI, Google Gemini, Anthropic Claude) parses the response directly into that model.

Apply this practice whenever LLM output is consumed by code (saved, displayed in a UI, passed to another function) rather than read by a human. It eliminates ad-hoc JSON parsing, regex extraction, and "the model added prose around the JSON" failures.

## Practice Rules

1. **Define the output schema as a Pydantic model first**, before writing any prompt. Every field gets a type, a `description`, and constraints (`ge`/`le`, enums) — the descriptions are consumed by the LLM, not just humans.
2. **Use each provider's native structured-output API** to bind the model class to the request — never ask for "JSON" in prose and parse it yourself:
   - OpenAI: `responses.parse(..., text_format=Model)` → `result.output_parsed`
   - Gemini: `generate_content(..., config=GenerateContentConfig(response_mime_type="application/json", response_schema=Model))` → `result.parsed`
   - Anthropic: `beta.messages.parse(..., betas=["structured-outputs-2025-11-13"], output_format=Model)` → `result.parsed_output`
3. **Still describe the schema in the prompt.** The prompt embeds a field-by-field description (`CharacterResponse.detailed_model()`) with explicit constraints — schema enforcement and prompt instructions are complementary, not alternatives.
4. **Make response models immutable** (`frozen=True`) and tolerant of extra keys (`extra="ignore"`) so a provider adding fields never breaks parsing.
5. **Validate the provider/model pairing at the boundary** (CLI validates that the chosen model belongs to the chosen provider) and keep model IDs in `StrEnum`s, never as loose strings.
6. **Return the parsed Pydantic instance from the service layer**, so every downstream consumer works with typed data.

## Architecture

```
CLI (src/main.py)
  │  --llm-provider / --model validation
  ▼
Service layer (src/service/request_llm.py)
  │  request_openai / request_gemini / request_anthropic
  │  provider-specific prompt from src/prompt/prompt.py
  ▼
Provider SDK structured-output call
  │  parses straight into CharacterResponse (src/model/model.py)
  ▼
CharacterResponse.save_as_json() → outputs/<provider>_<uuid>.json
```

### Directory Structure

```
chapter_2/section_1/
├── src/
│   ├── config.py              # API keys from environment (pydantic settings)
│   ├── logger.py              # Logging setup
│   ├── main.py                # CLI entry point (Click, async)
│   ├── client/
│   │   └── llm_client.py      # Provider/model enums + SDK client instances
│   ├── model/
│   │   └── model.py           # CharacterResponse Pydantic schema
│   ├── prompt/
│   │   └── prompt.py          # Provider-specific prompt builders
│   └── service/
│       └── request_llm.py     # One request function per provider
├── outputs/                   # Generated JSON files
├── Makefile
├── pyproject.toml
├── .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Schema as the single source of truth (`src/model/model.py`)

```python
class CharacterResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True, frozen=True, extra="ignore", ...)

    first_name: str = Field(..., description="The first name of the character.")
    last_name: str = Field(..., description="The last name of the character.")
    gender: Gender = Field(Gender.MALE, description="The gender of the character.")
    age: int = Field(..., description="The age of the character.", ge=0, le=100)
    personalities: list[CharacterPersonality] = Field(
        ..., description="The three most important personality traits of the character."
    )
```

Field descriptions and constraints double as instructions to the LLM; `frozen=True` prevents accidental mutation after parsing.

### 2. One request function per provider, same return type (`src/service/request_llm.py`)

```python
async def request_openai(model: OpenAIModel) -> CharacterResponse:
    result = await openai_client.responses.parse(
        model=model, input=prompt, text_format=CharacterResponse,
    )
    return result.output_parsed

async def request_anthropic(model: AnthropicModel) -> CharacterResponse:
    result = await anthropic_client.beta.messages.parse(
        model=model, max_tokens=1024,
        betas=["structured-outputs-2025-11-13"],
        messages=prompt, output_format=CharacterResponse,
    )
    return result.parsed_output
```

Provider APIs differ, but every function returns the same validated `CharacterResponse` — callers never see provider-specific response objects.

### 3. Schema echoed into the prompt (`src/prompt/prompt.py`)

```python
def make_openai_prompt() -> list:
    params = CharacterResponse.detailed_model()   # field-by-field description dict
    param_dump = json.dumps(params, indent=2, ensure_ascii=False)
    return [{"role": "system", "content": f"""...以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：
{param_dump}
..."""}, ...]
```

`detailed_model()` renders the Pydantic schema into a human/LLM-readable structure so the prompt and the enforced schema can never drift apart.

### 4. Model IDs as enums with provider validation (`src/client/llm_client.py`, `src/main.py`)

```python
class AnthropicModel(StrEnum):
    CLAUDE_SONNET_5 = "claude-sonnet-5"
    CLAUDE_OPUS_4_8 = "claude-opus-4-8"
    CLAUDE_OPUS_4_7 = "claude-opus-4-7"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5"
```

```python
if llm_provider == LLMProvider.ANTHROPIC and model not in AnthropicModel.list_str():
    raise ValueError(f"Invalid model '{model}' for provider '{llm_provider.value}'.")
```

## Data Models

| Model | Purpose |
|-------|---------|
| `CharacterResponse` | The structured output schema; also renders itself into prompt text and saves itself as JSON |
| `CharacterPersonality` | Nested model — one personality trait (short label + description) |
| `Gender` | `StrEnum` constraining the gender field to `female`/`male` |
| `LLMProvider` | `StrEnum`: `openai` / `gemini` / `anthropic` |
| `OpenAIModel`, `GeminiModel`, `AnthropicModel` | `StrEnum`s of valid model IDs per provider |

## Setup & Run

```bash
# 1. API keys
cp .envrc.example .envrc   # set OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY

# 2. Dependencies
uv sync

# 3. Run (canonical example)
uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH

# Other providers
uv run python -m src.main --llm-provider OPENAI --model GPT_5_4_MINI
uv run python -m src.main --llm-provider ANTHROPIC --model CLAUDE_SONNET_4_6
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--llm-provider` | `-lp` | Yes | `gemini` | Provider: `OPENAI` / `GEMINI` / `ANTHROPIC` |
| `--model` | `-m` | Yes | — | Model enum name (must belong to the chosen provider) |
| `--output-directory` | `-od` | No | `outputs` | Directory for generated JSON files |

Available model choices (enum names from `src/client/llm_client.py`; the enum value is the API model ID):
- **OpenAI**: `GPT_5_5`, `GPT_5_4`, `GPT_5_4_MINI`, `GPT_5_4_NANO`, `GPT_5_2`, `GPT_5_1`, `GPT_5`, `GPT_5_MINI`, `GPT_5_NANO`
- **Gemini**: `GEMINI_2_5_PRO`, `GEMINI_2_5_FLASH`, `GEMINI_2_5_FLASH_LITE`, `GEMINI_3_5_FLASH`, `GEMINI_3_1_FLASH_LITE`
- **Anthropic**: `CLAUDE_SONNET_5`, `CLAUDE_OPUS_4_8`, `CLAUDE_OPUS_4_7`, `CLAUDE_SONNET_4_6`, `CLAUDE_HAIKU_4_5`

## Development Commands

```bash
make lint    # ruff check --fix
make fmt     # ruff format
make fix     # lint + fmt
make mypy    # type checking
```

## Implementation Notes

- **Async throughout**: all provider calls are `async`; the CLI bridges with a small `async_cmd` decorator around `asyncio.run`. The Gemini client must be closed explicitly (`google_genai_client.aio.aclose()`).
- **Provider differences that matter**:
  - OpenAI's Responses API takes a message list and `text_format`.
  - Gemini takes `system_instruction` separately from `contents` and needs `response_mime_type="application/json"` alongside `response_schema`.
  - Anthropic's structured outputs are a beta (`structured-outputs-2025-11-13`) accessed via `client.beta.messages.parse`, and the prompt is a single user message (no system role used here).
- **Prompts are in Japanese** — structured output works independently of prompt language; the schema enforcement is language-neutral.
- **Constraint duplication is intentional**: `age: 0-100` lives in both the Pydantic `Field(ge=0, le=100)` (validation) and the prompt text (steering). Validation catches what steering misses.

## How to Apply This Practice to Your Own Project

1. Write the Pydantic model for exactly what your code needs downstream — nothing more. Add `description=` to every field.
2. Set `frozen=True` and `extra="ignore"` in `model_config`.
3. Pick the provider's parse-style API and bind the model class to the call (see Practice Rule 2 for the three bindings).
4. Generate the prompt's schema description from the model itself (like `detailed_model()`) so prompt and schema stay in sync.
5. Keep provider/model identifiers in `StrEnum`s and validate the pairing at your entry point.
6. Return only the parsed, validated instance from the service function; log the raw response for debugging.

# Chapter 2 Section 2: Auto-Structured Output — Generating Output Schemas from Natural-Language Prompts

## What This Section Demonstrates

Chapter 2 Section 1 assumes you can write the output schema by hand. This section covers the case where **the schema itself is unknown at design time**: the user describes what they want in natural language, and the system derives a JSON Schema from that description with one LLM call, dynamically builds a Pydantic model from it, and then uses that model for a normal structured-output request.

This two-step pattern (schema extraction → structured generation) turns free-form requirements into type-safe pipelines. Apply it when building tools whose users define the output shape at runtime — form builders, data-extraction services, "output it in this format" chat features — or when you want to bootstrap schemas from example documents instead of writing them manually.

## Practice Rules

1. **Split the work into two LLM calls with distinct jobs**: call 1 extracts a JSON Schema from the natural-language prompt(s); call 2 generates the actual data bound to the schema-derived model. Never ask one call to invent both shape and content.
2. **Validate the extracted schema before building anything from it** (`SchemaValidator.validate_schema`). Reject unsupported types/constructs early with a clear error.
3. **Retry schema extraction with the validation error in the retry prompt** (up to `max_retries=3`), so the LLM can fix its own schema instead of you silently accepting a broken one.
4. **Build the runtime model with `pydantic.create_model`** from the validated schema; carry over `required`/`default`/`description` so field semantics survive the conversion.
5. **Whitelist the type system**: enumerate supported JSON Schema types (`SupportedType`) and string formats (`StringFormat`) as `StrEnum`s with explicit Python-type mappings. Anything outside the whitelist fails fast.
6. **Escalate to a high-reasoning model only when the prompt is ambiguous** (`use_high_reasoning=True`); use the cheaper default model otherwise. Model choice is configurable via env vars (`BASIC_PREDICTION_MODEL`, `HIGH_PREDICTION_MODEL`).
7. **Type errors as a hierarchy** (`ExtractionError` → `SchemaValidationError` / `ModelBuildError`) so callers can distinguish "the LLM produced a bad schema" from "the schema can't be represented".

## Architecture

```
Natural-language prompt(s)
        │
        ▼
┌──────────────────────────────────────────────┐
│ Step 1: StructureExtractor.extract_structure │
│  SchemaGenerator ──LLM──> JSON Schema        │
│  SchemaValidator.validate_schema (retry x3)  │
│  ModelBuilder.build_model                    │
│      └─> dynamic pydantic.BaseModel subclass │
└──────────────────┬───────────────────────────┘
                   ▼
┌──────────────────────────────────────────────┐
│ Step 2: normal structured output             │
│  client.responses.parse(text_format=T_Model) │
│      └─> validated instance ──> JSON file    │
└──────────────────────────────────────────────┘
```

### Directory Structure

```
chapter_2/section_2/
├── src/
│   ├── config.py / logger.py / main.py       # config, logging, CLI (Click)
│   ├── auto_structured_output/               # the reusable library
│   │   ├── extractor.py                      # StructureExtractor facade + error types
│   │   ├── schema_generator.py               # LLM call + retry loop for schema extraction
│   │   ├── validators.py                     # SchemaValidator (whitelist enforcement)
│   │   ├── model_builder.py                  # JSON Schema -> pydantic.create_model
│   │   ├── model.py                          # SupportedType / StringFormat enums
│   │   └── prompts.py                        # schema-extraction / retry prompt builders
│   ├── client/llm_client.py                  # OpenAIModel enum + client
│   └── examples/
│       ├── runner.py                         # end-to-end 2-step runner
│       ├── basic_usage.py                    # 5 basic examples
│       ├── advanced_examples.py              # 6 examples (nesting, anyOf, constraints)
│       └── high_reasoning_examples.py        # 6 examples using high-reasoning extraction
├── outputs/
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The two-step flow end to end (`src/examples/runner.py`)

```python
extractor = StructureExtractor(llm_client=llm_client, model=model)
T_Model = extractor.extract_structure([prompt])          # Step 1: prompt -> Pydantic class

response = llm_client.responses.parse(                    # Step 2: same prompt, typed output
    model=model,
    input=[{"role": "user", "content": prompt}],
    text_format=T_Model,
)
data = response.output_parsed                             # instance of the dynamic model
```

The same natural-language prompt drives both steps: first to derive the shape, then to fill it.

### 2. Facade with typed failure modes (`src/auto_structured_output/extractor.py`)

```python
class StructureExtractor:
    def extract_structure(self, prompts: list[str], use_high_reasoning: bool = False) -> type[BaseModel]:
        try:
            schema_json = self._extract_schema_from_prompt(prompts, use_high_reasoning)
            validated_schema = self._validate_schema(schema_json)
            return self._build_model(validated_schema)
        except SchemaValidationError:
            raise
        except ModelBuildError:
            raise
        except Exception as e:
            raise ExtractionError(f"Error occurred during structure extraction: {e}") from e
```

Accepts *multiple* prompts to produce one unified schema covering all of them.

### 3. Retry with the validation error fed back (`src/auto_structured_output/schema_generator.py`)

```python
for attempt in range(self.max_retries):
    try:
        schema = self._call_api(client, model, messages)
        SchemaValidator.validate_schema(schema)
        return schema
    except ValueError as e:
        ...  # build retry messages containing the failed schema + error text
```

The retry prompt (`get_schema_retry_messages`) includes what was wrong, so retries converge instead of re-rolling blindly.

### 4. Dynamic model construction (`src/auto_structured_output/model_builder.py`)

```python
for field_name, field_info in properties.items():
    field_type = self._get_field_type(field_info)          # maps via SupportedType/StringFormat
    if field_name in required_fields:
        fields[field_name] = (field_type, Field(..., description=description))
    else:
        fields[field_name] = (Optional[field_type], Field(default_value, description=description))

model_class: type[BaseModel] = create_model(name, **fields)
```

Handles nested objects, arrays of objects, `anyOf` unions, enums (`Literal`), and string formats (`date-time` → `datetime`, etc.).

## Data Models

| Model | Purpose |
|-------|---------|
| `SupportedType` | Whitelisted JSON Schema types + mapping to Python types |
| `StringFormat` | Whitelisted `format` values (`date-time`, `email`, `uuid`, …) + Python-type mapping |
| `ExtractionError` / `SchemaValidationError` / `ModelBuildError` | Error hierarchy for the extraction pipeline |
| Dynamic models | Created at runtime by `ModelBuilder` via `pydantic.create_model` — never hand-written |
| `OpenAIModel` | `StrEnum` of usable OpenAI model IDs |

## Setup & Run

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY (optionally BASIC_PREDICTION_MODEL / HIGH_PREDICTION_MODEL)
uv sync

# Canonical example
uv run python -m src.main -m GPT_5_4 -e example_1_simple_user_model

# Ambiguous-prompt examples that escalate to high reasoning
uv run python -m src.main -m GPT_5_4 -e example_6_high_reasoning
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--model` | `-m` | Yes | — | OpenAI model enum name (e.g. `GPT_5_4`) |
| `--example` | `-e` | No | — | Example to run (17 available: 5 basic / 6 advanced / 6 high-reasoning) |
| `--output-directory` | `-od` | No | `outputs` | Directory for extracted JSON files |

## Development Commands

```bash
make lint    # ruff check --fix
make fmt     # ruff format
make fix     # lint + fmt
make mypy    # type checking
```

## Implementation Notes

- **This section is OpenAI-only** — the pattern generalizes, but the schema-extraction prompt and `responses.parse` binding are written against the OpenAI Responses API.
- **Schema unification across prompts**: passing several prompts to `extract_structure` yields one schema that covers all of them — useful for deriving a schema from multiple example documents.
- **Cost profile**: every runtime schema derivation is an extra LLM call. Cache the built model class per prompt (or persist the JSON Schema) when the same shape is requested repeatedly.
- **The whitelist is the safety boundary.** `create_model` executes with whatever the schema says; restricting types/formats to `SupportedType`/`StringFormat` prevents the LLM from smuggling unsupported constructs into your type system.
- **High-reasoning mode** changes only the extraction model, not the generation model — shape inference is the hard part; filling a known shape is cheap.

## How to Apply This Practice to Your Own Project

1. Copy the `auto_structured_output/` package shape: facade (`extractor`), LLM step (`schema_generator`), validation (`validators`), model construction (`model_builder`), type whitelist (`model`), prompts (`prompts`).
2. Write the schema-extraction prompt to output *JSON Schema only*, and keep a retry variant that embeds the previous schema + validation error.
3. Decide your supported-type whitelist first; every type you allow must have an explicit Python mapping.
4. Wire step 2 to your provider's schema-bound API (`responses.parse` / Gemini `response_schema` / Anthropic `output_format`).
5. Add caching keyed on the prompt (or schema hash) before shipping — don't pay the extraction call per request.
6. Surface `SchemaValidationError` to users as "couldn't derive a valid format from your description" — it's a user-input problem, not a system fault.

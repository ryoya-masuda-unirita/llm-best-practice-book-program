# Chapter 2 Section 8: Structured Template Prompting with Jinja2 and YAML

## What This Section Demonstrates

Hardcoded prompt strings scatter across a codebase, drift out of sync, and can't be reviewed or reused. This section implements **prompt-as-configuration**: prompts live in version-controlled YAML files with Jinja2 placeholders (`{{ gender }}`, `{% if additional_instructions %}` …), and a small `TemplateEngine` loads, validates, and renders them into LLM message lists at runtime. Variable sets live in their own YAML files, so the same template runs with different data.

Apply this practice as soon as you have more than one prompt, more than one prompt consumer, or non-engineers editing prompt text. It separates prompt content (reviewable text) from application logic (code), and makes missing-variable errors fail fast instead of producing silently broken prompts.

## Practice Rules

1. **Store each prompt as a YAML file with `system_prompt` / `user_prompt` keys**; use Jinja2 syntax for variables and conditionals inside the values.
2. **Validate variables before rendering.** Extract required variables from the template AST (`jinja2.meta.find_undeclared_variables`) and raise `TemplateValidationError` listing what's missing — never render with silent gaps.
3. **Render to the provider message format in one place** (`render_prompt_messages` → `[{"role": "system", ...}, {"role": "user", ...}]`) so call sites never do string assembly.
4. **Keep variable sets in separate YAML files** (`variables/*.yaml`) — one template × many variable files covers personas, campaigns, product types.
5. **Inject the output schema into the template as a variable too** (`{{ response_schema | indent(2) }}`), generated from the Pydantic model, so prompt text and enforced schema stay in sync.
6. **Configure Jinja2 for prompt-friendly whitespace**: `trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True` — whitespace bugs in prompts are real bugs.
7. **Unit-test the template layer without any LLM** (`tests/test_template_engine.py`): assert rendering, validation failures, and message structure.

## Architecture

```
templates/*.yaml      variables/*.yaml
 (Jinja2 in YAML)      (data per use case)
        └──────┬──────────┘
               ▼
TemplateEngine (src/service/template_engine.py)
  get_template_variables()  ← jinja2.meta AST inspection
  validate_variables()      ← fail fast on missing vars
  render_template()         ← Jinja2 render → yaml.safe_load
  render_prompt_messages()  ← → [{"role": "system"}, {"role": "user"}]
               ▼
request_llm (src/service/request_llm.py) → OpenAI structured output → CharacterResponse
```

### Directory Structure

```
chapter_2/section_8/
├── templates/
│   ├── character_generation.yaml   # system/user prompt with {{ gender }}, {{ age }}, schema injection
│   ├── email_formal.yaml / email_casual.yaml
│   └── product_description.yaml
├── variables/
│   ├── character_artist.yaml / character_detective.yaml
│   ├── email_campaign_summer.yaml / email_campaign_winter.yaml
│   └── product_electronics.yaml / product_apparel.yaml
├── src/
│   ├── main.py                     # CLI: pick template + variables + model
│   ├── service/
│   │   ├── template_engine.py      # TemplateEngine + TemplateValidationError
│   │   └── request_llm.py          # path resolution, variable loading, LLM execution
│   ├── model/model.py              # CharacterRequest / CharacterResponse
│   ├── client/llm_client.py        # OpenAIModel enum + client
│   └── config.py / logger.py
├── tests/                          # template engine + prompt tests (no LLM needed)
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Template file: prompt + logic + schema slot (`templates/character_generation.yaml`)

```yaml
system_prompt: >-
  あなたは創造的なキャラクタージェネレーターです。
  ...以下の構造に厳密に従ったJSONオブジェクトで応答する必要があります：

  {{ response_schema | indent(2) }}
  ...
user_prompt: >-
  ユニークで興味深いフィクションのキャラクターを、詳細な性格と共に生成してください。
  性別は「{{ gender }}」、年齢は「{{ age }}」歳です。
{% if additional_instructions %}
  {{ additional_instructions }}
{% endif %}
```

### 2. Fail-fast variable validation (`src/service/template_engine.py`)

```python
def get_template_variables(self, template_name: str) -> set[str]:
    template_source = self.env.loader.get_source(self.env, template_name)[0]
    parsed_content = self.env.parse(template_source)
    return meta.find_undeclared_variables(parsed_content)      # AST, not regex

def validate_variables(self, template_name, variables) -> None:
    missing_vars = self.get_template_variables(template_name) - set(variables.keys())
    if missing_vars:
        raise TemplateValidationError(f"Missing required variables for template '{template_name}': {missing_vars}")
```

### 3. Render straight to message format (`src/service/template_engine.py`)

```python
def render_prompt_messages(self, template_name, variables, ...) -> list[dict[str, str]]:
    rendered = self.render_template(template_name, variables)   # Jinja2 → yaml.safe_load
    return [
        {"role": "system", "content": rendered["system_prompt"]},
        {"role": "user", "content": rendered["user_prompt"]},
    ]
```

### 4. Variable files as data (`variables/character_artist.yaml`)

```yaml
gender: "female"
age: 28
additional_instructions: "このキャラクターは画家で、感受性が豊かです。..."
```

`prepare_character_variables()` merges these with computed values (like the rendered `response_schema`) before rendering.

## Data Models

| Model | Purpose |
|-------|---------|
| `CharacterRequest` / `CharacterResponse` | Demo task input/output schemas (structured output) |
| `TemplateValidationError` | Raised on missing variables or missing `system_prompt`/`user_prompt` keys |
| `OpenAIModel` | `StrEnum` of usable model IDs |

## Setup & Run

```bash
cp .envrc.example .envrc     # set OPENAI_API_KEY
uv sync

# Canonical example (template with default variables)
uv run python -m src.main -m GPT_5_4 -t templates/character_generation.yaml

# Template + variable file combinations
uv run python -m src.main -m GPT_5_4 -t templates/character_generation.yaml -v variables/character_artist.yaml
uv run python -m src.main -m GPT_5_4 -t templates/email_formal.yaml -v variables/email_campaign_summer.yaml
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--model` | `-m` | Yes | — | OpenAI model enum name |
| `--template` | `-t` | Yes | — | Template YAML path |
| `--variables` | `-v` | No | — | Variables YAML path |
| `--output-directory` | `-od` | No | `outputs` | Output directory |

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
uv run pytest tests/ -v      # template engine + prompt tests, no API key needed
```

## Implementation Notes

- **Why YAML wrapping Jinja2 (not raw text files)**: one file carries multiple named prompt parts (`system_prompt`, `user_prompt` — extensible to `few_shot_examples` etc.), and `yaml.safe_load` after rendering gives structure for free.
- **Whitespace control**: `>-` folded scalars in YAML plus `trim_blocks`/`lstrip_blocks` in Jinja2 keep rendered prompts free of stray blank lines — diff the rendered output when editing templates.
- **The template layer is fully testable offline** — rendering and validation tests run without API keys, which makes prompt changes CI-checkable.
- **Schema injection keeps prompt and validation aligned**: the `response_schema` variable is generated from `CharacterResponse.detailed_model()`, the same model used for structured output enforcement.
- **Review workflow**: prompt changes become YAML diffs in pull requests; non-engineers can edit templates without touching Python.

## How to Apply This Practice to Your Own Project

1. Create `templates/` and move every inline prompt into a YAML file with `system_prompt`/`user_prompt` keys; parameterize differences with `{{ vars }}` and `{% if %}` blocks.
2. Copy `TemplateEngine` as-is — it has no project-specific logic.
3. Route all prompt construction through `render_prompt_messages()`; delete ad-hoc f-string prompt assembly.
4. Put per-use-case data in `variables/*.yaml`; treat new use cases as new variable files, not new templates, until the structure actually differs.
5. If the task uses structured output, inject the schema description as a template variable derived from the Pydantic model.
6. Add rendering/validation unit tests; run them in CI so prompt edits can't ship broken.

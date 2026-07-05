# Chapter 6 Section 1: Constraining Input Freedom — Free-Form vs Structured LLM Interfaces

## What This Section Demonstrates

Stability in LLM applications comes not only from constraining *outputs* (Chapter 2 Section 1) but from constraining *inputs*. This section is a Streamlit app that puts the two interface philosophies side by side for the same task (character generation):

- **Free-form tab** — one text area, anything goes. Maximum flexibility; the request may be off-domain, under-specified, or adversarial, and results vary accordingly.
- **Structured form tab** — a `st.form` with a gender selectbox, age slider, and a bounded free-text field for extras. Every submission is a valid, typed `CharacterRequest` before the LLM is ever called.

The practice: **design the input surface so invalid requests are unrepresentable**, and keep free text confined to a supplementary field with clear scope. Apply this to any user-facing LLM feature — forms, pickers, and sliders are prompt engineering by UI.

## Practice Rules

1. **Map UI controls to your request model's fields** — gender → selectbox over the `Gender` enum, age → slider within the model's `ge/le` bounds. The form *is* the validation.
2. **Confine free text to one optional field** (`additional_instructions`) whose role in the prompt is fixed and limited; never let free text define the whole task.
3. **Normalize the free-form path through the same typed request** (`create_freeform_request` fills defaults and stuffs the text into `additional_instructions`) — even the flexible UI produces a `CharacterRequest`, so the backend has one contract.
4. **Share the entire backend between both interfaces** — same `call_llm`, same providers, same structured output — so the only variable in the comparison is input design.
5. **Show the structured output next to the rendered result** (`st.json(result.model_dump())` beside the profile view) — making structure visible teaches users what the system actually consumes.
6. **Keep provider/model selection in the sidebar as enums** — configuration is also a constrained input.

## Architecture

```
Streamlit app (app.py)
├── sidebar: provider/model selection (enum-driven selectboxes)
├── Tab 1: render_freeform_tab
│     st.text_area → create_freeform_request()   ← defaults + free text into one field
└── Tab 2: render_structured_form_tab
      st.form: selectbox(Gender) + slider(age) + bounded text
      → CharacterRequest (typed, always valid)
            ▼ both tabs
      call_llm(provider, model, character_request)
            ▼
      src/service/request_llm.py  (OpenAI / Gemini structured output)
            ▼
      display_character_result: st.json(structured) + rendered profile
```

### Directory Structure

```
chapter_6/section_1/
├── app.py                     # Streamlit UI: tabs, sidebar, rendering
├── src/
│   ├── service/request_llm.py # provider calls (structured output)
│   ├── model/model.py         # CharacterRequest / CharacterResponse / Gender
│   ├── prompt/prompt.py       # dynamic prompt generation from requests
│   ├── client/llm_client.py   # provider/model enums + clients
│   └── config.py / logger.py
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Structured form → typed request (`app.py`)

```python
def render_structured_form_tab(provider: LLMProvider, model: str) -> None:
    with st.form("character_form"):
        # gender: st.selectbox over Gender enum
        # age:    st.slider within model bounds
        # extras: bounded st.text_area
        # submit → CharacterRequest(gender=..., age=..., additional_instructions=...)
```

Invalid combinations can't be submitted; the LLM never sees malformed input.

### 2. Free text funneled into the same contract

```python
def create_freeform_request(user_prompt: str) -> CharacterRequest:
    """Use default values and put the user's free text into additional_instructions."""
    ...
```

Even "maximum freedom" is normalized — the backend has exactly one entry type.

### 3. One shared backend for both tabs

```python
def call_llm(provider: LLMProvider, model: str, character_request: CharacterRequest) -> CharacterResponse:
    # dispatches to request_openai / request_gemini — identical for both interfaces
```

### 4. Structure made visible

```python
def display_character_result(result: CharacterResponse) -> None:
    col_left, col_right = st.columns(2)
    with col_left:
        st.json(result.model_dump())        # the machine view
    with col_right:
        st.markdown(f"**名前:** {result.first_name} {result.last_name}")   # the human view
```

## Data Models

| Model | Purpose |
|-------|---------|
| `CharacterRequest` | The single input contract (gender enum, bounded age, optional free text) |
| `CharacterResponse` | Structured generation output |
| `LLMProvider` + model enums | Sidebar configuration vocabulary |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY
uv sync

# Launch the app (opens on :8501)
uv run streamlit run app.py

# Headless (CI / server)
uv run streamlit run app.py --server.headless true
```

Try the same request in both tabs — e.g. "25歳の女性の魔法使い" free-form vs gender=female/age=25 in the form — and compare stability across repeated runs.

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Flexibility is a cost, not a feature default.** The free-form tab shows the failure modes explicitly: off-topic requests, missing parameters the model must guess, and prompt-injection surface. The structured tab eliminates all three by construction.
- **The right amount of freedom is a product decision** — this app frames it as a dial: enum fields (no freedom) → bounded sliders (numeric freedom) → scoped free-text (contained freedom). Place each input on that dial deliberately.
- **UI constraints double as documentation**: a slider labeled 0–100 tells users the valid range without error messages; a form can't produce "please enter a valid age" churn.
- **This is also a security practice** — the smaller and more scoped the free-text surface, the smaller the injection surface passed to the model.
- **Streamlit specifics**: state flows top-down per rerun; `st.form` batches inputs until submit (preventing per-keystroke reruns), and unique `key=`s keep tab widgets independent.

## How to Apply This Practice to Your Own Project

1. Write the typed request model first (enums, bounds, optional scoped free text) — then design the UI as a projection of that model.
2. Convert every "big text box" feature to structured fields + one supplementary instruction field; measure the drop in bad outputs.
3. Normalize any remaining free-form path through the same request model with explicit defaults.
4. Render the structured request/response next to the human-readable result during development — it exposes prompt/contract drift instantly.
5. Keep one backend entry point for all interface variants so input design is the only experimental variable.
6. Revisit the freedom dial per field when users complain: widen a bound or add an enum value — don't reopen the free-for-all.

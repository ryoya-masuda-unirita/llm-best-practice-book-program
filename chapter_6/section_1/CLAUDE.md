# Section 9 Project Status Report

**Project**: Chapter 2 Section 9 - LLMを安定して使うために自由度を下げる
**Last Updated**: 2025-10-18
**Status**: Active Development

---

## Overview

This project demonstrates a fundamental LLM application design principle: **reducing user input flexibility to achieve stability and predictability**. Unlike Section 1 which focuses on structured outputs, Section 9 focuses on **structured inputs** through an interactive Streamlit web application.

### Key Differentiator

Section 9 is **unique in Chapter 2** as it:
- Provides an **interactive web UI** (the only section with Streamlit)
- Demonstrates **comparative learning** by showing both good and bad approaches side-by-side
- Focuses on **input design** rather than output design
- Serves as an **educational tool** for understanding production LLM application patterns

---

## Current Architecture

### Application Structure

```
Streamlit Web App (app.py)
    ├── Free-form Interface Tab (demonstrates flexibility, potential instability)
    ├── Structured Form Interface Tab (demonstrates constraints, stability)
    └── Model Selection Sidebar (OpenAI/Gemini model switching)

Supporting Infrastructure (src/)
    ├── client/llm_client.py    - LLM client initialization
    ├── model/model.py           - CharacterRequest + CharacterResponse
    ├── prompt/prompt.py         - Dynamic prompt generation from requests
    ├── service/request_llm.py   - LLM invocation logic
    ├── config.py                - API key management
    └── logger.py                - Logging utilities
```

### Design Pattern: Request/Response Separation

**CharacterRequest** (Input Model):
- Structures user input before it becomes a prompt
- Validates: gender (enum), age (0-100), optional additional instructions
- Enforces constraints at the input layer

**CharacterResponse** (Output Model):
- Same as Section 1
- Ensures structured output from LLM

This separation is the **core architectural innovation** of Section 9.

---

## Recent Changes

### Removed: CLI Interface (`src/main.py`)

**Date**: 2025-10-18
**Reason**: Streamline to focus on interactive demonstration

The CLI was removed to:
1. **Simplify the project scope** - Focus exclusively on the web-based comparative demo
2. **Avoid redundancy** - Section 1 already demonstrates CLI usage
3. **Emphasize the educational goal** - The Streamlit UI is the primary teaching tool

**Impact**:
- Project now has a single, clear entry point: `streamlit run app.py`
- README.md updated to remove all CLI references
- No impact on core functionality (all LLM logic is in `src/service/`)

---

## Implementation Details

### 1. Two-Tab Comparison Pattern

**Tab 1: Free-form Interface**
- Purpose: Demonstrate high flexibility, low stability
- User Input: Single text area for arbitrary prompts
- Shows: Difficulty in consistent parsing, error handling complexity
- Educational Value: "This is what NOT to do in production"

**Tab 2: Structured Form Interface**
- Purpose: Demonstrate controlled flexibility, high stability
- User Input: Dropdowns, number inputs, optional text area
- Shows: Predictable results, easy validation, better UX
- Educational Value: "This is the production-ready pattern"

### 2. Dynamic Prompt Generation

```python
# prompt.py
def make_prompt(character_request: CharacterRequest) -> list:
    # Embeds validated user input into a structured prompt
    # System prompt defines output schema (CharacterResponse)
    # User prompt contains the constrained inputs
```

**Key Insight**: By accepting a `CharacterRequest` parameter, the prompt function enforces that all inputs are pre-validated before prompt construction.

### 3. Multi-Provider Support

**OpenAI Models** (9 options):
- gpt-5.5
- GPT-5.4 series: gpt-5.4, gpt-5.4-mini, gpt-5.4-nano
- gpt-5.2, gpt-5.1
- GPT-5 series: gpt-5, gpt-5-mini, gpt-5-nano

**Gemini Models** (5 options):
- gemini-2.5-pro
- gemini-2.5-flash
- gemini-2.5-flash-lite
- gemini-3.5-flash
- gemini-3.1-flash-lite

Both providers use structured output features:
- OpenAI: `beta.chat.completions.parse()` with `response_format`
- Gemini: `generate_content()` with `response_schema`

### 4. Streamlit UI Features

**Sidebar**:
- LLM provider selection (OpenAI/Gemini)
- Model selection (dynamically updates based on provider)

**Tab Content**:
- Input fields (different for each tab)
- "Generate" button
- JSON output display
- Formatted profile display
- Expandable "Internal Prompt" section (shows what was actually sent to LLM)

**Educational Messaging**:
- `st.info()` for free-form tab (warns about risks)
- `st.success()` for structured tab (highlights benefits)

---

## Technical Stack

### Dependencies

**Core**:
- `streamlit>=1.50.0` - Web UI framework (unique to Section 9)
- `pydantic>=2.12.2` - Data validation and modeling
- `openai>=2.4.0` - OpenAI API client
- `google-genai>=1.45.0` - Google Gemini API client

**Supporting**:
- `python-dotenv>=1.1.1` - Environment variable management
- `click>=8.3.0` - CLI parsing (used by other sections, minimal use here)

### Python Version

Requires Python 3.13.2+ for:
- Modern type hints (`str | None` syntax)
- Enhanced async/await support
- Pydantic v2 compatibility

---

## File Organization

```
section_9/
├── app.py                    # 🎯 Main entry point (Streamlit app)
├── src/
│   ├── client/
│   │   └── llm_client.py     # Initialize OpenAI/Gemini clients
│   ├── model/
│   │   └── model.py          # CharacterRequest + CharacterResponse
│   ├── prompt/
│   │   └── prompt.py         # make_prompt(character_request)
│   ├── service/
│   │   └── request_llm.py    # request_openai(), request_gemini()
│   ├── config.py             # API key loading with Secret[str]
│   └── logger.py             # Logging configuration
├── outputs/                  # Generated JSON files (gitignored)
├── .envrc.example            # Template for API keys
├── pyproject.toml            # Project dependencies
├── Makefile                  # Build/lint commands
├── README.md                 # User documentation
└── CLAUDE.md                 # This file
```

### Key Files

**`app.py`** (Main Application):
- ~200-300 lines
- Two tabs with distinct UI patterns
- Model selection logic
- LLM invocation with error handling
- Output formatting (JSON + pretty-printed)

**`src/model/model.py`** (Data Models):
- `Gender(StrEnum)` - FEMALE/MALE
- `CharacterPersonality(BaseModel)` - short_personality, description
- `CharacterRequest(BaseModel)` - **NEW**: gender, age, additional_instructions
- `CharacterResponse(BaseModel)` - Same as Section 1

**`src/prompt/prompt.py`** (Prompt Generation):
- `make_prompt(character_request: CharacterRequest) -> list`
- Generates system + user messages
- Embeds CharacterResponse schema in system prompt
- Embeds user inputs in user prompt

**`src/service/request_llm.py`** (LLM Service):
- `request_openai(prompt, model)` - Async OpenAI call
- `request_gemini(prompt, model)` - Async Gemini call
- Both return `CharacterResponse` (parsed)

---

## Configuration

### Environment Variables

Required in `.envrc`:
```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIzaSy...
```

Managed by:
- `python-dotenv` - Loads from `.envrc`
- `pydantic.Secret[str]` - Masks in logs
- `src/config.py` - Validates presence

### Security Notes

- API keys are **never logged** (Secret[str] automatic masking)
- `.envrc` is **gitignored**
- `.envrc.example` provides template without secrets

---

## Usage Patterns

### For End Users

```bash
# Start the web app
streamlit run app.py

# Access at http://localhost:8501
# Try both tabs to compare interfaces
```

### For Developers

```python
# Import the request model
from src.model.model import CharacterRequest, Gender

# Create a structured request
request = CharacterRequest(
    gender=Gender.MALE,
    age=25,
    additional_instructions="Make them a sci-fi character"
)

# Generate prompt
from src.prompt.prompt import make_prompt
prompt = make_prompt(request)

# Call LLM
from src.service.request_llm import request_openai
from src.model.model import OpenAIModel
result = await request_openai(prompt, OpenAIModel.GPT_5_4_MINI)
```

---

## Testing Strategy

### Manual Testing Scenarios

**Scenario 1: Free-form Tab**
1. Enter: "Create a 30-year-old female character"
2. Observe: LLM attempts to parse intent from free text
3. Risk: Might misinterpret age, gender, or other details

**Scenario 2: Structured Form Tab**
1. Select: Female, Age: 30
2. Observe: Inputs are guaranteed to be valid
3. Benefit: No parsing ambiguity, validated before LLM call

**Scenario 3: Model Switching**
1. Change provider from OpenAI to Gemini
2. Observe: Model dropdown updates automatically
3. Generate with both providers
4. Compare: Both produce valid CharacterResponse JSON

**Scenario 4: Validation**
1. Try to enter age > 100 in structured form
2. Observe: Number input prevents invalid values
3. Benefit: Client-side validation before API call

### Expected Behavior

✅ **Structured form should always produce**:
- Valid JSON matching CharacterResponse schema
- Correct gender (exactly as selected)
- Correct age (exactly as entered)
- Consistent 3 personalities

⚠️ **Free-form might produce**:
- Varied interpretations of the request
- Occasional parsing errors
- Inconsistent results across runs

---

## Design Decisions

### Why Streamlit?

1. **Rapid prototyping** - Built web UI in <100 lines
2. **Interactive demos** - Perfect for educational content
3. **No frontend complexity** - Pure Python, no HTML/CSS/JS
4. **State management** - Session state for model persistence

### Why Remove CLI?

1. **Focus** - Section 1 already demonstrates CLI patterns
2. **Clarity** - One entry point reduces confusion
3. **Purpose** - This section is about **comparison**, which requires UI

### Why Two Tabs?

1. **Comparison** - Side-by-side demonstration is more effective
2. **Education** - Users experience both approaches directly
3. **Contrast** - Highlights trade-offs visually

### Why CharacterRequest Model?

1. **Type safety** - Pydantic validates at Python level
2. **Documentation** - Model serves as API contract
3. **Reusability** - Could be used by REST API, GraphQL, etc.
4. **Separation** - Input validation separate from LLM logic

---

## Known Limitations

### Current Constraints

1. **No persistent storage** - Generated characters are not saved to database
2. **No batch generation** - One character at a time
3. **No export options** - Can't download results (only copy JSON)
4. **Limited customization** - Only gender, age, additional_instructions

### Future Enhancements (Not Planned)

These are **intentionally omitted** to keep the example focused:

- ❌ User authentication
- ❌ Character history/favorites
- ❌ Multiple character generation
- ❌ Advanced prompt templates
- ❌ Custom output formats (PDF, DOCX)
- ❌ API endpoint exposure

**Rationale**: Section 9 is a **pedagogical example**, not a production application.

---

## Relationship to Other Sections

### Section 1 (Basic Structured Output)

**Section 1** teaches:
- How to get structured outputs from LLMs
- Pydantic model integration with OpenAI/Gemini
- Basic CLI application structure

**Section 9** builds on this by adding:
- Structured **inputs** (not just outputs)
- Interactive UI for comparison
- Request/Response pattern

**Code Reuse**:
- CharacterResponse model is identical
- LLM client setup is similar
- Config/logger are conceptually the same

### Other Sections

Section 9 is **self-contained** but demonstrates patterns used in:
- **Section 2**: Logging/observability (though simplified here)
- **Section 3**: Error handling and resilience
- **Section 4**: Structured data flow
- **Section 5**: API design patterns (request/response)

---

## Troubleshooting

### Common Issues

**Issue**: "Module not found: streamlit"
- **Cause**: Dependencies not installed
- **Fix**: Run `uv sync` or `pip install -e .`

**Issue**: "API key not found"
- **Cause**: `.envrc` not created or not loaded
- **Fix**: Copy `.envrc.example` to `.envrc` and add keys

**Issue**: Streamlit won't start
- **Cause**: Port 8501 already in use
- **Fix**: `streamlit run app.py --server.port 8502`

**Issue**: JSON parsing errors in free-form tab
- **Cause**: This is **expected behavior** demonstrating the problem
- **Solution**: Switch to structured form tab

**Issue**: Different results each time
- **Cause**: High temperature settings (1.0 for OpenAI, 2.0 for Gemini)
- **Expected**: Variability is intentional for creative generation

---

## Performance Characteristics

### Response Times

**Typical latency** (depends on model and network):
- OpenAI GPT-5.4-mini: 2-4 seconds
- OpenAI GPT-5: 4-8 seconds
- Gemini 2.5 Flash: 2-5 seconds
- Gemini 2.5 Pro: 5-10 seconds

### Cost Considerations

**Approximate costs per character generation**:
- GPT-5.4-mini: $0.001-0.003
- GPT-5.4: $0.01-0.02
- Gemini 2.5 Flash: $0.0001-0.0005
- Gemini 2.5 Pro: $0.002-0.005

*Note: These are estimates and vary based on prompt length and output.*

---

## Educational Value

### Learning Objectives

After using this section, developers should understand:

1. ✅ **Input Constraint Principle**: Reducing user freedom improves reliability
2. ✅ **Request/Response Pattern**: Separate input models from output models
3. ✅ **Validation Layers**: Validate early (UI) and often (Pydantic)
4. ✅ **Trade-off Analysis**: Flexibility vs. Stability spectrum
5. ✅ **Production Patterns**: How to design user-facing LLM apps

### Key Takeaways

**For Product Designers**:
- Users don't need full prompt engineering control
- Structured forms provide better UX than text areas
- Constraints enable better error messages

**For Engineers**:
- Pydantic models enforce contracts at boundaries
- Type-safe inputs prevent entire classes of bugs
- Separation of concerns improves maintainability

**For Architects**:
- Input validation is as important as output validation
- Request models document API contracts
- Interactive demos are powerful teaching tools

---

## Maintenance Notes

### Code Health

**Linting**: Uses Ruff via Makefile
```bash
make lint    # Run linter
make format  # Auto-format code
```

**Type Checking**: Pydantic provides runtime validation (static type checking not configured)

**Dependencies**: Keep updated (especially openai and google-genai for new features)

### Future-Proofing

**When models change**:
1. Update `src/model/model.py` enum values
2. Update README.md model lists
3. Test with new models

**When APIs change**:
1. Check `src/service/request_llm.py` for compatibility
2. Update client initialization in `src/client/llm_client.py`
3. Run manual tests with both providers

---

## Documentation Status

- ✅ README.md - Complete, user-focused
- ✅ CLAUDE.md - This file, technical overview
- ✅ Code comments - Key functions documented
- ⚠️ API docs - Not generated (project too small)
- ⚠️ Tutorial - Embedded in README

---

## Summary

**Section 9** successfully demonstrates a critical LLM application design principle through an interactive, comparative web interface. The removal of the CLI sharpened the focus on the educational goal: showing developers why and how to constrain user inputs for production stability.

**Current Status**: ✅ Feature complete, ready for use
**Next Steps**: None - project is in stable state for educational purposes
**Recommended Use**: Run `streamlit run app.py` and explore both tabs to understand the principle

---

*This document reflects the state of the project as of 2025-10-18. It should be updated when significant changes occur.*

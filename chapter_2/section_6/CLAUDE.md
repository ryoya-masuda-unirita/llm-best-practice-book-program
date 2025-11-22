# Chapter 2 Section 6: Structured Template Prompting - Project Status Report

**Generated**: 2025-10-18
**Project**: Structured Template Prompting with Jinja2 and YAML
**Status**: ✅ Implementation Complete - Production Ready
**Version**: 1.0

---

## 📊 Project Overview

This section implements a production-ready structured template prompting system for Large Language Model (LLM) applications. The system addresses critical challenges in prompt management: maintainability, reusability, testability, and collaborative development.

### Core Problem

Traditional prompt management approaches fail for LLM applications because:
- Hardcoded prompts in source code are difficult to modify and maintain
- Copy-paste duplication leads to inconsistency and maintenance overhead
- Non-technical team members cannot easily improve prompts
- Testing and version control of prompts is challenging
- Dynamic prompt assembly from multiple sources becomes unmanageable

### Solution

A template-driven architecture that separates prompt structure from code, enabling:
- YAML-based template definition with Jinja2 for dynamic variable injection
- Complete separation of prompt logic (templates) from data (variables)
- Validation to ensure all required variables are provided
- Multiple template variations for A/B testing and multi-use cases
- Non-engineer prompt editing without touching code
- Clean version control and collaboration workflows

---

## ✅ Completed Features

### Core Components
- [x] TemplateEngine class with Jinja2 integration (src/service/template_engine.py - 147 lines)
- [x] Variable extraction (`get_template_variables`)
- [x] Variable validation (`validate_variables`)
- [x] Template rendering (`render_template`)
- [x] Message format conversion (`render_prompt_messages`)
- [x] YAML template format with system_prompt and user_prompt keys
- [x] Support for Jinja2 features (variables, conditionals, loops, filters)

### Templates and Variables
- [x] Character generation template (templates/character_generation.yaml)
- [x] Product description template (templates/product_description.yaml)
- [x] Email templates: formal and casual (templates/email_*.yaml)
- [x] Character variable files: artist, detective (variables/character_*.yaml)
- [x] Product variable files: electronics, apparel (variables/product_*.yaml)
- [x] Email campaign variables: summer, winter (variables/email_campaign_*.yaml)

### Application Integration
- [x] Prompt generation using templates (src/prompt/prompt.py)
- [x] LLM request handlers for OpenAI (src/service/request_llm.py)
- [x] CLI with model and provider selection (src/main.py)
- [x] Pydantic models for type safety (src/model/model.py)
- [x] Configuration management (src/config.py)
- [x] Logging setup (src/logger.py)

### Testing
- [x] 54 comprehensive tests across 2 test files
- [x] TemplateEngine tests (46 tests) - initialization, validation, rendering, edge cases
- [x] Prompt generation tests (8 tests)
- [x] Test fixtures for temporary template directories (tests/conftest.py)
- [x] Coverage for Unicode, special characters, nested structures

### Infrastructure
- [x] Makefile for common tasks (install, test, run, lint)
- [x] pytest configuration with asyncio support
- [x] Environment variable management
- [x] Dependencies: jinja2>=3.1.6, pyyaml>=6.0.3

### Documentation
- [x] Comprehensive README.md (Japanese, production-ready)
- [x] CLAUDE.md design specification (this file)
- [x] Inline code documentation
- [x] Usage examples and patterns

---

## 📁 Project Structure

```
section_6/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration (API keys)
│   ├── logger.py                  # Logging setup
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py          # OpenAI client
│   ├── model/
│   │   ├── __init__.py
│   │   └── model.py               # Request/Response models
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py              # make_prompt function
│   └── service/
│       ├── __init__.py
│       ├── request_llm.py         # LLM request handlers
│       └── template_engine.py     # Template engine (147 lines)
├── templates/                      # YAML templates (4 files)
│   ├── character_generation.yaml
│   ├── product_description.yaml
│   ├── email_formal.yaml
│   └── email_casual.yaml
├── variables/                      # Variable definitions (6 files)
│   ├── character_artist.yaml
│   ├── character_detective.yaml
│   ├── product_electronics.yaml
│   ├── product_apparel.yaml
│   ├── email_campaign_summer.yaml
│   └── email_campaign_winter.yaml
├── tests/                          # Test suite (54 tests)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_template_engine.py    # 46 tests
│   └── test_prompt.py             # 8 tests
├── outputs/                        # Generated files (gitignored)
├── .envrc.example
├── pyproject.toml
├── pytest.ini
├── Makefile
├── README.md
└── CLAUDE.md
```

**Statistics**:
- 17 Python files
- 54 comprehensive tests
- 4 template files
- 6 variable files

---

## 🎓 Key Implementation Details

### 1. TemplateEngine (src/service/template_engine.py)

**Purpose**: Core template management system using Jinja2 and YAML

**Key Methods**:
- `get_template_variables(template_name)` - Extract all variable names from a template
- `validate_variables(template_name, variables)` - Validate that all required variables are provided
- `render_template(template_name, variables, validate=True)` - Render template to dict
- `render_prompt_messages(...)` - Render and convert to LLM API message format

**Features**:
- Automatic variable extraction using `jinja2.meta.find_undeclared_variables()`
- Validation before rendering to catch errors early
- Support for Jinja2 filters, conditionals, loops
- Proper YAML indentation handling (`trim_blocks`, `lstrip_blocks`)

### 2. YAML Template Format

**Standard Structure**:
```yaml
system_prompt: >-
  System instruction text here.
  {{ variable_name }}

user_prompt: >-
  User instruction text here.
  {% if optional_variable %}
  {{ optional_variable }}
  {% endif %}
```

**Jinja2 Features Supported**:
- Variable substitution: `{{ variable }}`
- Conditionals: `{% if condition %}...{% endif %}`
- Loops: `{% for item in list %}...{% endfor %}`
- Filters: `{{ variable | indent(2) }}`

### 3. Variable Files

Separate YAML files containing data to inject into templates:

```yaml
# variables/character_artist.yaml
gender: "female"
age: 28
additional_instructions: "このキャラクターは画家で、感受性が豊かです。"
```

**Benefits**:
- Same template, multiple data sets
- Easy A/B testing
- Non-engineer editable
- Version control for variations

### 4. Prompt Generation (src/prompt/prompt.py)

```python
# Initialize template engine once at module level
_template_engine = TemplateEngine(template_dir=_template_dir)

def make_prompt(character_request: CharacterRequest) -> list:
    # Prepare variables
    template_variables = {
        "response_schema": response_schema,
        "gender": character_request.gender.value,
        "age": character_request.age,
        "additional_instructions": character_request.additional_instructions or "",
    }

    # Render with validation
    return _template_engine.render_prompt_messages(
        template_name="character_generation.yaml",
        variables=template_variables,
        validate=True
    )
```

---

## 🧪 Testing Strategy

### Test Coverage (54 tests)

**TemplateEngine Tests** (46 tests):
- Initialization: valid/invalid directories, string paths
- Variable extraction: simple, loops, conditionals, multiple vars
- Variable validation: missing, extra, partial variables
- Template rendering: loops, conditionals, nested structures
- Message conversion: default keys, custom keys, missing keys
- Edge cases: Unicode, None values, special chars, boolean values

**Prompt Generation Tests** (8 tests):
- Correct message format
- Variable injection
- Schema inclusion
- Conditional sections
- Validation enforcement

### Running Tests

```bash
# All tests
make test
uv run pytest

# With coverage
make pytest-cov

# Specific test file
uv run pytest tests/test_template_engine.py -v

# Failed tests only
make pytest-failed
```

---

## 🚀 Usage Examples

### Basic CLI Usage

```bash
# Install dependencies
uv sync
make install

# Run with OpenAI
uv run python -m src.main --model gpt-4o
make run-openai

# Custom output directory
uv run python -m src.main -m gpt-4o-mini -od ./my_outputs
```

### Programmatic Usage

```python
from src.service.template_engine import TemplateEngine

# Initialize engine
engine = TemplateEngine(template_dir="templates")

# Define variables
variables = {
    "gender": "female",
    "age": 28,
    "additional_instructions": "Creative and artistic."
}

# Render to LLM message format
messages = engine.render_prompt_messages(
    template_name="character_generation.yaml",
    variables=variables,
    validate=True
)

# Use with LLM API
response = await llm_client.generate(messages=messages)
```

---

## 💡 Key Benefits

### 1. Enhanced Maintainability
- Centralized prompt management
- No code changes for prompt updates
- Version control for prompt history
- Easy rollback to previous versions

### 2. Improved Reusability
- One template, multiple variable sets
- Easy A/B testing
- Template variations for different use cases

### 3. Team Collaboration
- Non-engineers can edit YAML files
- Product managers can iterate on prompts
- Domain experts can refine instructions
- No code deployment for prompt changes

### 4. Better Testing
- Templates testable in isolation
- Systematic validation testing
- Edge case coverage
- Mock data testing

### 5. Flexibility
- Jinja2 provides powerful features
- Conditional content
- Loop constructs
- Filter functions

---

## ⚖️ Trade-offs and Considerations

### Benefits
1. Maintainability: Centralized prompt management
2. Reusability: One template, many variable sets
3. Testability: Easy to test templates in isolation
4. Collaboration: Non-engineers can edit YAML files
5. Version Control: Git-friendly prompt history
6. Validation: Catch missing variables early

### Trade-offs
1. **Complexity**: Additional abstraction layer
   - Mitigation: Good documentation, examples

2. **Over-abstraction Risk**: Too many template layers
   - Mitigation: Keep templates simple, limit nesting

3. **Debugging Challenges**: Errors in template or variables
   - Mitigation: Detailed error messages, validation

4. **Performance**: Template parsing overhead
   - Mitigation: Cache compiled templates (Jinja2 default)

5. **Logic in Templates**: Temptation to add business logic
   - Mitigation: Keep templates simple, complex logic in Python

---

## 📚 Best Practices

### Do's
1. Keep templates simple - minimize logic
2. Always validate in production (`validate=True`)
3. Use variable files for data separation
4. Write template tests
5. Document required variables
6. Version control templates and variables
7. Use meaningful file names
8. Monitor template usage

### Don'ts
1. Don't put business logic in templates
2. Don't skip validation in production
3. Don't hardcode variables
4. Don't over-abstract
5. Don't ignore template errors
6. Don't mix languages in same file
7. Don't commit sensitive data
8. Don't skip documentation

---

## 🔮 Future Enhancements

### Planned Features
1. **Template Inheritance** - Base templates with extensions
2. **Template Macros** - Reusable template components
3. **Template Linting** - Validate YAML and Jinja2 syntax
4. **Template Preview** - Render with sample data
5. **Performance Optimization** - Template caching
6. **Advanced Validation** - Type checking for variables
7. **Multi-model Templates** - Model-specific optimizations
8. **Template Analytics** - Track usage and performance

---

## 🛠️ Troubleshooting

### Common Issues

**1. TemplateNotFound Error**
```
jinja2.exceptions.TemplateNotFound: character_generation.yaml
```
Solution: Check template directory path, verify file exists

**2. Missing Variables**
```
TemplateValidationError: Missing required variables: {'age'}
```
Solution: Use `get_template_variables()` to check required variables

**3. YAML Syntax Error**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```
Solution: Check indentation and colons in YAML

**4. Undefined Variable**
```
jinja2.exceptions.UndefinedError: 'age' is undefined
```
Solution: Enable validation or use default values in template

---

## 📖 References

- **Design Pattern**: Template Method Pattern
- **Jinja2 Documentation**: https://jinja.palletsprojects.com/
- **YAML Specification**: https://yaml.org/spec/
- **Best Practices**: Separation of Concerns, DRY principle
- **Testing**: pytest, fixture-based testing
- **Chapter Reference**: Chapter 2, Section 6 - Structured Template Prompting

---

## 📝 Changelog

### v1.0 (2025-10-18) - Initial Implementation

**Core Features**:
- TemplateEngine class with Jinja2 integration
- YAML template format
- Variable validation
- Message format conversion
- Jinja2 features support

**Templates** (4 files):
- Character generation
- Product description
- Email (formal and casual)

**Variable Files** (6 files):
- Character variations: artist, detective
- Product variations: electronics, apparel
- Email campaigns: summer, winter

**Testing**:
- 54 comprehensive tests
- Full edge case coverage
- Temporary directory fixtures

**Infrastructure**:
- CLI with provider/model selection
- LLM request handlers
- Makefile automation
- pytest configuration

**Documentation**:
- Comprehensive README.md (Japanese)
- CLAUDE.md (this file)
- Code documentation
- Usage examples

---

**Generated by**: Claude Code
**Date**: 2025-10-18
**Version**: 1.0

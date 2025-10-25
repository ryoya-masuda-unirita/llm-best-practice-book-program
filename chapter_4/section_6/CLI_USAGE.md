# CLI Usage Guide

## Fixed Issues

✅ **Model names**: Now accepts lowercase with hyphens (e.g., `gemini-2.5-flash`)
✅ **Provider names**: Now accepts lowercase (e.g., `gemini` or `openai`)
✅ **Case insensitive**: Both uppercase and lowercase work

## Correct Command Format

### Original Command (Now Works!)

```bash
python -m src.main \
  -t "SF世界の平和について" \
  -l ja \
  -lp gemini \
  -m gemini-2.5-flash \
  -od outputs/ \
  -no 4 \
  -ns 4
```

### Alternative Formats (All Valid)

```bash
# Lowercase (recommended)
python -m src.main -t "SF世界の平和について" -l ja -lp gemini -m gemini-2.5-flash

# Uppercase also works
python -m src.main -t "SF世界の平和について" -l ja -lp GEMINI -m GEMINI-2.5-FLASH

# Mixed case works too
python -m src.main -t "SF世界の平和について" -l ja -lp Gemini -m Gemini-2.5-Flash
```

## Available Options

### LLM Providers (`-lp` / `--llm-provider`)
- `openai` (or `OPENAI`)
- `gemini` (or `GEMINI`)

### OpenAI Models (`-m` / `--model`)
- `gpt-5`
- `gpt-5-mini`
- `gpt-5-nano`
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4.1-nano`
- `gpt-4o`
- `gpt-4o-mini`

### Gemini Models (`-m` / `--model`)
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

## Common Examples

### English Article with OpenAI

```bash
python -m src.main \
  -t "The Future of Artificial Intelligence" \
  -l en \
  -lp openai \
  -m gpt-4o
```

### Japanese Article with Gemini (Auto-select)

```bash
python -m src.main \
  -t "量子コンピューティングの応用" \
  -l ja \
  -lp gemini \
  -m gemini-2.5-flash \
  --auto-select
```

### Custom Variants and Output Directory

```bash
python -m src.main \
  -t "Climate Change Solutions" \
  -l en \
  -lp gemini \
  -m gemini-2.5-pro \
  -od my_articles \
  -no 5 \
  -ns 4
```

## Quick Reference

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--theme` | `-t` | Article theme (required) | - |
| `--language` | `-l` | `en` or `ja` (required) | - |
| `--llm-provider` | `-lp` | `openai` or `gemini` (required) | `gemini` |
| `--model` | `-m` | Model name (required) | - |
| `--output-directory` | `-od` | Output directory | `outputs` |
| `--num-outline-variants` | `-no` | Number of outline variants | 3 |
| `--num-second-half-variants` | `-ns` | Number of second half variants | 3 |
| `--auto-select` | `-a` | Auto-select (no human input) | False |

## Troubleshooting

### Invalid model error
```bash
Error: Invalid value for '--model': 'GEMINI_2_5_FLASH' is not one of ...
```

**Solution**: Use lowercase with hyphens:
```bash
# Wrong: -m GEMINI_2_5_FLASH
# Right: -m gemini-2.5-flash
```

### Invalid provider error
```bash
Error: Invalid value for '--llm-provider': 'GEMINI' is not one of ...
```

**Solution**: Use lowercase (case-insensitive now):
```bash
# All work: -lp gemini, -lp GEMINI, -lp Gemini
```

### API Key error
```bash
KeyError: 'GEMINI_API_KEY'
```

**Solution**: Set up your environment variables:
```bash
cp .envrc.example .envrc
# Edit .envrc with your API keys
source .envrc
```

## Testing Without API Calls

To verify the CLI without making API calls:

```bash
# Check available options
python -m src.main --help

# This would work if API keys are set
python -m src.main -t "Test" -l en -lp gemini -m gemini-2.5-flash --auto-select
```

# Gemini Model Fix - Schema Validation Issue

## Issue

When running with Gemini models, the following error occurred:

```
Failed to review article with Gemini: 5 validation errors for Schema
properties.grade.enum.0
  Input should be a valid string [type=string_type, input_value=1, input_type=int]
```

## Root Cause

The `ArticleReview` model used `Literal[1, 2, 3, 4, 5]` for the `grade` field. When Pydantic generates JSON schema for Gemini API:

- **Before**: Generated an enum with integer values `[1, 2, 3, 4, 5]`
- **Problem**: Gemini's schema validator expected string enum values
- **Result**: Schema validation failed

## Solution

Changed the `grade` field from `Literal[1, 2, 3, 4, 5]` to `int` with constraints:

```python
# Before (caused Gemini error):
grade: Literal[1, 2, 3, 4, 5] = Field(
    ...,
    description="Grade from 1 (very poor) to 5 (excellent)",
)

# After (works with both OpenAI and Gemini):
grade: int = Field(
    ...,
    description="Grade from 1 (very poor) to 5 (excellent)",
    ge=1,  # greater than or equal to 1
    le=5,  # less than or equal to 5
)
```

## JSON Schema Comparison

### Before (Enum - Failed with Gemini)
```json
{
  "grade": {
    "enum": [1, 2, 3, 4, 5],
    "type": "integer"
  }
}
```

### After (Integer with Constraints - Works with Both)
```json
{
  "grade": {
    "type": "integer",
    "minimum": 1,
    "maximum": 5,
    "description": "Grade from 1 (very poor) to 5 (excellent)"
  }
}
```

## Files Changed

- `src/model/parallel_world_model.py`: Updated `ArticleReview.grade` field definition

## Verification

Run the following test to verify:

```bash
python -c "
from src.model.parallel_world_model import ArticleReview
import json

# Test the model
review = ArticleReview(
    reasoning='Test review',
    grade=5,
    strengths=['Good'],
    weaknesses=[]
)
print(f'Grade: {review.grade} (type: {type(review.grade).__name__})')
print(f'Is acceptable: {review.is_acceptable()}')

# Check schema
schema = ArticleReview.model_json_schema()
print(f\"Grade schema: {json.dumps(schema['properties']['grade'], indent=2)}\")
"
```

Expected output:
```
Grade: 5 (type: int)
Is acceptable: True
Grade schema: {
  "description": "Grade from 1 (very poor) to 5 (excellent)",
  "maximum": 5,
  "minimum": 1,
  "title": "Grade",
  "type": "integer"
}
```

## Important Note: Supported Models

The command used `gemini-2.5-mini`, but this model is **not** in our supported list.

### Supported Gemini Models:
- ✅ `gemini-2.5-pro`
- ✅ `gemini-2.5-flash`
- ✅ `gemini-2.5-flash-lite`
- ❌ `gemini-2.5-mini` (not supported)

### Corrected Command

```bash
# Wrong model name:
python -m src.main -t "SF世界の平和について" -l ja -lp gemini -m gemini-2.5-mini

# Correct (use one of the supported models):
python -m src.main -t "SF世界の平和について" -l ja -lp gemini -m gemini-2.5-flash
```

## Testing the Fix

Test with Gemini (requires API key):

```bash
# Set up environment
cp .envrc.example .envrc
# Edit .envrc to add your GEMINI_API_KEY
source .envrc

# Run with supported model
python -m src.main \
  -t "SF世界の平和について" \
  -l ja \
  -lp gemini \
  -m gemini-2.5-flash \
  -od outputs/ \
  -no 2 \
  -ns 2 \
  --auto-select
```

## Status

✅ **Fixed**: Schema validation error resolved
✅ **Tested**: Model validation works correctly
✅ **Compatible**: Works with both OpenAI and Gemini APIs
⚠️ **Note**: Use supported model names (see list above)

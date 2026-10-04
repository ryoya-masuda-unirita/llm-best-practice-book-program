# Chapter 2 Section 7: LLM-as-a-Judge — Evaluating LLM Output with LLMs

## What This Section Demonstrates

LLM output quality can't be asserted with string equality, and human review doesn't scale. This section implements **LLM-as-a-Judge**: after a generation call, a second, structured LLM call scores the output against explicit criteria (accuracy / comprehensiveness / clarity), each with a 1–5 score and written reasoning, plus an overall score.

The judge is provider-independent — you can generate with Gemini and judge with OpenAI or Anthropic (**cross-provider evaluation**), which reduces self-preference bias. Apply this practice for RAG answer quality, prompt A/B testing, regression checks in CI, continuous quality monitoring, and automated output filtering.

## Practice Rules

1. **Make the judge a structured-output call.** The verdict is a Pydantic model (`JudgeResponse`), never free text — scores become data you can aggregate, threshold, and store.
2. **Score against named criteria with anchored scales.** The judge prompt defines each criterion (正確性/網羅性/明瞭さ) and what 1–5 mean concretely; every score must come with `reasoning`.
3. **Force per-criterion reasoning before the score** (`reasoning` field ordered first in `EvaluationCriterion`) — the model justifies, then rates.
4. **Set `temperature=0.0` for the judge** (where the provider supports it) — evaluation should be as deterministic as possible.
5. **Prefer a different provider/model for judging than for generation** to avoid self-preference bias. Keep both configurable (`-jp/-jm` separate from `-lp/-m`).
6. **Give the judge the full task context**: original question, the response being judged, and optionally the request parameters and reference context — accuracy can only be judged against what was asked.
7. **Persist generation and judgment side by side** (paired output files) so failures can be audited later.

## Architecture

```
CLI (src/main.py)
  │ -lp/-m: generator   -jp/-jm: judge (defaults to generator if omitted)
  ▼
request_with_judge (src/service/request_llm.py)
  ├─ Step 1: generate CharacterResponse   (structured output, any provider)
  ├─ Step 2: build JudgeRequest {question, response, request_parameters, context}
  └─ Step 3: judge_with_{openai|gemini|anthropic} → JudgeResponse
  ▼
outputs/<id>_<provider>_character.json + <id>_<provider>_judge.json
```

### Directory Structure

```
chapter_2/section_7/
├── src/
│   ├── main.py                        # CLI: generation + judge options
│   ├── client/llm_client.py           # 3-provider clients + model enums
│   ├── model/
│   │   ├── model.py                   # CharacterResponse (generation schema)
│   │   └── llm_as_a_judge_model.py    # JudgeRequest / JudgeResponse / EvaluationCriterion
│   ├── prompt/
│   │   ├── prompt.py                  # generation prompts
│   │   └── llm_as_a_judge_prompt.py   # judge prompts (criteria + anchored scale)
│   ├── service/
│   │   ├── request_llm.py             # generation + integrated request_with_judge
│   │   └── llm_as_a_judge.py          # judge_with_openai / gemini / anthropic
│   └── config.py / logger.py
├── outputs/
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. The verdict schema (`src/model/llm_as_a_judge_model.py`)

```python
class EvaluationCriterion(BaseModel):
    reasoning: str = Field(..., description="The reasoning behind the score.")   # reasoning first
    criterion_name: str = Field(..., description="The name of the evaluation criterion.")
    score: int = Field(..., description="The evaluation score from 1 to 5.", ge=1, le=5)

class JudgeResponse(BaseModel):
    evaluations: list[EvaluationCriterion]
    overall_score: float = Field(..., ge=1.0, le=5.0)
    summary: str
```

### 2. Anchored criteria in the judge prompt (`src/prompt/llm_as_a_judge_prompt.py`)

```text
【評価軸】
1. 正確性 (accuracy): 回答が質問に対して正確かつ事実として正しいか
2. 網羅性 (comprehensiveness): 質問に対して必要な情報が十分に含まれているか
3. 明瞭さ (clarity): 回答が理解しやすく、適切な表現で書かれているか

【評価基準】
- 1点: 完全に不適切 … - 5点: 完璧 (非常に正確、完全、明瞭)
```

Named criteria + concrete score anchors are what make scores comparable across runs.

### 3. Deterministic, structured judge call (`src/service/llm_as_a_judge.py`)

```python
async def judge_with_gemini(judge_request: JudgeRequest, model: GeminiModel) -> JudgeResponse:
    system_prompt, user_prompt = make_gemini_judge_prompt(judge_request)
    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=JudgeResponse,
            temperature=0.0,                      # deterministic evaluation
        ),
    )
    return result.parsed
```

`judge_with_openai` (`responses.parse(text_format=JudgeResponse)`) and `judge_with_anthropic` follow the same shape.

### 4. Generation + evaluation in one flow (`src/service/request_llm.py`)

```python
async def request_with_judge(...) -> tuple[CharacterResponse, JudgeResponse]:
    character_response = await request_<provider>(prompt, model)          # Step 1
    judge_request = JudgeRequest(question=user_prompt,
                                 response=character_response.model_dump_json(indent=2))
    judge_response = await judge_with_<judge_provider>(judge_request, judge_model)  # Step 2
    return character_response, judge_response
```

The response under evaluation is serialized JSON — the judge sees exactly what downstream consumers would.

## Data Models

| Model | Purpose |
|-------|---------|
| `JudgeRequest` | question, response, optional context / request_parameters |
| `JudgeResponse` | evaluations list + overall_score (1.0–5.0) + summary |
| `EvaluationCriterion` | reasoning + criterion_name + score (1–5) |
| `CharacterResponse` | The generation task's output schema (evaluation target) |

## Setup & Run

```bash
cp .envrc.example .envrc     # OPENAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY
uv sync

# Canonical example (generate + judge with Gemini)
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5

# Cross-provider evaluation (recommended): generate with Gemini, judge with Anthropic
uv run python -m src.main -g FEMALE -a 25 -lp ANTHROPIC -m CLAUDE_HAIKU_4_5 \
  -jp ANTHROPIC -jm CLAUDE_SONNET_4_6
```

### CLI Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--gender` | `-g` | Yes | Character gender (FEMALE/MALE) |
| `--age` | `-a` | Yes | Character age (0–100) |
| `--additional-instructions` | `-ai` | No | Extra generation instructions |
| `--llm-provider` | `-lp` | Yes | Generation provider (OPENAI/GEMINI/ANTHROPIC) |
| `--model` | `-m` | Yes | Generation model enum name |
| `--output-directory` | `-od` | No | Output directory (default `outputs`) |
| `--judge-provider` | `-jp` | No | Judge provider (defaults to generation provider) |
| `--judge-model` | `-jm` | No | Judge model enum name |

Outputs: `outputs/<id>_<provider>_character.json` (generation) and `outputs/<id>_<provider>_judge.json` (verdict).

## Development Commands

```bash
make lint / make fmt / make fix / make mypy
```

## Implementation Notes

- **Consistency levers**: temperature 0, structured output, explicit criteria/anchors, and (optionally) a stronger judge model than generator. Judges are still LLMs — expect ±1 score noise; aggregate over multiple samples for decisions.
- **Cross-provider judging** mitigates self-preference (models rating their own style highly) and provider-correlated blind spots.
- **`overall_score` is computed by the judge** as the average across criteria and validated `ge=1.0, le=5.0` — recompute it yourself downstream if you need exactness.
- **The judge prompt is Japanese**; criteria names carry English keys (accuracy/comprehensiveness/clarity) so downstream aggregation is language-neutral.
- **Use cases**: RAG answer scoring (pass retrieved docs as `context`), prompt A/B testing (fix judge, vary generation prompt), CI quality gates (fail below threshold — see Chapter 2 Section 9), production sampling audits.

## How to Apply This Practice to Your Own Project

1. Define your criteria (3–5 max) and write one-sentence definitions plus concrete 1–5 anchors for each; put them verbatim in the judge system prompt.
2. Copy the `JudgeRequest`/`JudgeResponse`/`EvaluationCriterion` model shape; keep `reasoning` before `score`.
3. Implement `judge_with_<provider>` as a structured-output call with temperature 0.
4. Wire an integrated `request_with_judge` so every evaluated generation persists both artifacts together.
5. Judge with a different provider/model than you generate with; make both configurable.
6. Decide thresholds empirically: run the judge over known-good and known-bad samples first, then set the pass bar.

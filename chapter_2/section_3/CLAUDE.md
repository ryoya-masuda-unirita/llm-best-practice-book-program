# Chapter 2 Section 3: Structuring Unstructured Data — Multimodal Extraction from Images

## What This Section Demonstrates

This section extracts **structured, typed data from unstructured image documents** (invoices and presentation slides) with a multimodal LLM, replacing the traditional OCR → text parsing → rule-based extraction pipeline with schema-bound LLM calls.

The key practice is a **classify-then-extract two-step flow**: a first cheap LLM call identifies the document type; a second call extracts data using the Pydantic schema specific to that type. Apply this whenever you ingest heterogeneous documents (invoices, receipts, slides, forms) and need machine-processable output — one generic "extract everything" prompt with a union schema is both less accurate and harder to maintain than per-type schemas.

## Practice Rules

1. **Upload the image once, reuse the handle**: `client.aio.files.upload(file=path)` returns a `File` reference passed to every subsequent call — don't re-encode the image per step.
2. **Step 1 classifies, step 2 extracts.** The classification call returns a tiny schema (`Diagram` with a `DiagramType` enum). Route to the type-specific extraction prompt AND schema based on the result.
3. **One Pydantic schema per document type**, mirroring the real document structure (nested models for line items, totals, bank details / chart data points). Don't force different document types into one schema.
4. **Bind the schema on every call** via `GenerateContentConfig(response_mime_type="application/json", response_schema=Model)` — both the classification and extraction steps are structured-output calls.
5. **Use enums for closed vocabularies** (`DiagramType`, `InvoiceBankAccountType`, `InvoiceTaxType`, `SlideDiagramType`) so invalid categories fail validation instead of leaking into data.
6. **Make uncertain fields optional.** Real documents omit fields (invoice number, payment deadline); model them as `Optional` rather than letting the LLM hallucinate values.
7. **Avoid `dict` fields in Gemini response schemas** — Gemini does not support `additionalProperties`. Type every field explicitly.

## Architecture

```
CLI (src/main.py)
  │  --image-path upload via Gemini Files API
  ▼
request_gemini (src/service/request_llm.py)
  │
  ├─ Step 1: request_identify_diagram_type()
  │    response_schema=Diagram → DiagramType (invoice | slide)
  │
  └─ Step 2: extract_from_image()
       ├─ INVOICE → make_invoice_prompt() + response_schema=Invoice
       └─ SLIDE   → make_slide_prompt()   + response_schema=Slide
  ▼
outputs/gemini_<uuid>.json
```

### Directory Structure

```
chapter_2/section_3/
├── data/                  # Sample images: 請求書 (invoices) *.png, slide_*.png
├── outputs/               # Extracted JSON
├── src/
│   ├── main.py            # CLI entry point (Click, async)
│   ├── config.py          # GEMINI_API_KEY via SecretStr
│   ├── logger.py
│   ├── client/llm_client.py   # GeminiModel enum + async client
│   ├── model/model.py         # Diagram / Invoice / Slide schema tree
│   ├── prompt/prompt.py       # classification + per-type extraction prompts
│   └── service/request_llm.py # 2-step orchestration
├── Makefile / pyproject.toml / .envrc.example
└── CLAUDE.md
```

## Key Implementation Patterns

### 1. Two-step orchestration (`src/service/request_llm.py`)

```python
async def request_gemini(model: str, gemini_path: File) -> Invoice | Slide:
    diagram = await request_identify_diagram_type(model=model, gemini_path=gemini_path)
    result = await extract_from_image(model=model, gemini_path=gemini_path,
                                      diagram_type=diagram.diagram_type)
    return result
```

Classification and extraction stay separate so each prompt does one focused job.

### 2. Type-routed schema selection (`src/service/request_llm.py`)

```python
async def extract_from_image(model, gemini_path, diagram_type) -> Invoice | Slide:
    system_prompt, user_prompt = (
        make_invoice_prompt() if diagram_type == DiagramType.INVOICE else make_slide_prompt()
    )
    response_schema = Invoice if diagram_type == DiagramType.INVOICE else Slide

    result = await google_genai_client.aio.models.generate_content(
        model=model,
        contents=[gemini_path, user_prompt],           # image handle + text in one contents list
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    return result.parsed
```

Prompt and schema are selected together — they must always agree.

### 3. Image upload once via Files API (`src/main.py`)

```python
gemini_path: File = await google_genai_client.aio.files.upload(file=image_path)
result = await request_gemini(model=model, gemini_path=gemini_path)
```

### 4. Document-shaped schema tree (`src/model/model.py`)

```
Diagram (diagram_type: DiagramType)          # step-1 output
Invoice                                      # step-2 output (invoices)
 ├── InvoiceIssuerInfo / InvoiceRecipientInfo
 ├── InvoiceFinancialTotals
 ├── InvoiceBankDetails (InvoiceBankAccountType)
 └── list[InvoiceLineItem] (InvoiceTaxType)
Slide                                        # step-2 output (slides)
 └── list[SlideDiagram] (SlideDiagramType)
      └── list[ChartDataPoint]               # label / value / unit / series
```

## Data Models

| Model | Purpose |
|-------|---------|
| `Diagram` / `DiagramType` | Step-1 classification result: `invoice` or `slide` |
| `Invoice` + nested models | Full invoice: issuer, recipient, totals, bank details, line items |
| `Slide` / `SlideDiagram` / `ChartDataPoint` | Slide with per-diagram chart data, split by chart type |
| `SlideDiagramType` | `bar_chart`, `line_chart`, `pie_chart`, `flow_chart`, `system_diagram`, `image_diagram` |

## Setup & Run

```bash
cp .envrc.example .envrc     # set GEMINI_API_KEY
uv sync

# Canonical example (invoice image)
uv run python -m src.main -m GEMINI_2_5_FLASH -i data/002_請求書_47491048.png

# Slide image
uv run python -m src.main -m GEMINI_2_5_FLASH -i data/slide_0.png -od outputs/
```

### CLI Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--model` | `-m` | Yes | — | Gemini model enum name (`GEMINI_2_5_PRO` / `GEMINI_2_5_FLASH` / `GEMINI_2_5_FLASH_LITE` …) |
| `--image-path` | `-i` | Yes | — | Path to the input image (must exist) |
| `--output-directory` | `-od` | No | `outputs` | Output directory for extracted JSON |

## Development Commands

```bash
make lint    # ruff check --fix
make fmt     # ruff format
make fix     # lint + fmt
make mypy    # type checking
```

## Implementation Notes

- **Why two steps instead of one union schema**: a single "extract as Invoice OR Slide" call forces the model to juggle both schemas at once; splitting classification from extraction keeps each prompt short and measurably improves field accuracy. The classification output is also useful metadata by itself.
- **Combination graphs**: a slide containing a bar+line combo chart is extracted as *separate* `SlideDiagram` entries, one per chart type, so different metrics never share one data-point list. This decomposition rule lives in `make_slide_prompt()`.
- **Gemini constraint — no `additionalProperties`**: response schemas must not contain plain `dict` fields; every structure is an explicitly typed Pydantic model.
- **API keys as `SecretStr`** in `src/config.py` (unwrap with `.get_secret_value()`), so keys never leak into logs.
- **Cleanup**: close the async Gemini client (`await google_genai_client.aio.aclose()`) before exit.

## How to Apply This Practice to Your Own Project

1. List the document types you ingest and write one Pydantic schema per type, mirroring the document's real structure (nested models, enums for closed sets, `Optional` for often-missing fields).
2. Add a minimal classification schema (one enum field) and a classification prompt as step 1.
3. Route step 2 on the classification result, selecting prompt and schema *as a pair*.
4. Upload media once via the provider's file API and pass the handle to both steps.
5. Log the raw LLM response at each step for auditability before returning the parsed object.
6. Validate business rules downstream (totals add up, dates parse) — schema validation ensures shape, not arithmetic.

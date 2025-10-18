# Section 2: Structured Logging for LLMOps - Design Specification

## Project Overview

This section implements a production-ready structured logging system for Large Language Model (LLM) operations. The system addresses critical challenges in LLMOps: observability, debugging, compliance, and performance monitoring.

**Core Problem:** Traditional logging approaches fail for LLM applications because:
- Prompts and responses are too long for standard log streams
- Unstructured logs make it difficult to aggregate metrics and analyze patterns
- Sensitive data in prompts requires special handling
- Performance overhead from logging can impact user experience

**Solution:** A dual-layer logging architecture that separates metadata (structured logs) from content (prompt storage), enabling:
- Machine-readable JSON logs for easy aggregation and analysis
- Separate storage for long prompt/response content
- Automatic sensitive data masking
- Async processing to minimize performance impact
- Complete request traceability with unique identifiers

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│                        (main.py)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLMOpsLogger                           │
│                   (llmops_logger.py)                        │
│                                                             │
│  • track_llm_request()  - Context manager for auto tracking│
│  • log_llm_request()    - Manual logging interface         │
│  • retrieve_prompt()    - Fetch stored prompts             │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   Structured Log         │  │     Prompt Storage           │
│ (model/llmops_log.py)    │  │ (service/prompt_storage.py)  │
│                          │  │                              │
│  • LLMOpsLogEntry        │  │  • PromptStorage (ABC)       │
│    - timestamp           │  │  • LocalFilePromptStorage    │
│    - request_id          │  │  • get_prompt_storage()      │
│    - prompt_id           │  │                              │
│    - model               │  │  PromptData Model:           │
│    - temperature         │  │  (model/prompt_data.py)      │
│    - latency_ms          │  │    - prompt_id               │
│    - status_code         │  │    - prompt_content          │
│    - level               │  │    - response_content        │
│    - metadata            │  │    - mask_sensitive_data()   │
│  • LogLevel enum         │  │                              │
│  • StorageType enum      │  │  Storage Structure:          │
│                          │  │  prompt_storage/             │
│                          │  │    └── YYYY/                 │
│                          │  │        └── MM/               │
│                          │  │            └── DD/           │
│                          │  │                └── {id}.json │
└──────────┬───────────────┘  └──────────┬───────────────────┘
           │                             │
           ▼                             ▼
   JSON to stdout              Async file I/O
   (streaming logs)            (date-partitioned storage)
```

### Data Flow

1. **Request Initiation**: Application uses `track_llm_request()` context manager
2. **Timing**: Start time captured automatically
3. **LLM Call**: Application makes LLM request within context
4. **Response Capture**: Response stored in tracking dictionary
5. **Latency Calculation**: Automatic timing on context exit
6. **Parallel Processing**:
   - Structured log entry created and written to stdout (synchronous)
   - Prompt/response content stored to file system (asynchronous)
7. **Error Handling**: Exceptions caught, logged with ERROR level

## Core Components

### 1. LLMOpsLogEntry (src/model/llmops_log.py)

**Purpose**: Define the structured format for LLM operation logs

**Key Features**:
- Pydantic model for type safety and validation
- Auto-generated ISO 8601 timestamps
- Validation constraints (e.g., temperature 0.0-2.0)
- JSON serialization with exclude_none for clean output
- No prompt content - only metadata

**Design Rationale**:
- Structured format enables easy parsing by log aggregation tools (Datadog, BigQuery, Elasticsearch)
- Consistent schema across all LLM operations
- Small size suitable for high-volume streaming
- Reference to prompt content via prompt_id instead of embedding

**Fields**:
```python
timestamp: str              # ISO 8601 format, auto-generated
request_id: str            # Unique identifier for tracing
prompt_id: str             # Reference to stored prompt
user_id: Optional[str]     # User tracking for audit
model: str                 # LLM model name
temperature: float         # Generation parameter (0.0-2.0)
latency_ms: Optional[float] # Response time
status_code: Optional[int]  # HTTP-like status
error_message: Optional[str] # Error details
level: LogLevel            # INFO/DEBUG/ERROR/WARNING
metadata: dict[str, Any]   # Extensible custom data
```

### 2. PromptStorage (src/service/prompt_storage.py)

**Purpose**: Manage separate storage of prompt and response content

**Architecture**:
```
PromptStorage (ABC)
    │
    ├── save_prompt(prompt_data, mask_sensitive) -> str
    └── retrieve_prompt(prompt_id) -> Optional[PromptData]
         │
         └── LocalFilePromptStorage
             ├── Date-partitioned directory structure
             ├── Async file I/O
             └── Sensitive data masking
```

**Key Features**:

1. **Date-based Partitioning**:
   - Structure: `prompt_storage/YYYY/MM/DD/prompt_id.json`
   - Benefits: Efficient searches, easy data retention policies
   - Example: `prompt_storage/2024/03/15/a1b2c3d4-...-7890.json`

2. **Sensitive Data Masking**:
   - Regex-based PII detection (SSN, email, credit card)
   - Applied to both prompt and response content
   - Recursive masking for nested structures (lists, dicts)
   - Patterns:
     - SSN: `\d{3}-\d{2}-\d{4}` -> `***-**-****`
     - Email: `user@domain.com` -> `***@***.***`
     - Credit Card: `4111-1111-1111-1111` -> `****-****-****-****`

3. **Async Operations**:
   - Non-blocking I/O to avoid request latency impact
   - Fire-and-forget pattern for saves
   - Error handling with logging (doesn't fail main request)

4. **Extensible Design**:
   - Abstract base class for multiple backends
   - Future implementations: S3Storage, GCSStorage, DatabaseStorage
   - Factory pattern for easy switching

**PromptData Model** (src/model/prompt_data.py):
```python
prompt_id: str              # Unique identifier
prompt_content: Any         # String or list of messages
response_content: Optional[Any] # LLM response
created_at: str            # ISO 8601 timestamp
metadata: dict[str, Any]   # Additional context
```

### 3. LLMOpsLogger (src/service/llmops_logger.py)

**Purpose**: Main interface for LLM operation logging

**Key Methods**:

1. **track_llm_request()** - Context Manager Pattern
   ```python
   async with llmops_logger.track_llm_request(
       model="gpt-4o-mini",
       temperature=1.0,
       prompt_content=prompt,
       user_id="user123"
   ) as tracking:
       response = await llm_client.generate(...)
       tracking["response"] = response
   ```

   **Benefits**:
   - Automatic timing (no manual start/stop)
   - Automatic error handling
   - Guaranteed cleanup (finally block)
   - Clean API - no manual logging calls

   **Implementation Details**:
   - Generates request_id and prompt_id if not provided
   - Captures start time on entry
   - Yields tracking dict for response storage
   - Calculates latency on exit (success or failure)
   - Sets status_code: 200 for success, 500 for exceptions
   - Logs with appropriate level (INFO or ERROR)

2. **log_llm_request()** - Manual Logging
   ```python
   await llmops_logger.log_llm_request(
       request_id=request_id,
       prompt_id=prompt_id,
       model="gpt-4",
       temperature=0.7,
       prompt_content=prompt,
       response_content=response,
       latency_ms=1234.56
   )
   ```

   **Use Cases**:
   - When not using context manager
   - Batch logging scenarios
   - Custom timing logic

3. **retrieve_prompt()** - Prompt Retrieval
   ```python
   prompt_data = await llmops_logger.retrieve_prompt(prompt_id)
   ```

   **Use Cases**:
   - Debugging specific requests
   - Reproducing issues
   - Audit and compliance reviews

**Configuration**:
- `enable_masking`: Toggle sensitive data masking (default: True)
- `prompt_storage`: Inject custom storage backend
- `logger`: Standard Python logger for output

### 4. Factory Function (create_llmops_logger)

**Purpose**: Simplified logger creation with sensible defaults

```python
from src.service.llmops_logger import create_llmops_logger
from src.model.llmops_log import StorageType
import logging

llmops_logger = create_llmops_logger(
    logger_name="llmops",
    log_level=logging.INFO,
    storage_type=StorageType.LOCAL,
    enable_masking=True
)
```

**Features**:
- Creates and configures standard Python logger
- Sets up StreamHandler with simple formatter (logs are already JSON)
- Initializes prompt storage via factory (using `get_prompt_storage()`)
- Supports StorageType enum (LOCAL, S3, etc.)
- Returns ready-to-use LLMOpsLogger instance

## Implementation Patterns

### Pattern 1: Context Manager Usage (Recommended)

```python
from src.service.llmops_logger import create_llmops_logger
from src.client.llm_client import openai_client
from src.model.model import CharacterResponse
from src.prompt.prompt import make_prompt

llmops_logger = create_llmops_logger()

async def generate_character(user_id: str):
    prompt = make_prompt()

    async with llmops_logger.track_llm_request(
        model="gpt-4o-mini",
        temperature=1.0,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"feature": "character_generation", "provider": "openai"}
    ) as tracking:
        response = await openai_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=prompt,
            response_format=CharacterResponse,
            temperature=1.0
        )
        parsed_response = response.choices[0].message.parsed
        tracking["response"] = parsed_response.model_dump() if parsed_response else None
        return parsed_response
```

**Why This Pattern?**
- No manual timing code
- Automatic error handling and logging
- Clean separation of concerns
- Guaranteed log entry even on exceptions

### Pattern 2: Manual Logging

```python
import time
from uuid import uuid4
from src.service.llmops_logger import create_llmops_logger
from src.model.llmops_log import LogLevel
from src.client.llm_client import openai_client

llmops_logger = create_llmops_logger()

start_time = time.time()
try:
    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=prompt,
        response_format=CharacterResponse,
        temperature=0.7
    )
    latency_ms = (time.time() - start_time) * 1000

    parsed_response = response.choices[0].message.parsed

    await llmops_logger.log_llm_request(
        request_id=str(uuid4()),
        prompt_id=str(uuid4()),
        model="gpt-4o-mini",
        temperature=0.7,
        prompt_content=prompt,
        response_content=parsed_response.model_dump() if parsed_response else None,
        latency_ms=latency_ms,
        status_code=200,
        level=LogLevel.INFO
    )
except Exception as e:
    latency_ms = (time.time() - start_time) * 1000
    await llmops_logger.log_llm_request(
        request_id=str(uuid4()),
        prompt_id=str(uuid4()),
        model="gpt-4o-mini",
        temperature=0.7,
        prompt_content=prompt,
        latency_ms=latency_ms,
        status_code=500,
        error_message=str(e),
        level=LogLevel.ERROR
    )
```

**Use Cases**:
- When you need custom timing logic
- Batch processing scenarios
- Integration with existing error handling

### Pattern 3: Custom Storage Backend

```python
from src.service.prompt_storage import PromptStorage
from src.model.prompt_data import PromptData

class S3PromptStorage(PromptStorage):
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)

    async def save_prompt(self, prompt_data: PromptData, mask_sensitive: bool = True) -> str:
        if mask_sensitive:
            prompt_data.mask_sensitive_data()

        key = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{prompt_data.prompt_id}.json"
        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.bucket_name,
            Key=key,
            Body=json.dumps(prompt_data.model_dump()),
            ContentType='application/json'
        )
        return f"s3://{self.bucket_name}/{key}"

    async def retrieve_prompt(self, prompt_id: str) -> Optional[PromptData]:
        # Implementation with S3 search logic
        pass

# Usage
from src.service.llmops_logger import LLMOpsLogger
import logging

logger = logging.getLogger("llmops")
llmops_logger = LLMOpsLogger(
    logger=logger,
    prompt_storage=S3PromptStorage(bucket_name="my-llm-prompts")
)
```

## Testing Strategy

### Test Coverage

1. **Unit Tests** (tests/test_llmops_log.py - 37 tests):
   - Model validation (temperature range, required fields)
   - JSON serialization
   - Timestamp generation
   - Field exclusion (exclude_none)
   - StorageType and LogLevel enum validation

2. **Unit Tests** (tests/test_prompt_storage.py - 39 tests):
   - Date partitioning logic
   - Sensitive data masking (SSN, email, credit card)
   - Recursive masking (nested structures)
   - File I/O operations
   - Async save/retrieve operations
   - Storage factory function

3. **Unit Tests** (tests/test_llmops_logger.py - 35 tests):
   - Context manager timing accuracy
   - Error handling and status codes
   - Request/prompt ID generation
   - Async storage task creation
   - Log level routing
   - Integration tests with actual LLM providers

**Total: 111 tests** covering all core functionality

### Test Fixtures (conftest.py)

```python
@pytest.fixture
def temp_storage_dir(tmp_path):
    """Provide isolated temporary storage for tests"""

@pytest.fixture
def mock_logger():
    """Mock logger for capturing log calls"""

@pytest.fixture
def llmops_logger(mock_logger, temp_storage_dir):
    """Configured LLMOpsLogger for testing"""
```

### Key Test Scenarios

1. **Masking Validation**:
   - SSN patterns masked correctly
   - Email addresses masked
   - Credit card numbers masked
   - Nested structures handled
   - Non-sensitive data unchanged

2. **Timing Accuracy**:
   - Latency measurement within acceptable margin
   - Async operations don't block
   - Context manager cleanup on exceptions

3. **Storage Integrity**:
   - Date partitioning creates correct paths
   - Files saved with correct content
   - Retrieval finds correct prompts
   - Missing prompts return None

## Configuration

### Environment Variables

```bash
# LLM Provider API Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Optional: Custom storage location
PROMPT_STORAGE_DIR=./prompt_storage

# Optional: Logging level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Project Configuration (pyproject.toml)

```toml
[project]
name = "section-2"
version = "0.1.0"
requires-python = ">=3.13.2"

dependencies = [
    "pydantic>=2.0.0",      # Data validation and models
    "python-dotenv>=1.0.0",  # Environment variable management
    "openai>=1.0.0",         # OpenAI API client
    "google-genai>=1.0.0",   # Google Gemini API client
    "click>=8.0.0",          # CLI interface
]

[dependency-groups]
dev = [
    "pytest>=8.4.2",         # Testing framework
    "pytest-asyncio>=1.2.0", # Async test support
    "pytest-mock>=3.15.1",   # Mocking utilities
]
```

### Pytest Configuration (pytest.ini)

```ini
[pytest]
asyncio_mode = auto          # Automatic async test detection
python_files = test_*.py
python_functions = test_*
addopts = -v --strict-markers --tb=short --disable-warnings
testpaths = tests
minversion = 3.13
```

## Usage Examples

### Basic Usage

```bash
# Install dependencies
uv sync

# Run with OpenAI (model required)
uv run python -m src.main --llm-provider openai --model gpt-4o-mini --user-id user123

# Run with Gemini (model required)
uv run python -m src.main --llm-provider gemini --model gemini-2.0-flash-exp --user-id user456

# Specify output directory
uv run python -m src.main --llm-provider gemini --model gemini-2.0-flash-exp --output-directory ./results

# Specify storage type
uv run python -m src.main --llm-provider openai --model gpt-4o-mini --storage-type local

# Short form options
uv run python -m src.main -lp gemini -m gemini-2.0-flash-exp -u user123 -od ./outputs
```

### Log Output Examples

**Structured Log (stdout)**:
```json
{
  "timestamp": "2024-03-15T10:30:45.123456+00:00",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "prompt_id": "p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890",
  "user_id": "user123",
  "model": "gpt-4o-mini",
  "temperature": 1.0,
  "latency_ms": 1234.56,
  "status_code": 200,
  "level": "INFO",
  "metadata": {
    "provider": "openai",
    "response_format": "CharacterResponse"
  }
}
```

**Stored Prompt (prompt_storage/2024/03/15/p1q2r3s4...json)**:
```json
{
  "prompt_id": "p1q2r3s4-t5u6-v7w8-xyz9-ab1234567890",
  "prompt_content": [
    {
      "role": "system",
      "content": "You are a creative character generator..."
    },
    {
      "role": "user",
      "content": "Generate a unique fictional character..."
    }
  ],
  "response_content": {
    "first_name": "Akira",
    "last_name": "Tanaka",
    "gender": "male",
    "age": 28,
    "personalities": ["creative", "analytical"]
  },
  "created_at": "2024-03-15T10:30:45.123456",
  "metadata": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

## Benefits and Use Cases

### 1. Enhanced Observability

**Problem**: Traditional logs don't provide structured data for analysis
**Solution**: JSON logs with consistent schema

**Use Cases**:
- Send logs to Datadog/BigQuery/Elasticsearch for analysis
- Create dashboards for model performance
- Track metrics over time (latency trends, error rates)
- Compare different models or configurations

**Example Query** (SQL-based log aggregation):
```sql
SELECT model, AVG(latency_ms) as avg_latency, COUNT(*) as total_requests
FROM llmops_logs
WHERE timestamp >= NOW() - INTERVAL '24 hours'
  AND status_code = 200
GROUP BY model
ORDER BY avg_latency DESC
```

### 2. Improved Debugging

**Problem**: Hard to reproduce issues without original prompts
**Solution**: Complete request tracking with stored prompts

**Use Cases**:
- Retrieve exact prompt and response for any request_id
- Reproduce issues locally
- Analyze failed requests
- Compare successful vs failed patterns

**Example**:
```python
from src.service.llmops_logger import create_llmops_logger

llmops_logger = create_llmops_logger()

# User reports issue with request "a1b2c3d4-..."
prompt_data = await llmops_logger.retrieve_prompt("p1q2r3s4-...")

if prompt_data:
    # Now you have:
    # - Original prompt content: prompt_data.prompt_content
    # - Model response: prompt_data.response_content
    # - Metadata: prompt_data.metadata
    # - Full context for debugging
    print(f"Prompt: {prompt_data.prompt_content}")
    print(f"Response: {prompt_data.response_content}")
```

### 3. Security and Compliance

**Problem**: Sensitive data in logs poses privacy/compliance risks
**Solution**: Automatic PII masking + separate storage

**Benefits**:
- PII automatically masked before storage
- Separate storage enables access control
- Audit trail with user_id and timestamps
- Compliance with data retention policies (TTL on storage)

**Example**:
```python
from src.model.prompt_data import PromptData

# Input: "Contact me at john.doe@example.com or 123-45-6789"
prompt_data = PromptData(
    prompt_id="test",
    prompt_content="Contact me at john.doe@example.com or 123-45-6789"
)
prompt_data.mask_sensitive_data()

# Stored: "Contact me at ***@***.*** or ***-**-****"
print(prompt_data.prompt_content)  # Output: "Contact me at ***@***.*** or ***-**-****"
```

### 4. Performance Monitoring

**Problem**: LLM latency varies widely, hard to track
**Solution**: Automatic latency tracking per request

**Use Cases**:
- Identify slow models or configurations
- Track P50, P95, P99 latency percentiles
- Detect performance degradation
- Optimize temperature settings for speed

**Example Analysis**:
```sql
SELECT
  model,
  temperature,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency
FROM llmops_logs
WHERE status_code = 200
GROUP BY model, temperature
```

### 5. Quality Analysis and A/B Testing

**Problem**: Hard to evaluate prompt or model changes
**Solution**: Metadata field for experiment tracking

**Use Cases**:
- Compare prompt variations (A/B testing)
- Track model version changes
- Measure impact of temperature adjustments
- User cohort analysis

**Example**:
```python
from src.service.llmops_logger import create_llmops_logger
from src.client.llm_client import openai_client
from src.model.model import CharacterResponse

llmops_logger = create_llmops_logger()

# Variant A
async with llmops_logger.track_llm_request(
    model="gpt-4o-mini",
    temperature=0.7,
    prompt_content=prompt_v1,
    metadata={"experiment": "prompt_test", "variant": "A"}
) as tracking:
    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=prompt_v1,
        response_format=CharacterResponse,
        temperature=0.7
    )
    tracking["response"] = response.choices[0].message.parsed.model_dump()

# Variant B
async with llmops_logger.track_llm_request(
    model="gpt-4o-mini",
    temperature=0.7,
    prompt_content=prompt_v2,
    metadata={"experiment": "prompt_test", "variant": "B"}
) as tracking:
    response = await openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=prompt_v2,
        response_format=CharacterResponse,
        temperature=0.7
    )
    tracking["response"] = response.choices[0].message.parsed.model_dump()

# Later: Analyze which variant performed better using log aggregation
```

## Trade-offs and Considerations

### Benefits

1. **Complete Traceability**: Every LLM request tracked end-to-end
2. **Debugging Ease**: Stored prompts enable issue reproduction
3. **Performance Insights**: Automatic latency tracking and analysis
4. **Security**: Separate storage with PII masking
5. **Flexibility**: Extensible storage backends (local, S3, GCS)
6. **Non-blocking**: Async storage doesn't impact request latency
7. **Standards-compliant**: JSON logs work with any aggregation tool

### Trade-offs

1. **Storage Costs**:
   - Long prompts/responses accumulate quickly
   - Each request creates a file
   - Mitigation: TTL policies, compression, cloud storage tiers

2. **System Complexity**:
   - Additional components to maintain
   - Two storage systems (logs + prompts)
   - Mitigation: Good documentation, abstractions, factory patterns

3. **Potential Log Loss**:
   - Async operations may lose data on system crash
   - Fire-and-forget pattern doesn't guarantee delivery
   - Mitigation: Message queue (Kafka), retry logic, health checks

4. **PII Detection Limitations**:
   - Regex-based masking misses context-dependent PII
   - May mask too much or too little
   - Mitigation: NER models, custom masking rules, human review

5. **Retrieval Performance**:
   - Linear search through date directories
   - Slow for large prompt counts
   - Mitigation: Index database, ElasticSearch, metadata cache

6. **Testing Complexity**:
   - Async code requires special test setup
   - Mock coordination for multiple components
   - Mitigation: Fixtures, test utilities, good examples

### Mitigation Strategies

1. **Storage Management**:
   ```python
   # Implement TTL policy
   def cleanup_old_prompts(retention_days=30):
       cutoff = datetime.now() - timedelta(days=retention_days)
       for prompt_file in find_prompts_before(cutoff):
           prompt_file.unlink()
   ```

2. **Reliable Delivery** (Future Enhancement):
   ```python
   class KafkaPromptStorage(PromptStorage):
       async def save_prompt(self, prompt_data, mask_sensitive=True):
           # Publish to Kafka topic
           # Consumer stores to S3/GCS
           # Guarantees delivery even on system failure
   ```

3. **Advanced PII Detection** (Future Enhancement):
   ```python
   from transformers import pipeline

   class NERPromptMasker:
       def __init__(self):
           self.ner = pipeline("ner", model="bert-base-NER")

       def mask_entities(self, text):
           entities = self.ner(text)
           # Mask PERSON, ORG, LOC, etc.
   ```

4. **Indexed Retrieval** (Future Enhancement):
   ```python
   class IndexedPromptStorage(PromptStorage):
       def __init__(self, db_connection):
           self.db = db_connection
           # Store metadata in database for fast search
           # Store content in S3
   ```

## Directory Structure

```
section_2/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Application entry point with CLI
│   ├── config.py                # Configuration management (API keys)
│   ├── logger.py                # Basic logger setup
│   ├── client/
│   │   ├── __init__.py
│   │   └── llm_client.py        # LLM provider abstraction (OpenAI, Gemini)
│   ├── model/
│   │   ├── __init__.py
│   │   ├── model.py             # CharacterResponse data model
│   │   ├── llmops_log.py        # Structured log entry model + enums
│   │   └── prompt_data.py       # PromptData model with masking
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── prompt.py            # Prompt generation logic
│   └── service/
│       ├── __init__.py
│       ├── llmops_logger.py     # Main logging interface
│       ├── prompt_storage.py    # Prompt storage implementations
│       └── request_llm.py       # LLM request functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures (using tempfile)
│   ├── test_llmops_log.py       # Log entry tests (37 tests)
│   ├── test_llmops_logger.py    # Logger interface tests (35 tests)
│   └── test_prompt_storage.py   # Storage implementation tests (39 tests)
├── prompt_storage/              # Stored prompts (gitignored)
│   └── YYYY/MM/DD/*.json        # Date-partitioned structure
├── outputs/                      # Generated character files
├── pyproject.toml               # Project configuration
├── pytest.ini                   # Test configuration (asyncio_mode=auto)
├── Makefile                     # Build and test commands
├── README.md                    # User documentation (Japanese)
└── CLAUDE.md                    # This file - design specification
```

## Core Application Integration

### Request LLM Functions (src/service/request_llm.py)

This module provides the actual integration between the LLMOps logger and LLM providers:

**OpenAI Integration**:
```python
async def request_openai(
    model: OpenAIModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user",
) -> CharacterResponse:
    """Request character generation from OpenAI with structured logging."""
    prompt = make_prompt()
    temperature = 1.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "openai", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await openai_client.beta.chat.completions.parse(
            model=model,
            messages=prompt,
            response_format=CharacterResponse,
            temperature=temperature,
        )
        parsed_response = result.choices[0].message.parsed
        tracking["response"] = parsed_response.model_dump() if parsed_response else None
        return parsed_response
```

**Gemini Integration**:
```python
async def request_gemini(
    model: GeminiModel,
    llmops_logger: LLMOpsLogger,
    user_id: str = "default_user"
) -> CharacterResponse:
    """Request character generation from Gemini with structured logging."""
    prompt = make_prompt()
    temperature = 2.0

    async with llmops_logger.track_llm_request(
        model=model,
        temperature=temperature,
        prompt_content=prompt,
        user_id=user_id,
        metadata={"provider": "gemini", "model": model, "response_format": "CharacterResponse"},
    ) as tracking:
        result = await google_genai_client.aio.models.generate_content(
            model=model,
            contents=prompt[-1]["content"],
            config=GenerateContentConfig(
                system_instruction=prompt[0]["content"],
                response_mime_type="application/json",
                response_schema=CharacterResponse,
                temperature=temperature,
            ),
        )
        tracking["response"] = result.parsed.model_dump() if result.parsed else None
        return result.parsed
```

These functions demonstrate the recommended pattern for integrating LLMOps logging with actual LLM API calls.

## Future Enhancements

### Planned Features

1. **Cloud Storage Backends**
   - S3PromptStorage implementation
   - GCSPromptStorage implementation
   - Azure Blob Storage support
   - Configuration-based backend selection via StorageType enum

2. **Reliable Message Delivery**
   - Kafka integration for prompt storage
   - Dead letter queue for failed storage
   - Retry logic with exponential backoff
   - Health checks and monitoring

3. **Advanced PII Detection**
   - NER model integration (spaCy, Transformers)
   - Context-aware entity masking
   - Custom entity types
   - Configurable masking strategies

4. **Cost Tracking**
   - Token usage logging
   - Cost calculation per request
   - Budget alerts and limits
   - Cost attribution by user/team

5. **Performance Optimization**
   - Indexed prompt storage (database metadata)
   - Batch storage operations
   - Log compression
   - Sampling for high-volume scenarios

6. **Visualization and Analytics**
   - Grafana dashboard templates
   - Pre-built SQL queries
   - Jupyter notebook examples
   - Real-time monitoring UI

7. **Enhanced Testing**
   - Load testing suite
   - Chaos engineering scenarios
   - Performance benchmarks
   - Integration test examples

### Extension Points

The system is designed for extension through:

1. **Custom Storage Backends**: Implement `PromptStorage` ABC
2. **Custom Masking Rules**: Extend `PromptData.mask_sensitive_data()`
3. **Custom Metadata**: Use `metadata` field in log entries
4. **Custom Log Levels**: Extend `LogLevel` enum
5. **Custom Serialization**: Override `to_json_string()` method

## Best Practices

### Do's

1. **Always use context managers** for automatic error handling and timing
2. **Include meaningful metadata** for future analysis and debugging
3. **Set appropriate user_id** for audit trails and user tracking
4. **Enable masking in production** to protect sensitive data
5. **Monitor storage costs** and implement TTL policies
6. **Use structured logging in production** (LOG_LEVEL=INFO)
7. **Test masking rules** with your specific data patterns
8. **Index prompt storage** for production-scale retrieval

### Don'ts

1. **Don't log PII without masking** - compliance risk
2. **Don't use sync I/O** for prompt storage - blocks requests
3. **Don't skip error handling** in context managers
4. **Don't store credentials** in metadata
5. **Don't ignore storage failures** - monitor error logs
6. **Don't retrieve prompts synchronously** in request path
7. **Don't use DEBUG level in production** - too verbose
8. **Don't hard-code request/prompt IDs** - use auto-generation

## Monitoring and Alerts

### Key Metrics to Track

1. **Latency Metrics**:
   - Average latency by model
   - P95/P99 latency percentiles
   - Latency trends over time

2. **Error Rates**:
   - Error count and percentage by model
   - Error distribution by user
   - Common error messages

3. **Storage Metrics**:
   - Prompt storage failures
   - Storage disk usage
   - Retrieval times

4. **Usage Metrics**:
   - Requests per user
   - Model distribution
   - Temperature distribution

### Sample Alert Rules

```yaml
# High error rate
- alert: HighLLMErrorRate
  expr: sum(rate(llmops_logs{level="ERROR"}[5m])) / sum(rate(llmops_logs[5m])) > 0.05

# High latency
- alert: HighLLMLatency
  expr: histogram_quantile(0.95, llmops_logs_latency_ms) > 5000

# Storage failures
- alert: PromptStorageFailures
  expr: rate(prompt_storage_errors[5m]) > 0.1
```

## References

- **Design Pattern**: Structured Logging for Microservices
- **PII Masking**: GDPR and CCPA compliance patterns
- **Async Processing**: Python asyncio best practices
- **Log Aggregation**: ELK Stack, Datadog, BigQuery integration
- **Chapter Reference**: Chapter 2, Section 2 - LLMOps Structured Logging

## Changelog

- **v0.1.0** (Initial): Core structured logging implementation with local file storage
  - LLMOpsLogEntry model (src/model/llmops_log.py)
  - PromptData model with PII masking (src/model/prompt_data.py)
  - LocalFilePromptStorage with date partitioning (src/service/prompt_storage.py)
  - LLMOpsLogger with context manager (src/service/llmops_logger.py)
  - StorageType and LogLevel enums
  - Automatic latency tracking
  - PII masking (regex-based)
  - Request functions for OpenAI and Gemini (src/service/request_llm.py)
  - CLI interface with multiple options (--llm-provider, --model, --storage-type, etc.)
  - Comprehensive test suite (111 tests total)
  - Makefile for build and test automation

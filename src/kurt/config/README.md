# Hierarchical Configuration System

Kurt supports a hierarchical configuration system for LLM and embedding models, allowing you to set defaults globally and override them at the module or step level.

## Configuration Hierarchy

Resolution order (first match wins):

1. **Step-specific**: `<MODULE>.<STEP>.<CATEGORY>_<PARAM>`
2. **Module-level**: `<MODULE>.<CATEGORY>_<PARAM>`
3. **Global**: `<CATEGORY>_<PARAM>`
4. **Legacy keys** (backwards compatible): `INDEXING_LLM_MODEL`, `ANSWER_LLM_MODEL`

Where:
- `MODULE` = `INDEXING`, `ANSWER`, `RETRIEVAL`
- `STEP` = step name like `SECTION_EXTRACTIONS`, `ENTITY_CLUSTERING`
- `CATEGORY` = `LLM` or `EMBEDDING`
- `PARAM` = `MODEL`, `API_BASE`, `API_KEY`, `TEMPERATURE`, `MAX_TOKENS`

## Quick Examples

### Cloud Provider (Default)

```ini
# kurt.config

# Use OpenAI for everything
LLM_MODEL="openai/gpt-4o-mini"
EMBEDDING_MODEL="openai/text-embedding-3-small"
```

### Local LLM Server

```ini
# kurt.config

# Point all LLM calls to a local server
LLM_MODEL="mistral-7b"
LLM_API_BASE="http://localhost:8080/v1/"
LLM_API_KEY="not_needed"

# Local embeddings too
EMBEDDING_MODEL="nomic-embed-text"
EMBEDDING_API_BASE="http://localhost:8080/v1/"
```

### Module-Specific Overrides

```ini
# kurt.config

# Global defaults
LLM_MODEL="openai/gpt-4o-mini"
EMBEDDING_MODEL="openai/text-embedding-3-small"

# Use a smarter model for answering questions
ANSWER.LLM_MODEL="openai/gpt-4o"

# Use a local model for indexing (cheaper/faster)
INDEXING.LLM_MODEL="mistral-7b"
INDEXING.LLM_API_BASE="http://localhost:8080/v1/"
```

### Step-Level Overrides

```ini
# kurt.config

# Global defaults
LLM_MODEL="openai/gpt-4o-mini"

# Most indexing uses gpt-4o-mini, but section extraction needs a smarter model
INDEXING.SECTION_EXTRACTIONS.LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"

# Entity clustering uses local embeddings
INDEXING.ENTITY_CLUSTERING.EMBEDDING_MODEL="bge-large"
INDEXING.ENTITY_CLUSTERING.EMBEDDING_API_BASE="http://localhost:8080/v1/"
```

## Full Configuration Reference

### LLM Settings

| Key Pattern | Example | Description |
|-------------|---------|-------------|
| `LLM_MODEL` | `"openai/gpt-4o-mini"` | Global LLM model |
| `LLM_API_BASE` | `"http://localhost:8080/v1/"` | Global API endpoint |
| `LLM_API_KEY` | `"sk-..."` or `"not_needed"` | API key (optional for local) |
| `LLM_TEMPERATURE` | `0.7` | Temperature (optional) |
| `LLM_MAX_TOKENS` | `4000` | Max tokens (optional) |
| `<MODULE>.LLM_MODEL` | `INDEXING.LLM_MODEL` | Module-level model |
| `<MODULE>.LLM_API_BASE` | `ANSWER.LLM_API_BASE` | Module-level endpoint |
| `<MODULE>.<STEP>.LLM_MODEL` | `INDEXING.SECTION_EXTRACTIONS.LLM_MODEL` | Step-level model |

### Embedding Settings

| Key Pattern | Example | Description |
|-------------|---------|-------------|
| `EMBEDDING_MODEL` | `"openai/text-embedding-3-small"` | Global embedding model |
| `EMBEDDING_API_BASE` | `"http://localhost:8080/v1/"` | Global embedding endpoint |
| `EMBEDDING_API_KEY` | `"sk-..."` | Embedding API key |
| `<MODULE>.EMBEDDING_MODEL` | `INDEXING.EMBEDDING_MODEL` | Module-level embedding |
| `<MODULE>.<STEP>.EMBEDDING_MODEL` | `INDEXING.ENTITY_CLUSTERING.EMBEDDING_MODEL` | Step-level embedding |

### Legacy Keys (Backwards Compatible)

These keys still work for backwards compatibility:

| Legacy Key | Equivalent New Key |
|------------|-------------------|
| `INDEXING_LLM_MODEL` | `INDEXING.LLM_MODEL` or `LLM_MODEL` |
| `ANSWER_LLM_MODEL` | `ANSWER.LLM_MODEL` or `LLM_MODEL` |

## API Implementation

### Using `resolve_model_settings()`

The `resolve_model_settings()` function provides hierarchical config resolution:

```python
from kurt.config.base import resolve_model_settings

# Get LLM settings for indexing module
settings = resolve_model_settings("LLM", module_name="INDEXING")
print(settings.model)     # e.g., "mistral-7b"
print(settings.api_base)  # e.g., "http://localhost:8080/v1/"

# Get embedding settings for a specific step
settings = resolve_model_settings(
    "EMBEDDING",
    module_name="INDEXING",
    step_name="ENTITY_CLUSTERING"
)

# Use with step config override
settings = resolve_model_settings(
    "LLM",
    module_name="INDEXING",
    step_config=my_step_config  # Has llm_model attribute
)
```

### ModelSettings Dataclass

```python
@dataclass
class ModelSettings:
    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
```

### Using in DSPy

```python
from kurt.core.dspy_helpers import get_dspy_lm
from kurt.utils.embeddings import generate_embeddings

# LLM - auto-detects module from call stack
lm = get_dspy_lm()

# LLM - with explicit step config
lm = get_dspy_lm(config=my_step_config)

# Embeddings - with module context
embeddings = generate_embeddings(
    ["text1", "text2"],
    module_name="INDEXING",
    step_name="ENTITY_CLUSTERING"
)
```

## Naming Conventions

- **Dots (`.`)**: Separate hierarchy levels (module, step, param)
- **Underscores (`_`)**: Separate words within a level
- **ALL_CAPS**: Consistent with existing config style

Examples:
- `INDEXING.SECTION_EXTRACTIONS.LLM_MODEL` - module.step.category_param
- `ANSWER.LLM_API_BASE` - module.category_param
- `LLM_MODEL` - global flat key

## Common Configurations

### Ollama

```ini
LLM_MODEL="mistral"
LLM_API_BASE="http://localhost:11434/v1/"
LLM_API_KEY="not_needed"

EMBEDDING_MODEL="nomic-embed-text"
EMBEDDING_API_BASE="http://localhost:11434/v1/"
```

### LM Studio

```ini
LLM_MODEL="local-model"
LLM_API_BASE="http://localhost:1234/v1/"
LLM_API_KEY="not_needed"
```

### vLLM

```ini
LLM_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
LLM_API_BASE="http://localhost:8000/v1/"
LLM_API_KEY="not_needed"
```

### llama.cpp Server

```ini
LLM_MODEL="local"
LLM_API_BASE="http://localhost:8080/v1/"
LLM_API_KEY="not_needed"
```

### Mixed: Local Indexing + Cloud Answering

```ini
# Use local model for indexing (cheaper)
INDEXING.LLM_MODEL="mistral-7b"
INDEXING.LLM_API_BASE="http://localhost:8080/v1/"

# Use cloud for answering (smarter)
ANSWER.LLM_MODEL="openai/gpt-4o"

# Use OpenAI for embeddings
EMBEDDING_MODEL="openai/text-embedding-3-small"
```

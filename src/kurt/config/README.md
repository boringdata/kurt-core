# Module-Level Configuration Design

## Problem

Currently, all configuration is flat in `kurt.config`:
```
INDEXING_LLM_MODEL="anthropic/claude-3-haiku-20240307"
MAX_CONCURRENT_INDEXING=50
```

This doesn't scale well when:
1. Different pipeline steps need different settings (e.g., different LLM models for extraction vs resolution)
2. Modules (indexing, fetch) have step-specific configs
3. We want to expose tunable parameters without polluting the global config

## Proposed Design

### Config Structure

Use dot notation for hierarchy: `<MODULE>.<STEP>.<PARAM>`

```ini
# kurt.config

# === Global defaults (used when step-specific not set) ===
INDEXING_LLM_MODEL="anthropic/claude-3-haiku-20240307"
MAX_CONCURRENT_INDEXING=50

# === Module-specific overrides ===

# Indexing module - step-specific configs
INDEXING.SECTION_EXTRACTIONS.LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"
INDEXING.SECTION_EXTRACTIONS.MAX_CONCURRENT=20
INDEXING.SECTION_EXTRACTIONS.BATCH_SIZE=10

INDEXING.ENTITY_CLUSTERING.EPS=0.25
INDEXING.ENTITY_CLUSTERING.MIN_SAMPLES=2

INDEXING.ENTITY_RESOLUTION.LLM_MODEL="anthropic/claude-3-haiku-20240307"
INDEXING.ENTITY_RESOLUTION.MAX_CONCURRENT=30

INDEXING.CLAIM_CLUSTERING.EPS=0.3

# Fetch module configs
FETCH.FIRECRAWL.API_KEY="fc-xxx"
FETCH.FIRECRAWL.TIMEOUT=30

FETCH.TRAFILATURA.INCLUDE_IMAGES=false
FETCH.TRAFILATURA.FAVOR_PRECISION=true
```

### Naming Convention

- **Dots (`.`)**: Separate hierarchy levels (module, step, param)
- **Underscores (`_`)**: Separate words within a level
- **ALL_CAPS**: Consistent with existing config style

Examples:
- `INDEXING.SECTION_EXTRACTIONS.LLM_MODEL` - module.step.param
- `INDEXING.ENTITY_CLUSTERING.MIN_SAMPLES` - multi-word param
- `FETCH.TRAFILATURA.FAVOR_PRECISION` - fetch module config

## Implementation

### 1. ModelConfig Schema (in each model file)

Each step declares its configurable parameters using `ModelConfig`:

```python
# step_extract_sections.py
from kurt.config import ModelConfig, ConfigParam

class SectionExtractionsConfig(ModelConfig):
    """Configuration for section_extractions step."""

    llm_model: str = ConfigParam(
        fallback="INDEXING_LLM_MODEL",  # Falls back to global
        description="LLM model for extraction"
    )
    max_concurrent: int = ConfigParam(
        fallback="MAX_CONCURRENT_INDEXING",
        ge=1, le=100,
        description="Max concurrent LLM calls"
    )
    batch_size: int = ConfigParam(
        default=50,
        ge=1, le=200,
        description="Batch size for DSPy calls"
    )


@model(
    name="indexing.section_extractions",
    config_schema=SectionExtractionsConfig,  # <-- NEW
    ...
)
def section_extractions(sources, writer, config: SectionExtractionsConfig, **kwargs):
    # Use config.llm_model, config.batch_size, etc.
    ...
```

The config key is derived from the model name:
- `indexing.section_extractions` → `INDEXING.SECTION_EXTRACTIONS.`
- Parameter `llm_model` → `LLM_MODEL`
- Full key: `INDEXING.SECTION_EXTRACTIONS.LLM_MODEL`

### 2. ConfigParam Class

```python
from kurt.config import ConfigParam

# Simple param with default
batch_size: int = ConfigParam(default=50)

# Param with fallback to global config
llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

# Param with validation constraints
eps: float = ConfigParam(default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon")
```

### 3. ModelConfig Base Class

```python
from kurt.config import ModelConfig, ConfigParam

class EntityClusteringConfig(ModelConfig):
    eps: float = ConfigParam(default=0.25, ge=0.0, le=1.0)
    min_samples: int = ConfigParam(default=2, ge=1)
    llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

# Load config for a specific model
config = EntityClusteringConfig.load("indexing.entity_clustering")
print(config.eps)  # 0.25 (default) or value from INDEXING.ENTITY_CLUSTERING.EPS
```

### 4. Integration with @model decorator

The decorator loads and injects the config automatically:

```python
# framework/decorator.py

def model(
    name: str,
    config_schema: Optional[Type[ModelConfig]] = None,
    ...
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Load step config if schema defined
            if config_schema:
                config = config_schema.load(name)
                kwargs['config'] = config

            return func(*args, **kwargs)

        return wrapper
    return decorator
```

### 5. Manual Usage (without decorator)

You can also use `get_step_config()` directly:

```python
from kurt.config import load_config, get_step_config

config = load_config()

# Get step-specific value with fallback
llm_model = get_step_config(
    config,
    module="INDEXING",
    step="SECTION_EXTRACTIONS",
    param="LLM_MODEL",
    fallback_key="INDEXING_LLM_MODEL",
    default="openai/gpt-4o-mini"
)
```

## Resolution Order

For each parameter, values are resolved in this order:

1. **Step-specific**: `INDEXING.SECTION_EXTRACTIONS.LLM_MODEL`
2. **Global fallback**: `INDEXING_LLM_MODEL` (specified via `ConfigParam.fallback`)
3. **Default**: Value from `ConfigParam.default`

## Benefits

1. **Step-specific tuning**: Each step can have different LLM models, concurrency limits
2. **Clear ownership**: Config params defined alongside the code that uses them
3. **Fallback chain**: Step-specific → Global → Default
4. **Type-safe**: Pydantic validation at load time
5. **Self-documenting**: Each step declares what's configurable
6. **Backwards compatible**: Global configs still work as fallbacks
7. **Readable hierarchy**: Dots clearly show module.step.param structure

## Complete Example

```python
# step_entity_clustering.py
from kurt.config import ModelConfig, ConfigParam

class EntityClusteringConfig(ModelConfig):
    """Configuration for entity clustering step."""

    eps: float = ConfigParam(
        default=0.25,
        ge=0.0, le=1.0,
        description="DBSCAN epsilon parameter for clustering"
    )
    min_samples: int = ConfigParam(
        default=2,
        ge=1,
        description="DBSCAN min_samples parameter"
    )
    llm_model: str = ConfigParam(
        fallback="INDEXING_LLM_MODEL",
        description="LLM for resolution decisions"
    )


@model(
    name="indexing.entity_clustering",
    db_model=EntityClusterRow,
    primary_key=["cluster_id"],
    config_schema=EntityClusteringConfig,
)
def entity_clustering(
    sources,
    writer,
    config: EntityClusteringConfig,
    **kwargs
):
    # Use typed config
    clustering = DBSCAN(eps=config.eps, min_samples=config.min_samples)

    # config.llm_model falls back to INDEXING_LLM_MODEL if not set
    llm = get_llm(config.llm_model)
    ...
```

## Migration Path

1. ✅ Add `ModelConfig` and `ConfigParam` classes to `kurt/config/model_config.py`
2. ✅ Add `get_step_config()` helper to `kurt/config/base.py`
3. ✅ Update config parser to support dot notation in keys
4. 🔲 Update `@model` decorator to accept `config_schema` parameter
5. 🔲 Gradually add `config_schema` to each step (backwards compatible)
6. Existing code continues working (uses global fallbacks)

## Design Decisions

1. **Naming**: `ModelConfig` (not `StepConfig`) to align with `@model` decorator terminology

2. **Location**: `ModelConfig` lives in `kurt.config` (not framework) so it can be used by any module

3. **Defaults location**: Step file owns defaults, global config is for overrides

4. **Validation**: Validate on load (fail fast)

5. **Backwards compatibility**: Global keys like `INDEXING_LLM_MODEL` still work as fallbacks

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

### Implementation

#### 1. Step Config Schema (in each model file)

Each step declares its configurable parameters:

```python
# step_extract_sections.py
from kurt.content.indexing_new.framework import StepConfig, ConfigParam

class SectionExtractionsConfig(StepConfig):
    """Configuration for section_extractions step."""

    llm_model: str = ConfigParam(
        default=None,  # Falls back to global INDEXING_LLM_MODEL
        description="LLM model for extraction"
    )
    max_concurrent: int = ConfigParam(
        default=None,  # Falls back to global MAX_CONCURRENT_INDEXING
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

#### 2. Config Resolution (in framework)

```python
# framework/config.py

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, get_type_hints
from kurt.config import load_config


class ConfigParam:
    """Metadata for step config parameters with fallback support."""

    def __init__(
        self,
        default: Any = None,
        fallback_global: Optional[str] = None,  # e.g., "INDEXING_LLM_MODEL"
        description: str = "",
        ge: Optional[float] = None,
        le: Optional[float] = None,
    ):
        self.default = default
        self.fallback_global = fallback_global
        self.description = description
        self.ge = ge
        self.le = le


class StepConfig(BaseModel):
    """Base class for step configuration."""

    # Store metadata about fields (set by subclasses)
    _config_params: Dict[str, ConfigParam] = {}

    @classmethod
    def load(cls, model_name: str) -> "StepConfig":
        """Load config for this step with fallback resolution.

        Resolution order:
        1. Step-specific: INDEXING.SECTION_EXTRACTIONS.LLM_MODEL
        2. Global fallback: INDEXING_LLM_MODEL
        3. Default from schema

        Args:
            model_name: Full model name like "indexing.section_extractions"
        """
        kurt_config = load_config()

        # Convert model name to config prefix: indexing.section_extractions -> INDEXING.SECTION_EXTRACTIONS
        prefix = model_name.upper().replace("_", ".").replace("..", ".")
        # Normalize: indexing.section_extractions -> INDEXING.SECTION_EXTRACTIONS
        parts = model_name.split(".")
        prefix = ".".join(p.upper() for p in parts)

        values = {}
        for field_name, param in cls._config_params.items():
            # Build step-specific key: INDEXING.SECTION_EXTRACTIONS.LLM_MODEL
            step_key = f"{prefix}.{field_name.upper()}"

            # Try step-specific first
            if hasattr(kurt_config, step_key):
                values[field_name] = getattr(kurt_config, step_key)
                continue

            # Try global fallback (e.g., INDEXING_LLM_MODEL)
            if param.fallback_global and hasattr(kurt_config, param.fallback_global):
                values[field_name] = getattr(kurt_config, param.fallback_global)
                continue

            # Use default from param
            if param.default is not None:
                values[field_name] = param.default

        return cls(**values)
```

#### 3. Integration with @model decorator

```python
# framework/decorator.py

def model(
    name: str,
    config_schema: Optional[Type[StepConfig]] = None,
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

### Config File Parsing

Extend `kurt/config/base.py` to handle dot notation:

```python
# In load_config()

# Parse hierarchical keys with dots
# INDEXING.SECTION_EXTRACTIONS.LLM_MODEL is stored as-is
# Config loader should support dots in key names
```

### Benefits

1. **Step-specific tuning**: Each step can have different LLM models, concurrency limits
2. **Clear ownership**: Config params defined alongside the code that uses them
3. **Fallback chain**: Step-specific -> Global -> Default
4. **Type-safe**: Pydantic validation at load time
5. **Self-documenting**: Each step declares what's configurable
6. **Backwards compatible**: Global configs still work as fallbacks
7. **Readable hierarchy**: Dots clearly show module.step.param structure

### Example Usage

```python
# In step_entity_clustering.py

class EntityClusteringConfig(StepConfig):
    _config_params = {
        "eps": ConfigParam(
            default=0.25,
            ge=0.0, le=1.0,
            description="DBSCAN epsilon parameter for clustering"
        ),
        "min_samples": ConfigParam(
            default=2,
            ge=1,
            description="DBSCAN min_samples parameter"
        ),
        "llm_model": ConfigParam(
            default=None,
            fallback_global="INDEXING_LLM_MODEL",
            description="LLM for resolution decisions"
        ),
    }

    eps: float = 0.25
    min_samples: int = 2
    llm_model: Optional[str] = None


@model(
    name="indexing.entity_clustering",
    config_schema=EntityClusteringConfig,
    ...
)
def entity_clustering(sources, writer, config: EntityClusteringConfig, **kwargs):
    # Use typed config
    clustering = DBSCAN(eps=config.eps, min_samples=config.min_samples)
    ...
```

### Migration Path

1. Add `StepConfig` and `ConfigParam` classes to `framework/config.py`
2. Update `@model` decorator to accept `config_schema` parameter
3. Update config parser in `kurt/config/base.py` to support dot notation in keys
4. Gradually add `config_schema` to each step (backwards compatible)
5. Existing code continues working (uses global fallbacks)

### Design Decisions

1. **Naming**: `INDEXING.SECTION_EXTRACTIONS.LLM_MODEL` (dots for hierarchy, underscores for multi-word)

2. **Defaults location**: Step file owns defaults, global config is for overrides

3. **Validation**: Validate on load (fail fast)

4. **Backwards compatibility**: Global keys like `INDEXING_LLM_MODEL` still work as fallbacks

# Indexing Framework (New)

This is the new model-based indexing framework, implementing the design from `model_refactor_plan.md`.

## Current Status

### ✅ Phase 1: Framework Complete

The framework infrastructure is fully implemented and tested:

- **`framework/`** - Core framework components
  - `decorator.py` - `@model` decorator for declarative model definition
  - `table_io.py` - TableReader/TableWriter with Pydantic schema support
  - `document_loader.py` - Document loading with filtering and incremental mode
  - `registry.py` - Model registry for managing registered models
  - `display.py` - Progress display with DBOS streaming integration
  - `dbos_integration.py` - DBOS event streaming for CLI updates
  - `dbos_events.py` - Event emission for model lifecycle
  - `dspy_helpers.py` - DSPy batch execution utilities
  - `testing.py` - Testing utilities and mocks
  - **`tests/`** - All framework tests (84 tests)
    - Unit tests (74 tests)
    - Integration tests (10 tests)

**✅ 84 total tests passing (100% pass rate)**

### 🚧 Phase 2: Model Migration (Next)

Models to be migrated from `indexing/` to `indexing_new/models/`:

1. **Document Sections** (`step_document_sections.py`)
   - Port from: `task_split_document.py` + `splitting.py`
   - Status: Not started

2. **Section Extraction** (`step_extract_sections.py`)
   - Port from: `task_extract_sections.py` + `task_gather_sections.py`
   - Status: Not started

3. **Entity Resolution** (4 stages)
   - Port from: `task_entity_resolution_*.py`
   - Status: Not started

4. **Claim Resolution** (3 stages)
   - Port from: `task_claim_*.py`
   - Status: Not started

### 📝 DSPy Signatures

DSPy signatures will be created fresh in `models/` as each model is migrated:
- They will NOT be imported from the old implementation
- Each model will define its own signatures as needed
- This avoids circular dependencies with the old code

## Directory Structure

```
indexing_new/
├── framework/           # Core framework (COMPLETE)
│   ├── __init__.py
│   ├── decorator.py
│   ├── table_io.py
│   ├── document_loader.py
│   ├── registry.py
│   ├── display.py
│   ├── dbos_integration.py
│   ├── dbos_events.py
│   ├── dspy_helpers.py
│   ├── testing.py
│   └── tests/          # All framework tests (84 tests)
│       ├── conftest.py
│       ├── test_decorator.py
│       ├── test_table_io.py
│       ├── test_document_loader.py
│       ├── test_dspy_helpers.py
│       ├── test_dbos_events.py
│       ├── test_pydantic_schema.py
│       ├── test_testing_utilities.py
│       ├── test_integration.py
│       └── test_end_to_end.py
├── models/             # Migrated models (TO BE CREATED)
│   └── (empty - models will be added during migration)
└── workflows/          # DBOS workflows (TO BE CREATED)
    └── (empty - workflows will be added during migration)
```

## Usage

The framework is ready for model migration. Example model definition:

```python
from pydantic import BaseModel
from kurt.content.indexing_new.framework import model, TableReader, TableWriter

class MyModelOutput(BaseModel):
    document_id: str
    result: str

@model(
    name="my.model",
    db_model=MyModelOutput,
    primary_key=["document_id"],
    description="Example model"
)
def my_model(reader: TableReader, writer: TableWriter, filters, **kwargs):
    # Model logic here
    results = [...]
    return writer.write(results)
```

## Next Steps

1. Start migrating `step_document_sections` model
2. Create the DSPy signatures it needs
3. Test against existing implementation for parity
4. Continue with remaining models in order
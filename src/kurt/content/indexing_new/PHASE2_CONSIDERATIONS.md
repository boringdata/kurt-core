# Phase 2 Considerations - Model Migration

## Framework Status
✅ Phase 1 Complete - 84 tests passing (100%)

## Recent Framework Improvements
- ✅ Enhanced error handling in `load_previous_state()` to distinguish between expected missing tables and real errors
- ✅ Added clear docstring clarifications for `id` vs `document_id` field naming convention
- ✅ Fixed empty DataFrame table creation issue with minimal schema fallback
- ✅ TableWriter now uses Pydantic models for table schema creation when available

## Important Implementation Notes

### 1. Document Loading Strategy
- **Current**: `load_documents()` calls `load_documents_for_indexing(..., force=True)` for backward compatibility
- **Action Required**: Real workflows should call:
  - `load_documents_for_indexing(filters, incremental_mode="delta", force=False)` for production
  - `load_document_with_state()` when previous state merging is needed
- **Why**: Only with `force=False` will incremental mode actually skip unchanged documents

### 2. Field Naming Convention
- **Metadata API** (`load_documents()`): Returns `id` field for backward compatibility
- **Full API** (`load_documents_for_indexing()`): Returns `document_id` field
- **Action Required**: Ensure models use `document_id` when processing full payloads
- **Test Strategy**: Tests should validate the correct field based on which API they're testing

### 3. Previous State Loading
- **Current**: `load_previous_state()` attempts to read from tables that don't exist yet:
  - `document_sections`, `section_extractions`, `entities`, `claims`, etc.
- **Action Required**: As each model is migrated:
  1. Create the table with the model's `@model` decorator
  2. Ensure table has `document_id` column for filtering
  3. Update tests to verify state loading works with real data
- **Note**: The framework gracefully returns `{}` for non-existent tables

### 4. TableReader Document Filtering
- **Current Logic**: `_is_document_table()` checks for `document_id` column existence
- **Risk**: May incorrectly apply filters to tables without this column
- **Action Required**: When creating new tables:
  - Ensure all document-level tables have `document_id` column
  - For non-document tables, verify TableReader skips filtering
  - Add tests for mixed table scenarios

### 5. Session Management
- **Fixed**: Now uses `with get_session() as session:` context manager
- **Benefit**: Prevents connection leaks
- **Pattern to Follow**: All new models should use this pattern

### 6. Delta Mode Integration
- **Current**: Basic hash checking implemented
- **Enhanced**: `load_documents_for_indexing()` now includes `previous_state` in delta mode
- **Next Steps**: Models need to:
  1. Check if document is skipped (`doc['skip']`)
  2. If not skipped, merge `doc['previous_state']` with new extractions
  3. Write merged results to table

## Migration Checklist for Each Model

When migrating a model from `indexing/` to `indexing_new/models/`:

- [ ] Create model file in `indexing_new/models/`
- [ ] Define Pydantic schema for table rows
- [ ] Implement `@model` decorated function
- [ ] Ensure proper use of `document_id` (not `id`) in processing
- [ ] Handle incremental mode:
  - [ ] Check `skip` flag
  - [ ] Load and merge previous state if needed
- [ ] Create/update DSPy signatures (don't import from old code)
- [ ] Add model-specific tests
- [ ] Verify table creation with correct schema
- [ ] Test incremental mode skip behavior
- [ ] Test state merging for delta updates

## Key Patterns to Follow

### Model Definition
```python
@model(
    name="indexing.my_model",
    db_model=MyModelRow,
    primary_key=["document_id", "other_key"],
    description="Model description"
)
def my_model(reader: TableReader, writer: TableWriter, filters: DocumentFilters):
    # Use load_documents_for_indexing for full processing
    docs = load_documents_for_indexing(filters, incremental_mode="delta", force=False)

    results = []
    for doc in docs:
        if doc['skip']:
            continue  # Skip unchanged documents

        # Process document
        # Access previous state if needed: doc.get('previous_state', {})

    return writer.write(results)
```

### Testing Pattern
```python
def test_model_incremental_mode(tmp_project):
    # Set up document with matching hash
    doc.indexed_with_hash = current_hash

    # Load with delta mode
    docs = load_documents_for_indexing(filters, incremental_mode="delta")

    # Verify skip behavior
    assert docs[0]['skip'] == True
    assert docs[0]['skip_reason'] == "content_unchanged"
```

## Known Limitations to Address

1. **State Tables**: Previous state loading expects tables that don't exist yet
2. **DSPy Signatures**: Need fresh implementation, not imports from old code
3. **DBOS Integration**: Models need to emit proper events for CLI streaming
4. **Workflow Orchestration**: DBOS workflows need to be created separately

## Success Metrics for Phase 2

- [ ] All models migrated and passing tests
- [ ] Incremental mode properly skips unchanged documents
- [ ] Previous state correctly loaded and merged
- [ ] No circular dependencies with old code
- [ ] DBOS events streaming to CLI
- [ ] Performance equal or better than old pipeline

## Framework Recommendations and Potential Improvements

### Dead Code to Remove
1. **`dbos_workflow.py`** - Empty file, workflow logic will be in `workflows/` directory
2. **Test reorganization** - All framework tests now properly under `framework/tests/`
3. **DSPy signatures** - Will be created fresh with each model, not imported from old code

### Potential Simplifications
1. **TableReader `where` parameter** - Currently accepts raw SQL WHERE clause
   - Consider structured query builder for safety
   - Or at minimum, parameter validation/escaping

2. **`load_documents()` force flag** - Currently hardcoded to `True` for backward compatibility
   - Consider deprecation warning when used
   - Guide users to `load_documents_for_indexing()` for production use

3. **Error handling consolidation** - Multiple try/except patterns could be standardized
   - Create common error handler utility
   - Consistent logging levels across framework

### Areas Needing Additional Testing
1. **Concurrent model execution** - DSPy batch concurrency under load
2. **Large document sets** - Performance with 10K+ documents
3. **State merging edge cases** - Complex delta mode scenarios
4. **Table schema evolution** - Handling model schema changes over time

### Documentation Needs
1. **Migration guide** - Step-by-step for converting old models
2. **Best practices** - Patterns for efficient model implementation
3. **Performance tuning** - Batch sizes, concurrency settings
4. **Troubleshooting guide** - Common issues and solutions
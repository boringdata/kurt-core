# Fetch Architecture Analysis

## Desired Pattern (from indexing.py)

```
Pattern:
- content/indexing_xxx.py: Business logic functions (pure logic + LLM calls)
- workflows/: DBOS orchestration (calls business logic + db operations)
- content/indexing.py: CLI entry point (calls workflows)
```

**Flow**: CLI → Workflow → Business Logic

---

## Current Fetch Architecture

### What We Have Now

#### 1. `fetch.py` - Mixed Concerns ❌
```python
# Contains:
- _fetch_from_cms() - Business logic (CMS fetching)
- fetch_content_from_source() - Business logic (Network I/O)
- extract_and_save_document_links() - Business logic + DB operations (MIXED!)
- fetch_document() - Orchestration (Used by map.py and tests)
- fetch_documents_batch() - Async orchestration
- extract_document_links() - Pure business logic
- save_document_links() - DB operations
```

**Problem**: Mixing business logic, DB operations, and orchestration in one file.

#### 2. `fetch_utils.py` - Mixed Concerns ❌
```python
# Contains:
- _get_fetch_engine() - Configuration utility ✓
- select_documents_for_fetch() - Filtering + DB query + document creation (MIXED!)
```

**Problem**: `select_documents_for_fetch()` does DB operations directly, should be in a workflow.

#### 3. `workflows/fetch.py` - Good Structure ✓
```python
# Contains:
- Workflow steps calling business logic from document.py, embeddings.py, fetch.py
- DBOS orchestration with checkpointing
- No direct business logic
```

**Status**: ✓ Already follows the pattern!

#### 4. `commands/content/fetch.py` - Too Complex ❌
```python
# Contains:
- Argument parsing ✓
- Document selection (calls select_documents_for_fetch()) - WRONG!
- Validation and confirmations ✓
- Direct calls to fetch_documents_batch() - SHOULD call workflow!
- Progress tracking and display ✓
```

**Problem**: CLI does too much orchestration, should just call workflow.

---

## Gap Analysis

### What's Wrong

| Component | Current State | Should Be |
|-----------|--------------|-----------|
| **Business Logic** | Scattered across `fetch.py`, `fetch_utils.py` | Centralized in `fetch_*.py` files |
| **DB Operations** | Mixed with business logic | Only in `@DBOS.transaction()` or `@DBOS.step()` |
| **Orchestration** | Partially in CLI, partially in workflows | Only in `workflows/fetch.py` |
| **CLI** | Does filtering, validation, orchestration | Just calls workflow |

### Specific Issues

1. **`select_documents_for_fetch()` does DB queries**
   - Location: `fetch_utils.py`
   - Problem: Directly queries database (lines 165-244)
   - Should be: Business logic returns filters, workflow does DB queries

2. **`extract_and_save_document_links()` mixes logic + DB**
   - Location: `fetch.py`
   - Problem: Extracts links (business logic) AND saves to DB (DB operation)
   - Should be: Split into `extract_document_links()` (pure) and workflow step for saving

3. **`save_document_links()` is in `fetch.py`**
   - Location: `fetch.py` (lines 899-967)
   - Problem: Pure DB operation in business logic file
   - Should be: In workflow or document.py

4. **CLI calls `fetch_documents_batch()` directly**
   - Location: `commands/content/fetch.py` (line 539)
   - Problem: Bypasses workflow layer
   - Should be: Call `fetch_batch_workflow()` from `workflows/fetch.py`

---

## Proposed Refactoring

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ CLI Layer (commands/content/fetch.py)                       │
│ - Parse arguments                                           │
│ - Validate inputs                                           │
│ - Display results                                           │
│ - Call workflow ONLY                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Workflow Layer (workflows/fetch.py)                         │
│ - @DBOS.workflow() orchestration                            │
│ - @DBOS.step() for DB queries                              │
│ - @DBOS.transaction() for DB writes                        │
│ - Calls business logic functions                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Business Logic Layer (fetch_*.py)                          │
│ - fetch_content.py: Pure fetching logic (Network I/O)     │
│ - fetch_filtering.py: Pure filtering logic (no DB)        │
│ - fetch_links.py: Pure link extraction logic              │
│ - fetch_utils.py: Configuration utilities                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CRUD Layer (document.py, embeddings.py)                    │
│ - Document CRUD operations                                  │
│ - Embedding generation                                      │
└─────────────────────────────────────────────────────────────┘
```

### File Organization (Target)

#### `fetch_content.py` (NEW - Business Logic)
```python
"""Pure fetching business logic - no DB operations."""

def fetch_from_cms(platform: str, instance: str, cms_document_id: str) -> tuple[str, dict]:
    """Fetch content from CMS - pure business logic."""

def fetch_from_web(source_url: str, fetch_engine: str) -> tuple[str, dict]:
    """Fetch content from web - pure business logic."""
```

#### `fetch_filtering.py` (NEW - Business Logic)
```python
"""Pure filtering logic - no DB operations."""

def build_document_filters(
    include_pattern: str = None,
    urls: str = None,
    files: str = None,
    ids: str = None,
    in_cluster: str = None,
    with_status: str = None,
    with_content_type: str = None,
    exclude: str = None,
    limit: int = None,
    refetch: bool = False,
) -> dict:
    """Build filter specification (no DB queries).

    Returns:
        {
            'url_list': [...],
            'file_list': [...],
            'id_filters': {...},
            'status_filters': {...},
            'glob_patterns': {...}
        }
    """
```

#### `fetch_links.py` (NEW - Business Logic)
```python
"""Pure link extraction logic - no DB operations."""

def extract_document_links(content: str, source_url: str, base_url: str = None) -> list[dict]:
    """Extract links from markdown - pure function."""
```

#### `fetch_utils.py` (KEEP - Configuration)
```python
"""Configuration and utilities - no business logic."""

def _get_fetch_engine(override: str = None) -> str:
    """Get configured fetch engine."""
```

#### `workflows/fetch.py` (ENHANCE - Orchestration)
```python
"""DBOS workflows for fetching."""

# NEW workflow step
@DBOS.step()
def select_documents_step(filters: dict) -> list[Document]:
    """Apply filters and return documents to fetch.

    This is where DB queries happen!
    """
    session = get_session()

    # Create documents for URLs (delegates to document.py)
    if filters['url_list']:
        add_documents_for_urls(filters['url_list'])

    # Query documents with filters
    stmt = build_query_from_filters(filters)
    docs = session.exec(stmt).all()

    return list(docs)

# Existing workflow (already good!)
@DBOS.workflow()
def fetch_document_workflow(identifier: str, fetch_engine: str = None):
    """5 checkpointed steps..."""

# ENHANCED workflow
@DBOS.workflow()
def fetch_batch_workflow(
    filters: dict,  # ← Filter spec from CLI (no DB queries yet!)
    fetch_engine: str = None,
    extract_metadata: bool = False,
):
    """
    Batch fetch with proper separation.

    1. Select documents (DB query in workflow step)
    2. Fetch each document (calls business logic)
    3. Optionally extract metadata
    """
    # Step 1: Query DB for documents (IN WORKFLOW)
    docs = select_documents_step(filters)

    # Step 2: Fetch each document
    results = []
    for doc in docs:
        result = fetch_document_workflow(doc.id, fetch_engine)
        results.append(result)

    return {"total": len(results), "results": results}
```

#### `commands/content/fetch.py` (SIMPLIFY - CLI Entry Point)
```python
"""CLI command - just calls workflow."""

def fetch_cmd(...):
    """CLI entry point."""
    # 1. Parse arguments
    identifier = ...

    # 2. Build filter specification (NO DB QUERIES!)
    from kurt.content.fetch_filtering import build_document_filters
    filters = build_document_filters(
        include_pattern=include_pattern,
        urls=urls,
        files=files,
        ...
    )

    # 3. Validate (user confirmations, warnings)
    if dry_run:
        # Preview only
        return

    # 4. Call workflow (THIS IS THE ONLY WORK WE DO!)
    from kurt.workflows.fetch import fetch_batch_workflow

    if background:
        # Enqueue workflow
        handle = fetch_queue.enqueue(
            fetch_batch_workflow,
            filters=filters,
            fetch_engine=engine,
            extract_metadata=not skip_index,
        )
    else:
        # Run workflow
        result = fetch_batch_workflow(
            filters=filters,
            fetch_engine=engine,
            extract_metadata=not skip_index,
        )

    # 5. Display results
    print_summary(result)
```

---

## Migration Steps

### Phase 1: Extract Business Logic

1. ✅ **Create `fetch_links.py`**
   - Move `extract_document_links()` from `fetch.py`
   - Keep it pure (no DB operations)

2. ✅ **Create `fetch_filtering.py`**
   - Move filtering logic from `select_documents_for_fetch()`
   - Make it pure: return filter specification, don't query DB
   - Example:
     ```python
     def build_document_filters(...) -> dict:
         """Build filter specification without querying DB."""
         return {
             'url_list': [url.strip() for url in urls.split(",")] if urls else [],
             'file_list': [f.strip() for f in files.split(",")] if files else [],
             'id_list': ids.split(",") if ids else [],
             'cluster_name': in_cluster,
             'status': with_status,
             'content_type': with_content_type,
             'include_pattern': include_pattern,
             'exclude_pattern': exclude,
             'limit': limit,
             'refetch': refetch,
         }
     ```

3. ✅ **Create `fetch_content.py`**
   - Move `_fetch_from_cms()` and `fetch_content_from_source()` from `fetch.py`
   - Rename to remove `_` prefix (they're business logic, not private!)
   - Keep them pure (Network I/O only, no DB)

### Phase 2: Move DB Operations to Workflows

4. ✅ **Add `select_documents_step()` to `workflows/fetch.py`**
   - Takes filter specification
   - Does DB queries
   - Creates documents if needed (delegates to document.py)
   - Returns list of Document objects

5. ✅ **Add `save_links_step()` to `workflows/fetch.py`**
   - Takes document_id and list of links
   - Saves to database
   - Currently `save_document_links()` in `fetch.py` should move here

6. ✅ **Update `extract_links_step()` in `workflows/fetch.py`**
   - Call pure `extract_document_links()` from `fetch_links.py`
   - Call `save_links_step()` to save to DB
   - Separate extraction (pure) from persistence (DB)

### Phase 3: Simplify CLI

7. ✅ **Update `commands/content/fetch.py`**
   - Remove direct DB queries
   - Build filter specification using `fetch_filtering.py`
   - Call `fetch_batch_workflow()` instead of `fetch_documents_batch()`
   - Keep only: arg parsing, validation, workflow call, display

### Phase 4: Clean Up

8. ✅ **Update `fetch.py`**
   - Remove moved functions
   - Keep only backward compatibility re-exports if needed
   - Or delete entirely if no backward compat needed

9. ✅ **Update tests**
   - Test business logic functions directly (pure functions)
   - Test workflows with mocks
   - Test CLI integration

---

## Benefits

### Before (Current State)
```
CLI (500 lines)
  ├─ select_documents_for_fetch() [DB queries]
  ├─ fetch_documents_batch() [Direct call, bypasses workflow]
  └─ Display results

fetch.py (900 lines)
  ├─ Business logic (fetching)
  ├─ DB operations (links, documents)
  └─ Orchestration (batch fetching)
```

**Problems**:
- DB operations scattered everywhere
- No DBOS checkpointing for document selection
- CLI has business logic
- Hard to test
- Hard to reuse

### After (Target State)
```
CLI (200 lines)
  ├─ Parse args
  ├─ Build filter spec (pure)
  ├─ Call workflow
  └─ Display results

workflows/fetch.py
  ├─ @DBOS.step() select_documents_step [DB queries HERE]
  ├─ @DBOS.workflow() fetch_batch_workflow [Orchestration]
  └─ @DBOS.step() save_links_step [DB writes HERE]

fetch_content.py (200 lines)
  └─ Pure fetching logic (Network I/O)

fetch_filtering.py (100 lines)
  └─ Pure filtering logic (build specs)

fetch_links.py (100 lines)
  └─ Pure link extraction (regex parsing)
```

**Benefits**:
- ✅ Clear separation: CLI → Workflow → Business Logic
- ✅ All DB operations in @DBOS.step() or @DBOS.transaction()
- ✅ Document selection is checkpointed (can resume!)
- ✅ Pure functions easy to test
- ✅ Business logic reusable
- ✅ Follows same pattern as indexing.py

---

## Comparison with Indexing Pattern

### Indexing (Good Pattern ✓)

```
commands/content/index.py (CLI)
  → calls index_documents()

content/indexing.py (Entry Point)
  → calls batch_extract_document_metadata()
  → calls complete_entity_resolution_workflow()

content/indexing_extract.py (Business Logic)
  → Pure DSPy calls, no DB

workflows/entity_resolution.py (Orchestration)
  → @DBOS.workflow()
  → @DBOS.step() with DB operations
  → Calls business logic from indexing_entity_resolution.py
```

### Fetch (Target Pattern)

```
commands/content/fetch.py (CLI)
  → builds filter spec with fetch_filtering.py
  → calls fetch_batch_workflow()

content/fetch_*.py (Business Logic)
  → fetch_content.py: Pure Network I/O
  → fetch_filtering.py: Pure filter building
  → fetch_links.py: Pure link extraction

workflows/fetch.py (Orchestration)
  → @DBOS.workflow() fetch_batch_workflow
  → @DBOS.step() select_documents_step (DB queries HERE)
  → @DBOS.step() fetch_content_step (calls fetch_content.py)
  → @DBOS.step() save_links_step (DB writes HERE)
```

**Result**: Same pattern, clear separation!

---

## Next Steps

Should I proceed with the refactoring? Here's what I propose:

1. **Create new business logic files**:
   - `fetch_content.py` (move pure fetching logic)
   - `fetch_filtering.py` (move pure filtering logic)
   - `fetch_links.py` (move pure link extraction)

2. **Enhance `workflows/fetch.py`**:
   - Add `select_documents_step()` for DB queries
   - Add `save_links_step()` for DB writes
   - Update `fetch_batch_workflow()` to use filter specs

3. **Simplify `commands/content/fetch.py`**:
   - Remove DB operations
   - Build filter spec
   - Call workflow only

4. **Clean up `fetch.py` and `fetch_utils.py`**:
   - Remove moved functions
   - Keep only backward compat if needed

What do you think? Should I proceed with this refactoring?

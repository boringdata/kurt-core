# `fetch_content()` Analysis & Simplification

## Current Situation

### What is `fetch_content()`?

**NOT a fetch function!** It's a **filtering and orchestration function** used by the CLI.

```python
# src/kurt/content/fetch.py
def fetch_content(
    include_pattern: str = None,
    urls: str = None,
    files: str = None,
    ids: str = None,
    in_cluster: str = None,
    with_status: str = None,
    with_content_type: str = None,
    exclude: str = None,
    limit: int = None,
    concurrency: int = 5,
    engine: str = None,
    skip_index: bool = False,
    refetch: bool = False,
) -> dict:
    """Returns dict with filtered documents to fetch"""
```

### What Does It Do?

1. **Validates** filters (requires at least one)
2. **Queries** database based on filters
3. **Creates** documents for new URLs/files
4. **Applies** glob patterns, cluster filters, status filters
5. **Returns** dict with:
   - `docs`: List of Document objects to fetch
   - `doc_ids`: List of document IDs
   - `warnings`: List of warnings
   - `errors`: List of errors

**It does NOT actually fetch anything!** It just returns which documents to fetch.

### Where is it used?

**Only in CLI:**
- `src/kurt/commands/content/fetch.py` - CLI command uses it to filter documents

### The Problem

- **Monster function**: ~230 lines, complex logic
- **Misleading name**: `fetch_content()` sounds like it fetches content, but it's just filtering!
- **Mixed responsibilities**: Database queries + document creation + glob matching + validation

## Proposed Solution

### Option 1: Rename & Keep As-Is

**Rename to clarify purpose:**

```python
# src/kurt/content/fetch.py → src/kurt/content/filtering.py

def select_documents_for_fetch(
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
) -> list[Document]:
    """
    Select documents to fetch based on filters.

    Returns:
        List of Document objects that match filters
    """
```

**Benefits:**
- Clear name: "select_documents" not "fetch_content"
- Simpler return: Just list of docs, not dict
- CLI handles warnings/errors

**Changes needed:**
- Move to `filtering.py` (already has `resolve_ids_to_uuids()`)
- Simplify return type
- Update CLI import

### Option 2: Break It Down

**Split into focused functions:**

```python
# src/kurt/content/filtering.py

def validate_fetch_filters(...) -> None:
    """Validate at least one filter is provided"""

def apply_document_filters(...) -> list[Document]:
    """Apply database filters (status, cluster, content_type)"""

def apply_glob_filters(...) -> list[Document]:
    """Apply glob patterns to filter documents"""

def create_documents_for_urls(...) -> list[UUID]:
    """Create document records for new URLs"""

def create_documents_for_files(...) -> list[UUID]:
    """Create document records for local files"""

def select_documents_for_fetch(...) -> list[Document]:
    """
    High-level function that orchestrates filtering.
    Delegates to helper functions above.
    """
```

**Benefits:**
- Each function has single responsibility
- Easier to test
- Easier to reuse

**Drawbacks:**
- More functions to maintain
- May be over-engineering for a CLI-only function

### Option 3: Move to CLI Layer

**Move logic to CLI command:**

```python
# src/kurt/commands/content/fetch.py

def _select_documents(
    include_pattern, urls, files, ids, in_cluster,
    with_status, with_content_type, exclude, limit, refetch
) -> list[Document]:
    """Select documents for CLI fetch command"""
    # All the filtering logic here
```

**Benefits:**
- Keep business logic close to where it's used
- No need to export from `fetch.py`
- CLI-specific logic stays in CLI

**Drawbacks:**
- CLI module becomes larger
- Logic not reusable (but is it needed elsewhere?)

## Recommendation

### ✅ **Option 1: Rename & Simplify**

**Best balance of clarity and simplicity:**

1. **Move to `filtering.py`** (already has document filtering logic)
2. **Rename** to `select_documents_for_fetch()`
3. **Simplify return type** to just `list[Document]`
4. **Remove** `concurrency`, `engine`, `skip_index` parameters (those are fetch params, not filter params)
5. **Let CLI handle** warnings/errors directly

### Implementation

```python
# src/kurt/content/filtering.py

def select_documents_for_fetch(
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
) -> list[Document]:
    """
    Select documents to fetch based on filters.

    Validates filters, queries database, creates documents for new URLs/files,
    and returns list of documents that match the criteria.

    Args:
        include_pattern: Glob pattern for source_url or content_path
        urls: Comma-separated URLs (creates documents if not exist)
        files: Comma-separated file paths (creates documents)
        ids: Comma-separated document IDs
        in_cluster: Cluster name filter
        with_status: Status filter (NOT_FETCHED | FETCHED | ERROR)
        with_content_type: Content type filter
        exclude: Glob pattern to exclude
        limit: Maximum documents to return
        refetch: If True, include FETCHED documents

    Returns:
        List of Document objects matching filters

    Raises:
        ValueError: If no filter provided or invalid parameters

    Example:
        # Get all NOT_FETCHED documents in cluster
        docs = select_documents_for_fetch(
            in_cluster="Tutorials",
            with_status="NOT_FETCHED"
        )
    """
```

### Changes needed:

1. **Move function from `fetch.py` to `filtering.py`**
2. **Rename** `fetch_content()` → `select_documents_for_fetch()`
3. **Remove parameters**: `concurrency`, `engine`, `skip_index` (those belong to CLI)
4. **Simplify return**: Return `list[Document]` instead of dict
5. **Update CLI** to handle warnings/errors locally

### Result

**Before:**
```python
# fetch.py (230 lines)
def fetch_content(...) -> dict:  # Misleading name!
```

**After:**
```python
# filtering.py (~180 lines)
def select_documents_for_fetch(...) -> list[Document]:  # Clear name!
```

**Benefits:**
- ✅ Clear name: Describes what it does (filtering)
- ✅ Right module: `filtering.py` handles document filtering
- ✅ Simpler interface: Just returns docs, not complex dict
- ✅ Smaller `fetch.py`: Focused on actual fetching only
- ✅ Better organized: Filtering logic with other filtering functions

## Current `fetch.py` Functions

After moving `fetch_content()`, `fetch.py` would contain:

### Core Functions (Keep)
1. `_get_fetch_engine()` - Engine selection
2. `_fetch_from_cms()` - CMS fetching
3. `fetch_content_from_source()` - Actual fetching ← This is real fetching!
4. `extract_and_save_document_links()` - Link extraction
5. `fetch_document()` - Legacy convenience wrapper
6. `fetch_documents_batch()` - Batch fetching
7. `extract_document_links()` - Link parsing
8. `save_document_links()` - Link saving

**Result:** `fetch.py` focuses ONLY on **actually fetching content** from sources.

## Summary

**Current situation:**
- `fetch_content()` is misnamed (doesn't fetch, just filters)
- 230 lines in wrong module
- Returns complex dict

**Proposed fix:**
- Move to `filtering.py`
- Rename to `select_documents_for_fetch()`
- Simplify return type
- Remove non-filter parameters

**Effort:** Low (mostly renaming + moving)

**Impact:** High (much clearer organization)

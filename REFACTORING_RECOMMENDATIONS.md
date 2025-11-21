# Function Organization Recommendations

After refactoring, some functions in `fetch.py` could be better organized. Here's the analysis:

## Current State

### Functions in `fetch.py` that should be moved:

| Function | Current Location | Should Move To | Reason |
|----------|-----------------|----------------|---------|
| `resolve_or_create_document()` | `content/fetch.py` | **`content/document.py`** | Document CRUD operation |
| `add_document()` | `content/fetch.py` | **`content/document.py`** | Document creation (already has `get_document`, `delete_document`) |
| `generate_document_embedding()` | `content/fetch.py` | **`content/embeddings.py`** | Embedding utility (already has `generate_embeddings()`) |
| `save_document_content_and_metadata()` | `content/fetch.py` | **`content/document.py`** | Document persistence operation |

### Functions that should STAY in `fetch.py`:

| Function | Reason |
|----------|--------|
| `fetch_content_from_source()` | Core fetch logic - belongs here |
| `extract_and_save_document_links()` | Link extraction - part of fetch process |
| `fetch_document()` | Main fetch orchestration |
| `fetch_documents_batch()` | Batch fetch orchestration |
| `fetch_content()` | CLI entry point for fetch |

---

## Detailed Analysis

### 1. `resolve_or_create_document()` → Move to `document.py`

**Current:**
```python
# src/kurt/content/fetch.py
def resolve_or_create_document(identifier: str | UUID) -> dict:
    """Find existing document or create new one."""
```

**Should be:**
```python
# src/kurt/content/document.py
def resolve_or_create_document(identifier: str | UUID) -> dict:
    """Find existing document or create new one."""
```

**Why:**
- `document.py` already has:
  - `get_document(document_id)` - Get by ID
  - `delete_document(document_id)` - Delete
  - `list_documents()` - List all
- This function is **document CRUD**, not fetch-specific
- Should be co-located with other document operations

**Existing Similar Function:**
- `get_document()` already does partial UUID resolution
- Could merge or keep both (one for simple get, one for resolve/create)

---

### 2. `add_document()` → Move to `document.py`

**Current:**
```python
# src/kurt/content/fetch.py (line 475)
def add_document(url: str, title: str = None) -> UUID:
    """Create document record with NOT_FETCHED status."""
```

**Should be:**
```python
# src/kurt/content/document.py
def add_document(url: str, title: str = None) -> UUID:
    """Create document record with NOT_FETCHED status."""
```

**Why:**
- Document creation is a CRUD operation
- `document.py` already has `get_document()` and `delete_document()`
- Should complete the CRUD set: **Create, Read, Update, Delete**

**Currently in `document.py`:**
- ❌ Create → **MISSING** (but `add_document` exists in `fetch.py`)
- ✅ Read → `get_document()`, `list_documents()`
- ❌ Update → **MISSING** (could add `update_document()`)
- ✅ Delete → `delete_document()`

---

### 3. `generate_document_embedding()` → Move to `embeddings.py`

**Current:**
```python
# src/kurt/content/fetch.py (line 297)
def generate_document_embedding(content: str) -> bytes:
    """Generate embedding vector for content."""
```

**Should be:**
```python
# src/kurt/content/embeddings.py
def generate_document_embedding(content: str) -> bytes:
    """Generate embedding for document content (first 1000 chars)."""
```

**Why:**
- `embeddings.py` already has:
  - `generate_embeddings(texts: list[str])` - Batch generation
  - `embedding_to_bytes(embedding)` - Conversion to bytes
  - `bytes_to_embedding(bytes)` - Conversion from bytes
- This is an **embedding utility**, not fetch-specific
- Can be reused outside of fetch context

**Possible Refactoring:**
```python
# src/kurt/content/embeddings.py

def generate_document_embedding(content: str, max_chars: int = 1000) -> bytes:
    """
    Generate embedding for document content.

    Uses first max_chars characters to avoid token limits.
    Returns bytes for database storage.
    """
    content_sample = content[:max_chars] if len(content) > max_chars else content
    embeddings = generate_embeddings([content_sample])
    return embedding_to_bytes(embeddings[0])
```

---

### 4. `save_document_content_and_metadata()` → Move to `document.py`

**Current:**
```python
# src/kurt/content/fetch.py (line 330)
def save_document_content_and_metadata(
    doc_id: UUID, content: str, metadata: dict, embedding: bytes | None
) -> dict:
    """Save content to filesystem and update database."""
```

**Should be:**
```python
# src/kurt/content/document.py
def save_document_content_and_metadata(
    doc_id: UUID, content: str, metadata: dict, embedding: bytes | None
) -> dict:
    """Save content to filesystem and update database (transactional)."""
```

**Why:**
- This is a **document update operation** (Update in CRUD)
- Updates multiple document fields + writes file
- Should be co-located with other document persistence operations
- `document.py` currently has no update function

**This would complete the CRUD pattern in `document.py`:**
- ✅ Create → `add_document()`
- ✅ Read → `get_document()`, `list_documents()`, `load_document_content()`
- ✅ Update → `save_document_content_and_metadata()` ← **NEW**
- ✅ Delete → `delete_document()`

---

## Proposed Refactoring Plan

### Phase 1: Move to `document.py`

```python
# src/kurt/content/document.py

# Add these functions:
def add_document(url: str, title: str = None) -> UUID:
    """Create document record with NOT_FETCHED status."""
    # Move from fetch.py

def resolve_or_create_document(identifier: str | UUID) -> dict:
    """Find existing document or create new one."""
    # Move from fetch.py

def save_document_content_and_metadata(
    doc_id: UUID, content: str, metadata: dict, embedding: bytes | None
) -> dict:
    """Save content to filesystem and update database."""
    # Move from fetch.py
```

### Phase 2: Move to `embeddings.py`

```python
# src/kurt/content/embeddings.py

def generate_document_embedding(content: str, max_chars: int = 1000) -> bytes:
    """Generate embedding for document content."""
    # Move from fetch.py
    # Refactor to use existing generate_embeddings() + embedding_to_bytes()
```

### Phase 3: Update `fetch.py` imports

```python
# src/kurt/content/fetch.py

from kurt.content.document import (
    add_document,
    resolve_or_create_document,
    save_document_content_and_metadata,
)
from kurt.content.embeddings import generate_document_embedding

# Keep only fetch-specific functions:
# - _get_fetch_engine()
# - _fetch_from_cms()
# - fetch_content_from_source()
# - extract_and_save_document_links()
# - fetch_document()
# - fetch_documents_batch()
# - fetch_content()
# - extract_document_links()
# - save_document_links()
```

### Phase 4: Update `workflows/fetch.py` imports

```python
# src/kurt/workflows/fetch.py

from kurt.content.document import (
    resolve_or_create_document,
    save_document_content_and_metadata,
)
from kurt.content.embeddings import generate_document_embedding
from kurt.content.fetch import (
    fetch_content_from_source,
    extract_and_save_document_links,
)
```

---

## Benefits of Refactoring

1. **Better Organization**
   - Functions grouped by responsibility (CRUD vs Fetch vs Embeddings)
   - Easier to find functions
   - Clear module boundaries

2. **Complete CRUD Pattern in `document.py`**
   - Create: `add_document()`
   - Read: `get_document()`, `list_documents()`, `load_document_content()`
   - Update: `save_document_content_and_metadata()`
   - Delete: `delete_document()`

3. **Reusability**
   - `generate_document_embedding()` can be used outside fetch
   - `save_document_content_and_metadata()` can be used for direct updates
   - `add_document()` can be used without fetching

4. **Focused Modules**
   - `fetch.py` → Only fetch-related logic
   - `document.py` → Only document CRUD operations
   - `embeddings.py` → Only embedding utilities

5. **No Breaking Changes**
   - Keep backward compatibility by re-exporting from `fetch.py`:
   ```python
   # src/kurt/content/fetch.py

   # For backward compatibility
   from kurt.content.document import (
       add_document,
       resolve_or_create_document,
       save_document_content_and_metadata,
   )
   from kurt.content.embeddings import generate_document_embedding

   __all__ = [
       # Re-export for backward compatibility
       "add_document",
       "resolve_or_create_document",
       "generate_document_embedding",
       "save_document_content_and_metadata",
       # Fetch-specific
       "fetch_content_from_source",
       "fetch_document",
       "fetch_documents_batch",
       ...
   ]
   ```

---

## Is `fetch_document()` Still Used?

**YES! Keep it!**

`fetch_document()` is still used in:

1. **Legacy code** - For backward compatibility
2. **Direct calls** - When you don't need DBOS workflows
3. **Batch operations** - `fetch_documents_batch()` calls it
4. **CLI fallback** - Simple one-off fetches

**Current usage:**
```python
# src/kurt/content/fetch.py (line 636)
async def _fetch_one_async(doc_id: str, ...) -> dict:
    result = await loop.run_in_executor(None, fetch_document, doc_id, fetch_engine)
```

**Should NOT remove** unless you update:
- All batch fetch operations
- All CLI commands
- All direct callers

**Better approach:** Keep it as a convenience function that delegates to the new helper functions (which it already does after refactoring!).

---

## Summary

### Functions to Move:

| # | Function | From | To | Priority |
|---|----------|------|-----|----------|
| 1 | `add_document()` | `fetch.py` | `document.py` | **HIGH** |
| 2 | `resolve_or_create_document()` | `fetch.py` | `document.py` | **HIGH** |
| 3 | `save_document_content_and_metadata()` | `fetch.py` | `document.py` | **MEDIUM** |
| 4 | `generate_document_embedding()` | `fetch.py` | `embeddings.py` | **MEDIUM** |

### Functions to Keep in `fetch.py`:

- ✅ `fetch_content_from_source()` - Core fetch logic
- ✅ `fetch_document()` - Main orchestration (delegates to helpers)
- ✅ `fetch_documents_batch()` - Batch orchestration
- ✅ `fetch_content()` - CLI entry point
- ✅ `extract_and_save_document_links()` - Link extraction
- ✅ All link-related functions

### Result:

- `fetch.py` focuses on **fetching content** from sources
- `document.py` handles **document CRUD** operations
- `embeddings.py` provides **embedding utilities**
- Clear separation of concerns
- Better code organization
- No breaking changes (re-export for compatibility)

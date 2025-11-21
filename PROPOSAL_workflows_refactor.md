# DBOS Workflows Refactoring Proposal

## Problem Statement

Current workflows are too coarse-grained:
- `fetch_document_step()` wraps a massive function doing 6+ different operations
- `fetch_and_index_workflow()` just delegates to another workflow (redundant)
- No checkpoint granularity for expensive operations (LLM embedding, HTTP fetch)
- If embedding fails, entire fetch is re-run

## Proposed Architecture

### Core Operations (in `content/fetch.py`)

Break down into focused, reusable functions:

```python
# 1. Document resolution
def resolve_or_create_document(identifier: str | UUID) -> Document:
    """Find existing or create new document record."""

# 2. Content fetching (network I/O - can fail)
def fetch_content_from_source(url: str, engine: str = None) -> tuple[str, dict]:
    """Fetch raw content + metadata from URL/CMS."""

# 3. Embedding generation (LLM - expensive, can fail)
def generate_document_embedding(content: str) -> bytes:
    """Generate embedding vector for content sample."""

# 4. Link extraction (fast, pure function)
def extract_and_save_links(doc_id: UUID, content: str, source_url: str) -> int:
    """Extract markdown links and save to database."""

# 5. Document persistence (database transaction)
def save_document_content(
    doc_id: UUID,
    content: str,
    metadata: dict,
    embedding: bytes | None,
    content_path: Path
) -> None:
    """Save content to filesystem and update database."""
```

### DBOS Workflow Steps (in `workflows/fetch.py`)

```python
@DBOS.step()
def resolve_document_step(identifier: str | UUID) -> dict:
    """Step 1: Resolve or create document record."""
    doc = resolve_or_create_document(identifier)
    return {
        "document_id": str(doc.id),
        "source_url": doc.source_url,
        "is_cms": bool(doc.cms_platform),
    }

@DBOS.step()
def fetch_content_step(source_url: str, engine: str = None) -> dict:
    """Step 2: Fetch content from source (HTTP/CMS API)."""
    content, metadata = fetch_content_from_source(source_url, engine)
    return {
        "content": content,
        "metadata": metadata,
        "content_length": len(content),
    }

@DBOS.step()
def generate_embedding_step(content: str) -> dict:
    """Step 3: Generate embedding (expensive LLM call)."""
    # Use first 1000 chars for embedding
    content_sample = content[:1000] if len(content) > 1000 else content
    embedding = generate_document_embedding(content_sample)
    return {
        "embedding": embedding,
        "embedding_dims": len(embedding) // 4,  # bytes to float32 count
    }

@DBOS.transaction()
def save_document_step(
    doc_id: str,
    content: str,
    metadata: dict,
    embedding: bytes | None,
) -> dict:
    """Step 4: Save to filesystem + database (transactional)."""
    # Create content path
    config = load_config()
    doc = session.get(Document, UUID(doc_id))

    if doc.cms_platform:
        content_path = create_cms_content_path(...)
    else:
        content_path = create_content_path(doc.source_url, config)

    # Save document
    save_document_content(UUID(doc_id), content, metadata, embedding, content_path)

    return {
        "content_path": str(content_path),
        "status": "FETCHED",
    }

@DBOS.step()
def extract_links_step(doc_id: str, content: str, source_url: str) -> dict:
    """Step 5: Extract and save document links."""
    links_count = extract_and_save_links(UUID(doc_id), content, source_url)
    return {"links_extracted": links_count}
```

### Workflow Orchestration

```python
@DBOS.workflow()
def fetch_document_workflow(
    identifier: str | UUID,
    fetch_engine: str | None = None,
) -> dict[str, Any]:
    """
    Durable workflow for fetching a document.

    Steps (each checkpointed):
    1. Resolve/create document record
    2. Fetch content from source (HTTP/CMS)
    3. Generate embedding (LLM - expensive!)
    4. Save to filesystem + database
    5. Extract and save links
    """
    # Step 1: Resolve document
    doc_info = resolve_document_step(identifier)
    doc_id = doc_info["document_id"]

    # Step 2: Fetch content (network I/O)
    fetch_result = fetch_content_step(doc_info["source_url"], fetch_engine)
    content = fetch_result["content"]
    metadata = fetch_result["metadata"]

    # Step 3: Generate embedding (expensive LLM call - checkpointed!)
    embedding_result = generate_embedding_step(content)
    embedding = embedding_result["embedding"]

    # Step 4: Save to database (transactional)
    save_result = save_document_step(doc_id, content, metadata, embedding)

    # Step 5: Extract links
    links_result = extract_links_step(doc_id, content, doc_info["source_url"])

    return {
        "document_id": doc_id,
        "status": save_result["status"],
        "content_length": fetch_result["content_length"],
        "embedding_dims": embedding_result["embedding_dims"],
        "links_extracted": links_result["links_extracted"],
        "content_path": save_result["content_path"],
    }


@DBOS.workflow()
def fetch_and_index_workflow(
    identifier: str | UUID,
    fetch_engine: str | None = None
) -> dict[str, Any]:
    """
    Complete fetch + index workflow.

    Steps (each checkpointed):
    1-5. Fetch document (via fetch_document_workflow)
    6. Extract metadata (LLM - expensive!)
    """
    # Step 1-5: Fetch document
    fetch_result = DBOS.invoke(fetch_document_workflow, identifier, fetch_engine)

    # Step 6: Extract metadata (separate expensive LLM call)
    metadata_result = extract_metadata_step(fetch_result["document_id"])

    return {
        **fetch_result,
        "metadata": metadata_result,
    }
```

## Benefits

1. **Granular Checkpointing**
   - If embedding fails, HTTP fetch is not re-run
   - If link extraction fails, content is already saved
   - Each expensive operation is checkpointed

2. **Better Testing**
   - Can test individual steps in isolation
   - Mock expensive operations (LLM calls)
   - Clear function boundaries

3. **Reusability**
   - Core functions can be used outside workflows
   - Steps can be composed differently
   - No monolithic "do everything" function

4. **Proper DBOS Patterns**
   - Use `@DBOS.transaction()` for database operations
   - Network I/O in separate steps
   - LLM calls isolated and checkpointed

5. **Better Error Handling**
   - Know exactly which step failed
   - Can retry individual steps
   - Clear failure recovery path

## Migration Path

1. **Phase 1**: Extract helper functions from `fetch_document()`
   - Keep `fetch_document()` as-is (backward compatible)
   - Add new focused functions

2. **Phase 2**: Create new workflow steps
   - Add new step functions in `workflows/fetch.py`
   - Keep old steps for backward compatibility

3. **Phase 3**: Update CLI to use new workflows
   - Switch `kurt content fetch` to new workflow
   - Deprecate old `fetch_and_index_workflow`

4. **Phase 4**: Remove old code
   - Delete deprecated workflows
   - Simplify `fetch_document()` or make it delegate to steps

## Cost Savings Example

**Before**: Fetch fails after embedding generation
- Re-run entire workflow
- Cost: 2x HTTP fetch + 2x embedding generation

**After**: Embedding generation fails
- Resume from `generate_embedding_step()`
- Cost: 1x HTTP fetch + 2x embedding generation
- **Savings**: 1x HTTP fetch (time + potential API costs)

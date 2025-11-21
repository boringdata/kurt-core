# DBOS Workflow Granularity Comparison

## Current Implementation (Too Coarse)

```
fetch_document_workflow()
└─> fetch_document_step()  ← ONE GIANT STEP
    ├─ Resolve document (DB lookup)
    ├─ HTTP fetch (network I/O) ❌ Can fail
    ├─ Generate embedding (LLM) ❌ Can fail + expensive
    ├─ Write to filesystem (I/O) ❌ Can fail
    ├─ Update database (transaction)
    └─ Extract links (parsing)

fetch_and_index_workflow()
└─> fetch_document_workflow(extract_metadata=True)  ← Just delegates!
    └─ (same as above)
```

**Problem**: If embedding fails, entire step re-runs (re-fetch HTTP!)

---

## Proposed Implementation (Better Balance)

```
fetch_document_workflow()
├─> resolve_document_step()           [Checkpoint 1] ✓
│   └─ Fast DB lookup
│
├─> fetch_content_step()              [Checkpoint 2] ✓
│   └─ HTTP fetch or CMS API
│   └─ Network I/O (can timeout/rate-limit)
│
├─> generate_embedding_step()         [Checkpoint 3] ✓ CRITICAL!
│   └─ EXPENSIVE LLM call (~$0.0001/call)
│   └─ If this fails, steps 1-2 don't re-run!
│
├─> save_document_transaction()       [Checkpoint 4] ✓
│   └─ Write file + update database (atomic)
│   └─ Uses @DBOS.transaction() for ACID
│
└─> extract_links_step()              [Checkpoint 5] ✓
    └─ Parse markdown + save links
    └─ Optional, doesn't block workflow

fetch_and_index_workflow()
├─> fetch_document_workflow()         [Checkpoint 1] ✓
│   └─ (all 5 steps above)
│
└─> extract_metadata_step()           [Checkpoint 2] ✓ CRITICAL!
    └─ EXPENSIVE LLM call (~$0.01/call)
    └─ If this fails, fetch is already done!
```

---

## Concrete Failure Scenarios

### Scenario 1: Network Timeout During Fetch

**Current**:
```
1. fetch_document_step() starts
2. HTTP fetch succeeds
3. Embedding generation succeeds
4. Database write FAILS (network partition)
5. Workflow restarts
6. ❌ Re-runs ENTIRE fetch_document_step()
   - Re-fetches HTTP (unnecessary!)
   - Re-generates embedding (wastes $0.0001!)
```

**Proposed**:
```
1. resolve_document_step() completes → [Checkpoint]
2. fetch_content_step() completes → [Checkpoint]
3. generate_embedding_step() completes → [Checkpoint]
4. save_document_transaction() FAILS
5. Workflow restarts
6. ✓ Skips steps 1-3 (already checkpointed)
7. ✓ Resumes from save_document_transaction()
   - No re-fetch!
   - No re-embedding!
```

**Savings**: 1 HTTP request + 1 LLM call

---

### Scenario 2: LLM API Timeout During Embedding

**Current**:
```
1. fetch_document_step() starts
2. HTTP fetch succeeds (5 seconds)
3. Embedding API times out (15 seconds)
4. ❌ Step fails, workflow restarts
5. ❌ Re-runs ENTIRE fetch_document_step()
   - Re-fetches HTTP (another 5 seconds wasted!)
```

**Proposed**:
```
1. resolve_document_step() completes → [Checkpoint]
2. fetch_content_step() completes → [Checkpoint]
3. generate_embedding_step() FAILS
4. Workflow restarts
5. ✓ Skips steps 1-2 (already checkpointed)
6. ✓ Resumes from generate_embedding_step()
   - No re-fetch! (saves 5 seconds)
```

**Savings**: 1 HTTP request + 5 seconds

---

### Scenario 3: Metadata Extraction Fails (Most Expensive!)

**Current**:
```
fetch_and_index_workflow()
└─> fetch_document_workflow(extract_metadata=True)
    ├─ fetch_document_step() succeeds
    └─ extract_metadata_step() FAILS

Workflow restarts:
❌ Re-runs fetch_document_step() (unnecessary!)
❌ Re-fetches content
❌ Re-generates embedding
```

**Proposed**:
```
fetch_and_index_workflow()
├─> fetch_document_workflow() completes → [Checkpoint]
│   ├─ All 5 sub-steps checkpointed
│   └─ Document fully fetched
│
└─> extract_metadata_step() FAILS

Workflow restarts:
✓ Skips fetch_document_workflow() (already checkpointed!)
✓ Resumes from extract_metadata_step()
✓ No re-fetch, no re-embedding!
```

**Savings**: 1 HTTP request + 1 embedding call + 5-10 seconds

---

## Cost Analysis

### Assumptions
- HTTP fetch: ~2-5 seconds
- Embedding generation: ~1-3 seconds + $0.0001/call
- Metadata extraction: ~5-10 seconds + $0.01/call
- Failure rate: ~5% (network issues, API timeouts, rate limits)

### Current Implementation (100 documents)
```
Total documents: 100
Failures: 5 (5%)

Failed fetches re-run ENTIRE step:
- 5 extra HTTP requests (10-25 seconds wasted)
- 5 extra embedding calls ($0.0005 wasted)

Failed metadata extractions re-run fetch step:
- Assuming 3 metadata failures
- 3 extra HTTP requests (6-15 seconds wasted)
- 3 extra embedding calls ($0.0003 wasted)

Total waste: 16-40 seconds + $0.0008
```

### Proposed Implementation (100 documents)
```
Total documents: 100
Failures: 5 (5%)

Failed embeddings resume from embedding step:
- 0 extra HTTP requests ✓
- 0 extra embeddings ✓

Failed metadata extractions resume from metadata step:
- 0 extra HTTP requests ✓
- 0 extra embeddings ✓

Total waste: 0 seconds + $0.00 ✓
```

**Savings per 100 documents**: ~20-30 seconds + $0.0008

**Savings per 10,000 documents**: ~30-50 minutes + $0.08

---

## Key Improvements

### 1. Checkpoint Granularity
- **Before**: 1 checkpoint (entire fetch)
- **After**: 5 checkpoints (each logical operation)

### 2. Failure Recovery
- **Before**: Re-run everything from scratch
- **After**: Resume from last successful checkpoint

### 3. LLM Cost Protection
- **Before**: Failed metadata → re-generate embedding ($$$)
- **After**: Failed metadata → resume from metadata step (✓)

### 4. DBOS Best Practices
- **Before**: No `@DBOS.transaction()` usage
- **After**: Proper transaction boundaries for DB operations

### 5. Debuggability
- **Before**: "fetch_document_step failed" (which part?)
- **After**: "generate_embedding_step failed" (exact failure point!)

---

## Migration Checklist

- [ ] Extract helper functions from `fetch_document()`
  - [ ] `resolve_or_create_document()`
  - [ ] `fetch_content_from_source()`
  - [ ] `generate_document_embedding()`
  - [ ] `save_document_content_and_metadata()`
  - [ ] `extract_and_save_document_links()`

- [ ] Create new workflow steps
  - [ ] `resolve_document_step()`
  - [ ] `fetch_content_step()`
  - [ ] `generate_embedding_step()`
  - [ ] `save_document_transaction()` (use `@DBOS.transaction()`)
  - [ ] `extract_links_step()`

- [ ] Refactor workflows
  - [ ] Update `fetch_document_workflow()` to use new steps
  - [ ] Update `fetch_and_index_workflow()` to properly checkpoint
  - [ ] Remove redundant `fetch_and_index_workflow()` delegation

- [ ] Update CLI integration
  - [ ] Test with `kurt content fetch`
  - [ ] Test with `kurt content index`
  - [ ] Verify backward compatibility

- [ ] Add tests
  - [ ] Unit tests for each helper function
  - [ ] Integration tests for workflow steps
  - [ ] End-to-end workflow tests
  - [ ] Checkpoint recovery tests (simulate failures)

---

## Conclusion

The current implementation treats workflows as **thin wrappers** around monolithic functions.

The proposed implementation treats workflows as **orchestrators** of focused, checkpointed steps.

**Key principle**: Each step should represent one **logical operation** that can **fail independently**.

If embedding generation can fail separately from HTTP fetch, they should be separate steps!

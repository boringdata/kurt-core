# Entity Resolution DBOS Workflow Refactoring

## Problem Statement

Current entity resolution has an 800-line monolithic function:
- `_create_entities_and_relationships()` does 6 different operations inline
- No checkpointing for expensive LLM calls during entity resolution
- If DSPy resolution fails halfway through, all previous LLM calls are lost ($$$ wasted)
- Hard to test individual pieces
- Complex transaction boundaries unclear

## Current vs. Proposed

### Before: 800-line Monolith
```python
def _create_entities_and_relationships(doc_to_kg_data, resolutions):
    # 100 lines: cleanup old entities
    # 50 lines: build mappings
    # 150 lines: resolve merge chains + cycle detection
    # 100 lines: group by canonical entity
    # 300 lines: create/link entities
    # 100 lines: create relationships
    # Total: 800 lines, no checkpoints, no clear boundaries
```

### After: Fine-Grained DBOS Steps
```python
@DBOS.workflow()
def entity_resolution_workflow(...):
    cleanup_old_entities_txn(...)           # 1 line - checkpointed
    groups = cluster_entities_step(...)     # 1 line - checkpointed
    resolutions = [resolve_group_step(g) for g in groups]  # 2 lines - checkpointed per group!
    entity_map = create_entities_txn(...)   # 1 line - checkpointed
    create_relationships_txn(...)           # 1 line - checkpointed
    # Total: ~30 lines main function
```

## Proposed Architecture

### Core Operations (in `content/entity_operations.py`)

Break down into focused, reusable functions:

```python
# 1. Clustering (pure compute)
def cluster_similar_entities(entities: list[dict]) -> list[list[dict]]:
    """Cluster entities using DBSCAN. Pure function, no I/O."""

# 2. Merge chain resolution (pure logic)
def resolve_merge_chains(resolutions: list[dict]) -> dict[str, str]:
    """Handle MERGE_WITH decisions + cycle detection. Pure function."""

# 3. Entity grouping (pure logic)
def group_by_canonical_entity(resolutions: list[dict], merge_map: dict) -> dict:
    """Group resolutions by canonical name. Pure function."""

# 4. Entity creation (database operation)
def create_entity_with_edges(session, canonical_name: str, entity_data: dict, docs: list) -> UUID:
    """Create entity + document edges. Database operation."""

# 5. Entity linking (database operation)
def link_entity_to_documents(session, entity_id: UUID, docs: list) -> None:
    """Link existing entity to documents. Database operation."""

# 6. Relationship creation (database operation)
def create_entity_relationships(session, relationships: list, entity_map: dict) -> int:
    """Create all relationships. Database operation."""
```

### DBOS Workflow Steps (in `workflows/entity_resolution.py`)

```python
# ============================================================================
# Steps - Lightweight compute/LLM operations
# ============================================================================

@DBOS.step()
def cluster_entities_step(entities: list[dict]) -> list[list[dict]]:
    """Step 1: Cluster similar entities using DBSCAN."""
    return cluster_similar_entities(entities)

@DBOS.step()
def resolve_entity_group_step(entity_group: list[dict]) -> dict:
    """
    Step 2: Resolve single entity group using LLM.

    ⚠️  EXPENSIVE: Calls DSPy/LLM
    ✅ CHECKPOINTED: Won't re-run if workflow restarts
    """
    # Call DSPy to decide: CREATE_NEW, MERGE_WITH, or link to existing
    return call_dspy_resolution(entity_group)

@DBOS.step()
def resolve_merge_chains_step(resolutions: list[dict]) -> dict[str, str]:
    """Step 3: Resolve merge chains and detect cycles."""
    return resolve_merge_chains(resolutions)

@DBOS.step()
def group_by_canonical_step(resolutions: list[dict], merge_map: dict) -> dict:
    """Step 4: Group resolutions by canonical entity."""
    return group_by_canonical_entity(resolutions, merge_map)

# ============================================================================
# Transactions - Database operations with ACID guarantees
# ============================================================================

@DBOS.transaction()
def cleanup_old_entities_txn(doc_ids: list[UUID], new_entity_names: set[str]):
    """
    Transaction 1: Clean up old document-entity links when re-indexing.

    ✅ ATOMIC: All deletes succeed or all roll back
    ✅ CHECKPOINTED: Won't re-run if workflow restarts after this
    """
    session = get_session()
    try:
        # 40 lines - delete stale links and orphaned entities
        for doc_id in doc_ids:
            cleanup_document_entities(session, doc_id, new_entity_names)
        session.commit()
    except:
        session.rollback()
        raise

@DBOS.transaction()
def create_entities_txn(
    canonical_groups: dict,
    entity_name_to_docs: dict
) -> dict[str, UUID]:
    """
    Transaction 2: Create/link all entities.

    ✅ ATOMIC: All entities created or none
    ✅ CHECKPOINTED: Won't re-run if workflow restarts after this

    Returns:
        dict mapping entity_name -> entity_id
    """
    session = get_session()
    entity_map = {}

    try:
        for canonical_name, group_resolutions in canonical_groups.items():
            decision = group_resolutions[0]["decision"]

            if decision == "CREATE_NEW":
                # Check for existing entity (re-indexing)
                existing = find_existing_entity(session, canonical_name, ...)
                if existing:
                    entity_id = existing.id
                else:
                    entity_id = create_entity_with_edges(
                        session,
                        canonical_name,
                        group_resolutions[0]["entity_data"],
                        entity_name_to_docs[canonical_name]
                    )
            else:
                entity_id = UUID(decision)
                link_entity_to_documents(
                    session,
                    entity_id,
                    entity_name_to_docs[canonical_name]
                )

            entity_map[canonical_name] = entity_id

        session.commit()
        return entity_map
    except:
        session.rollback()
        raise

@DBOS.transaction()
def create_relationships_txn(
    relationships: list[dict],
    entity_map: dict[str, UUID]
) -> int:
    """
    Transaction 3: Create all entity relationships.

    ✅ ATOMIC: All relationships created or none
    ✅ CHECKPOINTED: Won't re-run if workflow restarts after this
    """
    session = get_session()
    try:
        count = create_entity_relationships(session, relationships, entity_map)
        session.commit()
        return count
    except:
        session.rollback()
        raise

# ============================================================================
# Workflow - Orchestrates steps with automatic checkpointing
# ============================================================================

@DBOS.workflow()
def entity_resolution_workflow(
    doc_to_kg_data: dict[UUID, dict],
    new_entities: list[dict]
) -> dict[str, Any]:
    """
    Durable entity resolution workflow.

    If this crashes, DBOS automatically resumes from last completed step.

    Steps (each checkpointed):
    1. Cleanup old entities (txn)
    2. Cluster similar entities (step)
    3. Resolve each group with LLM (step per group) ← $$$ LLM calls checkpointed!
    4. Resolve merge chains (step)
    5. Group by canonical entity (step)
    6. Create/link all entities (txn)
    7. Create relationships (txn)

    Args:
        doc_to_kg_data: Dict mapping doc_id -> {new_entities, relationships}
        new_entities: All entities to resolve

    Returns:
        dict with entities_created, entities_linked, relationships_created
    """
    # Extract data
    all_doc_ids = list(doc_to_kg_data.keys())
    all_relationships = []
    entity_name_to_docs = {}

    for doc_id, kg_data in doc_to_kg_data.items():
        all_relationships.extend(kg_data["relationships"])
        for entity in kg_data["new_entities"]:
            if entity["name"] not in entity_name_to_docs:
                entity_name_to_docs[entity["name"]] = []
            entity_name_to_docs[entity["name"]].append({
                "document_id": doc_id,
                "confidence": entity["confidence"],
                "quote": entity.get("quote"),
            })

    # Step 1: Clean up old entities (transaction - checkpointed)
    new_entity_names = {e["name"] for e in new_entities}
    cleanup_old_entities_txn(all_doc_ids, new_entity_names)

    # Step 2: Cluster similar entities (step - checkpointed)
    entity_groups = cluster_entities_step(new_entities)

    # Step 3: Resolve each group with LLM (step per group - each checkpointed!)
    # ⚠️  CRITICAL: If this fails at group 5/10, groups 1-4 won't re-run (saves $$$)
    resolutions = []
    for group in entity_groups:
        resolution = resolve_entity_group_step(group)  # ← Checkpoint after each LLM call!
        resolutions.append(resolution)

    # Step 4: Resolve merge chains (step - checkpointed)
    merge_map = resolve_merge_chains_step(resolutions)

    # Step 5: Group by canonical entity (step - checkpointed)
    canonical_groups = group_by_canonical_step(resolutions, merge_map)

    # Step 6: Create/link all entities (transaction - checkpointed)
    entity_map = create_entities_txn(canonical_groups, entity_name_to_docs)

    # Step 7: Create relationships (transaction - checkpointed)
    relationships_count = create_relationships_txn(all_relationships, entity_map)

    # Summary
    entities_created = len([g for g, r in canonical_groups.items() if r[0]["decision"] == "CREATE_NEW"])
    entities_linked = len(canonical_groups) - entities_created

    return {
        "document_ids": [str(d) for d in all_doc_ids],
        "entities_created": entities_created,
        "entities_linked": entities_linked,
        "relationships_created": relationships_count,
        "workflow_id": DBOS.workflow_id,
    }
```

## Benefits

### 1. Granular Checkpointing
- **Before**: 10 LLM calls, crash at #7 → re-run all 10 ($$$ wasted)
- **After**: 10 LLM calls, crash at #7 → resume from #7 (only #7-10 re-run)
- **Savings**: 60% of LLM costs on retry

### 2. Clear Transaction Boundaries
```python
@DBOS.transaction()  # ← Automatic ACID guarantees
def create_entities_txn(...):
    # All entities created atomically
    # If any fails, all roll back
    # No partial entity states in database
```

### 3. Easy Testing
```python
# Test individual steps
def test_cluster_entities():
    groups = cluster_entities_step(mock_entities)
    assert len(groups) == 3

# Test transactions without workflow
def test_create_entities_txn():
    entity_map = create_entities_txn(mock_groups, mock_docs)
    assert len(entity_map) == 5
```

### 4. Readable Main Function
```python
# 30 lines (was 800!)
@DBOS.workflow()
def entity_resolution_workflow(...):
    cleanup_old_entities_txn(...)                    # 1 line
    groups = cluster_entities_step(...)              # 1 line
    resolutions = [resolve_entity_group_step(g) for g in groups]  # 2 lines
    merge_map = resolve_merge_chains_step(...)       # 1 line
    canonical_groups = group_by_canonical_step(...)  # 1 line
    entity_map = create_entities_txn(...)            # 1 line
    create_relationships_txn(...)                    # 1 line
    return summary                                   # 1 line
```

### 5. Better Observability
- DBOS dashboard shows which step failed
- Can see checkpoint progress (Step 3: 7/10 LLM calls completed)
- Retry from exact failure point

## File Structure

```
src/kurt/
  content/
    entity_operations.py         # ← Core functions (pure + DB operations)
    indexing_entity_resolution.py  # ← Keep for backward compatibility (deprecated)

  workflows/
    entity_resolution.py         # ← DBOS workflow + steps + transactions

  transactions/
    (No separate folder - keep transactions in workflows file for simplicity)
```

## Migration Path

### Phase 1: Extract Helper Functions (✅ Done)
- Added `find_existing_entity()` to `knowledge_graph.py`
- Added `find_or_create_document_entity_link()` to `knowledge_graph.py`

### Phase 2: Create DBOS Workflow (Next)
- Create `workflows/entity_resolution.py`
- Implement steps and transactions
- Keep old function for backward compatibility

### Phase 3: Update Usage
- Switch `finalize_knowledge_graph_from_index_results()` to call new workflow
- Add deprecation warning to old function

### Phase 4: Remove Old Code
- Delete `_create_entities_and_relationships()` after migration complete
- Remove backward compatibility shims

## Cost Savings Example

**Scenario**: Resolving 20 entity groups, crash at group 15

**Before**:
- Re-run entire workflow
- Cost: 40 LLM calls (20 original + 20 retry)
- Time: 2x full workflow duration

**After**:
- Resume from group 15
- Cost: 26 LLM calls (20 original + 6 retry from #15-20)
- Time: 1x full + 0.3x partial
- **Savings**: 35% fewer LLM calls, 40% less time

## Implementation Order

1. ✅ **Helpers in knowledge_graph.py** (already done)
2. ⏭️ **Create `workflows/entity_resolution.py`** with @DBOS decorators
3. ⏭️ **Extract pure functions** to `content/entity_operations.py`
4. ⏭️ **Update tests** to use new workflow
5. ⏭️ **Deprecate old function** with warning

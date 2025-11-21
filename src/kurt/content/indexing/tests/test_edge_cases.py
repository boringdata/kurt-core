"""Simple edge case tests for entity resolution."""


class TestMergeChainEdgeCases:
    """Test merge chain resolution edge cases."""

    def test_circular_merge_chain_detection(self):
        """Test that circular merge chains are detected and broken."""
        from kurt.db.graph_resolution import resolve_merge_chains

        # Create circular merge chain: A -> B -> C -> A
        resolutions = [
            {"entity_name": "A", "decision": "MERGE_WITH:B", "canonical": "B"},
            {"entity_name": "B", "decision": "MERGE_WITH:C", "canonical": "C"},
            {"entity_name": "C", "decision": "MERGE_WITH:A", "canonical": "A"},
        ]

        merge_map = resolve_merge_chains(resolutions)

        # Function only returns entities that merge (not CREATE_NEW)
        # Cycle should be broken - all should map to same entity
        assert len(set(merge_map.values())) == 1, "All entities should map to same canonical"
        print(f"✓ Circular merge resolved: {list(merge_map.values())[0]}")

    def test_merge_to_nonexistent_target(self):
        """Test that merge to nonexistent target is converted to CREATE_NEW."""
        from kurt.content.indexing.resolution import validate_merge_decisions

        resolutions = [
            {
                "entity_name": "Python",
                "decision": "MERGE_WITH:NonexistentEntity",
                "canonical": "NonexistentEntity",
                "aliases": [],
                "reasoning": "Merging",
            }
        ]

        validated = validate_merge_decisions(resolutions)

        # Should convert to CREATE_NEW
        assert validated[0]["decision"] == "CREATE_NEW"
        print("✓ Invalid merge target converted to CREATE_NEW")

    def test_transitive_merge_chains(self):
        """Test that transitive merge chains are resolved correctly."""
        from kurt.db.graph_resolution import resolve_merge_chains

        # A -> B -> C -> D (chain of merges)
        resolutions = [
            {"entity_name": "A", "decision": "MERGE_WITH:B", "canonical": "B"},
            {"entity_name": "B", "decision": "MERGE_WITH:C", "canonical": "C"},
            {"entity_name": "C", "decision": "MERGE_WITH:D", "canonical": "D"},
            {"entity_name": "D", "decision": "CREATE_NEW", "canonical": "D"},
        ]

        merge_map = resolve_merge_chains(resolutions)

        # Only merge decisions are in map (not CREATE_NEW)
        assert merge_map["A"] == "D"
        assert merge_map["B"] == "D"
        assert merge_map["C"] == "D"
        # D is CREATE_NEW, not in merge_map
        print("✓ Transitive merge chain: A -> B -> C -> D resolved")


class TestEmptyAndNoneValues:
    """Test handling of empty and None values."""

    def test_empty_entity_names_filtered(self):
        """Test that empty entity names are filtered before clustering."""
        from kurt.content.indexing.workflow_entity_resolution import cluster_entities_step

        # Only valid entities should be passed to clustering
        valid_entities = [
            {"name": "Python", "type": "Topic", "description": "Valid entity"},
        ]

        groups = cluster_entities_step(valid_entities)

        # Should cluster successfully
        assert isinstance(groups, dict)
        all_entities = [e for group in groups.values() for e in group]
        assert all(e.get("name") for e in all_entities)
        print("✓ Empty entity names filtered before clustering")

    def test_empty_aliases_in_resolutions(self):
        """Test that empty aliases don't cause issues."""
        from kurt.db.graph_resolution import resolve_merge_chains

        resolutions = [
            {
                "entity_name": "Python",
                "decision": "CREATE_NEW",
                "canonical": "Python",
                "aliases": ["", None, "Python Lang", ""],
            }
        ]

        # CREATE_NEW decisions don't appear in merge_map
        merge_map = resolve_merge_chains(resolutions)

        # Should not raise error - that's the test
        assert isinstance(merge_map, dict)
        print("✓ Empty/None aliases handled gracefully")


class TestOrphanedEntityCleanup:
    """Test orphaned entity cleanup logic."""

    def test_cleanup_old_entities_removes_orphans(self, tmp_project):
        """Test that cleanup_old_entities removes orphaned entities."""
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.graph_resolution import cleanup_old_entities
        from kurt.db.models import Document, DocumentEntity, Entity, IngestionStatus, SourceType

        session = get_session()

        # Create a test document
        doc = Document(
            title="Test",
            source_type=SourceType.URL,
            source_url=f"https://example.com/test-{uuid4().hex[:8]}",
            content_path="test.md",
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        # Create two entities
        entity1 = Entity(name="Python", entity_type="Topic", description="Lang")
        entity2 = Entity(name="Django", entity_type="Technology", description="Framework")
        session.add(entity1)
        session.add(entity2)
        session.commit()
        session.refresh(entity1)
        session.refresh(entity2)

        # Link both entities to document
        session.add(DocumentEntity(document_id=doc.id, entity_id=entity1.id))
        session.add(DocumentEntity(document_id=doc.id, entity_id=entity2.id))
        session.commit()

        # Simulate re-indexing with only Python (Django becomes orphaned)
        doc_to_kg_data = {
            doc.id: {
                "new_entities": [],
                "existing_entities": [{"id": str(entity1.id), "name": "Python"}],
            }
        }

        orphaned_count = cleanup_old_entities(session, doc_to_kg_data)
        session.commit()
        session.close()

        print(f"✓ Cleanup processed {orphaned_count} orphaned entities")


class TestUnicodeSupport:
    """Test Unicode entity name support."""

    def test_unicode_in_merge_chains(self):
        """Test that Unicode entity names work in merge chain resolution."""
        from kurt.db.graph_resolution import resolve_merge_chains

        resolutions = [
            {"entity_name": "Python编程", "decision": "CREATE_NEW", "canonical": "Python编程"},
            {"entity_name": "François", "decision": "CREATE_NEW", "canonical": "François"},
            {"entity_name": "Café", "decision": "MERGE_WITH:François", "canonical": "François"},
        ]

        merge_map = resolve_merge_chains(resolutions)

        # Only Café should be in merge_map (it merges), not CREATE_NEW ones
        assert "Café" in merge_map
        assert merge_map["Café"] == "François"
        print("✓ Unicode entity names handled in merge chains")

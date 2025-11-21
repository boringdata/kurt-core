"""Integration tests for SQLite to PostgreSQL content migration."""

from uuid import UUID, uuid4

from sqlmodel import select

from kurt.db.models import Document, Entity, SourceType, Workspace


class TestContentMigration:
    """Test migrating content from local SQLite to cloud PostgreSQL."""

    def test_migrate_documents_to_new_workspace(self, postgres_db):
        """Test migrating documents from local workspace to new cloud workspace."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        # Simulate local mode workspace (default UUID)
        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")

        # Create new cloud workspace
        cloud_workspace_id = uuid4()

        with client.get_session() as session:
            # Create cloud workspace
            cloud_ws = Workspace(
                id=cloud_workspace_id,
                name="Cloud Workspace",
                slug="cloud",
                owner_email="user@example.com",
            )
            session.add(cloud_ws)
            session.commit()

            # Create documents in "local" workspace
            doc1 = Document(
                tenant_id=local_workspace_id,
                title="Local Doc 1",
                source_type=SourceType.URL,
                source_url="https://local1.example.com",
            )
            doc2 = Document(
                tenant_id=local_workspace_id,
                title="Local Doc 2",
                source_type=SourceType.URL,
                source_url="https://local2.example.com",
            )
            session.add(doc1)
            session.add(doc2)
            session.commit()

            # Get document IDs before migration
            doc1_id = doc1.id
            doc2_id = doc2.id

            # Simulate migration: change tenant_id
            local_docs = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()

            for doc in local_docs:
                doc.tenant_id = cloud_workspace_id

            session.commit()

            # Verify migration
            # Local workspace should have no documents
            local_docs_after = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()
            assert len(local_docs_after) == 0

            # Cloud workspace should have all migrated documents
            cloud_docs = session.exec(
                select(Document).where(Document.tenant_id == cloud_workspace_id)
            ).all()
            assert len(cloud_docs) == 2

            # Verify document IDs and content unchanged
            cloud_doc_ids = {doc.id for doc in cloud_docs}
            assert doc1_id in cloud_doc_ids
            assert doc2_id in cloud_doc_ids

            cloud_titles = {doc.title for doc in cloud_docs}
            assert "Local Doc 1" in cloud_titles
            assert "Local Doc 2" in cloud_titles

    def test_migrate_entities_to_new_workspace(self, postgres_db):
        """Test migrating entities from local workspace to cloud workspace."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")
        cloud_workspace_id = uuid4()

        with client.get_session() as session:
            # Create cloud workspace
            cloud_ws = Workspace(id=cloud_workspace_id, name="Cloud Workspace", slug="cloud")
            session.add(cloud_ws)
            session.commit()

            # Create entities in local workspace
            entity1 = Entity(
                tenant_id=local_workspace_id,
                name="Local Entity 1",
                entity_type="PRODUCT",
            )
            entity2 = Entity(
                tenant_id=local_workspace_id,
                name="Local Entity 2",
                entity_type="ORGANIZATION",
            )
            session.add(entity1)
            session.add(entity2)
            session.commit()

            # Migrate entities
            local_entities = session.exec(
                select(Entity).where(Entity.tenant_id == local_workspace_id)
            ).all()

            for entity in local_entities:
                entity.tenant_id = cloud_workspace_id

            session.commit()

            # Verify migration
            local_entities_after = session.exec(
                select(Entity).where(Entity.tenant_id == local_workspace_id)
            ).all()
            assert len(local_entities_after) == 0

            cloud_entities = session.exec(
                select(Entity).where(Entity.tenant_id == cloud_workspace_id)
            ).all()
            assert len(cloud_entities) == 2

    def test_migrate_mixed_content(self, postgres_db):
        """Test migrating both documents and entities together."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")
        cloud_workspace_id = uuid4()

        with client.get_session() as session:
            # Create cloud workspace
            cloud_ws = Workspace(id=cloud_workspace_id, name="Cloud Workspace", slug="cloud")
            session.add(cloud_ws)
            session.commit()

            # Create mixed content in local workspace
            doc = Document(
                tenant_id=local_workspace_id,
                title="Local Doc",
                source_type=SourceType.URL,
                source_url="https://example.com",
            )
            entity = Entity(
                tenant_id=local_workspace_id, name="Local Entity", entity_type="PRODUCT"
            )
            session.add(doc)
            session.add(entity)
            session.commit()

            # Count items before migration
            total_items = len(
                session.exec(select(Document).where(Document.tenant_id == local_workspace_id)).all()
            ) + len(
                session.exec(select(Entity).where(Entity.tenant_id == local_workspace_id)).all()
            )
            assert total_items == 2

            # Migrate all content
            docs = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()
            entities = session.exec(
                select(Entity).where(Entity.tenant_id == local_workspace_id)
            ).all()

            for item in docs + entities:
                item.tenant_id = cloud_workspace_id

            session.commit()

            # Verify all content migrated
            cloud_total = len(
                session.exec(select(Document).where(Document.tenant_id == cloud_workspace_id)).all()
            ) + len(
                session.exec(select(Entity).where(Entity.tenant_id == cloud_workspace_id)).all()
            )
            assert cloud_total == 2

    def test_partial_migration(self, postgres_db):
        """Test migrating only specific documents (e.g., by source_url prefix)."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")
        cloud_workspace_id = uuid4()

        with client.get_session() as session:
            # Create cloud workspace
            cloud_ws = Workspace(id=cloud_workspace_id, name="Cloud Workspace", slug="cloud")
            session.add(cloud_ws)
            session.commit()

            # Create documents from different sources
            blog_doc1 = Document(
                tenant_id=local_workspace_id,
                title="Blog Post 1",
                source_type=SourceType.URL,
                source_url="https://blog.example.com/post1",
            )
            blog_doc2 = Document(
                tenant_id=local_workspace_id,
                title="Blog Post 2",
                source_type=SourceType.URL,
                source_url="https://blog.example.com/post2",
            )
            other_doc = Document(
                tenant_id=local_workspace_id,
                title="Other Doc",
                source_type=SourceType.URL,
                source_url="https://other.example.com/doc",
            )
            session.add(blog_doc1)
            session.add(blog_doc2)
            session.add(other_doc)
            session.commit()

            # Migrate only blog documents
            blog_docs = session.exec(
                select(Document).where(
                    Document.tenant_id == local_workspace_id,
                    Document.source_url.startswith("https://blog.example.com/"),  # type: ignore
                )
            ).all()

            for doc in blog_docs:
                doc.tenant_id = cloud_workspace_id

            session.commit()

            # Verify partial migration
            # Local workspace should still have 1 document
            local_docs = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()
            assert len(local_docs) == 1
            assert local_docs[0].title == "Other Doc"

            # Cloud workspace should have 2 blog documents
            cloud_docs = session.exec(
                select(Document).where(Document.tenant_id == cloud_workspace_id)
            ).all()
            assert len(cloud_docs) == 2
            cloud_titles = {doc.title for doc in cloud_docs}
            assert "Blog Post 1" in cloud_titles
            assert "Blog Post 2" in cloud_titles

    def test_migration_preserves_metadata(self, postgres_db):
        """Test that migration preserves document metadata."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")
        cloud_workspace_id = uuid4()

        with client.get_session() as session:
            # Create cloud workspace
            cloud_ws = Workspace(id=cloud_workspace_id, name="Cloud Workspace", slug="cloud")
            session.add(cloud_ws)
            session.commit()

            # Create document with metadata
            doc = Document(
                tenant_id=local_workspace_id,
                title="Test Document",
                source_type=SourceType.URL,
                source_url="https://example.com",
            )
            session.add(doc)
            session.commit()

            # Capture original metadata
            original_id = doc.id
            original_title = doc.title
            original_source_url = doc.source_url
            original_created_at = doc.created_at

            # Migrate
            doc.tenant_id = cloud_workspace_id
            session.commit()

            # Verify metadata preserved
            migrated_doc = session.exec(select(Document).where(Document.id == original_id)).first()

            assert migrated_doc is not None
            assert migrated_doc.id == original_id
            assert migrated_doc.title == original_title
            assert migrated_doc.source_url == original_source_url
            assert migrated_doc.created_at == original_created_at
            assert migrated_doc.tenant_id == cloud_workspace_id

    def test_dry_run_migration(self, postgres_db):
        """Test dry-run migration (count without changing)."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")

        with client.get_session() as session:
            # Create test content
            doc = Document(
                tenant_id=local_workspace_id,
                title="Test Doc",
                source_type=SourceType.URL,
                source_url="https://example.com",
            )
            entity = Entity(tenant_id=local_workspace_id, name="Test Entity", entity_type="PRODUCT")
            session.add(doc)
            session.add(entity)
            session.commit()

            # Dry run: count items without migrating
            docs_to_migrate = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()
            entities_to_migrate = session.exec(
                select(Entity).where(Entity.tenant_id == local_workspace_id)
            ).all()

            doc_count = len(docs_to_migrate)
            entity_count = len(entities_to_migrate)
            total_count = doc_count + entity_count

            # Verify counts
            assert doc_count == 1
            assert entity_count == 1
            assert total_count == 2

            # Verify nothing was changed (rollback to be sure)
            session.rollback()

            # Verify items still in local workspace
            local_docs_after = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()
            local_entities_after = session.exec(
                select(Entity).where(Entity.tenant_id == local_workspace_id)
            ).all()

            assert len(local_docs_after) == 1
            assert len(local_entities_after) == 1


class TestMigrationEdgeCases:
    """Test edge cases in content migration."""

    def test_migrate_zero_items(self, postgres_db):
        """Test migration when no items exist."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")
        cloud_workspace_id = uuid4()

        with client.get_session() as session:
            # Create cloud workspace
            cloud_ws = Workspace(id=cloud_workspace_id, name="Cloud Workspace", slug="cloud")
            session.add(cloud_ws)
            session.commit()

            # Count items (should be 0)
            docs = session.exec(
                select(Document).where(Document.tenant_id == local_workspace_id)
            ).all()
            entities = session.exec(
                select(Entity).where(Entity.tenant_id == local_workspace_id)
            ).all()

            assert len(docs) == 0
            assert len(entities) == 0

            # Migration should complete without errors
            for item in docs + entities:
                item.tenant_id = cloud_workspace_id

            session.commit()

    def test_migrate_to_same_workspace(self, postgres_db):
        """Test migrating to the same workspace (no-op)."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        workspace_id = uuid4()

        with client.get_session() as session:
            # Create workspace
            ws = Workspace(id=workspace_id, name="Workspace", slug="ws")
            session.add(ws)
            session.commit()

            # Create document
            doc = Document(
                tenant_id=workspace_id,
                title="Test Doc",
                source_type=SourceType.URL,
                source_url="https://example.com",
            )
            session.add(doc)
            session.commit()

            doc_id = doc.id

            # "Migrate" to same workspace
            doc.tenant_id = workspace_id
            session.commit()

            # Verify document unchanged
            same_doc = session.exec(select(Document).where(Document.id == doc_id)).first()
            assert same_doc is not None
            assert same_doc.tenant_id == workspace_id

    def test_migration_count_reporting(self, postgres_db):
        """Test accurate counting of items to migrate."""
        from kurt.db.base import get_database_client

        client = get_database_client()

        local_workspace_id = UUID("00000000-0000-0000-0000-000000000000")

        with client.get_session() as session:
            # Create various items
            docs = [
                Document(
                    tenant_id=local_workspace_id,
                    title=f"Doc {i}",
                    source_type=SourceType.URL,
                    source_url=f"https://example.com/{i}",
                )
                for i in range(5)
            ]

            entities = [
                Entity(
                    tenant_id=local_workspace_id,
                    name=f"Entity {i}",
                    entity_type="PRODUCT",
                )
                for i in range(3)
            ]

            for item in docs + entities:
                session.add(item)
            session.commit()

            # Count items
            doc_count = len(
                session.exec(select(Document).where(Document.tenant_id == local_workspace_id)).all()
            )
            entity_count = len(
                session.exec(select(Entity).where(Entity.tenant_id == local_workspace_id)).all()
            )
            total_count = doc_count + entity_count

            assert doc_count == 5
            assert entity_count == 3
            assert total_count == 8

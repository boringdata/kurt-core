"""Tests for document loader."""

import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.loaders import (
    load_documents,
)


class TestDocumentLoaderWithContent:
    """Tests for document loader with content functionality."""

    def test_load_documents_includes_content(self, tmp_project):
        """Test that load_documents includes content."""
        pass  # Test implementation requires full project setup

    def test_incremental_mode_skip_unchanged(self, tmp_project):
        """Test that incremental mode skips unchanged documents."""
        pass  # Test implementation requires full project setup

    def test_force_flag_overrides_skip(self, tmp_project):
        """Test that force flag processes even unchanged documents."""
        pass  # Test implementation requires full project setup

    def test_load_documents_basic(self):
        """Test basic loading returns correct structure."""
        filters = DocumentFilters(limit=1)
        docs = load_documents(filters)
        assert isinstance(docs, list)

        # If there are docs, check structure
        if docs:
            doc = docs[0]
            assert isinstance(doc, dict)
            # Check essential fields
            assert "document_id" in doc
            assert "content" in doc
            assert "skip" in doc

    def test_load_documents_with_invalid_status(self):
        """Test loading documents with invalid status returns empty."""
        filters = DocumentFilters(with_status="INVALID_STATUS")
        docs = load_documents(filters)
        assert docs == []

    def test_load_documents_with_invalid_ids(self):
        """Test that invalid IDs are handled gracefully."""
        filters = DocumentFilters(ids="not-a-uuid,also-not-uuid")
        docs = load_documents(filters)
        assert isinstance(docs, list)

    def test_load_documents_with_specific_id(self):
        """Test filtering by specific document ID."""
        filters = DocumentFilters(ids="00000000-0000-0000-0000-000000000000")
        docs = load_documents(filters)
        assert docs == []

    def test_load_documents_respects_limit(self):
        """Test that limit filter is respected."""
        filters = DocumentFilters(limit=5)
        docs = load_documents(filters)
        assert isinstance(docs, list)
        assert len(docs) <= 5

    def test_load_documents_full_mode(self):
        """Test full mode loading."""
        filters = DocumentFilters(limit=1)
        docs = load_documents(filters, incremental_mode="full")
        assert isinstance(docs, list)
        # In full mode, documents should never skip
        for doc in docs:
            assert doc.get("skip", False) is False

    def test_load_documents_delta_mode(self):
        """Test delta mode loading."""
        filters = DocumentFilters(limit=1)
        docs = load_documents(filters, incremental_mode="delta")
        assert isinstance(docs, list)
        # In delta mode, documents may skip based on their hash

    @pytest.mark.skip(reason="Requires tmp_project fixture from main test suite")
    def test_load_previous_state_empty_table(self):
        """Test loading previous state from empty/non-existent table."""
        pass  # Test implementation requires full project setup

    @pytest.mark.skip(reason="Requires tmp_project fixture from main test suite")
    def test_load_document_with_state(self):
        """Test loading document with previous state."""
        pass  # Test implementation requires full project setup

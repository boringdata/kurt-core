"""Tests for document link extraction and storage."""

from uuid import uuid4

import pytest

from kurt.content.fetch import extract_document_links, save_document_links
from kurt.content.filtering import get_document_links
from kurt.db.database import get_session
from kurt.db.models import Document, DocumentLink, IngestionStatus, SourceType


class TestExtractDocumentLinks:
    """Test markdown link extraction."""

    def test_extract_simple_link(self):
        """Test extracting a simple markdown link."""
        content = "See [Getting Started](https://example.com/getting-started) for details."
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/getting-started"
        assert links[0]["anchor_text"] == "Getting Started"

    def test_extract_relative_link(self):
        """Test resolving relative URLs."""
        content = "See [Next Page](./next) for more."
        source_url = "https://example.com/docs/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/docs/next"
        assert links[0]["anchor_text"] == "Next Page"

    def test_extract_parent_relative_link(self):
        """Test resolving parent relative URLs."""
        content = "See [Overview](../overview) for context."
        source_url = "https://example.com/docs/guides/tutorial"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/docs/overview"
        assert links[0]["anchor_text"] == "Overview"

    def test_skip_external_links(self):
        """Test that external links (different domain) are skipped."""
        content = """
        Internal: [Guide](https://example.com/guide)
        External: [Other Site](https://other.com/page)
        """
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        # Should only find internal link
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/guide"

    def test_skip_anchor_links(self):
        """Test that anchor links are skipped."""
        content = "Jump to [Section](#section) below."
        source_url = "https://example.com/page"

        links = extract_document_links(content, source_url)

        assert len(links) == 0

    def test_skip_mailto_links(self):
        """Test that mailto links are skipped."""
        content = "Contact [support](mailto:support@example.com) for help."
        source_url = "https://example.com/page"

        links = extract_document_links(content, source_url)

        assert len(links) == 0

    def test_extract_multiple_links(self):
        """Test extracting multiple links from content."""
        content = """
        Prerequisites: [Setup](https://example.com/setup)
        See also: [Advanced Guide](https://example.com/advanced)
        Related: [API Reference](https://example.com/api)
        """
        source_url = "https://example.com/tutorial"

        links = extract_document_links(content, source_url)

        assert len(links) == 3
        assert {link["anchor_text"] for link in links} == {
            "Setup",
            "Advanced Guide",
            "API Reference",
        }

    def test_truncate_long_anchor_text(self):
        """Test that anchor text is truncated to 500 chars."""
        long_text = "A" * 600
        content = f"See [{long_text}](https://example.com/page) for details."
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert len(links[0]["anchor_text"]) == 500
        assert links[0]["anchor_text"] == "A" * 500

    def test_link_with_title_attribute(self):
        """Test extracting link with title attribute."""
        content = '[Guide](https://example.com/guide "Helpful Guide")'
        source_url = "https://example.com/intro"

        links = extract_document_links(content, source_url)

        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/guide"
        assert links[0]["anchor_text"] == "Guide"

    def test_empty_content(self):
        """Test extracting from empty content."""
        links = extract_document_links("", "https://example.com/page")

        assert len(links) == 0

    def test_no_links_in_content(self):
        """Test content with no markdown links."""
        content = "This is plain text with no links."
        links = extract_document_links(content, "https://example.com/page")

        assert len(links) == 0


class TestSaveDocumentLinks:
    """Test saving document links to database."""

    def test_save_links_creates_records(self, tmp_project):
        """Test that save_document_links creates DocumentLink records."""
        session = get_session()
        # Create source and target documents
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target_doc = Document(
            title="Target",
            source_url="https://example.com/target",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(source_doc)
        session.add(target_doc)
        session.commit()
        session.refresh(source_doc)
        session.refresh(target_doc)

        # Save links
        links = [
            {"url": "https://example.com/target", "anchor_text": "See Target"},
        ]
        count = save_document_links(source_doc.id, links)

        assert count == 1

        # Verify link was created
        from sqlmodel import select

        link = session.exec(select(DocumentLink)).first()
        assert link is not None
        assert link.source_document_id == source_doc.id
        assert link.target_document_id == target_doc.id
        assert link.anchor_text == "See Target"

    def test_save_links_skips_unknown_targets(self, tmp_project):
        """Test that links to unknown URLs are not saved."""
        session = get_session()
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(source_doc)
        session.commit()

        # Try to save link to non-existent document
        links = [
            {"url": "https://example.com/nonexistent", "anchor_text": "Missing"},
        ]
        count = save_document_links(source_doc.id, links)

        assert count == 0

        # Verify no links were created
        from sqlmodel import select

        links_in_db = session.exec(select(DocumentLink)).all()
        assert len(links_in_db) == 0

    def test_save_links_deletes_existing(self, tmp_project):
        """Test that existing links are deleted on refetch."""
        session = get_session()
        # Create documents
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target1 = Document(
            title="Target 1",
            source_url="https://example.com/target1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target2 = Document(
            title="Target 2",
            source_url="https://example.com/target2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([source_doc, target1, target2])
        session.commit()

        # Save initial links
        links_v1 = [{"url": "https://example.com/target1", "anchor_text": "Target 1"}]
        save_document_links(source_doc.id, links_v1)

        # Verify first link exists
        from sqlmodel import select

        links_in_db = session.exec(select(DocumentLink)).all()
        assert len(links_in_db) == 1

        # Save new links (simulating refetch)
        links_v2 = [{"url": "https://example.com/target2", "anchor_text": "Target 2"}]
        save_document_links(source_doc.id, links_v2)

        # Verify old link was replaced
        links_in_db = session.exec(select(DocumentLink)).all()
        assert len(links_in_db) == 1
        assert links_in_db[0].target_document_id == target2.id

    def test_save_multiple_links(self, tmp_project):
        """Test saving multiple links at once."""
        session = get_session()
        # Create documents
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target1 = Document(
            title="Target 1",
            source_url="https://example.com/target1",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target2 = Document(
            title="Target 2",
            source_url="https://example.com/target2",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([source_doc, target1, target2])
        session.commit()

        # Save multiple links
        links = [
            {"url": "https://example.com/target1", "anchor_text": "First"},
            {"url": "https://example.com/target2", "anchor_text": "Second"},
        ]
        count = save_document_links(source_doc.id, links)

        assert count == 2

        # Verify both links were created
        from sqlmodel import select

        links_in_db = session.exec(select(DocumentLink)).all()
        assert len(links_in_db) == 2

    def test_save_empty_links_list(self, tmp_project):
        """Test saving empty links list."""
        session = get_session()
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(source_doc)
        session.commit()

        count = save_document_links(source_doc.id, [])

        assert count == 0


class TestGetDocumentLinks:
    """Test retrieving document links."""

    def test_get_outbound_links(self, tmp_project):
        """Test getting outbound links (links FROM a document)."""
        session = get_session()
        # Create documents
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target_doc = Document(
            title="Target",
            source_url="https://example.com/target",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([source_doc, target_doc])
        session.commit()

        # Create link
        link = DocumentLink(
            source_document_id=source_doc.id,
            target_document_id=target_doc.id,
            anchor_text="See Target",
        )
        session.add(link)
        session.commit()

        # Get outbound links
        links = get_document_links(str(source_doc.id), direction="outbound")

        assert len(links) == 1
        assert links[0]["source_title"] == "Source"
        assert links[0]["target_title"] == "Target"
        assert links[0]["anchor_text"] == "See Target"

    def test_get_inbound_links(self, tmp_project):
        """Test getting inbound links (links TO a document)."""
        session = get_session()
        # Create documents
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target_doc = Document(
            title="Target",
            source_url="https://example.com/target",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([source_doc, target_doc])
        session.commit()

        # Create link
        link = DocumentLink(
            source_document_id=source_doc.id,
            target_document_id=target_doc.id,
            anchor_text="See Target",
        )
        session.add(link)
        session.commit()

        # Get inbound links (to target_doc)
        links = get_document_links(str(target_doc.id), direction="inbound")

        assert len(links) == 1
        assert links[0]["source_title"] == "Source"
        assert links[0]["target_title"] == "Target"
        assert links[0]["anchor_text"] == "See Target"

    def test_get_links_with_partial_uuid(self, tmp_project):
        """Test getting links using partial UUID."""
        session = get_session()
        # Create documents
        source_doc = Document(
            title="Source",
            source_url="https://example.com/source",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        target_doc = Document(
            title="Target",
            source_url="https://example.com/target",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([source_doc, target_doc])
        session.commit()

        # Create link
        link = DocumentLink(
            source_document_id=source_doc.id,
            target_document_id=target_doc.id,
            anchor_text="Link",
        )
        session.add(link)
        session.commit()

        # Get links using partial UUID (first 8 chars)
        doc_id_str = str(source_doc.id)
        partial_id = doc_id_str[:8]
        links = get_document_links(partial_id, direction="outbound")

        assert len(links) == 1

    def test_get_links_no_results(self, tmp_project):
        """Test getting links when document has no links."""
        session = get_session()
        doc = Document(
            title="Isolated",
            source_url="https://example.com/isolated",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(doc)
        session.commit()

        links = get_document_links(str(doc.id), direction="outbound")

        assert len(links) == 0

    def test_get_links_invalid_direction(self, tmp_project):
        """Test that invalid direction raises ValueError."""
        session = get_session()
        doc = Document(
            title="Doc",
            source_url="https://example.com/doc",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add(doc)
        session.commit()

        with pytest.raises(ValueError, match="Invalid direction"):
            get_document_links(str(doc.id), direction="invalid")

    def test_get_links_nonexistent_document(self, tmp_project):
        """Test that nonexistent document raises ValueError."""
        fake_id = str(uuid4())

        with pytest.raises(ValueError):
            get_document_links(fake_id, direction="outbound")


class TestIntegration:
    """Integration tests for full link workflow."""

    def test_extract_and_save_workflow(self, tmp_project):
        """Test extracting links from content and saving to database."""
        session = get_session()
        # Create documents
        doc1 = Document(
            title="Introduction",
            source_url="https://example.com/intro",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        doc2 = Document(
            title="Setup",
            source_url="https://example.com/setup",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        doc3 = Document(
            title="Tutorial",
            source_url="https://example.com/tutorial",
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
        )
        session.add_all([doc1, doc2, doc3])
        session.commit()

        # Content with internal links
        content = """
        # Introduction

        Before you begin, complete the [Setup](https://example.com/setup).

        Then proceed to the [Tutorial](https://example.com/tutorial).
        """

        # Extract links
        links = extract_document_links(content, doc1.source_url)
        assert len(links) == 2

        # Save links
        count = save_document_links(doc1.id, links)
        assert count == 2

        # Query outbound links from doc1
        outbound = get_document_links(str(doc1.id), direction="outbound")
        assert len(outbound) == 2
        titles = {link["target_title"] for link in outbound}
        assert titles == {"Setup", "Tutorial"}

        # Query inbound links to doc2
        inbound = get_document_links(str(doc2.id), direction="inbound")
        assert len(inbound) == 1
        assert inbound[0]["source_title"] == "Introduction"
        assert inbound[0]["anchor_text"] == "Setup"

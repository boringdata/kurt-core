"""Tests for section-based document extraction."""

from unittest.mock import MagicMock, patch

import pytest

from kurt.content.indexing.extract import extract_document_metadata
from kurt.content.indexing.section_extraction import SectionExtractionResult, _merge_section_results
from kurt.content.indexing.splitting import DocumentSection, split_markdown_document


class TestDocumentSplitting:
    """Test document splitting functionality."""

    def test_small_document_no_split(self):
        """Small documents should not be split."""
        content = "# Short Document\n\nThis is a short document."
        sections = split_markdown_document(content, max_chars=5000)

        assert len(sections) == 1
        assert sections[0].content == content
        assert sections[0].heading is None  # Single section has no specific heading

    def test_large_document_with_headers(self):
        """Large documents should be split on headers."""
        content = (
            """# Introduction
This is the introduction section with some content.

## Section 1
"""
            + "x" * 3000
            + """

## Section 2
"""
            + "y" * 3000
            + """

## Section 3
Final section with content.
"""
        )
        sections = split_markdown_document(content, max_chars=5000, overlap_chars=200)

        assert len(sections) >= 2  # Should split due to size
        # Check that sections have appropriate headings
        headings = [s.heading for s in sections if s.heading]
        assert len(headings) > 0

    def test_overlap_regions(self):
        """Test that overlap regions are created between sections."""
        content = (
            """# Section 1
First section content that is reasonably long.
"""
            + "a" * 2000
            + """

# Section 2
Second section content that is also reasonably long.
"""
            + "b" * 2000
            + """

# Section 3
Third section content.
"""
            + "c" * 2000
        )

        sections = split_markdown_document(content, max_chars=3000, overlap_chars=200)

        # At least some sections should have overlap
        has_overlap = any(s.overlap_prefix or s.overlap_suffix for s in sections)
        assert has_overlap, "Sections should have overlap regions"

    def test_document_without_headers(self):
        """Documents without headers should be split by paragraphs."""
        content = (
            "Paragraph 1.\n" * 50 + "\n\n" + "Paragraph 2.\n" * 50 + "\n\n" + "Paragraph 3.\n" * 50
        )
        sections = split_markdown_document(content, max_chars=500, overlap_chars=50)

        assert len(sections) > 1  # Should split due to size
        # Sections should be numbered generically
        assert all("Section" in s.heading for s in sections if s.heading)


class TestSectionExtraction:
    """Test section-based extraction functionality."""

    def test_merge_section_results_entities(self):
        """Test that entity merging works correctly."""
        section_results = [
            SectionExtractionResult(
                section_id="s1",
                section_number=1,
                metadata={"content_type": "blog_post"},
                entities=[
                    {"name": "MotherDuck", "type": "Company", "description": "Cloud analytics"},
                    {"name": "DuckDB", "type": "Product", "description": "Database"},
                ],
                relationships=[],
                claims=[],
            ),
            SectionExtractionResult(
                section_id="s2",
                section_number=2,
                metadata={},
                entities=[
                    {
                        "name": "MotherDuck",
                        "type": "Company",
                        "description": "Analytics platform",
                    },  # Duplicate
                    {"name": "SQL", "type": "Technology", "description": "Query language"},  # New
                ],
                relationships=[],
                claims=[],
            ),
        ]

        merged = _merge_section_results(section_results)

        # Should have 3 unique entities (MotherDuck deduplicated)
        assert len(merged.entities) == 3
        entity_names = {e["name"] for e in merged.entities}
        assert entity_names == {"MotherDuck", "DuckDB", "SQL"}

    def test_merge_section_results_relationships(self):
        """Test that relationship merging works correctly."""
        section_results = [
            SectionExtractionResult(
                section_id="s1",
                section_number=1,
                metadata={},
                entities=[],
                relationships=[
                    {
                        "source_entity": "MotherDuck",
                        "target_entity": "DuckDB",
                        "relationship_type": "extends",
                    }
                ],
                claims=[],
            ),
            SectionExtractionResult(
                section_id="s2",
                section_number=2,
                metadata={},
                entities=[],
                relationships=[
                    {
                        "source_entity": "MotherDuck",
                        "target_entity": "DuckDB",
                        "relationship_type": "extends",  # Duplicate
                    },
                    {
                        "source_entity": "DuckDB",
                        "target_entity": "SQL",
                        "relationship_type": "uses",  # New
                    },
                ],
                claims=[],
            ),
        ]

        merged = _merge_section_results(section_results)

        # Should have 2 unique relationships (one deduplicated)
        assert len(merged.relationships) == 2

    def test_merge_section_results_claims(self):
        """Test that claim merging works correctly."""
        section_results = [
            SectionExtractionResult(
                section_id="s1",
                section_number=1,
                metadata={},
                entities=[],
                relationships=[],
                claims=[
                    {"statement": "MotherDuck is a cloud analytics platform", "type": "definition"}
                ],
            ),
            SectionExtractionResult(
                section_id="s2",
                section_number=2,
                metadata={},
                entities=[],
                relationships=[],
                claims=[
                    {
                        "statement": "MotherDuck is a cloud analytics platform",  # Duplicate
                        "type": "definition",
                    },
                    {
                        "statement": "DuckDB supports SQL queries",  # New
                        "type": "capability",
                    },
                ],
            ),
        ]

        merged = _merge_section_results(section_results)

        # Should have 2 unique claims (one deduplicated)
        assert len(merged.claims) == 2
        # Claims should have section references
        assert all("source_section" in claim for claim in merged.claims)

    def test_merge_with_errors(self):
        """Test that merging handles sections with errors gracefully."""
        section_results = [
            SectionExtractionResult(
                section_id="s1",
                section_number=1,
                metadata={"content_type": "blog_post"},
                entities=[{"name": "Entity1", "type": "Product"}],
                relationships=[],
                claims=[],
            ),
            SectionExtractionResult(
                section_id="s2",
                section_number=2,
                error="Extraction failed",  # This section had an error
            ),
            SectionExtractionResult(
                section_id="s3",
                section_number=3,
                metadata={},
                entities=[{"name": "Entity2", "type": "Company"}],
                relationships=[],
                claims=[],
            ),
        ]

        merged = _merge_section_results(section_results)

        # Should still merge successful sections
        assert len(merged.entities) == 2
        assert merged.sections_failed == 1
        assert merged.sections_processed == 3


class TestParallelProcessing:
    """Test parallel processing of sections."""

    def test_parallel_execution(self):
        """Test that sections are processed in parallel."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Track when each section starts processing
        processing_times = {}
        lock = threading.Lock()

        def mock_process_section(idx, section_id):
            """Mock section processing that tracks timing."""
            with lock:
                processing_times[section_id] = time.time()
            # Simulate processing time
            time.sleep(0.1)
            return idx, {"section_id": section_id, "processed": True}

        # Test with multiple sections
        sections = [f"section_{i}" for i in range(5)]
        results = [None] * len(sections)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(mock_process_section, i, s): i for i, s in enumerate(sections)
            }

            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        # Verify all sections were processed
        assert all(r is not None for r in results)
        assert len(results) == 5

        # Check that sections started processing close together (parallel)
        times = list(processing_times.values())
        times.sort()

        # If running in parallel with 3 workers:
        # First 3 should start almost simultaneously
        # Then the next 2 should start after first ones finish
        first_batch_delta = times[2] - times[0]  # Time between 1st and 3rd
        assert (
            first_batch_delta < 0.05
        ), f"First 3 sections should start within 50ms, got {first_batch_delta*1000:.0f}ms"

        # There should be a gap before the 4th section starts
        second_batch_delta = times[3] - times[2]  # Time between 3rd and 4th
        assert (
            second_batch_delta > 0.05
        ), f"4th section should wait for a worker, got {second_batch_delta*1000:.0f}ms"


class TestHybridExtraction:
    """Test the hybrid extraction approach."""

    @patch("kurt.content.indexing.extract.get_session")
    @patch("kurt.content.indexing.extract.load_document_content")
    def test_small_document_uses_single_extraction(self, mock_load_content, mock_get_session):
        """Small documents should use single extraction."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_doc = MagicMock()
        mock_doc.id = "12345678-1234-5678-1234-567812345678"
        mock_doc.title = "Test Doc"
        mock_doc.content_path = "test.md"
        mock_doc.status = "FETCHED"
        mock_session.get.return_value = mock_doc

        # Small document (< 5000 chars)
        mock_load_content.return_value = "Small document content"

        with patch("kurt.content.indexing.extract.dspy.ChainOfThought") as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_result = MagicMock()
            mock_result.metadata = '{"content_type": "blog_post"}'
            mock_result.entities = "[]"
            mock_result.relationships = "[]"
            mock_result.claims = "[]"
            mock_extractor.return_value = mock_result
            mock_extractor_class.return_value = mock_extractor

            # This should NOT trigger section-based extraction
            with patch("kurt.content.indexing.splitting.split_markdown_document") as mock_split:
                # Run extraction
                result = extract_document_metadata("test-id")

                # Verify split was not called
                mock_split.assert_not_called()

    @patch("kurt.content.indexing.extract.get_session")
    @patch("kurt.content.indexing.extract.load_document_content")
    def test_large_document_uses_section_extraction(self, mock_load_content, mock_get_session):
        """Large documents should use section-based extraction."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_doc = MagicMock()
        mock_doc.id = "12345678-1234-5678-1234-567812345678"
        mock_doc.title = "Test Doc"
        mock_doc.content_path = "test.md"
        mock_doc.status = "FETCHED"
        mock_session.get.return_value = mock_doc

        # Large document (> 5000 chars)
        mock_load_content.return_value = "x" * 6000

        with patch("kurt.content.indexing.extract.dspy.ChainOfThought") as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_result = MagicMock()
            mock_result.metadata = '{"content_type": "blog_post"}'
            mock_result.entities = "[]"
            mock_result.relationships = "[]"
            mock_result.claims = "[]"
            mock_extractor.return_value = mock_result
            mock_extractor_class.return_value = mock_extractor

            # This SHOULD trigger section-based extraction
            with patch("kurt.content.indexing.splitting.split_markdown_document") as mock_split:
                mock_split.return_value = [
                    DocumentSection(
                        section_id="s1",
                        section_number=1,
                        heading="Section 1",
                        content="x" * 3000,
                        start_offset=0,
                        end_offset=3000,
                    ),
                    DocumentSection(
                        section_id="s2",
                        section_number=2,
                        heading="Section 2",
                        content="x" * 3000,
                        start_offset=3000,
                        end_offset=6000,
                    ),
                ]

                # Run extraction
                result = extract_document_metadata("test-id")

                # Verify split was called
                mock_split.assert_called_once()
                # Verify extractor was called multiple times (once per section)
                assert mock_extractor.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

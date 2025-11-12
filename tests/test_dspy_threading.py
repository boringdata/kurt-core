"""Test DSPy threading behavior in index module."""

import asyncio
import threading
import unittest
import uuid
from unittest.mock import MagicMock, patch

import dspy

from kurt.content.index import (
    _get_extract_metadata_signature,
    batch_extract_document_metadata,
    extract_document_metadata,
)


class TestDSPyThreading(unittest.TestCase):
    """Test that DSPy configuration works correctly in threaded environments."""

    def setUp(self):
        """Reset DSPy before each test."""
        # Clear any existing DSPy configuration
        try:
            dspy.settings.lm = None
        except Exception:
            pass

    def test_single_thread_configuration(self):
        """Test that DSPy can be configured in a single thread."""
        with (
            patch("kurt.db.database.get_session") as mock_session,
            patch("kurt.config.load_config") as mock_config,
            patch("kurt.config.get_config_or_default") as mock_config_default,
        ):
            # Mock configuration
            mock_config_default.return_value = MagicMock(INDEXING_LLM_MODEL="openai/gpt-4o-mini")
            mock_config.return_value = MagicMock(get_absolute_sources_path=lambda: MagicMock())

            # Mock document with a proper UUID
            test_uuid = str(uuid.uuid4())
            mock_doc = MagicMock()
            mock_doc.id = test_uuid
            mock_doc.ingestion_status.value = "FETCHED"
            mock_doc.content_path = "test.md"
            mock_doc.indexed_with_hash = None
            mock_doc.content_type = None
            mock_doc.title = "Test Doc"
            mock_doc.primary_topics = []
            mock_doc.tools_technologies = []

            # Mock session
            mock_sess = MagicMock()
            mock_sess.get.return_value = mock_doc
            mock_session.return_value = mock_sess

            # Mock file operations
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.read_text", return_value="Test content"),
                patch("kurt.utils.calculate_content_hash", return_value="hash123"),
                patch("kurt.utils.get_git_commit_hash", return_value="commit123"),
                patch("kurt.db.metadata_sync.write_frontmatter_to_file"),
            ):
                # Mock DSPy extractor
                with patch("dspy.ChainOfThought") as mock_cot:
                    mock_extractor = MagicMock()
                    mock_metadata = MagicMock()
                    mock_metadata.content_type.value = "guide"
                    mock_metadata.primary_topics = ["test"]
                    mock_metadata.tools_technologies = []
                    mock_metadata.extracted_title = None
                    mock_metadata.has_code_examples = False
                    mock_metadata.has_step_by_step_procedures = False
                    mock_metadata.has_narrative_structure = False
                    mock_extractor.return_value = MagicMock(metadata=mock_metadata)
                    mock_cot.return_value = mock_extractor

                    # This should configure DSPy without issues
                    result = extract_document_metadata(test_uuid, force=False)

                    # Verify DSPy is configured
                    self.assertIsNotNone(dspy.settings.lm)
                    self.assertEqual(result["document_id"], test_uuid)

    def test_multiple_threads_share_configuration(self):
        """Test that DSPy must be configured in main thread before worker threads."""
        results = []
        errors = []

        # Pre-configure DSPy in the main thread (required for threading)
        lm = dspy.LM("openai/gpt-4o-mini")
        dspy.configure(lm=lm)

        with (
            patch("kurt.db.database.get_session") as mock_session,
            patch("kurt.config.load_config") as mock_config,
            patch("kurt.config.get_config_or_default") as mock_config_default,
        ):
            # Mock configuration
            mock_config_default.return_value = MagicMock(INDEXING_LLM_MODEL="openai/gpt-4o-mini")
            mock_config.return_value = MagicMock(get_absolute_sources_path=lambda: MagicMock())

            # Create UUIDs for testing
            test_uuids = [str(uuid.uuid4()) for _ in range(5)]

            def create_mock_doc(doc_id):
                """Create a mock document with unique ID."""
                mock_doc = MagicMock()
                # Store the actual UUID object in the mock document
                try:
                    mock_doc.id = uuid.UUID(doc_id)
                except ValueError:
                    mock_doc.id = doc_id
                mock_doc.ingestion_status.value = "FETCHED"
                mock_doc.content_path = f"{doc_id}.md"
                mock_doc.indexed_with_hash = None
                mock_doc.content_type = None
                mock_doc.title = f"Test Doc {str(doc_id)[:8]}"
                mock_doc.primary_topics = []
                mock_doc.tools_technologies = []
                return mock_doc

            # Thread-safe mock setup
            import threading

            docs_lock = threading.Lock()
            docs = {}

            def mock_get_fn(doc_class, doc_id):
                # Convert UUID object to string if needed
                doc_id_str = str(doc_id) if hasattr(doc_id, "hex") else doc_id
                with docs_lock:
                    if doc_id_str not in docs:
                        docs[doc_id_str] = create_mock_doc(doc_id_str)
                    return docs[doc_id_str]

            # Mock session
            mock_sess = MagicMock()
            mock_sess.get.side_effect = mock_get_fn
            mock_session.return_value = mock_sess

            # Mock file operations
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.read_text", return_value="Test content"),
                patch("kurt.utils.calculate_content_hash", return_value="hash123"),
                patch("kurt.utils.get_git_commit_hash", return_value="commit123"),
                patch("kurt.db.metadata_sync.write_frontmatter_to_file"),
            ):
                # Mock DSPy extractor
                with patch("dspy.ChainOfThought") as mock_cot:
                    mock_extractor = MagicMock()
                    mock_metadata = MagicMock()
                    mock_metadata.content_type.value = "guide"
                    mock_metadata.primary_topics = ["test"]
                    mock_metadata.tools_technologies = []
                    mock_metadata.extracted_title = None
                    mock_metadata.has_code_examples = False
                    mock_metadata.has_step_by_step_procedures = False
                    mock_metadata.has_narrative_structure = False
                    mock_extractor.return_value = MagicMock(metadata=mock_metadata)
                    mock_cot.return_value = mock_extractor

                    def worker(doc_id):
                        try:
                            # Pass a pre-configured extractor to avoid threading issues
                            result = extract_document_metadata(
                                doc_id, extractor=mock_extractor, force=False
                            )
                            results.append(result)
                        except Exception as e:
                            errors.append(str(e))

                    # Run multiple threads with valid UUIDs
                    threads = []
                    for test_uuid in test_uuids:
                        t = threading.Thread(target=worker, args=(test_uuid,))
                        threads.append(t)
                        t.start()

                    # Wait for all threads
                    for t in threads:
                        t.join()

                    # All threads should succeed when extractor is passed
                    if errors:
                        self.fail(f"Thread errors: {errors}")
                    self.assertEqual(len(results), 5, f"Results: {results}, Errors: {errors}")
                    self.assertEqual(len(errors), 0)

                    # DSPy should remain configured
                    self.assertEqual(dspy.settings.lm, lm)

    def test_extract_metadata_signature_generation(self):
        """Test that signature class can be generated in any thread."""
        signatures = []

        def worker():
            sig = _get_extract_metadata_signature()
            signatures.append(sig)

        # Run in multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should get a signature class
        self.assertEqual(len(signatures), 3)
        for sig in signatures:
            self.assertTrue(issubclass(sig, dspy.Signature))

    def test_batch_extraction_with_threading(self):
        """Test batch extraction handles threading correctly - runs sync test of async function."""
        doc_ids = [str(uuid.uuid4()) for _ in range(10)]

        with patch("kurt.config.get_config_or_default") as mock_config_default:
            mock_config_default.return_value = MagicMock(INDEXING_LLM_MODEL="openai/gpt-4o-mini")

            # Mock DSPy
            with patch("dspy.ChainOfThought") as mock_cot, patch("dspy.LM"):
                mock_extractor = MagicMock()
                mock_metadata = MagicMock()
                mock_metadata.content_type.value = "guide"
                mock_metadata.primary_topics = ["test"]
                mock_metadata.tools_technologies = []
                mock_cot.return_value = mock_extractor
                mock_extractor.return_value = MagicMock(metadata=mock_metadata)

                # Patch extract_document_metadata after DSPy setup
                with patch("kurt.content.index.extract_document_metadata") as mock_extract:
                    mock_extract.return_value = {
                        "document_id": "test-id",
                        "title": "Test Doc",
                        "content_type": "guide",
                        "topics": ["test"],
                        "tools": [],
                        "skipped": False,
                    }

                    # This should handle threading internally - run async function in sync test
                    result = asyncio.run(
                        batch_extract_document_metadata(doc_ids, max_concurrent=3, force=False)
                    )

                    # Verify results
                    self.assertEqual(result["total"], 10)
                    self.assertGreaterEqual(result["succeeded"], 0)

    def test_dspy_reuse_existing_configuration(self):
        """Test that existing DSPy configuration is reused."""
        # Pre-configure DSPy
        lm = dspy.LM("openai/gpt-4o-mini")
        dspy.configure(lm=lm)

        with (
            patch("kurt.db.database.get_session") as mock_session,
            patch("kurt.config.load_config") as mock_config,
            patch("kurt.config.get_config_or_default") as mock_config_default,
        ):
            # Mock configuration
            mock_config_default.return_value = MagicMock(INDEXING_LLM_MODEL="openai/gpt-4o-mini")
            mock_config.return_value = MagicMock(get_absolute_sources_path=lambda: MagicMock())

            # Mock document with a proper UUID
            test_uuid = str(uuid.uuid4())
            mock_doc = MagicMock()
            mock_doc.id = test_uuid
            mock_doc.ingestion_status.value = "FETCHED"
            mock_doc.content_path = "test.md"
            mock_doc.indexed_with_hash = None
            mock_doc.content_type = None
            mock_doc.title = "Test Doc"
            mock_doc.primary_topics = []
            mock_doc.tools_technologies = []

            # Mock session
            mock_sess = MagicMock()
            mock_sess.get.return_value = mock_doc
            mock_session.return_value = mock_sess

            # Mock file operations
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.read_text", return_value="Test content"),
                patch("kurt.utils.calculate_content_hash", return_value="hash123"),
                patch("kurt.utils.get_git_commit_hash", return_value="commit123"),
                patch("kurt.db.metadata_sync.write_frontmatter_to_file"),
            ):
                # Mock DSPy extractor
                with patch("dspy.ChainOfThought") as mock_cot:
                    mock_extractor = MagicMock()
                    mock_metadata = MagicMock()
                    mock_metadata.content_type.value = "guide"
                    mock_metadata.primary_topics = ["test"]
                    mock_metadata.tools_technologies = []
                    mock_metadata.extracted_title = None
                    mock_metadata.has_code_examples = False
                    mock_metadata.has_step_by_step_procedures = False
                    mock_metadata.has_narrative_structure = False
                    mock_extractor.return_value = MagicMock(metadata=mock_metadata)
                    mock_cot.return_value = mock_extractor

                    # This should reuse existing configuration
                    with patch("kurt.content.index.logger"):
                        extract_document_metadata(test_uuid, force=False)

                        # Should still have the same lm configured
                        self.assertEqual(dspy.settings.lm, lm)


if __name__ == "__main__":
    unittest.main()

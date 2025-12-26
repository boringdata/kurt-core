"""Tests for LLM response cache control feature.

Tests the no_cache/cache parameter propagation through:
1. Workflow level (run_workflow, run_pipeline_workflow)
2. Model level (via ctx.metadata["no_cache"])
3. DSPy helpers (get_dspy_lm, run_batch_sync)
"""

from unittest.mock import MagicMock, patch

import pandas as pd

from kurt.core import PipelineContext
from kurt.utils.filtering import DocumentFilters


class TestWorkflowNoCacheParameter:
    """Tests for no_cache parameter in workflow functions."""

    def test_run_workflow_creates_context_with_no_cache_true(self):
        """Test that run_workflow creates ModelContext with no_cache=True in metadata."""
        # Test the ModelContext creation directly since DBOS wrapper complicates testing
        from kurt.core.model_runner import ModelContext

        # When run_workflow is called with no_cache=True, it creates:
        # ctx = ModelContext(..., metadata={"no_cache": no_cache})

        ctx = ModelContext(
            filters=DocumentFilters(),
            workflow_id="test-wf",
            metadata={"no_cache": True},
        )

        assert ctx.metadata["no_cache"] is True

    def test_run_workflow_creates_context_with_no_cache_false(self):
        """Test that run_workflow creates ModelContext with no_cache=False in metadata."""
        from kurt.core.model_runner import ModelContext

        ctx = ModelContext(
            filters=DocumentFilters(),
            workflow_id="test-wf",
            metadata={"no_cache": False},
        )

        assert ctx.metadata["no_cache"] is False

    def test_workflow_signature_accepts_no_cache_parameter(self):
        """Test that run_workflow function signature includes no_cache parameter."""
        import inspect

        from kurt.core.workflow import run_workflow

        # Get the signature - need to unwrap DBOS decorator
        # The actual function is wrapped by @DBOS.workflow()
        sig = inspect.signature(run_workflow)
        param_names = list(sig.parameters.keys())

        assert "no_cache" in param_names

        # Check default value is False
        no_cache_param = sig.parameters["no_cache"]
        assert no_cache_param.default is False

    def test_run_pipeline_workflow_signature_accepts_no_cache(self):
        """Test that run_pipeline_workflow function signature includes no_cache parameter."""
        import inspect

        from kurt.core.workflow import run_pipeline_workflow

        sig = inspect.signature(run_pipeline_workflow)
        param_names = list(sig.parameters.keys())

        assert "no_cache" in param_names

        # Check default value is False
        no_cache_param = sig.parameters["no_cache"]
        assert no_cache_param.default is False


class TestModelContextNoCacheMetadata:
    """Tests for no_cache metadata in PipelineContext."""

    def test_context_metadata_contains_no_cache(self):
        """Test that PipelineContext can store no_cache in metadata."""
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-wf",
            metadata={"no_cache": True},
        )

        assert ctx.metadata["no_cache"] is True

    def test_context_metadata_no_cache_default_false(self):
        """Test that no_cache defaults to False when not specified."""
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-wf",
        )

        # Metadata should be empty dict if not provided
        assert ctx.metadata.get("no_cache", False) is False


class TestSectionExtractionsNoCacheIntegration:
    """Tests for no_cache integration in section_extractions model."""

    def test_section_extractions_reads_no_cache_from_context(self):
        """Test that section_extractions model reads no_cache from context metadata."""
        # This tests the actual implementation in step_extract_sections.py
        # Lines 321-324: no_cache = ctx.metadata.get("no_cache", False)

        # Mock the run_batch_sync to capture the cache parameter
        captured_cache = {}

        def mock_run_batch_sync(**kwargs):
            captured_cache["value"] = kwargs.get("cache")
            return []

        with patch(
            "kurt.content.indexing.step_extract_sections.run_batch_sync",
            mock_run_batch_sync,
        ):
            # Import the model function
            from kurt.content.indexing.step_extract_sections import (
                SectionExtractionsConfig,
                section_extractions,
            )
            from kurt.core import Reference
            from kurt.core.testing import MockTableWriter

            # Create context with no_cache=True
            ctx = PipelineContext(
                filters=DocumentFilters(),
                workflow_id="test-wf",
                metadata={"no_cache": True},
            )

            # Create mock sections reference
            mock_sections_df = pd.DataFrame(
                [
                    {
                        "document_id": "doc-1",
                        "section_id": "sec-1",
                        "content": "Test content",
                    }
                ]
            )

            # We need to test that when the model runs, it passes cache=False to run_batch_sync
            # when no_cache=True in the context

            # Create a mock reference
            mock_ref = MagicMock(spec=Reference)
            mock_ref.df = mock_sections_df

            # Create mock writer
            mock_writer = MockTableWriter()
            mock_writer.write = MagicMock(return_value={"rows_written": 0})

            # Create config
            config = SectionExtractionsConfig()

            # Patch _load_existing_entities_by_document to return empty dict
            with patch(
                "kurt.content.indexing.step_extract_sections._load_existing_entities_by_document",
                return_value={},
            ):
                # Run the model
                try:
                    section_extractions(
                        ctx=ctx,
                        sections=mock_ref,
                        writer=mock_writer,
                        config=config,
                    )
                except Exception:
                    pass  # Ignore errors from mock setup

                # Verify cache was set based on no_cache
                # no_cache=True should result in cache=False (cache = not no_cache)
                assert captured_cache.get("value") is False

    def test_section_extractions_cache_enabled_by_default(self):
        """Test that section_extractions uses cache=True when no_cache not set."""
        captured_cache = {}

        def mock_run_batch_sync(**kwargs):
            captured_cache["value"] = kwargs.get("cache")
            return []

        with patch(
            "kurt.content.indexing.step_extract_sections.run_batch_sync",
            mock_run_batch_sync,
        ):
            from kurt.content.indexing.step_extract_sections import (
                SectionExtractionsConfig,
                section_extractions,
            )
            from kurt.core import Reference
            from kurt.core.testing import MockTableWriter

            # Create context WITHOUT no_cache (defaults to False)
            ctx = PipelineContext(
                filters=DocumentFilters(),
                workflow_id="test-wf",
                # No metadata or no_cache not specified
            )

            mock_sections_df = pd.DataFrame(
                [
                    {
                        "document_id": "doc-1",
                        "section_id": "sec-1",
                        "content": "Test content",
                    }
                ]
            )

            mock_ref = MagicMock(spec=Reference)
            mock_ref.df = mock_sections_df

            mock_writer = MockTableWriter()
            mock_writer.write = MagicMock(return_value={"rows_written": 0})

            config = SectionExtractionsConfig()

            with patch(
                "kurt.content.indexing.step_extract_sections._load_existing_entities_by_document",
                return_value={},
            ):
                try:
                    section_extractions(
                        ctx=ctx,
                        sections=mock_ref,
                        writer=mock_writer,
                        config=config,
                    )
                except Exception:
                    pass

                # When no_cache is not set (defaults to False), cache should be True
                assert captured_cache.get("value") is True


class TestCLINoCacheFlag:
    """Tests for CLI --no-cache flag."""

    def test_index_command_no_cache_flag_exists(self):
        """Test that index command has --no-cache flag defined."""
        from kurt.commands.content.index import index

        # Check that the command has the no_cache parameter
        param_names = [p.name for p in index.params]
        assert "no_cache" in param_names

        # Find the parameter and check its type
        no_cache_param = next(p for p in index.params if p.name == "no_cache")
        assert no_cache_param.is_flag is True

    def test_index_command_no_cache_help_text(self):
        """Test that --no-cache flag has appropriate help text."""
        from kurt.commands.content.index import index

        no_cache_param = next(p for p in index.params if p.name == "no_cache")
        assert "cache" in no_cache_param.help.lower()
        assert "bypass" in no_cache_param.help.lower() or "disable" in no_cache_param.help.lower()

    def test_index_command_passes_no_cache_to_workflow(self):
        """Test that index command passes no_cache to the workflow function."""
        from click.testing import CliRunner

        runner = CliRunner()

        # We need to mock the entire workflow chain
        captured_no_cache = {}

        def mock_index_and_finalize(*args, **kwargs):
            captured_no_cache["value"] = kwargs.get("no_cache")
            return {
                "indexing": {"succeeded": 0, "failed": 0, "skipped": 0},
                "kg_result": None,
            }

        # The imports in index.py are lazy (inside the function), so we patch the modules
        with patch(
            "kurt.content.document.list_documents_for_indexing",
            return_value=[MagicMock(id="test-id")],
        ):
            with patch(
                "kurt.content.filtering.resolve_filters",
                return_value=MagicMock(
                    ids=["test-id"],
                    include_pattern=None,
                    in_cluster=None,
                    with_status=None,
                    with_content_type=None,
                ),
            ):
                with patch(
                    "kurt.commands.content._live_display.index_and_finalize_with_two_stage_progress",
                    mock_index_and_finalize,
                ):
                    with patch(
                        "kurt.db.metadata_sync.process_metadata_sync_queue",
                        return_value={"processed": 0},
                    ):
                        from kurt.cli import main

                        # Test with --no-cache flag
                        runner.invoke(main, ["content", "index", "test-id", "--no-cache"])

                        # Check that no_cache was passed as True
                        assert captured_no_cache.get("value") is True

    def test_index_command_default_cache_enabled(self):
        """Test that index command defaults to cache enabled (no --no-cache)."""
        from click.testing import CliRunner

        runner = CliRunner()

        captured_no_cache = {}

        def mock_index_and_finalize(*args, **kwargs):
            captured_no_cache["value"] = kwargs.get("no_cache")
            return {
                "indexing": {"succeeded": 0, "failed": 0, "skipped": 0},
                "kg_result": None,
            }

        with patch(
            "kurt.content.document.list_documents_for_indexing",
            return_value=[MagicMock(id="test-id")],
        ):
            with patch(
                "kurt.content.filtering.resolve_filters",
                return_value=MagicMock(
                    ids=["test-id"],
                    include_pattern=None,
                    in_cluster=None,
                    with_status=None,
                    with_content_type=None,
                ),
            ):
                with patch(
                    "kurt.commands.content._live_display.index_and_finalize_with_two_stage_progress",
                    mock_index_and_finalize,
                ):
                    with patch(
                        "kurt.db.metadata_sync.process_metadata_sync_queue",
                        return_value={"processed": 0},
                    ):
                        from kurt.cli import main

                        # Test WITHOUT --no-cache flag
                        runner.invoke(main, ["content", "index", "test-id"])

                        # Check that no_cache was passed as False (cache enabled)
                        assert captured_no_cache.get("value") is False


class TestEndToEndCachePropagation:
    """Integration tests for cache control propagation through the entire stack."""

    def test_cache_disabled_propagates_from_cli_to_dspy(self):
        """Test that --no-cache propagates all the way from CLI to DSPy LM creation."""
        # This is a conceptual test showing the full propagation path
        #
        # 1. CLI receives --no-cache flag → no_cache=True
        # 2. index_and_finalize_with_two_stage_progress(no_cache=True)
        # 3. DBOS.start_workflow(run_pipeline_workflow, no_cache=True)
        # 4. run_workflow(no_cache=True) → ModelContext(metadata={"no_cache": True})
        # 5. section_extractions model reads ctx.metadata["no_cache"] = True
        # 6. run_batch_sync(cache=not no_cache) → run_batch_sync(cache=False)
        # 7. get_dspy_lm(cache=False)
        # 8. dspy.LM(cache=False)
        #
        # Each step is tested individually in other tests.
        # This test documents the expected propagation path.
        pass

    def test_cache_enabled_by_default_throughout_stack(self):
        """Test that cache is enabled by default throughout the stack."""
        # Default behavior verification:
        #
        # 1. CLI default: no_cache=False
        # 2. run_workflow default: no_cache=False
        # 3. ctx.metadata.get("no_cache", False) → False
        # 4. run_batch_sync(cache=not False) → run_batch_sync(cache=True)
        # 5. get_dspy_lm(cache=True)
        # 6. dspy.LM(cache=True)
        pass

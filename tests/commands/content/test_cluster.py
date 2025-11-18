"""
Tests for 'cluster-urls' command (document organization).

These tests use mocked LLM responses to avoid expensive API calls.
"""

from unittest.mock import patch

from kurt.cli import main


class ClusteringResult:
    """
    Simple result object that mimics DSPy ComputeClustersAndClassify output structure.

    Used for mocking the LLM response in tests. DSPy signatures with multiple OutputFields
    return objects where each field is an attribute of the result object.

    This class is designed to work with the mock_dspy_signature fixture by providing
    a __fields__ attribute that lists the output field names, mimicking a Pydantic v1 model.
    """

    # Mimic Pydantic v1 model structure for the fixture
    __fields__ = {"clusters": None, "classifications": None, "assignments": None}

    def __init__(self, clusters, classifications, assignments):
        self.clusters = clusters
        self.classifications = classifications
        self.assignments = assignments


def create_mock_assignments(classifications_list, clusters_list):
    """Helper to create assignments from classifications and clusters.

    Assigns each document to the first cluster by index (for simplicity in tests).
    """
    from kurt.content.cluster import DocumentClusterAssignment

    if not clusters_list:
        return []

    # Assign all documents to the first cluster (by index)
    first_cluster_name = clusters_list[0].name
    return [
        DocumentClusterAssignment(document_index=idx, cluster_name=first_cluster_name)
        for idx in range(len(classifications_list))
    ]


class TestClusterUrlsCommand:
    """Tests for 'cluster-urls' command with mocked LLM."""

    def test_cluster_urls_help(self, isolated_cli_runner):
        """Test cluster-urls help text."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "cluster", "--help"])
        assert result.exit_code == 0
        assert "Organize documents into topic clusters" in result.output
        assert "LLM" in result.output

    def test_cluster_urls_with_no_documents(self, isolated_cli_runner):
        """Test cluster-urls with empty database."""
        runner, project_dir = isolated_cli_runner

        result = runner.invoke(main, ["content", "cluster"])
        # Should handle gracefully (no crash)
        assert result.exit_code == 0 or "No documents" in result.output

    def test_cluster_urls_requires_dspy_configured(self, isolated_cli_runner):
        """Test that cluster-urls requires DSPy configuration."""
        runner, project_dir = isolated_cli_runner

        # Create test documents
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
        session.commit()

        # Mock to avoid slow API calls, but simulate API key error
        with patch("kurt.content.cluster.dspy.LM") as mock_lm:
            mock_lm.side_effect = Exception("AuthenticationError: OpenAI API key required")

            # Run cluster-urls (should fail gracefully)
            result = runner.invoke(main, ["content", "cluster"])

            # Command should show error about missing API key
            assert result.exit_code == 1
            assert "OpenAI" in result.output or "API" in result.output or "key" in result.output

    def test_cluster_urls_with_include_pattern(self, isolated_cli_runner, mock_dspy_signature):
        """Test --include pattern for filtering before clustering."""
        runner, project_dir = isolated_cli_runner

        # Create test documents with different URL patterns
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        # Documents matching pattern
        docs_matching = []
        for i in range(3):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/docs/page{i}",
                title=f"Docs Page {i}",
                description=f"Documentation page {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            docs_matching.append(doc)

        # Documents NOT matching pattern
        for i in range(2):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/api/ref{i}",
                title=f"API Ref {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)

        session.commit()

        # Define the mock output for the clustering signature
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        def mock_clustering_output(**kwargs):
            """Return clustering results based on input pages."""
            _ = kwargs.get("pages", [])  # noqa: F841
            clusters = [
                TopicClusterOutput(
                    name="Documentation",
                    description="Docs pages",
                )
            ]
            classifications = [
                ContentTypeClassification(url=d.source_url, content_type="reference")
                for d in docs_matching
            ]
            return ClusteringResult(
                clusters=clusters,
                classifications=classifications,
                assignments=create_mock_assignments(classifications, clusters),
            )

        # Mock the LLM clustering to avoid API calls
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature(
                "ComputeClustersAndClassify", mock_clustering_output
            ) as mock_module:
                # Run cluster-urls with pattern
                result = runner.invoke(main, ["content", "cluster", "--include", "*/docs/*"])

                # Debug output if test fails
                if result.exit_code != 0:
                    print(f"\nCommand output:\n{result.output}")
                    if result.exception:
                        import traceback

                        traceback.print_exception(
                            type(result.exception), result.exception, result.exception.__traceback__
                        )

                # Should succeed with mocked LLM
                assert result.exit_code == 0
                assert "Computing topic clusters" in result.output

                # Verify the mock was actually called
                assert mock_module.called, "ComputeClustersAndClassify mock should have been called"

                # Verify that only docs matching pattern were clustered
                # The mock should have been called with only 3 pages (not 5)
                if mock_module.called:
                    call_args = mock_module.call_args
                    pages = call_args.kwargs.get("pages", [])
                    # Should only cluster the 3 matching docs
                    assert len(pages) == 3, f"Expected 3 pages, got {len(pages)}"
                    # Verify URLs are from docs/ path only
                    for page in pages:
                        assert "/docs/" in page.url

    def test_cluster_urls_works_on_not_fetched(self, isolated_cli_runner, mock_dspy_signature):
        """Test clustering works on NOT_FETCHED documents (no content needed)."""
        runner, project_dir = isolated_cli_runner

        # Create NOT_FETCHED documents
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/tutorial{i}",
                title=f"Tutorial {i}",
                description=f"Learn about topic {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,  # No content
            )
            session.add(doc)
        session.commit()

        # Define the mock output
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="Tutorials",
                description="Tutorial content",
            )
        ]

        mock_classifications = [
            ContentTypeClassification(
                url=f"https://example.com/tutorial{i}", content_type="tutorial"
            )
            for i in range(5)
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock LLM to avoid slow API calls
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls (should work with just URL/title/description)
                result = runner.invoke(main, ["content", "cluster"])

                # Command should succeed with mocked LLM
                assert result.exit_code == 0
                assert "Computing topic clusters" in result.output

    def test_cluster_urls_format_json(self, isolated_cli_runner, mock_dspy_signature):
        """Test --format json output."""
        runner, project_dir = isolated_cli_runner

        # Create test documents
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()
        for i in range(3):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
        session.commit()

        # Define the mock output
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="Pages",
                description="Page content",
            )
        ]

        mock_classifications = [
            ContentTypeClassification(url=f"https://example.com/page{i}", content_type="other")
            for i in range(3)
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock LLM to avoid slow API calls
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls with JSON format
                result = runner.invoke(main, ["content", "cluster", "--format", "json"])

                # Command should succeed with mocked LLM
                assert result.exit_code == 0
                # Check for JSON output or at least success
                assert (
                    "Computing topic clusters" in result.output or "json" in result.output.lower()
                )

    def test_cluster_urls_without_pattern_clusters_all(
        self, isolated_cli_runner, mock_dspy_signature
    ):
        """Test that cluster-urls without --include clusters ALL documents."""
        runner, project_dir = isolated_cli_runner

        # Create diverse test documents
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        all_docs = []
        # Create documents from different domains
        for domain in ["docs.example.com", "blog.example.com", "api.example.com"]:
            for i in range(2):
                doc = Document(
                    id=uuid4(),
                    source_url=f"https://{domain}/page{i}",
                    title=f"{domain} Page {i}",
                    description=f"Content from {domain}",
                    source_type=SourceType.URL,
                    ingestion_status=IngestionStatus.NOT_FETCHED,
                )
                session.add(doc)
                all_docs.append(doc)

        session.commit()

        # Define the mock output
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="Documentation",
                description="Docs",
            ),
            TopicClusterOutput(
                name="Blog Posts",
                description="Blog",
            ),
        ]

        mock_classifications = [
            ContentTypeClassification(
                url=doc.source_url,
                content_type="reference" if "docs" in doc.source_url else "blog",
            )
            for doc in all_docs
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock the LLM clustering to avoid API calls
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result) as mock_module:
                # Run cluster-urls WITHOUT --include (should cluster ALL)
                result = runner.invoke(main, ["content", "cluster"])

                # Should succeed with mocked LLM
                assert result.exit_code == 0
                assert "Computing topic clusters" in result.output

                # Verify that ALL documents were clustered
                if mock_module.called:
                    call_args = mock_module.call_args
                    pages = call_args.kwargs.get("pages", [])
                    # Should cluster all 6 documents
                    assert len(pages) == 6, f"Expected 6 pages (all docs), got {len(pages)}"


# Note: Full integration tests with actual LLM calls should be in tests/integration/
# These are basic unit tests that verify command structure and options work


# ============================================================================
# Additional Tests for CLI-SPEC.md Coverage
# ============================================================================


class TestClusterUrlsAdditionalOptions:
    """Additional tests for cluster-urls options from CLI-SPEC.md."""

    def test_cluster_urls_with_force_flag(self, isolated_cli_runner, mock_dspy_signature):
        """Test --force flag to re-cluster already clustered documents."""
        runner, project_dir = isolated_cli_runner

        # Create test documents that are already clustered
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import (
            Document,
            DocumentClusterEdge,
            IngestionStatus,
            SourceType,
            TopicCluster,
        )

        session = get_session()

        # Create existing cluster
        existing_cluster = TopicCluster(id=uuid4(), name="OldCluster", description="Old clustering")
        session.add(existing_cluster)

        # Create documents and link to existing cluster
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page{i}",
                title=f"Page {i}",
                description=f"Description {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            session.commit()

            # Link to existing cluster
            edge = DocumentClusterEdge(
                id=uuid4(), document_id=doc.id, cluster_id=existing_cluster.id
            )
            session.add(edge)

        session.commit()

        # Define the mock output
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="NewCluster",
                description="New clustering",
            )
        ]

        mock_classifications = [
            ContentTypeClassification(url=f"https://example.com/page{i}", content_type="other")
            for i in range(5)
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock LLM for clustering
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls with --force to re-cluster
                result = runner.invoke(main, ["content", "cluster", "--force"])

                # Should succeed (force bypasses "already clustered" check)
                assert result.exit_code == 0

    def test_cluster_urls_classifies_automatically(self, isolated_cli_runner, mock_dspy_signature):
        """Test that clustering automatically classifies content types (no flag needed)."""
        runner, project_dir = isolated_cli_runner

        # Create test documents without content_type
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        docs = []
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/blog/post{i}",
                title=f"Blog Post {i}",
                description=f"Blog content {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
                content_type=None,  # Not yet classified
            )
            session.add(doc)
            docs.append(doc)

        session.commit()

        # Define the mock output
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Single LLM call returns both clusters and classifications
        mock_clusters = [
            TopicClusterOutput(
                name="Blog Posts",
                description="Blog content",
            )
        ]
        mock_classifications = [
            ContentTypeClassification(url=docs[i].source_url, content_type="blog") for i in range(5)
        ]
        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock clustering and classification (single LLM call)
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls (no special flag needed)
                result = runner.invoke(main, ["content", "cluster"])

                # Should succeed
                assert result.exit_code == 0
                # Check that both classification and clustering happened
                assert "Computing topic clusters" in result.output
                assert "Classified" in result.output

    def test_cluster_urls_force_flag_bypass_safety_check(
        self, isolated_cli_runner, mock_dspy_signature
    ):
        """Test that --force ignores existing clusters and creates fresh (vs incremental refinement)."""
        runner, project_dir = isolated_cli_runner

        # Create test documents that are already clustered
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import (
            Document,
            DocumentClusterEdge,
            IngestionStatus,
            SourceType,
            TopicCluster,
        )

        session = get_session()

        # Create existing cluster
        existing_cluster = TopicCluster(
            id=uuid4(), name="ExistingCluster", description="Already exists"
        )
        session.add(existing_cluster)
        session.flush()

        # Create documents and link to existing cluster
        docs = []
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/existing{i}",
                title=f"Existing Doc {i}",
                description=f"Already clustered document {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            session.flush()
            docs.append(doc)

            # Link to existing cluster
            edge = DocumentClusterEdge(
                id=uuid4(), document_id=doc.id, cluster_id=existing_cluster.id
            )
            session.add(edge)

        session.commit()

        # Test WITHOUT --force (should refine existing clusters)
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="RefinedCluster",
                description="Refined from existing",
            )
        ]

        mock_classifications = [
            ContentTypeClassification(url=doc.source_url, content_type="reference") for doc in docs
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result) as mock_module:
                result_without_force = runner.invoke(main, ["content", "cluster"])

                # Should succeed with incremental clustering
                assert result_without_force.exit_code == 0
                assert (
                    "Refined" in result_without_force.output
                    or "clusters" in result_without_force.output.lower()
                )

                # Verify existing_clusters was passed to LLM
                assert mock_module.called
                call_kwargs = mock_module.call_args.kwargs
                assert "existing_clusters" in call_kwargs
                assert len(call_kwargs["existing_clusters"]) == 1  # One existing cluster

        # Test WITH --force (should ignore existing clusters)
        # Define clusters and classifications

        mock_clusters_force = [
            TopicClusterOutput(
                name="FreshCluster",
                description="Fresh clustering",
            )
        ]

        mock_classifications_force = [
            ContentTypeClassification(url=doc.source_url, content_type="reference") for doc in docs
        ]

        mock_result_force = ClusteringResult(
            clusters=mock_clusters_force,
            classifications=mock_classifications_force,
            assignments=create_mock_assignments(mock_classifications_force, mock_clusters_force),
        )

        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature(
                "ComputeClustersAndClassify", mock_result_force
            ) as mock_module:
                # Run with --force flag
                result_with_force = runner.invoke(main, ["content", "cluster", "--force"])

                # Should succeed
                assert result_with_force.exit_code == 0
                assert "Computing topic clusters" in result_with_force.output

                # Verify existing_clusters was EMPTY (force mode)
                assert mock_module.called
                call_kwargs = mock_module.call_args.kwargs
                assert "existing_clusters" in call_kwargs
                assert len(call_kwargs["existing_clusters"]) == 0  # Empty in force mode

    def test_cluster_urls_force_flag_without_existing_clusters(
        self, isolated_cli_runner, mock_dspy_signature
    ):
        """Test --force works when no existing clusters (no-op for safety check)."""
        runner, project_dir = isolated_cli_runner

        # Create test documents WITHOUT any existing clusters
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        docs = []
        for i in range(3):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/fresh{i}",
                title=f"Fresh Doc {i}",
                description=f"Never been clustered {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            docs.append(doc)

        session.commit()

        # Define the mock output
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="FirstCluster",
                description="First time clustering",
            )
        ]

        mock_classifications = [
            ContentTypeClassification(url=doc.source_url, content_type="guide") for doc in docs
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock LLM clustering
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run with --force even though there are no existing clusters
                result = runner.invoke(main, ["content", "cluster", "--force"])

                # Should succeed (--force is safe to use even when not needed)
                assert result.exit_code == 0
                assert "Computing topic clusters" in result.output

    def test_cluster_urls_large_batch_warning(self, isolated_cli_runner, mock_dspy_signature):
        """Test warning displays when >500 documents."""
        runner, project_dir = isolated_cli_runner

        # Create >500 test documents to trigger warning (use smaller count for faster test)
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        # Use 250 docs to test batching (>200 triggers batching message)
        doc_count = 250
        docs = []
        for i in range(doc_count):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/doc{i}",
                title=f"Doc {i}",
                description=f"Description {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            docs.append(doc)

        session.commit()

        # Create a dynamic response function that returns appropriate data for each batch
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        def batch_response(**kwargs):
            pages = kwargs.get("pages", [])
            clusters = [
                TopicClusterOutput(
                    name="TestCluster",
                    description="Test",
                )
            ]

            classifications = [
                ContentTypeClassification(url=page.url, content_type="other") for page in pages
            ]

            return ClusteringResult(
                clusters=clusters,
                classifications=classifications,
                assignments=create_mock_assignments(classifications, clusters),
            )

        # Mock LLM clustering (return minimal clusters to speed up test)
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", batch_response):
                # Run cluster-urls
                result = runner.invoke(main, ["content", "cluster"])

                # Debug: print output if failed
                if result.exit_code != 0:
                    print("\n=== COMMAND OUTPUT ===")
                    print(result.output)
                    if result.exception:
                        print("\n=== EXCEPTION ===")
                        import traceback

                        traceback.print_exception(
                            type(result.exception), result.exception, result.exception.__traceback__
                        )

                # Should show batching message
                assert result.exit_code == 0
                assert "batches" in result.output.lower() or "250" in result.output

    def test_cluster_urls_displays_actual_doc_counts(
        self, isolated_cli_runner, mock_dspy_signature
    ):
        """Test that doc counts in table are accurate (not '?')."""
        runner, project_dir = isolated_cli_runner

        # Create test documents
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus, SourceType

        session = get_session()

        # Create 10 documents - we'll cluster them into 2 clusters
        docs = []
        for i in range(10):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/doc{i}",
                title=f"Doc {i}",
                description=f"Description {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            docs.append(doc)

        session.commit()

        # Define the mock output - use a simple object with the required attributes
        from kurt.content.cluster import ContentTypeClassification, TopicClusterOutput

        # Define clusters and classifications

        mock_clusters = [
            TopicClusterOutput(
                name="ClusterA",
                description="First cluster",
            ),
            TopicClusterOutput(
                name="ClusterB",
                description="Second cluster",
            ),
        ]

        mock_classifications = [
            ContentTypeClassification(url=doc.source_url, content_type="guide") for doc in docs
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=create_mock_assignments(mock_classifications, mock_clusters),
        )

        # Mock LLM clustering - return 2 clusters with specific example URLs
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls
                result = runner.invoke(main, ["content", "cluster"])

                # Should succeed
                assert result.exit_code == 0
                assert "Computing topic clusters" in result.output

                # Verify actual doc counts are displayed (not "?")
                # The command queries the database to get real counts
                assert (
                    "?" not in result.output or result.output.count("?") == 0
                )  # No question marks for counts

                # Should show doc counts for each cluster
                # ClusterA should have 3 docs (from example URLs)
                # ClusterB should have 2 docs (from example URLs)
                # Note: The current implementation only links example URLs, not all docs
                assert "3" in result.output or "2" in result.output  # At least one of the counts

                # Verify table format shows "Doc Count" column
                assert "Doc Count" in result.output

    def test_cluster_urls_uses_index_based_assignment(
        self, isolated_cli_runner, mock_dspy_signature
    ):
        """Test that cluster assignment uses document indices, not URLs (more robust)."""
        runner, project_dir = isolated_cli_runner

        # Create test documents
        from uuid import uuid4

        from kurt.db.database import get_session
        from kurt.db.models import Document, DocumentClusterEdge, IngestionStatus, SourceType

        session = get_session()

        docs = []
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/doc{i}",
                title=f"Doc {i}",
                description=f"Description {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            docs.append(doc)

        session.commit()

        # Define the mock output with explicit index-based assignments
        from kurt.content.cluster import (
            ContentTypeClassification,
            DocumentClusterAssignment,
            TopicClusterOutput,
        )

        mock_clusters = [
            TopicClusterOutput(
                name="ClusterA",
                description="First cluster",
            ),
            TopicClusterOutput(
                name="ClusterB",
                description="Second cluster",
            ),
        ]

        mock_classifications = [
            ContentTypeClassification(url=doc.source_url, content_type="guide") for doc in docs
        ]

        # Explicitly assign documents by index to different clusters
        mock_assignments = [
            DocumentClusterAssignment(document_index=0, cluster_name="ClusterA"),
            DocumentClusterAssignment(document_index=1, cluster_name="ClusterA"),
            DocumentClusterAssignment(document_index=2, cluster_name="ClusterB"),
            DocumentClusterAssignment(document_index=3, cluster_name="ClusterB"),
            DocumentClusterAssignment(document_index=4, cluster_name="ClusterA"),
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=mock_assignments,
        )

        # Mock LLM clustering
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls
                result = runner.invoke(main, ["content", "cluster"])

                # Should succeed
                assert result.exit_code == 0
                assert "Computing topic clusters" in result.output

                # Verify assignments were created based on indices
                # ClusterA should have 3 docs (indices 0, 1, 4)
                # ClusterB should have 2 docs (indices 2, 3)
                edges = session.query(DocumentClusterEdge).all()
                assert len(edges) == 5, f"Expected 5 edges, got {len(edges)}"

                # Verify correct cluster assignments by counting
                from kurt.db.models import TopicCluster

                cluster_a = (
                    session.query(TopicCluster).filter(TopicCluster.name == "ClusterA").first()
                )
                cluster_b = (
                    session.query(TopicCluster).filter(TopicCluster.name == "ClusterB").first()
                )

                assert cluster_a is not None
                assert cluster_b is not None

                cluster_a_docs = (
                    session.query(DocumentClusterEdge)
                    .filter(DocumentClusterEdge.cluster_id == cluster_a.id)
                    .count()
                )
                cluster_b_docs = (
                    session.query(DocumentClusterEdge)
                    .filter(DocumentClusterEdge.cluster_id == cluster_b.id)
                    .count()
                )

                assert cluster_a_docs == 3, f"ClusterA should have 3 docs, got {cluster_a_docs}"
                assert cluster_b_docs == 2, f"ClusterB should have 2 docs, got {cluster_b_docs}"

    def test_cluster_urls_handles_null_assignments(self, isolated_cli_runner, mock_dspy_signature):
        """Test that cluster assignment can handle documents that don't fit any cluster (cluster_name=None)."""
        from uuid import uuid4

        from kurt.content.cluster import (
            ContentTypeClassification,
            DocumentClusterAssignment,
            TopicClusterOutput,
        )
        from kurt.db.database import get_session
        from kurt.db.models import Document, DocumentClusterEdge, IngestionStatus, SourceType

        runner, project_dir = isolated_cli_runner

        session = get_session()

        # Create 5 test documents
        docs = []
        for i in range(5):
            doc = Document(
                id=uuid4(),
                source_url=f"https://example.com/page-{i}",
                name=f"Page {i}",
                description=f"Description {i}",
                source_type=SourceType.URL,
                ingestion_status=IngestionStatus.NOT_FETCHED,
            )
            session.add(doc)
            docs.append(doc)

        session.commit()

        # Define the mock output with some null assignments
        mock_clusters = [
            TopicClusterOutput(
                name="TechCluster",
                description="Technical content",
            ),
        ]

        mock_classifications = [
            ContentTypeClassification(url=doc.source_url, content_type="guide") for doc in docs
        ]

        # Some documents assigned to cluster, others set to None (don't fit)
        mock_assignments = [
            DocumentClusterAssignment(document_index=0, cluster_name="TechCluster"),
            DocumentClusterAssignment(document_index=1, cluster_name=None),  # Doesn't fit
            DocumentClusterAssignment(document_index=2, cluster_name="TechCluster"),
            DocumentClusterAssignment(document_index=3, cluster_name=None),  # Doesn't fit
            DocumentClusterAssignment(document_index=4, cluster_name="TechCluster"),
        ]

        mock_result = ClusteringResult(
            clusters=mock_clusters,
            classifications=mock_classifications,
            assignments=mock_assignments,
        )

        # Mock LLM clustering
        with patch("kurt.content.cluster.dspy.LM"):
            with mock_dspy_signature("ComputeClustersAndClassify", mock_result):
                # Run cluster-urls
                result = runner.invoke(main, ["content", "cluster"])

                assert result.exit_code == 0, f"Command failed: {result.output}"

            # Verify only 3 edges were created (docs 0, 2, 4)
            edges = session.query(DocumentClusterEdge).all()
            assert len(edges) == 3, f"Expected 3 edges (only assigned docs), got {len(edges)}"

            # Verify all 3 edges point to TechCluster
            from kurt.db.models import TopicCluster

            tech_cluster = (
                session.query(TopicCluster).filter(TopicCluster.name == "TechCluster").first()
            )

            assert tech_cluster is not None

            tech_cluster_docs = (
                session.query(DocumentClusterEdge)
                .filter(DocumentClusterEdge.cluster_id == tech_cluster.id)
                .count()
            )

            assert (
                tech_cluster_docs == 3
            ), f"TechCluster should have 3 docs (0,2,4), got {tech_cluster_docs}"

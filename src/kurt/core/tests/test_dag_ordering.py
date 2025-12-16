"""Tests for dependency graph building and topological sorting.

Tests:
1. build_dependency_graph - extracting dependencies from Reference declarations
2. topological_sort - ordering models by execution level
3. Edge cases: cycles, self-references, external dependencies
"""

import pytest

from kurt.core.references import (
    Reference,
    build_dependency_graph,
    topological_sort,
)
from kurt.core.registry import ModelRegistry


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph function."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Clean up test models before each test."""
        # Save existing models
        self._original_models = ModelRegistry._models.copy()
        yield
        # Restore original models
        ModelRegistry._models = self._original_models

    def _register_mock_model(self, name: str, dependencies: list[str]):
        """Register a mock model with specified dependencies."""
        references = {}
        for i, dep in enumerate(dependencies):
            references[f"ref_{i}"] = Reference(model_name=dep)

        ModelRegistry._models[name] = {
            "function": lambda ctx, **kw: {},
            "references": references,
            "table_name": name.replace(".", "_"),
        }

    def test_empty_model_list(self):
        """Test with empty model list."""
        graph = build_dependency_graph([])
        assert graph == {}

    def test_single_model_no_deps(self):
        """Test single model with no dependencies."""
        self._register_mock_model("test.model_a", [])

        graph = build_dependency_graph(["test.model_a"])

        assert graph == {"test.model_a": []}

    def test_simple_chain(self):
        """Test simple linear chain: A -> B -> C."""
        self._register_mock_model("test.model_a", [])
        self._register_mock_model("test.model_b", ["test.model_a"])
        self._register_mock_model("test.model_c", ["test.model_b"])

        graph = build_dependency_graph(["test.model_a", "test.model_b", "test.model_c"])

        assert graph["test.model_a"] == []
        assert graph["test.model_b"] == ["test.model_a"]
        assert graph["test.model_c"] == ["test.model_b"]

    def test_diamond_dependency(self):
        """Test diamond pattern: A -> B, A -> C, B -> D, C -> D."""
        self._register_mock_model("test.a", [])
        self._register_mock_model("test.b", ["test.a"])
        self._register_mock_model("test.c", ["test.a"])
        self._register_mock_model("test.d", ["test.b", "test.c"])

        graph = build_dependency_graph(["test.a", "test.b", "test.c", "test.d"])

        assert graph["test.a"] == []
        assert graph["test.b"] == ["test.a"]
        assert graph["test.c"] == ["test.a"]
        assert set(graph["test.d"]) == {"test.b", "test.c"}

    def test_external_dependency_ignored(self):
        """Test that dependencies outside the model list are ignored."""
        self._register_mock_model("test.a", [])
        self._register_mock_model("test.b", ["test.a", "external.model"])

        graph = build_dependency_graph(["test.a", "test.b"])

        # external.model not in list, so only test.a is included
        assert graph["test.a"] == []
        assert graph["test.b"] == ["test.a"]

    def test_table_name_to_model_mapping(self):
        """Test that table_name references map back to model names."""
        # Model A referenced by table name in B
        self._register_mock_model("test.model_a", [])

        # B references via table_name (test_model_a)
        references = {"ref_0": Reference(model_name="test_model_a")}
        ModelRegistry._models["test.model_b"] = {
            "function": lambda ctx, **kw: {},
            "references": references,
            "table_name": "test_model_b",
        }

        graph = build_dependency_graph(["test.model_a", "test.model_b"])

        # test_model_a should map to test.model_a
        assert graph["test.model_b"] == ["test.model_a"]

    def test_multiple_independent_models(self):
        """Test multiple models with no dependencies on each other."""
        self._register_mock_model("test.a", [])
        self._register_mock_model("test.b", [])
        self._register_mock_model("test.c", [])

        graph = build_dependency_graph(["test.a", "test.b", "test.c"])

        assert graph["test.a"] == []
        assert graph["test.b"] == []
        assert graph["test.c"] == []

    def test_model_not_in_registry(self):
        """Test handling of model not found in registry."""
        graph = build_dependency_graph(["nonexistent.model"])

        # Should return empty deps for unregistered model
        assert graph == {"nonexistent.model": []}


class TestTopologicalSort:
    """Tests for topological_sort function."""

    def test_empty_graph(self):
        """Test with empty graph."""
        levels = topological_sort({})
        assert levels == []

    def test_single_node(self):
        """Test single node graph."""
        levels = topological_sort({"a": []})
        assert levels == [["a"]]

    def test_simple_chain(self):
        """Test linear chain produces one node per level."""
        graph = {
            "a": [],
            "b": ["a"],
            "c": ["b"],
        }

        levels = topological_sort(graph)

        assert len(levels) == 3
        assert levels[0] == ["a"]
        assert levels[1] == ["b"]
        assert levels[2] == ["c"]

    def test_parallel_at_same_level(self):
        """Test that independent nodes are at the same level."""
        graph = {
            "a": [],
            "b": [],
            "c": ["a", "b"],
        }

        levels = topological_sort(graph)

        assert len(levels) == 2
        # a and b should be in first level (sorted alphabetically)
        assert set(levels[0]) == {"a", "b"}
        assert levels[1] == ["c"]

    def test_diamond_pattern(self):
        """Test diamond dependency pattern."""
        graph = {
            "a": [],
            "b": ["a"],
            "c": ["a"],
            "d": ["b", "c"],
        }

        levels = topological_sort(graph)

        assert len(levels) == 3
        assert levels[0] == ["a"]
        assert set(levels[1]) == {"b", "c"}
        assert levels[2] == ["d"]

    def test_complex_dag(self):
        """Test more complex DAG structure."""
        # DAG:
        #   a ──┬──> c ──> e
        #       │         ↑
        #   b ──┴──> d ───┘
        graph = {
            "a": [],
            "b": [],
            "c": ["a", "b"],
            "d": ["a", "b"],
            "e": ["c", "d"],
        }

        levels = topological_sort(graph)

        assert len(levels) == 3
        assert set(levels[0]) == {"a", "b"}
        assert set(levels[1]) == {"c", "d"}
        assert levels[2] == ["e"]

    def test_cycle_detection_simple(self):
        """Test that simple cycles are detected."""
        graph = {
            "a": ["b"],
            "b": ["a"],
        }

        with pytest.raises(ValueError, match="Circular dependency"):
            topological_sort(graph)

    def test_cycle_detection_chain(self):
        """Test that longer cycles are detected."""
        graph = {
            "a": ["c"],
            "b": ["a"],
            "c": ["b"],
        }

        with pytest.raises(ValueError, match="Circular dependency"):
            topological_sort(graph)

    def test_self_reference(self):
        """Test that self-reference is detected as cycle."""
        graph = {
            "a": ["a"],
        }

        with pytest.raises(ValueError, match="Circular dependency"):
            topological_sort(graph)

    def test_deterministic_ordering(self):
        """Test that output is deterministic (sorted within levels)."""
        graph = {
            "z": [],
            "a": [],
            "m": [],
        }

        levels = topological_sort(graph)

        # All at same level, should be sorted
        assert levels == [["a", "m", "z"]]

    def test_wide_parallel_level(self):
        """Test handling of many parallel nodes."""
        # 10 independent nodes, then one that depends on all
        graph = {f"node_{i}": [] for i in range(10)}
        graph["final"] = [f"node_{i}" for i in range(10)]

        levels = topological_sort(graph)

        assert len(levels) == 2
        assert len(levels[0]) == 10
        assert levels[1] == ["final"]

    def test_deep_chain(self):
        """Test handling of deep dependency chain."""
        # Chain of 20 nodes
        graph = {"node_0": []}
        for i in range(1, 20):
            graph[f"node_{i}"] = [f"node_{i-1}"]

        levels = topological_sort(graph)

        assert len(levels) == 20
        for i, level in enumerate(levels):
            assert level == [f"node_{i}"]


class TestDAGIntegration:
    """Integration tests for build_dependency_graph + topological_sort."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Clean up test models before each test."""
        self._original_models = ModelRegistry._models.copy()
        yield
        ModelRegistry._models = self._original_models

    def _register_mock_model(self, name: str, dependencies: list[str]):
        """Register a mock model with specified dependencies."""
        references = {}
        for i, dep in enumerate(dependencies):
            references[f"ref_{i}"] = Reference(model_name=dep)

        ModelRegistry._models[name] = {
            "function": lambda ctx, **kw: {},
            "references": references,
            "table_name": name.replace(".", "_"),
        }

    def test_indexing_pipeline_pattern(self):
        """Test the actual indexing pipeline pattern."""
        # Simulates the real indexing pipeline structure:
        # document_sections -> section_extractions -> entity_clustering -> entity_resolution
        #                                         -> claim_clustering -> claim_resolution
        self._register_mock_model("indexing.document_sections", [])
        self._register_mock_model("indexing.section_extractions", ["indexing.document_sections"])
        self._register_mock_model("indexing.entity_clustering", ["indexing.section_extractions"])
        self._register_mock_model("indexing.claim_clustering", ["indexing.section_extractions"])
        self._register_mock_model(
            "indexing.entity_resolution",
            ["indexing.entity_clustering", "indexing.section_extractions"],
        )
        self._register_mock_model(
            "indexing.claim_resolution",
            [
                "indexing.claim_clustering",
                "indexing.entity_resolution",
                "indexing.section_extractions",
            ],
        )

        models = [
            "indexing.document_sections",
            "indexing.section_extractions",
            "indexing.entity_clustering",
            "indexing.claim_clustering",
            "indexing.entity_resolution",
            "indexing.claim_resolution",
        ]

        graph = build_dependency_graph(models)
        levels = topological_sort(graph)

        # Level 1: document_sections (no deps)
        assert levels[0] == ["indexing.document_sections"]

        # Level 2: section_extractions (depends on doc_sections)
        assert levels[1] == ["indexing.section_extractions"]

        # Level 3: entity_clustering and claim_clustering (both depend on section_extractions)
        assert set(levels[2]) == {"indexing.entity_clustering", "indexing.claim_clustering"}

        # Level 4: entity_resolution (depends on entity_clustering)
        assert levels[3] == ["indexing.entity_resolution"]

        # Level 5: claim_resolution (depends on claim_clustering, entity_resolution)
        assert levels[4] == ["indexing.claim_resolution"]

    def test_partial_pipeline(self):
        """Test building DAG for subset of pipeline."""
        self._register_mock_model("indexing.a", [])
        self._register_mock_model("indexing.b", ["indexing.a"])
        self._register_mock_model("indexing.c", ["indexing.b"])
        self._register_mock_model("indexing.d", ["indexing.c"])

        # Only include b and c, not a or d
        models = ["indexing.b", "indexing.c"]

        graph = build_dependency_graph(models)
        levels = topological_sort(graph)

        # a is not in list, so b has no deps in the graph
        # c depends on b
        assert len(levels) == 2
        assert levels[0] == ["indexing.b"]
        assert levels[1] == ["indexing.c"]

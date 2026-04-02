"""
Tests for DAG builder.
"""

from __future__ import annotations

import pytest

from kurt.workflows.toml.dag import (
    CycleDetectedError,
    ExecutionPlan,
    build_dag,
)
from kurt.workflows.toml.parser import StepDef

# ============================================================================
# Helper Functions
# ============================================================================


def make_step(
    step_type: str = "map",
    depends_on: list[str] | None = None,
    priority: int | None = None,
) -> StepDef:
    """Create a StepDef with optional dependencies and priority."""
    config = {}
    if priority is not None:
        config["priority"] = priority
    return StepDef(
        type=step_type,
        depends_on=depends_on or [],
        config=config,
    )


# ============================================================================
# ExecutionPlan Tests
# ============================================================================


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""

    def test_default_values(self):
        """ExecutionPlan has sensible defaults."""
        plan = ExecutionPlan()
        assert plan.levels == []
        assert plan.total_steps == 0
        assert plan.parallelizable is False
        assert plan.critical_path == []

    def test_with_values(self):
        """ExecutionPlan stores provided values."""
        plan = ExecutionPlan(
            levels=[["a"], ["b", "c"]],
            total_steps=3,
            parallelizable=True,
            critical_path=["a", "b"],
        )
        assert plan.levels == [["a"], ["b", "c"]]
        assert plan.total_steps == 3
        assert plan.parallelizable is True
        assert plan.critical_path == ["a", "b"]


# ============================================================================
# build_dag Tests - Empty and Single Step
# ============================================================================


class TestBuildDagBasic:
    """Tests for basic build_dag functionality."""

    def test_empty_steps(self):
        """Empty steps dict returns empty plan."""
        plan = build_dag({})

        assert plan.levels == []
        assert plan.total_steps == 0
        assert plan.parallelizable is False
        assert plan.critical_path == []

    def test_single_step_no_deps(self):
        """Single step with no dependencies."""
        steps = {"only": make_step("map")}

        plan = build_dag(steps)

        assert plan.levels == [["only"]]
        assert plan.total_steps == 1
        assert plan.parallelizable is False
        assert plan.critical_path == ["only"]

    def test_two_independent_steps(self):
        """Two steps with no dependencies can run in parallel."""
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch"),
        }

        plan = build_dag(steps)

        assert plan.levels == [["a", "b"]]  # Alphabetical order
        assert plan.total_steps == 2
        assert plan.parallelizable is True
        assert len(plan.critical_path) == 1  # Either 'a' or 'b'

    def test_two_sequential_steps(self):
        """Two steps with one depending on the other."""
        steps = {
            "first": make_step("map"),
            "second": make_step("fetch", depends_on=["first"]),
        }

        plan = build_dag(steps)

        assert plan.levels == [["first"], ["second"]]
        assert plan.total_steps == 2
        assert plan.parallelizable is False
        assert plan.critical_path == ["first", "second"]


# ============================================================================
# build_dag Tests - Execution Levels
# ============================================================================


class TestBuildDagLevels:
    """Tests for execution level computation."""

    def test_linear_chain(self):
        """Linear dependency chain creates one step per level."""
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch", depends_on=["a"]),
            "c": make_step("llm", depends_on=["b"]),
            "d": make_step("write-db", depends_on=["c"]),
        }

        plan = build_dag(steps)

        assert plan.levels == [["a"], ["b"], ["c"], ["d"]]
        assert plan.total_steps == 4
        assert plan.parallelizable is False

    def test_diamond_pattern(self):
        """Diamond dependency pattern (fan-out then fan-in)."""
        steps = {
            "source": make_step("map"),
            "left": make_step("fetch", depends_on=["source"]),
            "right": make_step("fetch", depends_on=["source"]),
            "merge": make_step("sql", depends_on=["left", "right"]),
        }

        plan = build_dag(steps)

        assert plan.levels == [["source"], ["left", "right"], ["merge"]]
        assert plan.total_steps == 4
        assert plan.parallelizable is True

    def test_multiple_roots(self):
        """Multiple root nodes (no dependencies) in level 0."""
        steps = {
            "root1": make_step("map"),
            "root2": make_step("map"),
            "root3": make_step("map"),
            "child": make_step("fetch", depends_on=["root1", "root2"]),
        }

        plan = build_dag(steps)

        assert plan.levels[0] == ["root1", "root2", "root3"]
        assert plan.levels[1] == ["child"]

    def test_complex_dag(self):
        """Complex DAG with multiple levels and fan-in/fan-out."""
        #     a
        #    / \
        #   b   c
        #   |   |\
        #   d   e f
        #    \ /
        #     g
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch", depends_on=["a"]),
            "c": make_step("fetch", depends_on=["a"]),
            "d": make_step("llm", depends_on=["b"]),
            "e": make_step("llm", depends_on=["c"]),
            "f": make_step("embed", depends_on=["c"]),
            "g": make_step("write-db", depends_on=["d", "e"]),
        }

        plan = build_dag(steps)

        assert plan.levels[0] == ["a"]
        assert set(plan.levels[1]) == {"b", "c"}
        assert set(plan.levels[2]) == {"d", "e", "f"}
        assert plan.levels[3] == ["g"]
        assert plan.total_steps == 7
        assert plan.parallelizable is True


# ============================================================================
# build_dag Tests - Tie-Break Ordering
# ============================================================================


class TestBuildDagOrdering:
    """Tests for deterministic tie-break ordering."""

    def test_alphabetical_ordering_in_level(self):
        """Steps in same level are sorted alphabetically by default."""
        steps = {
            "zebra": make_step("map"),
            "apple": make_step("fetch"),
            "mango": make_step("llm"),
        }

        plan = build_dag(steps)

        assert plan.levels == [["apple", "mango", "zebra"]]

    def test_priority_ordering_in_level(self):
        """Steps with priority are sorted by priority first."""
        steps = {
            "low": make_step("map", priority=100),
            "high": make_step("fetch", priority=1),
            "medium": make_step("llm", priority=50),
        }

        plan = build_dag(steps)

        assert plan.levels == [["high", "medium", "low"]]

    def test_priority_then_alphabetical(self):
        """Same priority falls back to alphabetical."""
        steps = {
            "z_first": make_step("map", priority=1),
            "a_first": make_step("fetch", priority=1),
            "m_second": make_step("llm", priority=2),
        }

        plan = build_dag(steps)

        # priority=1: a_first, z_first (alphabetical)
        # priority=2: m_second
        assert plan.levels == [["a_first", "z_first", "m_second"]]

    def test_default_priority_is_100(self):
        """Steps without priority default to 100."""
        steps = {
            "default": make_step("map"),  # priority=100 (default)
            "explicit": make_step("fetch", priority=100),
            "higher": make_step("llm", priority=50),
        }

        plan = build_dag(steps)

        # higher (50), then default and explicit (100, alphabetical)
        assert plan.levels == [["higher", "default", "explicit"]]

    def test_consistent_ordering_across_runs(self):
        """Ordering is deterministic across multiple runs."""
        steps = {
            "c": make_step("map"),
            "a": make_step("fetch"),
            "b": make_step("llm"),
        }

        results = [build_dag(steps).levels for _ in range(10)]

        # All runs should produce identical ordering
        assert all(r == results[0] for r in results)
        assert results[0] == [["a", "b", "c"]]


# ============================================================================
# build_dag Tests - Critical Path
# ============================================================================


class TestBuildDagCriticalPath:
    """Tests for critical path computation."""

    def test_single_step_critical_path(self):
        """Single step is its own critical path."""
        steps = {"only": make_step("map")}

        plan = build_dag(steps)

        assert plan.critical_path == ["only"]

    def test_linear_chain_critical_path(self):
        """Linear chain has itself as critical path."""
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch", depends_on=["a"]),
            "c": make_step("llm", depends_on=["b"]),
        }

        plan = build_dag(steps)

        assert plan.critical_path == ["a", "b", "c"]

    def test_diamond_critical_path(self):
        """Diamond pattern has path length 3."""
        steps = {
            "source": make_step("map"),
            "left": make_step("fetch", depends_on=["source"]),
            "right": make_step("fetch", depends_on=["source"]),
            "merge": make_step("sql", depends_on=["left", "right"]),
        }

        plan = build_dag(steps)

        assert len(plan.critical_path) == 3
        assert plan.critical_path[0] == "source"
        assert plan.critical_path[1] in ("left", "right")
        assert plan.critical_path[2] == "merge"

    def test_multiple_equal_paths_uses_tiebreak(self):
        """When paths are equal length, use priority then alphabetical."""
        steps = {
            "root": make_step("map"),
            "path_a": make_step("fetch", depends_on=["root"], priority=10),
            "path_b": make_step("fetch", depends_on=["root"], priority=10),
        }

        plan = build_dag(steps)

        # Both paths have same length and priority, alphabetical wins
        assert plan.critical_path == ["root", "path_a"]

    def test_priority_affects_critical_path(self):
        """Higher priority path preferred in critical path."""
        steps = {
            "root": make_step("map"),
            "low_priority": make_step("fetch", depends_on=["root"], priority=100),
            "high_priority": make_step("fetch", depends_on=["root"], priority=1),
        }

        plan = build_dag(steps)

        # high_priority has priority=1, preferred
        assert plan.critical_path == ["root", "high_priority"]

    def test_longer_path_beats_priority(self):
        """Longer path is always preferred over priority."""
        steps = {
            "root": make_step("map"),
            "short": make_step("fetch", depends_on=["root"], priority=1),
            "long_a": make_step("fetch", depends_on=["root"], priority=100),
            "long_b": make_step("llm", depends_on=["long_a"], priority=100),
        }

        plan = build_dag(steps)

        # Longer path wins even with lower priority
        assert len(plan.critical_path) == 3
        assert plan.critical_path == ["root", "long_a", "long_b"]


# ============================================================================
# build_dag Tests - Cycle Detection
# ============================================================================


class TestBuildDagCycleDetection:
    """Tests for cycle detection."""

    def test_self_cycle(self):
        """Self-referencing step is detected as cycle."""
        steps = {
            "loop": StepDef(type="map", depends_on=["loop"]),
        }

        with pytest.raises(CycleDetectedError) as exc_info:
            build_dag(steps)

        assert "loop" in exc_info.value.cycle
        assert "loop -> loop" in str(exc_info.value)

    def test_two_step_cycle(self):
        """Two-step cycle is detected."""
        steps = {
            "a": StepDef(type="map", depends_on=["b"]),
            "b": StepDef(type="fetch", depends_on=["a"]),
        }

        with pytest.raises(CycleDetectedError) as exc_info:
            build_dag(steps)

        assert "a" in exc_info.value.cycle
        assert "b" in exc_info.value.cycle

    def test_three_step_cycle(self):
        """Three-step cycle is detected."""
        steps = {
            "a": StepDef(type="map", depends_on=["c"]),
            "b": StepDef(type="fetch", depends_on=["a"]),
            "c": StepDef(type="llm", depends_on=["b"]),
        }

        with pytest.raises(CycleDetectedError) as exc_info:
            build_dag(steps)

        cycle = exc_info.value.cycle
        assert len(cycle) >= 3
        assert "a" in cycle
        assert "b" in cycle
        assert "c" in cycle

    def test_cycle_with_external_nodes(self):
        """Cycle detection works even with non-cyclic nodes present."""
        steps = {
            "root": make_step("map"),
            "good": make_step("fetch", depends_on=["root"]),
            "cycle_a": StepDef(type="llm", depends_on=["cycle_b"]),
            "cycle_b": StepDef(type="embed", depends_on=["cycle_a"]),
        }

        with pytest.raises(CycleDetectedError) as exc_info:
            build_dag(steps)

        # Cycle should only contain the cyclic nodes
        assert "cycle_a" in exc_info.value.cycle
        assert "cycle_b" in exc_info.value.cycle

    def test_cycle_error_message_format(self):
        """Cycle error message shows clear path."""
        steps = {
            "start": StepDef(type="map", depends_on=["end"]),
            "middle": StepDef(type="fetch", depends_on=["start"]),
            "end": StepDef(type="llm", depends_on=["middle"]),
        }

        with pytest.raises(CycleDetectedError) as exc_info:
            build_dag(steps)

        # Error message should have arrow format
        error_msg = str(exc_info.value)
        assert " -> " in error_msg
        assert "Circular dependency detected:" in error_msg


# ============================================================================
# build_dag Tests - Parallelizable Flag
# ============================================================================


class TestBuildDagParallelizable:
    """Tests for parallelizable flag."""

    def test_single_step_not_parallelizable(self):
        """Single step is not parallelizable."""
        steps = {"only": make_step("map")}

        plan = build_dag(steps)

        assert plan.parallelizable is False

    def test_linear_chain_not_parallelizable(self):
        """Linear chain is not parallelizable."""
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch", depends_on=["a"]),
            "c": make_step("llm", depends_on=["b"]),
        }

        plan = build_dag(steps)

        assert plan.parallelizable is False

    def test_two_independent_steps_parallelizable(self):
        """Two independent steps are parallelizable."""
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch"),
        }

        plan = build_dag(steps)

        assert plan.parallelizable is True

    def test_diamond_is_parallelizable(self):
        """Diamond pattern is parallelizable."""
        steps = {
            "source": make_step("map"),
            "left": make_step("fetch", depends_on=["source"]),
            "right": make_step("fetch", depends_on=["source"]),
            "merge": make_step("sql", depends_on=["left", "right"]),
        }

        plan = build_dag(steps)

        assert plan.parallelizable is True


# ============================================================================
# build_dag Tests - Edge Cases
# ============================================================================


class TestBuildDagEdgeCases:
    """Tests for edge cases."""

    def test_missing_dependency_ignored(self):
        """Missing dependencies are ignored (parser should catch this)."""
        # This shouldn't happen in practice (parser validates deps)
        # but build_dag should handle gracefully
        steps = {
            "a": make_step("map"),
            "b": StepDef(type="fetch", depends_on=["nonexistent"]),
        }

        # Should not raise, just ignore missing dep
        plan = build_dag(steps)

        # Both steps at level 0 since 'nonexistent' doesn't exist
        assert plan.total_steps == 2

    def test_wide_parallel_level(self):
        """Many steps at same level (wide parallelism)."""
        steps = {f"step_{i}": make_step("map") for i in range(100)}

        plan = build_dag(steps)

        assert len(plan.levels) == 1
        assert len(plan.levels[0]) == 100
        assert plan.parallelizable is True

    def test_deep_chain(self):
        """Very deep dependency chain."""
        steps: dict[str, StepDef] = {}
        prev = None
        for i in range(50):
            name = f"step_{i}"
            deps = [prev] if prev else []
            steps[name] = StepDef(type="map", depends_on=deps)
            prev = name

        plan = build_dag(steps)

        assert len(plan.levels) == 50
        assert plan.total_steps == 50
        assert plan.parallelizable is False
        assert len(plan.critical_path) == 50

    def test_multiple_dependencies_same_level(self):
        """Step depending on multiple steps at same level."""
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch"),
            "c": make_step("llm"),
            "merge": make_step("sql", depends_on=["a", "b", "c"]),
        }

        plan = build_dag(steps)

        assert plan.levels == [["a", "b", "c"], ["merge"]]

    def test_fan_out_fan_in_multiple_levels(self):
        """Multiple fan-out/fan-in patterns."""
        #     a
        #    /|\
        #   b c d
        #    \|/
        #     e
        #    /|\
        #   f g h
        #    \|/
        #     i
        steps = {
            "a": make_step("map"),
            "b": make_step("fetch", depends_on=["a"]),
            "c": make_step("fetch", depends_on=["a"]),
            "d": make_step("fetch", depends_on=["a"]),
            "e": make_step("sql", depends_on=["b", "c", "d"]),
            "f": make_step("llm", depends_on=["e"]),
            "g": make_step("llm", depends_on=["e"]),
            "h": make_step("llm", depends_on=["e"]),
            "i": make_step("write-db", depends_on=["f", "g", "h"]),
        }

        plan = build_dag(steps)

        assert plan.levels[0] == ["a"]
        assert set(plan.levels[1]) == {"b", "c", "d"}
        assert plan.levels[2] == ["e"]
        assert set(plan.levels[3]) == {"f", "g", "h"}
        assert plan.levels[4] == ["i"]
        assert plan.parallelizable is True

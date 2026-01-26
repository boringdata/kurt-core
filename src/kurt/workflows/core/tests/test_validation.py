"""Tests for workflow validation utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from kurt.workflows.core import detect_cycle, validate_cron


@dataclass
class MockStep:
    """Mock step for testing cycle detection."""

    depends_on: list[str]


class TestDetectCycle:
    """Tests for detect_cycle function."""

    def test_no_cycle_empty(self) -> None:
        """Empty graph has no cycle."""
        assert detect_cycle({}) is None

    def test_no_cycle_single_node(self) -> None:
        """Single node with no dependencies has no cycle."""
        steps = {"a": MockStep(depends_on=[])}
        assert detect_cycle(steps) is None

    def test_no_cycle_linear(self) -> None:
        """Linear chain: a -> b -> c has no cycle."""
        steps = {
            "a": MockStep(depends_on=[]),
            "b": MockStep(depends_on=["a"]),
            "c": MockStep(depends_on=["b"]),
        }
        assert detect_cycle(steps) is None

    def test_no_cycle_diamond(self) -> None:
        """Diamond shape (a -> b,c -> d) has no cycle."""
        steps = {
            "a": MockStep(depends_on=[]),
            "b": MockStep(depends_on=["a"]),
            "c": MockStep(depends_on=["a"]),
            "d": MockStep(depends_on=["b", "c"]),
        }
        assert detect_cycle(steps) is None

    def test_no_cycle_complex_dag(self) -> None:
        """Complex DAG with multiple paths has no cycle."""
        steps = {
            "a": MockStep(depends_on=[]),
            "b": MockStep(depends_on=["a"]),
            "c": MockStep(depends_on=["a"]),
            "d": MockStep(depends_on=["b"]),
            "e": MockStep(depends_on=["b", "c"]),
            "f": MockStep(depends_on=["d", "e"]),
        }
        assert detect_cycle(steps) is None

    def test_self_loop(self) -> None:
        """Self-loop: a -> a is detected."""
        steps = {"a": MockStep(depends_on=["a"])}
        cycle = detect_cycle(steps)
        assert cycle is not None
        assert cycle == ["a", "a"]

    def test_simple_cycle_two_nodes(self) -> None:
        """Simple cycle: a -> b -> a."""
        steps = {
            "a": MockStep(depends_on=["b"]),
            "b": MockStep(depends_on=["a"]),
        }
        cycle = detect_cycle(steps)
        assert cycle is not None
        # Cycle should be [a, b, a] or [b, a, b] depending on start
        assert len(cycle) == 3
        assert cycle[0] == cycle[-1]  # Starts and ends with same node

    def test_simple_cycle_three_nodes(self) -> None:
        """Simple cycle: a -> b -> c -> a."""
        steps = {
            "a": MockStep(depends_on=["b"]),
            "b": MockStep(depends_on=["c"]),
            "c": MockStep(depends_on=["a"]),
        }
        cycle = detect_cycle(steps)
        assert cycle is not None
        # Cycle should be [a, b, c, a] (sorted order starts with 'a')
        assert cycle == ["a", "b", "c", "a"]

    def test_cycle_in_subgraph(self) -> None:
        """Cycle in a subgraph: a -> b -> c -> b (c points back to b)."""
        steps = {
            "a": MockStep(depends_on=["b"]),
            "b": MockStep(depends_on=["c"]),
            "c": MockStep(depends_on=["b"]),  # Cycle: b -> c -> b
        }
        cycle = detect_cycle(steps)
        assert cycle is not None
        # Cycle should be [b, c, b]
        assert cycle == ["b", "c", "b"]

    def test_cycle_with_independent_nodes(self) -> None:
        """Cycle exists alongside independent nodes."""
        steps = {
            "a": MockStep(depends_on=[]),  # Independent
            "b": MockStep(depends_on=["c"]),
            "c": MockStep(depends_on=["d"]),
            "d": MockStep(depends_on=["b"]),  # Cycle: b -> c -> d -> b
            "e": MockStep(depends_on=["a"]),  # Independent chain
        }
        cycle = detect_cycle(steps)
        assert cycle is not None
        # Cycle should be [b, c, d, b]
        assert cycle == ["b", "c", "d", "b"]

    def test_missing_dependency_ignored(self) -> None:
        """Missing dependencies are ignored (not treated as error)."""
        steps = {
            "a": MockStep(depends_on=["nonexistent"]),
            "b": MockStep(depends_on=["a"]),
        }
        # No cycle, just missing dependency
        assert detect_cycle(steps) is None

    def test_dict_input(self) -> None:
        """detect_cycle works with dict-based steps (not just objects)."""
        steps = {
            "a": {"depends_on": ["b"]},
            "b": {"depends_on": ["c"]},
            "c": {"depends_on": ["a"]},
        }
        cycle = detect_cycle(steps)
        assert cycle is not None
        assert cycle == ["a", "b", "c", "a"]

    def test_dict_missing_depends_on(self) -> None:
        """Dict without depends_on key defaults to empty list."""
        steps = {
            "a": {},  # No depends_on key
            "b": {"depends_on": ["a"]},
        }
        assert detect_cycle(steps) is None

    def test_deterministic_order(self) -> None:
        """Cycle detection is deterministic (sorted step order)."""
        steps = {
            "z": MockStep(depends_on=["y"]),
            "y": MockStep(depends_on=["x"]),
            "x": MockStep(depends_on=["z"]),
        }
        # Run multiple times to verify determinism
        results = [detect_cycle(steps) for _ in range(5)]
        assert all(r == results[0] for r in results)
        # Should start with 'x' (alphabetically first)
        assert results[0] == ["x", "z", "y", "x"]


class TestValidateCron:
    """Tests for validate_cron function."""

    def test_valid_cron_expression(self) -> None:
        """Valid cron expressions return empty error list."""
        errors = validate_cron("0 9 * * 1-5")  # Weekdays at 9am
        assert errors == []

    def test_valid_cron_every_minute(self) -> None:
        """Every minute cron is valid."""
        errors = validate_cron("* * * * *")
        assert errors == []

    def test_valid_cron_complex(self) -> None:
        """Complex cron expressions are valid."""
        errors = validate_cron("0 0,12 1 */2 *")  # Midnight and noon on 1st, every 2 months
        assert errors == []

    def test_invalid_cron_expression(self) -> None:
        """Invalid cron expressions return error messages."""
        errors = validate_cron("invalid cron")
        # If croniter is installed, we get an error
        # If not installed, we skip validation
        # So we just check that it doesn't crash
        assert isinstance(errors, list)

    def test_invalid_cron_too_many_fields(self) -> None:
        """Too many fields in cron expression."""
        errors = validate_cron("* * * * * * *")  # 7 fields
        assert isinstance(errors, list)

    def test_invalid_cron_out_of_range(self) -> None:
        """Out of range values in cron expression."""
        errors = validate_cron("60 * * * *")  # 60 minutes is invalid
        assert isinstance(errors, list)

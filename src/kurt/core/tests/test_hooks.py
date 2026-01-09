"""
Unit tests for Lifecycle Hooks.

Tests StepHooks base class, NoopStepHooks, and CompositeStepHooks.
"""

from __future__ import annotations

from unittest.mock import Mock

from kurt.core.hooks import CompositeStepHooks, NoopStepHooks, StepHooks

# ============================================================================
# StepHooks Base Class Tests
# ============================================================================


class TestStepHooksBase:
    """Test StepHooks base class."""

    def test_on_start_returns_none(self):
        """on_start returns None by default."""
        hooks = StepHooks()
        result = hooks.on_start(step_name="test", total=10, concurrency=3)
        assert result is None

    def test_on_row_success_returns_none(self):
        """on_row_success returns None by default."""
        hooks = StepHooks()
        result = hooks.on_row_success(
            step_name="test",
            idx=0,
            total=10,
            latency_ms=100,
            prompt="p",
            tokens_in=10,
            tokens_out=5,
            cost=0.01,
            result={},
        )
        assert result is None

    def test_on_row_error_returns_none(self):
        """on_row_error returns None by default."""
        hooks = StepHooks()
        result = hooks.on_row_error(
            step_name="test",
            idx=0,
            total=10,
            latency_ms=100,
            prompt="p",
            tokens_in=10,
            tokens_out=5,
            cost=0.01,
            error=ValueError("err"),
        )
        assert result is None

    def test_on_result_returns_none(self):
        """on_result returns None by default."""
        hooks = StepHooks()
        result = hooks.on_result(
            step_name="test",
            idx=0,
            total=10,
            status="success",
            error=None,
        )
        assert result is None

    def test_on_end_returns_none(self):
        """on_end returns None by default."""
        hooks = StepHooks()
        result = hooks.on_end(
            step_name="test",
            successful=8,
            total=10,
            errors=["e1", "e2"],
        )
        assert result is None


# ============================================================================
# NoopStepHooks Tests
# ============================================================================


class TestNoopStepHooks:
    """Test NoopStepHooks does nothing."""

    def test_all_methods_callable(self):
        """All hook methods are callable without error."""
        hooks = NoopStepHooks()
        hooks.on_start(step_name="t", total=1, concurrency=1)
        hooks.on_row_success(
            step_name="t",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            result={},
        )
        hooks.on_row_error(
            step_name="t",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            error=Exception(),
        )
        hooks.on_result(step_name="t", idx=0, total=1, status="success", error=None)
        hooks.on_end(step_name="t", successful=1, total=1, errors=[])

    def test_inherits_from_step_hooks(self):
        """NoopStepHooks is a subclass of StepHooks."""
        hooks = NoopStepHooks()
        assert isinstance(hooks, StepHooks)


# ============================================================================
# CompositeStepHooks Tests
# ============================================================================


class TestCompositeStepHooks:
    """Test CompositeStepHooks fans out to all hooks."""

    def test_on_start_calls_all_hooks(self):
        """on_start is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_start(step_name="test", total=10, concurrency=3)
        hook1.on_start.assert_called_once_with(step_name="test", total=10, concurrency=3)
        hook2.on_start.assert_called_once_with(step_name="test", total=10, concurrency=3)

    def test_on_row_success_calls_all_hooks(self):
        """on_row_success is called on all hooks with same args."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_row_success(
            step_name="test",
            idx=0,
            total=10,
            latency_ms=100,
            prompt="p",
            tokens_in=10,
            tokens_out=5,
            cost=0.01,
            result={"key": "val"},
        )
        hook1.on_row_success.assert_called_once()
        hook2.on_row_success.assert_called_once()

        # Verify arguments match
        call_kwargs = hook1.on_row_success.call_args.kwargs
        assert call_kwargs["step_name"] == "test"
        assert call_kwargs["result"] == {"key": "val"}

    def test_on_row_error_calls_all_hooks(self):
        """on_row_error is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        err = ValueError("test")
        composite.on_row_error(
            step_name="test",
            idx=0,
            total=10,
            latency_ms=100,
            prompt="p",
            tokens_in=10,
            tokens_out=5,
            cost=0.01,
            error=err,
        )
        hook1.on_row_error.assert_called_once()
        hook2.on_row_error.assert_called_once()

        # Verify error is passed
        call_kwargs = hook1.on_row_error.call_args.kwargs
        assert call_kwargs["error"] is err

    def test_on_result_calls_all_hooks(self):
        """on_result is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_result(step_name="test", idx=0, total=10, status="success", error=None)
        hook1.on_result.assert_called_once_with(
            step_name="test", idx=0, total=10, status="success", error=None
        )
        hook2.on_result.assert_called_once_with(
            step_name="test", idx=0, total=10, status="success", error=None
        )

    def test_on_end_calls_all_hooks(self):
        """on_end is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_end(step_name="test", successful=8, total=10, errors=["e1"])
        hook1.on_end.assert_called_once_with(
            step_name="test", successful=8, total=10, errors=["e1"]
        )
        hook2.on_end.assert_called_once_with(
            step_name="test", successful=8, total=10, errors=["e1"]
        )

    def test_none_hooks_filtered(self):
        """None values in hooks list are filtered out."""
        hook1 = Mock()
        composite = CompositeStepHooks([hook1, None, None])
        composite.on_start(step_name="test", total=1, concurrency=1)
        hook1.on_start.assert_called_once()

    def test_empty_hooks_list(self):
        """Empty hooks list doesn't error."""
        composite = CompositeStepHooks([])
        # Should not raise
        composite.on_start(step_name="test", total=1, concurrency=1)
        composite.on_row_success(
            step_name="test",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            result={},
        )
        composite.on_row_error(
            step_name="test",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            error=Exception(),
        )
        composite.on_result(step_name="test", idx=0, total=1, status="success", error=None)
        composite.on_end(step_name="test", successful=1, total=1, errors=[])

    def test_inherits_from_step_hooks(self):
        """CompositeStepHooks is a subclass of StepHooks."""
        composite = CompositeStepHooks([])
        assert isinstance(composite, StepHooks)

    def test_multiple_hooks_order_preserved(self):
        """Hooks are called in the order they were added."""
        call_order = []

        hook1 = Mock()
        hook1.on_start.side_effect = lambda **kwargs: call_order.append("hook1")

        hook2 = Mock()
        hook2.on_start.side_effect = lambda **kwargs: call_order.append("hook2")

        hook3 = Mock()
        hook3.on_start.side_effect = lambda **kwargs: call_order.append("hook3")

        composite = CompositeStepHooks([hook1, hook2, hook3])
        composite.on_start(step_name="test", total=1, concurrency=1)

        assert call_order == ["hook1", "hook2", "hook3"]

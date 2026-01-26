"""
Unit tests for tool error taxonomy.
"""

from __future__ import annotations

from kurt.tools.core.errors import (
    ToolCanceledError,
    ToolConfigError,
    ToolError,
    ToolExecutionError,
    ToolInputError,
    ToolNotFoundError,
    ToolTimeoutError,
)


class TestToolError:
    """Test base ToolError class."""

    def test_basic_error(self):
        """ToolError stores message and details."""
        err = ToolError("Something went wrong", {"key": "value"})
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.details == {"key": "value"}

    def test_empty_details_default(self):
        """ToolError defaults to empty details dict."""
        err = ToolError("Error message")
        assert err.details == {}

    def test_inherits_from_exception(self):
        """ToolError is an Exception."""
        err = ToolError("test")
        assert isinstance(err, Exception)


class TestToolNotFoundError:
    """Test ToolNotFoundError."""

    def test_error_message(self):
        """Error message includes tool name."""
        err = ToolNotFoundError("my_tool")
        assert "my_tool" in str(err)
        assert err.tool_name == "my_tool"

    def test_details_contain_tool_name(self):
        """Details dict contains tool name."""
        err = ToolNotFoundError("fetch")
        assert err.details == {"tool_name": "fetch"}

    def test_inherits_from_tool_error(self):
        """ToolNotFoundError inherits from ToolError."""
        err = ToolNotFoundError("test")
        assert isinstance(err, ToolError)


class TestToolConfigError:
    """Test ToolConfigError."""

    def test_error_message(self):
        """Error message includes tool name and message."""
        err = ToolConfigError("map", "missing required field 'url'")
        assert "map" in str(err)
        assert "missing required field 'url'" in str(err)
        assert err.tool_name == "map"

    def test_validation_errors(self):
        """Validation errors are stored."""
        validation_errors = [
            {"loc": ["url"], "msg": "field required", "type": "missing"}
        ]
        err = ToolConfigError("map", "validation failed", validation_errors)
        assert err.validation_errors == validation_errors
        assert err.details["validation_errors"] == validation_errors

    def test_empty_validation_errors_default(self):
        """Validation errors default to empty list."""
        err = ToolConfigError("map", "error")
        assert err.validation_errors == []

    def test_inherits_from_tool_error(self):
        """ToolConfigError inherits from ToolError."""
        err = ToolConfigError("test", "msg")
        assert isinstance(err, ToolError)


class TestToolInputError:
    """Test ToolInputError."""

    def test_error_message(self):
        """Error message includes tool name and message."""
        err = ToolInputError("llm", "invalid input schema")
        assert "llm" in str(err)
        assert "invalid input schema" in str(err)
        assert err.tool_name == "llm"

    def test_validation_errors(self):
        """Validation errors are stored."""
        validation_errors = [
            {"loc": ["content"], "msg": "field required", "type": "missing"}
        ]
        err = ToolInputError("llm", "validation failed", validation_errors)
        assert err.validation_errors == validation_errors

    def test_inherits_from_tool_error(self):
        """ToolInputError inherits from ToolError."""
        err = ToolInputError("test", "msg")
        assert isinstance(err, ToolError)


class TestToolExecutionError:
    """Test ToolExecutionError."""

    def test_error_message(self):
        """Error message includes tool name and message."""
        err = ToolExecutionError("fetch", "connection refused")
        assert "fetch" in str(err)
        assert "connection refused" in str(err)
        assert err.tool_name == "fetch"

    def test_cause_exception(self):
        """Cause exception is stored and reflected in details."""
        cause = ValueError("underlying error")
        err = ToolExecutionError("fetch", "failed", cause)
        assert err.cause is cause
        assert err.details["cause_type"] == "ValueError"
        assert err.details["cause_message"] == "underlying error"

    def test_no_cause(self):
        """Works without a cause exception."""
        err = ToolExecutionError("fetch", "failed")
        assert err.cause is None
        assert err.details["cause_type"] is None
        assert err.details["cause_message"] is None

    def test_inherits_from_tool_error(self):
        """ToolExecutionError inherits from ToolError."""
        err = ToolExecutionError("test", "msg")
        assert isinstance(err, ToolError)


class TestToolTimeoutError:
    """Test ToolTimeoutError."""

    def test_error_message(self):
        """Error message includes tool name and timeout."""
        err = ToolTimeoutError("agent", 30.0)
        assert "agent" in str(err)
        assert "30" in str(err)
        assert err.tool_name == "agent"
        assert err.timeout_seconds == 30.0

    def test_elapsed_time_in_message(self):
        """Elapsed time is included in message when provided."""
        err = ToolTimeoutError("agent", 30.0, elapsed_seconds=35.5)
        assert "35.50" in str(err)
        assert err.elapsed_seconds == 35.5

    def test_details_contain_all_fields(self):
        """Details contain all timing information."""
        err = ToolTimeoutError("agent", 30.0, elapsed_seconds=35.5)
        assert err.details == {
            "tool_name": "agent",
            "timeout_seconds": 30.0,
            "elapsed_seconds": 35.5,
        }

    def test_inherits_from_tool_error(self):
        """ToolTimeoutError inherits from ToolError."""
        err = ToolTimeoutError("test", 10.0)
        assert isinstance(err, ToolError)


class TestToolCanceledError:
    """Test ToolCanceledError."""

    def test_error_message_without_reason(self):
        """Error message without reason."""
        err = ToolCanceledError("llm")
        assert "llm" in str(err)
        assert "canceled" in str(err).lower()
        assert err.tool_name == "llm"
        assert err.reason is None

    def test_error_message_with_reason(self):
        """Error message includes reason when provided."""
        err = ToolCanceledError("llm", "user requested stop")
        assert "user requested stop" in str(err)
        assert err.reason == "user requested stop"

    def test_details_contain_reason(self):
        """Details contain the cancellation reason."""
        err = ToolCanceledError("llm", "system shutdown")
        assert err.details == {
            "tool_name": "llm",
            "reason": "system shutdown",
        }

    def test_inherits_from_tool_error(self):
        """ToolCanceledError inherits from ToolError."""
        err = ToolCanceledError("test")
        assert isinstance(err, ToolError)


class TestErrorHierarchy:
    """Test error class hierarchy."""

    def test_all_errors_catchable_as_tool_error(self):
        """All specific errors can be caught as ToolError."""
        errors = [
            ToolNotFoundError("x"),
            ToolConfigError("x", "m"),
            ToolInputError("x", "m"),
            ToolExecutionError("x", "m"),
            ToolTimeoutError("x", 10),
            ToolCanceledError("x"),
        ]
        for err in errors:
            try:
                raise err
            except ToolError as caught:
                assert caught is err

    def test_all_errors_have_message_attribute(self):
        """All errors have a message attribute."""
        errors = [
            ToolNotFoundError("x"),
            ToolConfigError("x", "m"),
            ToolInputError("x", "m"),
            ToolExecutionError("x", "m"),
            ToolTimeoutError("x", 10),
            ToolCanceledError("x"),
        ]
        for err in errors:
            assert hasattr(err, "message")
            assert isinstance(err.message, str)

    def test_all_errors_have_details_attribute(self):
        """All errors have a details attribute."""
        errors = [
            ToolNotFoundError("x"),
            ToolConfigError("x", "m"),
            ToolInputError("x", "m"),
            ToolExecutionError("x", "m"),
            ToolTimeoutError("x", 10),
            ToolCanceledError("x"),
        ]
        for err in errors:
            assert hasattr(err, "details")
            assert isinstance(err.details, dict)

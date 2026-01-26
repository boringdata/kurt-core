"""
Tests for input interpolation engine.
"""

from __future__ import annotations

import pytest

from kurt.workflows.toml.interpolation import (
    InterpolationError,
    extract_variables,
    interpolate_config,
    interpolate_step_config,
    validate_config_variables,
)

# ============================================================================
# Basic String Interpolation Tests
# ============================================================================


class TestBasicInterpolation:
    """Tests for basic {{var}} substitution."""

    def test_simple_substitution(self):
        """Single variable in string."""
        config = {"message": "Hello {{name}}"}
        inputs = {"name": "World"}
        result = interpolate_config(config, inputs)
        assert result == {"message": "Hello World"}

    def test_multiple_variables(self):
        """Multiple variables in one string."""
        config = {"message": "{{greeting}}, {{name}}!"}
        inputs = {"greeting": "Hello", "name": "World"}
        result = interpolate_config(config, inputs)
        assert result == {"message": "Hello, World!"}

    def test_variable_only_string(self):
        """String containing only a variable returns typed value."""
        config = {"count": "{{num}}"}
        inputs = {"num": 42}
        result = interpolate_config(config, inputs)
        assert result == {"count": 42}
        assert isinstance(result["count"], int)

    def test_variable_with_whitespace(self):
        """Whitespace around variable name is allowed."""
        config = {"value": "{{ spaced }}"}
        inputs = {"spaced": "works"}
        result = interpolate_config(config, inputs)
        assert result == {"value": "works"}

    def test_no_variables_passthrough(self):
        """Strings without variables pass through unchanged."""
        config = {"static": "no variables here"}
        inputs = {}
        result = interpolate_config(config, inputs)
        assert result == {"static": "no variables here"}

    def test_non_string_passthrough(self):
        """Non-string values pass through unchanged."""
        config = {"count": 42, "enabled": True, "rate": 3.14, "empty": None}
        inputs = {}
        result = interpolate_config(config, inputs)
        assert result == config

    def test_empty_config(self):
        """Empty config returns empty dict."""
        result = interpolate_config({}, {"a": 1})
        assert result == {}


# ============================================================================
# Nested Structure Tests
# ============================================================================


class TestNestedStructures:
    """Tests for nested dict/list interpolation."""

    def test_nested_dict(self):
        """Variables in nested dicts."""
        config = {
            "outer": {
                "inner": "{{value}}",
                "static": "unchanged",
            }
        }
        inputs = {"value": "replaced"}
        result = interpolate_config(config, inputs)
        assert result == {
            "outer": {
                "inner": "replaced",
                "static": "unchanged",
            }
        }

    def test_nested_list(self):
        """Variables in lists."""
        config = {"items": ["{{a}}", "static", "{{b}}"]}
        inputs = {"a": "first", "b": "third"}
        result = interpolate_config(config, inputs)
        assert result == {"items": ["first", "static", "third"]}

    def test_deeply_nested(self):
        """Variables in deeply nested structures."""
        config = {
            "level1": {
                "level2": {
                    "level3": ["{{deep}}"],
                }
            }
        }
        inputs = {"deep": "found"}
        result = interpolate_config(config, inputs)
        assert result["level1"]["level2"]["level3"] == ["found"]

    def test_list_of_dicts(self):
        """Variables in list of dicts."""
        config = {
            "records": [
                {"name": "{{name1}}"},
                {"name": "{{name2}}"},
            ]
        }
        inputs = {"name1": "Alice", "name2": "Bob"}
        result = interpolate_config(config, inputs)
        assert result == {
            "records": [
                {"name": "Alice"},
                {"name": "Bob"},
            ]
        }


# ============================================================================
# Type Coercion Tests
# ============================================================================


class TestTypeCoercion:
    """Tests for type coercion from string inputs."""

    def test_string_to_int(self):
        """String input converted to int with type hint."""
        config = {"batch_size": "{{size}}"}
        inputs = {"size": "100"}
        result = interpolate_config(config, inputs, type_hints={"batch_size": int})
        assert result["batch_size"] == 100
        assert isinstance(result["batch_size"], int)

    def test_string_to_float(self):
        """String input converted to float with type hint."""
        config = {"temperature": "{{temp}}"}
        inputs = {"temp": "0.7"}
        result = interpolate_config(config, inputs, type_hints={"temperature": float})
        assert result["temperature"] == 0.7
        assert isinstance(result["temperature"], float)

    def test_string_to_bool_true_variants(self):
        """String to bool conversion for true values."""
        for value in ["true", "True", "TRUE", "1", "yes", "YES"]:
            config = {"enabled": "{{flag}}"}
            inputs = {"flag": value}
            result = interpolate_config(config, inputs, type_hints={"enabled": bool})
            assert result["enabled"] is True

    def test_string_to_bool_false_variants(self):
        """String to bool conversion for false values."""
        for value in ["false", "False", "FALSE", "0", "no", "NO"]:
            config = {"enabled": "{{flag}}"}
            inputs = {"flag": value}
            result = interpolate_config(config, inputs, type_hints={"enabled": bool})
            assert result["enabled"] is False

    def test_int_passthrough_with_int_hint(self):
        """Int value passes through with int type hint."""
        config = {"count": "{{num}}"}
        inputs = {"num": 42}
        result = interpolate_config(config, inputs, type_hints={"count": int})
        assert result["count"] == 42
        assert isinstance(result["count"], int)

    def test_float_to_int_exact(self):
        """Float that is exact int can be converted."""
        config = {"count": "{{num}}"}
        inputs = {"num": 10.0}
        result = interpolate_config(config, inputs, type_hints={"count": int})
        assert result["count"] == 10
        assert isinstance(result["count"], int)

    def test_int_to_float(self):
        """Int can be converted to float."""
        config = {"rate": "{{num}}"}
        inputs = {"num": 10}
        result = interpolate_config(config, inputs, type_hints={"rate": float})
        assert result["rate"] == 10.0
        assert isinstance(result["rate"], float)

    def test_any_to_string(self):
        """Any value can be converted to string."""
        config = {"message": "{{value}}"}
        inputs = {"value": 42}
        result = interpolate_config(config, inputs, type_hints={"message": str})
        assert result["message"] == "42"
        assert isinstance(result["message"], str)

    def test_type_coercion_error_invalid_int(self):
        """Invalid int conversion raises InterpolationError."""
        config = {"count": "{{num}}"}
        inputs = {"num": "not_a_number"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, type_hints={"count": int})
        error = exc_info.value
        assert error.type == "type_coercion"
        assert error.var == "num"
        assert error.expected_type == "int"
        assert "not_a_number" in error.message

    def test_type_coercion_error_invalid_float(self):
        """Invalid float conversion raises InterpolationError."""
        config = {"rate": "{{value}}"}
        inputs = {"value": "abc"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, type_hints={"rate": float})
        error = exc_info.value
        assert error.type == "type_coercion"
        assert error.expected_type == "float"

    def test_type_coercion_error_invalid_bool(self):
        """Invalid bool conversion raises InterpolationError."""
        config = {"enabled": "{{flag}}"}
        inputs = {"flag": "maybe"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, type_hints={"enabled": bool})
        error = exc_info.value
        assert error.type == "type_coercion"
        assert error.expected_type == "bool"

    def test_float_to_int_non_exact_error(self):
        """Float with decimal cannot convert to int."""
        config = {"count": "{{num}}"}
        inputs = {"num": 10.5}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, type_hints={"count": int})
        error = exc_info.value
        assert error.type == "type_coercion"
        assert error.expected_type == "int"


# ============================================================================
# Escape Syntax Tests
# ============================================================================


class TestEscapeSyntax:
    """Tests for escaped brace handling."""

    def test_escaped_opening_brace(self):
        """\\{{ produces literal {{."""
        config = {"text": "Show \\{{literal}} braces"}
        inputs = {}
        result = interpolate_config(config, inputs)
        assert result == {"text": "Show {{literal}} braces"}

    def test_escaped_closing_brace(self):
        """\\}} produces literal }}."""
        config = {"text": "Closing \\}} brace"}
        inputs = {}
        result = interpolate_config(config, inputs)
        assert result == {"text": "Closing }} brace"}

    def test_escaped_with_variable(self):
        """Escaped braces alongside real variables."""
        config = {"text": "\\{{literal}} and {{var}}"}
        inputs = {"var": "replaced"}
        result = interpolate_config(config, inputs)
        assert result == {"text": "{{literal}} and replaced"}

    def test_multiple_escapes(self):
        """Multiple escaped sequences."""
        config = {"text": "\\{{a}} \\{{b}} \\{{c}}"}
        inputs = {}
        result = interpolate_config(config, inputs)
        assert result == {"text": "{{a}} {{b}} {{c}}"}

    def test_only_escaped_braces(self):
        """String with only escaped braces."""
        config = {"template": "\\{{placeholder\\}}"}
        inputs = {}
        result = interpolate_config(config, inputs)
        assert result == {"template": "{{placeholder}}"}


# ============================================================================
# Missing Input Tests
# ============================================================================


class TestMissingInputs:
    """Tests for missing required input handling."""

    def test_missing_input_raises(self):
        """Missing input raises InterpolationError."""
        config = {"message": "Hello {{name}}"}
        inputs = {}
        valid_vars = {"name"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars)
        error = exc_info.value
        assert error.type == "missing_input"
        assert error.var == "name"
        assert "name" in error.message

    def test_missing_input_in_nested(self):
        """Missing input in nested structure."""
        config = {"outer": {"inner": "{{missing}}"}}
        inputs = {}
        valid_vars = {"missing"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars)
        error = exc_info.value
        assert error.type == "missing_input"
        assert error.var == "missing"
        assert "outer.inner" in error.field

    def test_missing_one_of_multiple(self):
        """One of multiple inputs missing."""
        config = {"message": "{{a}} and {{b}}"}
        inputs = {"a": "first"}
        valid_vars = {"a", "b"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars)
        error = exc_info.value
        assert error.type == "missing_input"
        assert error.var == "b"


# ============================================================================
# Unknown Variable Tests (Typo Protection)
# ============================================================================


class TestUnknownVariables:
    """Tests for unknown variable detection."""

    def test_unknown_variable_raises(self):
        """Unknown variable raises InterpolationError."""
        config = {"message": "Hello {{unknwon}}"}  # Typo
        inputs = {"unknown": "World"}
        valid_vars = {"unknown"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars, step_name="test_step")
        error = exc_info.value
        assert error.type == "unknown_var"
        assert error.var == "unknwon"
        assert error.step == "test_step"
        assert "unknwon" in error.message

    def test_unknown_variable_in_list(self):
        """Unknown variable in list element."""
        config = {"items": ["{{valid}}", "{{typo}}"]}
        inputs = {"valid": "ok"}
        valid_vars = {"valid"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars)
        error = exc_info.value
        assert error.type == "unknown_var"
        assert error.var == "typo"
        assert "items[1]" in error.field

    def test_unknown_variable_in_nested_dict(self):
        """Unknown variable in nested dict."""
        config = {"outer": {"inner": {"deep": "{{nope}}"}}}
        inputs = {}
        valid_vars = {"yes"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars)
        error = exc_info.value
        assert error.type == "unknown_var"
        assert error.var == "nope"

    def test_valid_vars_from_inputs_default(self):
        """When valid_vars is None, uses input keys."""
        config = {"message": "{{unknown}}"}
        inputs = {"known": "value"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs)  # valid_vars=None
        error = exc_info.value
        assert error.type == "unknown_var"
        assert error.var == "unknown"


# ============================================================================
# Error Message Quality Tests
# ============================================================================


class TestErrorMessages:
    """Tests for error message quality."""

    def test_missing_input_message(self):
        """Missing input error has helpful message."""
        config = {"value": "{{my_var}}"}
        inputs = {}
        valid_vars = {"my_var"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, valid_vars=valid_vars)
        assert "Required input my_var not provided" in str(exc_info.value)

    def test_unknown_var_message_includes_step(self):
        """Unknown var error includes step name."""
        config = {"value": "{{typo}}"}
        inputs = {}
        valid_vars = {"correct"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(
                config, inputs, valid_vars=valid_vars, step_name="my_step"
            )
        msg = str(exc_info.value)
        assert "{{typo}}" in msg
        assert "my_step" in msg

    def test_type_coercion_message_includes_value(self):
        """Type coercion error includes the bad value."""
        config = {"count": "{{num}}"}
        inputs = {"num": "not_valid"}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate_config(config, inputs, type_hints={"count": int})
        msg = str(exc_info.value)
        assert "not_valid" in msg
        assert "int" in msg


# ============================================================================
# interpolate_step_config Tests
# ============================================================================


class TestInterpolateStepConfig:
    """Tests for the convenience wrapper function."""

    def test_basic_step_config(self):
        """Basic usage of interpolate_step_config."""
        step_config = {"model": "{{model_name}}", "temperature": "{{temp}}"}
        inputs = {"model_name": "gpt-4", "temp": 0.7}
        workflow_input_names = {"model_name", "temp"}

        result = interpolate_step_config(
            step_config,
            inputs,
            workflow_input_names=workflow_input_names,
            step_name="llm_step",
        )
        assert result == {"model": "gpt-4", "temperature": 0.7}

    def test_step_config_with_type_hints(self):
        """Step config with type hints."""
        step_config = {"batch_size": "{{size}}"}
        inputs = {"size": "100"}
        workflow_input_names = {"size"}

        result = interpolate_step_config(
            step_config,
            inputs,
            workflow_input_names=workflow_input_names,
            step_name="batch_step",
            type_hints={"batch_size": int},
        )
        assert result["batch_size"] == 100
        assert isinstance(result["batch_size"], int)

    def test_step_config_unknown_var(self):
        """Unknown var in step config raises with step name."""
        step_config = {"value": "{{typo}}"}
        inputs = {}
        workflow_input_names = {"correct"}

        with pytest.raises(InterpolationError) as exc_info:
            interpolate_step_config(
                step_config,
                inputs,
                workflow_input_names=workflow_input_names,
                step_name="my_step",
            )
        assert exc_info.value.step == "my_step"


# ============================================================================
# extract_variables Tests
# ============================================================================


class TestExtractVariables:
    """Tests for variable extraction utility."""

    def test_single_variable(self):
        """Extract single variable."""
        result = extract_variables("Hello {{name}}")
        assert result == {"name"}

    def test_multiple_variables(self):
        """Extract multiple variables."""
        result = extract_variables("{{a}} and {{b}} and {{c}}")
        assert result == {"a", "b", "c"}

    def test_repeated_variable(self):
        """Repeated variable counted once."""
        result = extract_variables("{{x}} {{x}} {{x}}")
        assert result == {"x"}

    def test_no_variables(self):
        """No variables returns empty set."""
        result = extract_variables("no variables here")
        assert result == set()

    def test_escaped_not_extracted(self):
        """Escaped variables not extracted."""
        result = extract_variables("\\{{escaped}} and {{real}}")
        assert result == {"real"}

    def test_variable_with_underscore(self):
        """Variable names can have underscores."""
        result = extract_variables("{{my_var_name}}")
        assert result == {"my_var_name"}


# ============================================================================
# validate_config_variables Tests
# ============================================================================


class TestValidateConfigVariables:
    """Tests for validation utility."""

    def test_valid_config_no_errors(self):
        """Valid config returns empty error list."""
        config = {"a": "{{x}}", "b": "{{y}}"}
        valid_vars = {"x", "y"}
        errors = validate_config_variables(config, valid_vars, "step1")
        assert errors == []

    def test_single_unknown_variable(self):
        """Single unknown variable returned as error."""
        config = {"value": "{{typo}}"}
        valid_vars = {"correct"}
        errors = validate_config_variables(config, valid_vars, "step1")
        assert len(errors) == 1
        assert errors[0].type == "unknown_var"
        assert errors[0].var == "typo"

    def test_multiple_unknown_variables(self):
        """Multiple unknown variables all returned."""
        config = {"a": "{{x}}", "b": "{{y}}", "c": "{{z}}"}
        valid_vars = {"x"}
        errors = validate_config_variables(config, valid_vars, "step1")
        assert len(errors) == 2
        error_vars = {e.var for e in errors}
        assert error_vars == {"y", "z"}

    def test_nested_unknown_variables(self):
        """Unknown variables in nested structures detected."""
        config = {
            "outer": {
                "inner": "{{bad}}",
            },
            "list": ["{{also_bad}}"],
        }
        valid_vars = set()
        errors = validate_config_variables(config, valid_vars, "step1")
        assert len(errors) == 2
        error_vars = {e.var for e in errors}
        assert error_vars == {"bad", "also_bad"}

    def test_error_includes_field_path(self):
        """Errors include the field path."""
        config = {"outer": {"inner": "{{unknown}}"}}
        valid_vars = set()
        errors = validate_config_variables(config, valid_vars, "my_step")
        assert len(errors) == 1
        assert "outer.inner" in errors[0].field
        assert errors[0].step == "my_step"


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string_value(self):
        """Empty string input substitutes correctly."""
        config = {"name": "{{empty}}"}
        inputs = {"empty": ""}
        result = interpolate_config(config, inputs)
        assert result == {"name": ""}

    def test_variable_at_start(self):
        """Variable at start of string."""
        config = {"msg": "{{greeting}} there!"}
        inputs = {"greeting": "Hi"}
        result = interpolate_config(config, inputs)
        assert result == {"msg": "Hi there!"}

    def test_variable_at_end(self):
        """Variable at end of string."""
        config = {"msg": "Hello {{name}}"}
        inputs = {"name": "World"}
        result = interpolate_config(config, inputs)
        assert result == {"msg": "Hello World"}

    def test_adjacent_variables(self):
        """Adjacent variables without separator."""
        config = {"combined": "{{a}}{{b}}{{c}}"}
        inputs = {"a": "1", "b": "2", "c": "3"}
        result = interpolate_config(config, inputs)
        assert result == {"combined": "123"}

    def test_variable_in_middle(self):
        """Variable in middle of string."""
        config = {"msg": "pre {{var}} post"}
        inputs = {"var": "middle"}
        result = interpolate_config(config, inputs)
        assert result == {"msg": "pre middle post"}

    def test_single_char_variable(self):
        """Single character variable name."""
        config = {"x": "{{a}}"}
        inputs = {"a": "value"}
        result = interpolate_config(config, inputs)
        assert result == {"x": "value"}

    def test_numeric_string_stays_string_without_hint(self):
        """Numeric string stays string without type hint."""
        config = {"value": "prefix {{num}} suffix"}
        inputs = {"num": 42}
        result = interpolate_config(config, inputs)
        assert result == {"value": "prefix 42 suffix"}
        assert isinstance(result["value"], str)

    def test_bool_value_in_partial_string(self):
        """Bool value converted to string in partial substitution."""
        config = {"msg": "Value is {{flag}}"}
        inputs = {"flag": True}
        result = interpolate_config(config, inputs)
        assert result == {"msg": "Value is True"}

    def test_list_in_input_value(self):
        """List as input value in full substitution."""
        config = {"items": "{{my_list}}"}
        inputs = {"my_list": [1, 2, 3]}
        result = interpolate_config(config, inputs)
        assert result == {"items": [1, 2, 3]}

    def test_dict_in_input_value(self):
        """Dict as input value in full substitution."""
        config = {"options": "{{opts}}"}
        inputs = {"opts": {"a": 1, "b": 2}}
        result = interpolate_config(config, inputs)
        assert result == {"options": {"a": 1, "b": 2}}

    def test_none_in_input_value(self):
        """None as input value in full substitution."""
        config = {"value": "{{null_val}}"}
        inputs = {"null_val": None}
        result = interpolate_config(config, inputs)
        assert result == {"value": None}

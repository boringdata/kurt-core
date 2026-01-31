"""
Standalone test runner for kurt.workflows.toml.parser that doesn't require pandas.
Run with: python src/kurt/engine/tests/run_standalone_tests.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

import tempfile
from pathlib import Path
from textwrap import dedent

from pydantic import BaseModel

# Import the module under test
from kurt.workflows.toml.parser import (
    CircularDependencyError,
    InputDef,
    StepDef,
    UnknownDependsOnError,
    UnknownKeyError,
    UnknownStepTypeError,
    WorkflowParseError,
    parse_workflow,
)

# For TOML decode error
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def write_toml(path: Path, content: str) -> Path:
    """Write TOML content to a file and return the path."""
    path.write_text(dedent(content).strip())
    return path


passed = 0
failed = 0


def test(name: str, fn):
    global passed, failed
    try:
        fn()
        print(f"  PASS: {name}")
        passed += 1
    except AssertionError as e:
        print(f"  FAIL: {name}")
        print(f"        {e}")
        failed += 1
    except Exception as e:
        print(f"  ERROR: {name}")
        print(f"        {type(e).__name__}: {e}")
        failed += 1


# ============================================================================
# InputDef Tests
# ============================================================================
print("\nTestInputDef:")


def test_minimal_input():
    i = InputDef(type="string")
    assert i.type == "string"
    assert i.required is False
    assert i.default is None


test("minimal_input", test_minimal_input)


def test_required_input():
    i = InputDef(type="int", required=True)
    assert i.required is True


test("required_input", test_required_input)


def test_string_with_default():
    i = InputDef(type="string", default="hello")
    assert i.default == "hello"


test("string_with_default", test_string_with_default)


def test_int_with_default():
    i = InputDef(type="int", default=42)
    assert i.default == 42


test("int_with_default", test_int_with_default)


def test_float_accepts_int():
    i = InputDef(type="float", default=10)
    assert i.default == 10


test("float_accepts_int", test_float_accepts_int)


def test_bool_with_default():
    i = InputDef(type="bool", default=True)
    assert i.default is True


test("bool_with_default", test_bool_with_default)


def test_invalid_default():
    try:
        InputDef(type="int", default="not an int")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "does not match type" in str(e)


test("invalid_default_raises", test_invalid_default)


# ============================================================================
# StepDef Tests
# ============================================================================
print("\nTestStepDef:")


def test_minimal_step():
    s = StepDef(type="map")
    assert s.type == "map"
    assert s.depends_on == []
    assert s.config == {}
    assert s.continue_on_error is False


test("minimal_step", test_minimal_step)


def test_step_with_deps():
    s = StepDef(type="llm", depends_on=["fetch", "map"])
    assert s.depends_on == ["fetch", "map"]


test("step_with_deps", test_step_with_deps)


def test_step_with_config():
    s = StepDef(type="llm", config={"model": "gpt-4"})
    assert s.config == {"model": "gpt-4"}


test("step_with_config", test_step_with_config)


# ============================================================================
# parse_workflow Tests - Basic
# ============================================================================
print("\nTestParseWorkflowBasic:")


def test_minimal_workflow():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "minimal.toml",
            """
            [workflow]
            name = "minimal"
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert result.workflow.name == "minimal"
        assert result.workflow.description is None
        assert result.inputs == {}
        assert result.steps == {}


test("minimal_workflow", test_minimal_workflow)


def test_workflow_with_description():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "desc.toml",
            """
            [workflow]
            name = "with-desc"
            description = "A workflow with a description"
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert result.workflow.description == "A workflow with a description"


test("workflow_with_description", test_workflow_with_description)


def test_workflow_with_inputs():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "inputs.toml",
            """
            [workflow]
            name = "with-inputs"

            [inputs.url]
            type = "string"
            required = true

            [inputs.limit]
            type = "int"
            default = 100
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert "url" in result.inputs
        assert result.inputs["url"].type == "string"
        assert result.inputs["url"].required is True
        assert result.inputs["limit"].default == 100


test("workflow_with_inputs", test_workflow_with_inputs)


def test_workflow_with_steps():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "steps.toml",
            """
            [workflow]
            name = "with-steps"

            [steps.discover]
            type = "map"
            config = { url = "https://example.com" }

            [steps.fetch]
            type = "fetch"
            depends_on = ["discover"]

            [steps.extract]
            type = "llm"
            depends_on = ["fetch"]
            config = { model = "gpt-4" }
            continue_on_error = true
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert "discover" in result.steps
        assert result.steps["discover"].type == "map"
        assert result.steps["fetch"].depends_on == ["discover"]
        assert result.steps["extract"].continue_on_error is True


test("workflow_with_steps", test_workflow_with_steps)


# ============================================================================
# parse_workflow Tests - Step Types
# ============================================================================
print("\nTestParseWorkflowStepTypes:")


def test_valid_step_types():
    for step_type in ["map", "fetch", "llm", "embed", "write", "sql", "agent"]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            toml_path = write_toml(
                Path(tmp_dir) / f"{step_type}.toml",
                f"""
                [workflow]
                name = "test-{step_type}"

                [steps.test]
                type = "{step_type}"
                """,
            )
            result = parse_workflow(toml_path, validate_tools=False)
            assert result.steps["test"].type == step_type


test("valid_step_types", test_valid_step_types)


def test_unknown_step_type():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "unknown.toml",
            """
            [workflow]
            name = "unknown-type"

            [steps.bad]
            type = "nonexistent"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised UnknownStepTypeError")
        except UnknownStepTypeError as e:
            assert e.step_name == "bad"
            assert e.step_type == "nonexistent"
            assert "Step bad has unknown type: nonexistent" in str(e)


test("unknown_step_type", test_unknown_step_type)


# ============================================================================
# parse_workflow Tests - Dependencies
# ============================================================================
print("\nTestParseWorkflowDependencies:")


def test_valid_dependencies():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "valid-deps.toml",
            """
            [workflow]
            name = "valid-deps"

            [steps.a]
            type = "map"

            [steps.b]
            type = "fetch"
            depends_on = ["a"]

            [steps.c]
            type = "llm"
            depends_on = ["a", "b"]
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert result.steps["c"].depends_on == ["a", "b"]


test("valid_dependencies", test_valid_dependencies)


def test_unknown_dependency():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "unknown-dep.toml",
            """
            [workflow]
            name = "unknown-dep"

            [steps.process]
            type = "llm"
            depends_on = ["nonexistent"]
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised UnknownDependsOnError")
        except UnknownDependsOnError as e:
            assert e.step_name == "process"
            assert e.dep == "nonexistent"


test("unknown_dependency", test_unknown_dependency)


def test_circular_dependency():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "circular.toml",
            """
            [workflow]
            name = "circular"

            [steps.a]
            type = "map"
            depends_on = ["b"]

            [steps.b]
            type = "fetch"
            depends_on = ["a"]
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised CircularDependencyError")
        except CircularDependencyError as e:
            assert "a" in e.cycle
            assert "b" in e.cycle


test("circular_dependency", test_circular_dependency)


def test_self_reference():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "self-ref.toml",
            """
            [workflow]
            name = "self-ref"

            [steps.loop]
            type = "llm"
            depends_on = ["loop"]
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised CircularDependencyError")
        except CircularDependencyError as e:
            assert "loop" in e.cycle


test("self_reference", test_self_reference)


# ============================================================================
# parse_workflow Tests - Strict Validation
# ============================================================================
print("\nTestParseWorkflowStrictValidation:")


def test_unknown_top_level_key():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "unknown-top.toml",
            """
            [workflow]
            name = "test"

            [unknown_section]
            foo = "bar"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised UnknownKeyError")
        except UnknownKeyError as e:
            assert e.location == "Workflow file"
            assert e.key == "unknown_section"


test("unknown_top_level_key", test_unknown_top_level_key)


def test_unknown_workflow_key():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "unknown-workflow.toml",
            """
            [workflow]
            name = "test"
            unknown_key = "value"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised UnknownKeyError")
        except UnknownKeyError as e:
            assert e.location == "[workflow]"
            assert e.key == "unknown_key"


test("unknown_workflow_key", test_unknown_workflow_key)


def test_unknown_input_key():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "unknown-input.toml",
            """
            [workflow]
            name = "test"

            [inputs.my_input]
            type = "string"
            unknown = "value"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised UnknownKeyError")
        except UnknownKeyError as e:
            assert "inputs.my_input" in e.location
            assert e.key == "unknown"


test("unknown_input_key", test_unknown_input_key)


def test_unknown_step_key():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "unknown-step.toml",
            """
            [workflow]
            name = "test"

            [steps.my_step]
            type = "map"
            unknown_option = true
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised UnknownKeyError")
        except UnknownKeyError as e:
            assert "steps.my_step" in e.location
            assert e.key == "unknown_option"


test("unknown_step_key", test_unknown_step_key)


# ============================================================================
# parse_workflow Tests - Errors
# ============================================================================
print("\nTestParseWorkflowErrors:")


def test_missing_workflow_section():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "no-workflow.toml",
            """
            [steps.test]
            type = "map"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised WorkflowParseError")
        except WorkflowParseError as e:
            assert "Missing required" in str(e)


test("missing_workflow_section", test_missing_workflow_section)


def test_missing_step_type():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "no-type.toml",
            """
            [workflow]
            name = "test"

            [steps.my_step]
            config = { foo = "bar" }
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised WorkflowParseError")
        except WorkflowParseError as e:
            assert "missing required 'type'" in str(e)


test("missing_step_type", test_missing_step_type)


def test_nonexistent_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            parse_workflow(Path(tmp_dir) / "nonexistent.toml", validate_tools=False)
            raise AssertionError("Should have raised FileNotFoundError")
        except FileNotFoundError:
            pass


test("nonexistent_file", test_nonexistent_file)


def test_invalid_toml():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = Path(tmp_dir) / "invalid.toml"
        toml_path.write_text("this is not valid [toml")
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised TOMLDecodeError")
        except tomllib.TOMLDecodeError:
            pass


test("invalid_toml", test_invalid_toml)


def test_input_not_table():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "input-not-table.toml",
            """
            [workflow]
            name = "test"

            [inputs]
            my_input = "not a table"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised WorkflowParseError")
        except WorkflowParseError as e:
            assert "must be a table" in str(e)


test("input_not_table", test_input_not_table)


def test_step_not_table():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "step-not-table.toml",
            """
            [workflow]
            name = "test"

            [steps]
            my_step = "not a table"
            """,
        )
        try:
            parse_workflow(toml_path, validate_tools=False)
            raise AssertionError("Should have raised WorkflowParseError")
        except WorkflowParseError as e:
            assert "must be a table" in str(e)


test("step_not_table", test_step_not_table)


# ============================================================================
# parse_workflow Tests - Output Schema Resolution
# ============================================================================
print("\nTestParseWorkflowOutputSchema:")


def test_output_schema_resolution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        models_path = tmp_dir / "models.py"
        models_path.write_text(
            """
from pydantic import BaseModel

class ExtractedEntity(BaseModel):
    name: str
    entity_type: str
"""
        )

        toml_path = write_toml(
            tmp_dir / "with-schema.toml",
            """
            [workflow]
            name = "test-schema"

            [steps.extract]
            type = "llm"
            config = { output_schema = "ExtractedEntity" }
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)
        schema = result.steps["extract"].config["output_schema"]
        assert isinstance(schema, type)
        assert issubclass(schema, BaseModel)
        assert schema.__name__ == "ExtractedEntity"


test("output_schema_resolution", test_output_schema_resolution)


def test_output_schema_explicit_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Create models.py in a subdirectory
        models_dir = tmp_dir / "custom"
        models_dir.mkdir()
        models_path = models_dir / "my_models.py"
        models_path.write_text(
            """
from pydantic import BaseModel

class CustomModel(BaseModel):
    value: str
"""
        )

        toml_path = write_toml(
            tmp_dir / "custom-models.toml",
            """
            [workflow]
            name = "test"

            [steps.extract]
            type = "llm"
            config = { output_schema = "CustomModel" }
            """,
        )

        result = parse_workflow(toml_path, models_path=models_path, validate_tools=False)
        schema = result.steps["extract"].config["output_schema"]
        assert isinstance(schema, type)
        assert schema.__name__ == "CustomModel"


test("output_schema_explicit_path", test_output_schema_explicit_path)


def test_non_llm_step_keeps_string():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "non-llm.toml",
            """
            [workflow]
            name = "test"

            [steps.map_step]
            type = "map"
            config = { output_schema = "SomeString" }
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert result.steps["map_step"].config["output_schema"] == "SomeString"


test("non_llm_step_keeps_string", test_non_llm_step_keeps_string)


def test_missing_models_keeps_string():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "no-models.toml",
            """
            [workflow]
            name = "test"

            [steps.extract]
            type = "llm"
            config = { output_schema = "MissingModel" }
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert result.steps["extract"].config["output_schema"] == "MissingModel"


test("missing_models_keeps_string", test_missing_models_keeps_string)


# ============================================================================
# Integration Tests
# ============================================================================
print("\nTestIntegration:")


def test_complex_dag():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "complex-dag.toml",
            """
            [workflow]
            name = "complex-dag"
            description = "A workflow with diamond dependencies"

            [steps.source1]
            type = "map"

            [steps.source2]
            type = "map"

            [steps.fetch1]
            type = "fetch"
            depends_on = ["source1"]

            [steps.fetch2]
            type = "fetch"
            depends_on = ["source2"]

            [steps.merge]
            type = "sql"
            depends_on = ["fetch1", "fetch2"]

            [steps.analyze]
            type = "llm"
            depends_on = ["merge"]

            [steps.embed]
            type = "embed"
            depends_on = ["merge"]

            [steps.save]
            type = "write"
            depends_on = ["analyze", "embed"]
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        assert len(result.steps) == 8
        assert set(result.steps["merge"].depends_on) == {"fetch1", "fetch2"}
        assert set(result.steps["save"].depends_on) == {"analyze", "embed"}


test("complex_dag", test_complex_dag)


def test_all_step_types():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toml_path = write_toml(
            Path(tmp_dir) / "all-types.toml",
            """
            [workflow]
            name = "all-types"

            [steps.step_map]
            type = "map"

            [steps.step_fetch]
            type = "fetch"
            depends_on = ["step_map"]

            [steps.step_llm]
            type = "llm"
            depends_on = ["step_fetch"]

            [steps.step_embed]
            type = "embed"
            depends_on = ["step_fetch"]

            [steps.step_sql]
            type = "sql"
            depends_on = ["step_llm", "step_embed"]

            [steps.step_write]
            type = "write"
            depends_on = ["step_sql"]

            [steps.step_agent]
            type = "agent"
            depends_on = ["step_write"]
            """,
        )
        result = parse_workflow(toml_path, validate_tools=False)
        types_used = {step.type for step in result.steps.values()}
        assert types_used == {"map", "fetch", "llm", "embed", "sql", "write", "agent"}


test("all_step_types", test_all_step_types)


# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 60)
print(f"PASSED: {passed}")
print(f"FAILED: {failed}")
print("=" * 60)

if failed > 0:
    sys.exit(1)

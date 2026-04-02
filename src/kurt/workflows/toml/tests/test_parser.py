"""
Tests for TOML workflow parser.
"""

from __future__ import annotations

import sys
from pathlib import Path

# tomllib is Python 3.11+, use tomli backport for 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from textwrap import dedent

import pytest
from pydantic import BaseModel

from kurt.workflows.toml.parser import (
    CircularDependencyError,
    InputDef,
    StepDef,
    UnknownDependsOnError,
    UnknownKeyError,
    UnknownStepTypeError,
    WorkflowDefinition,
    WorkflowMeta,
    WorkflowParseError,
    parse_workflow,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_workflow_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for workflow files."""
    return tmp_path


def write_toml(path: Path, content: str) -> Path:
    """Write TOML content to a file and return the path."""
    path.write_text(dedent(content).strip())
    return path


# ============================================================================
# InputDef Tests
# ============================================================================


class TestInputDef:
    """Tests for InputDef model."""

    def test_minimal_input(self):
        """InputDef with only required fields."""
        input_def = InputDef(type="string")
        assert input_def.type == "string"
        assert input_def.required is False
        assert input_def.default is None

    def test_required_input(self):
        """InputDef with required=True."""
        input_def = InputDef(type="int", required=True)
        assert input_def.required is True

    def test_string_input_with_default(self):
        """InputDef with string default value."""
        input_def = InputDef(type="string", default="hello")
        assert input_def.default == "hello"

    def test_int_input_with_default(self):
        """InputDef with int default value."""
        input_def = InputDef(type="int", default=42)
        assert input_def.default == 42

    def test_float_input_with_default(self):
        """InputDef with float default value."""
        input_def = InputDef(type="float", default=3.14)
        assert input_def.default == 3.14

    def test_float_input_accepts_int_default(self):
        """InputDef with float type accepts int default."""
        input_def = InputDef(type="float", default=10)
        assert input_def.default == 10

    def test_bool_input_with_default(self):
        """InputDef with bool default value."""
        input_def = InputDef(type="bool", default=True)
        assert input_def.default is True

    def test_invalid_default_type_raises(self):
        """InputDef raises if default doesn't match type."""
        with pytest.raises(ValueError, match="does not match type"):
            InputDef(type="int", default="not an int")

    def test_invalid_input_type_raises(self):
        """InputDef raises for invalid type values."""
        with pytest.raises(ValueError):
            InputDef(type="invalid")


# ============================================================================
# StepDef Tests
# ============================================================================


class TestStepDef:
    """Tests for StepDef model."""

    def test_minimal_step(self):
        """StepDef with only required fields."""
        step_def = StepDef(type="map")
        assert step_def.type == "map"
        assert step_def.depends_on == []
        assert step_def.config == {}
        assert step_def.continue_on_error is False

    def test_step_with_dependencies(self):
        """StepDef with depends_on."""
        step_def = StepDef(type="llm", depends_on=["fetch", "map"])
        assert step_def.depends_on == ["fetch", "map"]

    def test_step_with_config(self):
        """StepDef with tool-specific config."""
        config = {"model": "gpt-4", "temperature": 0.7}
        step_def = StepDef(type="llm", config=config)
        assert step_def.config == config

    def test_step_with_continue_on_error(self):
        """StepDef with continue_on_error=True."""
        step_def = StepDef(type="fetch", continue_on_error=True)
        assert step_def.continue_on_error is True


# ============================================================================
# WorkflowMeta Tests
# ============================================================================


class TestWorkflowMeta:
    """Tests for WorkflowMeta model."""

    def test_minimal_meta(self):
        """WorkflowMeta with only name."""
        meta = WorkflowMeta(name="my-workflow")
        assert meta.name == "my-workflow"
        assert meta.description is None

    def test_meta_with_description(self):
        """WorkflowMeta with description."""
        meta = WorkflowMeta(name="test", description="A test workflow")
        assert meta.description == "A test workflow"


# ============================================================================
# WorkflowDefinition Tests
# ============================================================================


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition model."""

    def test_minimal_definition(self):
        """WorkflowDefinition with required fields only."""
        defn = WorkflowDefinition(workflow=WorkflowMeta(name="test"))
        assert defn.workflow.name == "test"
        assert defn.inputs == {}
        assert defn.steps == {}

    def test_full_definition(self):
        """WorkflowDefinition with all fields."""
        defn = WorkflowDefinition(
            workflow=WorkflowMeta(name="full", description="Full test"),
            inputs={"url": InputDef(type="string", required=True)},
            steps={
                "fetch": StepDef(type="fetch", config={"timeout": 30}),
                "process": StepDef(type="llm", depends_on=["fetch"]),
            },
        )
        assert defn.workflow.name == "full"
        assert "url" in defn.inputs
        assert "fetch" in defn.steps
        assert "process" in defn.steps
        assert defn.steps["process"].depends_on == ["fetch"]


# ============================================================================
# parse_workflow Tests - Basic Parsing
# ============================================================================


class TestParseWorkflowBasic:
    """Tests for basic parse_workflow functionality."""

    def test_minimal_workflow(self, tmp_workflow_dir: Path):
        """Parse workflow with only [workflow] section."""
        toml_path = write_toml(
            tmp_workflow_dir / "minimal.toml",
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

    def test_workflow_with_description(self, tmp_workflow_dir: Path):
        """Parse workflow with description."""
        toml_path = write_toml(
            tmp_workflow_dir / "desc.toml",
            """
            [workflow]
            name = "with-desc"
            description = "A workflow with a description"
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        assert result.workflow.description == "A workflow with a description"

    def test_workflow_with_inputs(self, tmp_workflow_dir: Path):
        """Parse workflow with inputs section."""
        toml_path = write_toml(
            tmp_workflow_dir / "inputs.toml",
            """
            [workflow]
            name = "with-inputs"

            [inputs.url]
            type = "string"
            required = true

            [inputs.limit]
            type = "int"
            default = 100

            [inputs.verbose]
            type = "bool"
            default = false
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        assert "url" in result.inputs
        assert result.inputs["url"].type == "string"
        assert result.inputs["url"].required is True

        assert "limit" in result.inputs
        assert result.inputs["limit"].type == "int"
        assert result.inputs["limit"].default == 100

        assert "verbose" in result.inputs
        assert result.inputs["verbose"].type == "bool"
        assert result.inputs["verbose"].default is False

    def test_workflow_with_steps(self, tmp_workflow_dir: Path):
        """Parse workflow with steps section."""
        toml_path = write_toml(
            tmp_workflow_dir / "steps.toml",
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
        assert result.steps["discover"].config == {"url": "https://example.com"}

        assert "fetch" in result.steps
        assert result.steps["fetch"].depends_on == ["discover"]

        assert "extract" in result.steps
        assert result.steps["extract"].type == "llm"
        assert result.steps["extract"].depends_on == ["fetch"]
        assert result.steps["extract"].config == {"model": "gpt-4"}
        assert result.steps["extract"].continue_on_error is True

    def test_full_workflow(self, tmp_workflow_dir: Path):
        """Parse a complete workflow with all sections."""
        toml_path = write_toml(
            tmp_workflow_dir / "full.toml",
            """
            [workflow]
            name = "content-pipeline"
            description = "Fetch and process content from URLs"

            [inputs.source_url]
            type = "string"
            required = true

            [inputs.max_pages]
            type = "int"
            default = 50

            [steps.map]
            type = "map"
            config = { source = "{{source_url}}", depth = 2 }

            [steps.fetch]
            type = "fetch"
            depends_on = ["map"]
            config = { concurrency = 5 }

            [steps.embed]
            type = "embed"
            depends_on = ["fetch"]
            config = { model = "text-embedding-3-small" }

            [steps.save]
            type = "write-db"
            depends_on = ["embed"]
            config = { table = "documents" }
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        # Check workflow metadata
        assert result.workflow.name == "content-pipeline"
        assert "URLs" in result.workflow.description

        # Check inputs
        assert len(result.inputs) == 2
        assert result.inputs["source_url"].required is True
        assert result.inputs["max_pages"].default == 50

        # Check steps
        assert len(result.steps) == 4
        assert result.steps["map"].type == "map"
        assert result.steps["fetch"].depends_on == ["map"]
        assert result.steps["embed"].depends_on == ["fetch"]
        assert result.steps["save"].depends_on == ["embed"]


# ============================================================================
# parse_workflow Tests - Step Type Validation
# ============================================================================


class TestParseWorkflowStepTypes:
    """Tests for step type validation."""

    @pytest.mark.parametrize("step_type", ["map", "fetch", "llm", "embed", "write-db", "sql", "agent"])
    def test_valid_step_types(self, tmp_workflow_dir: Path, step_type: str):
        """All valid step types are accepted."""
        toml_path = write_toml(
            tmp_workflow_dir / f"{step_type}.toml",
            f"""
            [workflow]
            name = "test-{step_type}"

            [steps.test]
            type = "{step_type}"
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)
        assert result.steps["test"].type == step_type

    def test_unknown_step_type_raises(self, tmp_workflow_dir: Path):
        """Unknown step type raises UnknownStepTypeError."""
        toml_path = write_toml(
            tmp_workflow_dir / "unknown.toml",
            """
            [workflow]
            name = "unknown-type"

            [steps.bad]
            type = "nonexistent"
            """,
        )

        with pytest.raises(UnknownStepTypeError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert exc_info.value.step_name == "bad"
        assert exc_info.value.step_type == "nonexistent"
        assert "Step bad has unknown type: nonexistent" in str(exc_info.value)


# ============================================================================
# parse_workflow Tests - Dependency Validation
# ============================================================================


class TestParseWorkflowDependencies:
    """Tests for dependency validation."""

    def test_valid_dependencies(self, tmp_workflow_dir: Path):
        """Valid dependencies are accepted."""
        toml_path = write_toml(
            tmp_workflow_dir / "valid-deps.toml",
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

    def test_unknown_dependency_raises(self, tmp_workflow_dir: Path):
        """Unknown dependency raises UnknownDependsOnError."""
        toml_path = write_toml(
            tmp_workflow_dir / "unknown-dep.toml",
            """
            [workflow]
            name = "unknown-dep"

            [steps.process]
            type = "llm"
            depends_on = ["nonexistent"]
            """,
        )

        with pytest.raises(UnknownDependsOnError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert exc_info.value.step_name == "process"
        assert exc_info.value.dep == "nonexistent"
        assert "Step process depends on unknown step: nonexistent" in str(exc_info.value)

    def test_circular_dependency_self_raises(self, tmp_workflow_dir: Path):
        """Self-referencing step raises CircularDependencyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "self-ref.toml",
            """
            [workflow]
            name = "self-ref"

            [steps.loop]
            type = "llm"
            depends_on = ["loop"]
            """,
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert "loop" in exc_info.value.cycle

    def test_circular_dependency_two_step_raises(self, tmp_workflow_dir: Path):
        """Two-step cycle raises CircularDependencyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "two-cycle.toml",
            """
            [workflow]
            name = "two-cycle"

            [steps.a]
            type = "map"
            depends_on = ["b"]

            [steps.b]
            type = "fetch"
            depends_on = ["a"]
            """,
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        # Cycle should contain both steps
        assert "a" in exc_info.value.cycle
        assert "b" in exc_info.value.cycle

    def test_circular_dependency_three_step_raises(self, tmp_workflow_dir: Path):
        """Three-step cycle raises CircularDependencyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "three-cycle.toml",
            """
            [workflow]
            name = "three-cycle"

            [steps.a]
            type = "map"
            depends_on = ["c"]

            [steps.b]
            type = "fetch"
            depends_on = ["a"]

            [steps.c]
            type = "llm"
            depends_on = ["b"]
            """,
        )

        with pytest.raises(CircularDependencyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        # Cycle should contain all three steps
        assert len(exc_info.value.cycle) >= 3


# ============================================================================
# parse_workflow Tests - Strict Validation (Unknown Keys)
# ============================================================================


class TestParseWorkflowStrictValidation:
    """Tests for strict validation (unknown keys)."""

    def test_unknown_top_level_key_raises(self, tmp_workflow_dir: Path):
        """Unknown top-level key raises UnknownKeyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "unknown-top.toml",
            """
            [workflow]
            name = "test"

            [unknown_section]
            foo = "bar"
            """,
        )

        with pytest.raises(UnknownKeyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert exc_info.value.location == "Workflow file"
        assert exc_info.value.key == "unknown_section"

    def test_unknown_workflow_key_raises(self, tmp_workflow_dir: Path):
        """Unknown key in [workflow] section raises UnknownKeyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "unknown-workflow.toml",
            """
            [workflow]
            name = "test"
            unknown_key = "value"
            """,
        )

        with pytest.raises(UnknownKeyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert exc_info.value.location == "[workflow]"
        assert exc_info.value.key == "unknown_key"

    def test_unknown_input_key_raises(self, tmp_workflow_dir: Path):
        """Unknown key in input definition raises UnknownKeyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "unknown-input.toml",
            """
            [workflow]
            name = "test"

            [inputs.my_input]
            type = "string"
            unknown = "value"
            """,
        )

        with pytest.raises(UnknownKeyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert "inputs.my_input" in exc_info.value.location
        assert exc_info.value.key == "unknown"

    def test_unknown_step_key_raises(self, tmp_workflow_dir: Path):
        """Unknown key in step definition raises UnknownKeyError."""
        toml_path = write_toml(
            tmp_workflow_dir / "unknown-step.toml",
            """
            [workflow]
            name = "test"

            [steps.my_step]
            type = "map"
            unknown_option = true
            """,
        )

        with pytest.raises(UnknownKeyError) as exc_info:
            parse_workflow(toml_path, validate_tools=False)

        assert "steps.my_step" in exc_info.value.location
        assert exc_info.value.key == "unknown_option"


# ============================================================================
# parse_workflow Tests - Error Cases
# ============================================================================


class TestParseWorkflowErrors:
    """Tests for error handling in parse_workflow."""

    def test_missing_workflow_section_raises(self, tmp_workflow_dir: Path):
        """Missing [workflow] section raises WorkflowParseError."""
        toml_path = write_toml(
            tmp_workflow_dir / "no-workflow.toml",
            """
            [steps.test]
            type = "map"
            """,
        )

        with pytest.raises(WorkflowParseError, match="Missing required"):
            parse_workflow(toml_path, validate_tools=False)

    def test_missing_step_type_raises(self, tmp_workflow_dir: Path):
        """Step without type raises WorkflowParseError."""
        toml_path = write_toml(
            tmp_workflow_dir / "no-type.toml",
            """
            [workflow]
            name = "test"

            [steps.my_step]
            config = { foo = "bar" }
            """,
        )

        with pytest.raises(WorkflowParseError, match="missing required 'type'"):
            parse_workflow(toml_path, validate_tools=False)

    def test_nonexistent_file_raises(self, tmp_workflow_dir: Path):
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_workflow(tmp_workflow_dir / "nonexistent.toml", validate_tools=False)

    def test_invalid_toml_raises(self, tmp_workflow_dir: Path):
        """Malformed TOML raises TOMLDecodeError."""
        toml_path = tmp_workflow_dir / "invalid.toml"
        toml_path.write_text("this is not valid [toml")

        with pytest.raises(tomllib.TOMLDecodeError):
            parse_workflow(toml_path, validate_tools=False)

    def test_input_not_table_raises(self, tmp_workflow_dir: Path):
        """Input that's not a table raises WorkflowParseError."""
        toml_path = write_toml(
            tmp_workflow_dir / "input-not-table.toml",
            """
            [workflow]
            name = "test"

            [inputs]
            my_input = "not a table"
            """,
        )

        with pytest.raises(WorkflowParseError, match="must be a table"):
            parse_workflow(toml_path, validate_tools=False)

    def test_step_not_table_raises(self, tmp_workflow_dir: Path):
        """Step that's not a table raises WorkflowParseError."""
        toml_path = write_toml(
            tmp_workflow_dir / "step-not-table.toml",
            """
            [workflow]
            name = "test"

            [steps]
            my_step = "not a table"
            """,
        )

        with pytest.raises(WorkflowParseError, match="must be a table"):
            parse_workflow(toml_path, validate_tools=False)


# ============================================================================
# parse_workflow Tests - Output Schema Resolution
# ============================================================================


class TestParseWorkflowOutputSchema:
    """Tests for output_schema resolution in llm steps."""

    def test_output_schema_resolved_from_models_py(self, tmp_workflow_dir: Path):
        """output_schema string reference is resolved from models.py."""
        # Create models.py with a Pydantic model
        models_path = tmp_workflow_dir / "models.py"
        models_path.write_text(
            dedent(
                """
                from pydantic import BaseModel

                class ExtractedEntity(BaseModel):
                    name: str
                    entity_type: str
                """
            ).strip()
        )

        toml_path = write_toml(
            tmp_workflow_dir / "with-schema.toml",
            """
            [workflow]
            name = "test-schema"

            [steps.extract]
            type = "llm"
            config = { output_schema = "ExtractedEntity" }
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        # Schema should be resolved to the actual class
        schema = result.steps["extract"].config["output_schema"]
        assert isinstance(schema, type)
        assert issubclass(schema, BaseModel)
        assert schema.__name__ == "ExtractedEntity"

    def test_output_schema_kept_as_string_if_no_models(self, tmp_workflow_dir: Path):
        """output_schema kept as string if models.py doesn't exist."""
        toml_path = write_toml(
            tmp_workflow_dir / "no-models.toml",
            """
            [workflow]
            name = "test"

            [steps.extract]
            type = "llm"
            config = { output_schema = "MissingModel" }
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        # Schema should remain as string
        schema = result.steps["extract"].config["output_schema"]
        assert schema == "MissingModel"

    def test_output_schema_explicit_models_path(self, tmp_workflow_dir: Path):
        """output_schema resolution with explicit models_path."""
        # Create models.py in a subdirectory
        models_dir = tmp_workflow_dir / "custom"
        models_dir.mkdir()
        models_path = models_dir / "my_models.py"
        models_path.write_text(
            dedent(
                """
                from pydantic import BaseModel

                class CustomModel(BaseModel):
                    value: str
                """
            ).strip()
        )

        toml_path = write_toml(
            tmp_workflow_dir / "custom-models.toml",
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

    def test_non_llm_step_ignores_output_schema(self, tmp_workflow_dir: Path):
        """Non-llm steps don't attempt to resolve output_schema."""
        toml_path = write_toml(
            tmp_workflow_dir / "non-llm.toml",
            """
            [workflow]
            name = "test"

            [steps.map]
            type = "map"
            config = { output_schema = "SomeString" }
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        # Should remain as string (not attempted to resolve)
        assert result.steps["map"].config["output_schema"] == "SomeString"


# ============================================================================
# Integration Tests
# ============================================================================


class TestParseWorkflowIntegration:
    """Integration tests for parse_workflow."""

    def test_complex_dag(self, tmp_workflow_dir: Path):
        """Parse workflow with complex DAG structure."""
        toml_path = write_toml(
            tmp_workflow_dir / "complex-dag.toml",
            """
            [workflow]
            name = "complex-dag"
            description = "A workflow with diamond dependencies"

            [steps.source1]
            type = "map"
            config = { url = "https://site1.com" }

            [steps.source2]
            type = "map"
            config = { url = "https://site2.com" }

            [steps.fetch1]
            type = "fetch"
            depends_on = ["source1"]

            [steps.fetch2]
            type = "fetch"
            depends_on = ["source2"]

            [steps.merge]
            type = "sql"
            depends_on = ["fetch1", "fetch2"]
            config = { query = "SELECT * FROM results" }

            [steps.analyze]
            type = "llm"
            depends_on = ["merge"]
            config = { model = "gpt-4" }

            [steps.embed]
            type = "embed"
            depends_on = ["merge"]

            [steps.save]
            type = "write-db"
            depends_on = ["analyze", "embed"]
            config = { table = "output" }
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        # Verify structure
        assert len(result.steps) == 8

        # Verify fan-out
        assert result.steps["fetch1"].depends_on == ["source1"]
        assert result.steps["fetch2"].depends_on == ["source2"]

        # Verify fan-in
        assert set(result.steps["merge"].depends_on) == {"fetch1", "fetch2"}
        assert set(result.steps["save"].depends_on) == {"analyze", "embed"}

    def test_all_step_types_in_one_workflow(self, tmp_workflow_dir: Path):
        """Parse workflow using all seven step types."""
        toml_path = write_toml(
            tmp_workflow_dir / "all-types.toml",
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
            type = "write-db"
            depends_on = ["step_sql"]

            [steps.step_agent]
            type = "agent"
            depends_on = ["step_write"]
            """,
        )

        result = parse_workflow(toml_path, validate_tools=False)

        types_used = {step.type for step in result.steps.values()}
        assert types_used == {"map", "fetch", "llm", "embed", "sql", "write-db", "agent"}

"""
Tests for the fixture loading module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kurt.engine.fixtures import (
    FixtureLoadError,
    FixtureNotFoundError,
    FixtureSet,
    StepFixture,
    analyze_fixture_coverage,
    discover_fixture_steps,
    load_fixture,
    load_fixtures,
    load_jsonl,
)

# ============================================================================
# Test Fixtures (pytest fixtures for creating test data)
# ============================================================================


@pytest.fixture
def temp_fixtures_dir(tmp_path: Path) -> Path:
    """Create a temporary fixtures directory."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    return fixtures_dir


@pytest.fixture
def sample_fixture_files(temp_fixtures_dir: Path) -> Path:
    """Create sample fixture files in the temp directory."""
    # discover.output.jsonl
    discover_file = temp_fixtures_dir / "discover.output.jsonl"
    discover_file.write_text(
        '{"url": "https://example.com/page1", "title": "Page 1"}\n'
        '{"url": "https://example.com/page2", "title": "Page 2"}\n'
        '{"url": "https://example.com/page3", "title": "Page 3"}\n'
    )

    # fetch.output.jsonl
    fetch_file = temp_fixtures_dir / "fetch.output.jsonl"
    fetch_file.write_text(
        '{"url": "https://example.com/page1", "content": "Content 1"}\n'
        '{"url": "https://example.com/page2", "content": "Content 2"}\n'
    )

    # process.jsonl (without .output suffix)
    process_file = temp_fixtures_dir / "process.jsonl"
    process_file.write_text(
        '{"id": 1, "processed": true}\n'
    )

    return temp_fixtures_dir


# ============================================================================
# load_jsonl Tests
# ============================================================================


class TestLoadJsonl:
    """Tests for load_jsonl function."""

    def test_load_valid_jsonl(self, temp_fixtures_dir: Path):
        """Load a valid JSONL file."""
        file_path = temp_fixtures_dir / "test.jsonl"
        file_path.write_text(
            '{"name": "Alice", "age": 30}\n'
            '{"name": "Bob", "age": 25}\n'
        )

        records = load_jsonl(file_path)

        assert len(records) == 2
        assert records[0] == {"name": "Alice", "age": 30}
        assert records[1] == {"name": "Bob", "age": 25}

    def test_skip_empty_lines(self, temp_fixtures_dir: Path):
        """Empty lines are skipped."""
        file_path = temp_fixtures_dir / "test.jsonl"
        file_path.write_text(
            '{"a": 1}\n'
            '\n'
            '{"b": 2}\n'
            '   \n'
            '{"c": 3}\n'
        )

        records = load_jsonl(file_path)

        assert len(records) == 3
        assert records == [{"a": 1}, {"b": 2}, {"c": 3}]

    def test_skip_comments(self, temp_fixtures_dir: Path):
        """Lines starting with # are treated as comments."""
        file_path = temp_fixtures_dir / "test.jsonl"
        file_path.write_text(
            '# This is a comment\n'
            '{"data": 1}\n'
            '# Another comment\n'
            '{"data": 2}\n'
        )

        records = load_jsonl(file_path)

        assert len(records) == 2

    def test_file_not_found(self, temp_fixtures_dir: Path):
        """Non-existent file raises FixtureLoadError."""
        with pytest.raises(FixtureLoadError) as exc_info:
            load_jsonl(temp_fixtures_dir / "nonexistent.jsonl")

        assert "File not found" in str(exc_info.value)

    def test_invalid_json(self, temp_fixtures_dir: Path):
        """Invalid JSON raises FixtureLoadError."""
        file_path = temp_fixtures_dir / "test.jsonl"
        file_path.write_text(
            '{"valid": true}\n'
            'not valid json\n'
        )

        with pytest.raises(FixtureLoadError) as exc_info:
            load_jsonl(file_path)

        assert "Line 2" in str(exc_info.value)
        assert "Invalid JSON" in str(exc_info.value)

    def test_non_object_raises_error(self, temp_fixtures_dir: Path):
        """Non-object JSON values raise FixtureLoadError."""
        file_path = temp_fixtures_dir / "test.jsonl"
        file_path.write_text(
            '{"valid": true}\n'
            '[1, 2, 3]\n'  # Array, not object
        )

        with pytest.raises(FixtureLoadError) as exc_info:
            load_jsonl(file_path)

        assert "Line 2" in str(exc_info.value)
        assert "Expected object" in str(exc_info.value)


# ============================================================================
# load_fixture Tests
# ============================================================================


class TestLoadFixture:
    """Tests for load_fixture function."""

    def test_load_with_output_suffix(self, sample_fixture_files: Path):
        """Load fixture with .output.jsonl suffix."""
        fixture = load_fixture("discover", sample_fixture_files)

        assert fixture.step_name == "discover"
        assert len(fixture.output_data) == 3
        assert fixture.source_path == sample_fixture_files / "discover.output.jsonl"

    def test_load_without_output_suffix(self, sample_fixture_files: Path):
        """Load fixture without .output suffix."""
        fixture = load_fixture("process", sample_fixture_files)

        assert fixture.step_name == "process"
        assert len(fixture.output_data) == 1
        assert fixture.source_path == sample_fixture_files / "process.jsonl"

    def test_fixture_not_found(self, sample_fixture_files: Path):
        """Missing fixture raises FixtureNotFoundError."""
        with pytest.raises(FixtureNotFoundError) as exc_info:
            load_fixture("nonexistent", sample_fixture_files)

        assert exc_info.value.step_name == "nonexistent"
        assert len(exc_info.value.search_paths) > 0

    def test_prefer_output_suffix(self, temp_fixtures_dir: Path):
        """Prefer .output.jsonl over .jsonl when both exist."""
        # Create both files
        (temp_fixtures_dir / "step.output.jsonl").write_text('{"from": "output"}\n')
        (temp_fixtures_dir / "step.jsonl").write_text('{"from": "plain"}\n')

        fixture = load_fixture("step", temp_fixtures_dir)

        assert fixture.output_data[0]["from"] == "output"


# ============================================================================
# load_fixtures Tests
# ============================================================================


class TestLoadFixtures:
    """Tests for load_fixtures function."""

    def test_load_all_fixtures(self, sample_fixture_files: Path):
        """Load all fixtures from directory."""
        fixture_set = load_fixtures(sample_fixture_files)

        assert len(fixture_set.fixtures) == 3
        assert "discover" in fixture_set.fixtures
        assert "fetch" in fixture_set.fixtures
        assert "process" in fixture_set.fixtures

    def test_load_specific_steps(self, sample_fixture_files: Path):
        """Load fixtures for specific steps only."""
        fixture_set = load_fixtures(
            sample_fixture_files,
            step_names=["discover", "fetch"],
        )

        assert len(fixture_set.fixtures) == 2
        assert "discover" in fixture_set.fixtures
        assert "fetch" in fixture_set.fixtures
        assert "process" not in fixture_set.fixtures

    def test_missing_fixture_non_strict(self, sample_fixture_files: Path):
        """Non-strict mode skips missing fixtures."""
        fixture_set = load_fixtures(
            sample_fixture_files,
            step_names=["discover", "nonexistent"],
            strict=False,
        )

        assert len(fixture_set.fixtures) == 1
        assert "discover" in fixture_set.fixtures

    def test_missing_fixture_strict(self, sample_fixture_files: Path):
        """Strict mode raises error for missing fixtures."""
        with pytest.raises(FixtureNotFoundError):
            load_fixtures(
                sample_fixture_files,
                step_names=["discover", "nonexistent"],
                strict=True,
            )

    def test_nonexistent_directory_non_strict(self, tmp_path: Path):
        """Non-strict mode returns empty set for missing directory."""
        fixture_set = load_fixtures(
            tmp_path / "nonexistent",
            strict=False,
        )

        assert len(fixture_set.fixtures) == 0

    def test_nonexistent_directory_strict(self, tmp_path: Path):
        """Strict mode raises error for missing directory."""
        with pytest.raises(FileNotFoundError):
            load_fixtures(
                tmp_path / "nonexistent",
                strict=True,
            )


# ============================================================================
# FixtureSet Tests
# ============================================================================


class TestFixtureSet:
    """Tests for FixtureSet class."""

    def test_has_fixture(self):
        """has_fixture returns True when fixture exists."""
        fixture_set = FixtureSet(
            fixtures={
                "step1": StepFixture("step1", [{"a": 1}], Path("step1.jsonl")),
            }
        )

        assert fixture_set.has_fixture("step1") is True
        assert fixture_set.has_fixture("step2") is False

    def test_get_fixture(self):
        """get_fixture returns fixture or None."""
        fixture = StepFixture("step1", [{"a": 1}], Path("step1.jsonl"))
        fixture_set = FixtureSet(fixtures={"step1": fixture})

        assert fixture_set.get_fixture("step1") is fixture
        assert fixture_set.get_fixture("step2") is None

    def test_get_output_data(self):
        """get_output_data returns data or empty list."""
        fixture_set = FixtureSet(
            fixtures={
                "step1": StepFixture("step1", [{"a": 1}, {"b": 2}], Path("step1.jsonl")),
            }
        )

        assert fixture_set.get_output_data("step1") == [{"a": 1}, {"b": 2}]
        assert fixture_set.get_output_data("step2") == []

    def test_step_names(self):
        """step_names returns list of fixture step names."""
        fixture_set = FixtureSet(
            fixtures={
                "step1": StepFixture("step1", [], Path("step1.jsonl")),
                "step2": StepFixture("step2", [], Path("step2.jsonl")),
            }
        )

        assert set(fixture_set.step_names) == {"step1", "step2"}


# ============================================================================
# discover_fixture_steps Tests
# ============================================================================


class TestDiscoverFixtureSteps:
    """Tests for discover_fixture_steps function."""

    def test_discover_all_patterns(self, temp_fixtures_dir: Path):
        """Discover fixtures with various naming patterns."""
        (temp_fixtures_dir / "step_a.output.jsonl").write_text("{}\n")
        (temp_fixtures_dir / "step_b.output.json").write_text("{}\n")
        (temp_fixtures_dir / "step_c.jsonl").write_text("{}\n")
        (temp_fixtures_dir / "step_d.json").write_text("{}\n")

        steps = discover_fixture_steps(temp_fixtures_dir)

        assert set(steps) == {"step_a", "step_b", "step_c", "step_d"}

    def test_skip_non_fixture_files(self, temp_fixtures_dir: Path):
        """Non-fixture files are ignored."""
        (temp_fixtures_dir / "step.output.jsonl").write_text("{}\n")
        (temp_fixtures_dir / "README.md").write_text("Docs\n")
        (temp_fixtures_dir / "config.yaml").write_text("key: value\n")

        steps = discover_fixture_steps(temp_fixtures_dir)

        assert steps == ["step"]

    def test_empty_directory(self, temp_fixtures_dir: Path):
        """Empty directory returns empty list."""
        steps = discover_fixture_steps(temp_fixtures_dir)

        assert steps == []


# ============================================================================
# analyze_fixture_coverage Tests
# ============================================================================


class TestAnalyzeFixtureCoverage:
    """Tests for analyze_fixture_coverage function."""

    def test_full_coverage(self):
        """All steps have fixtures."""
        fixture_set = FixtureSet(
            fixtures={
                "step1": StepFixture("step1", [{"a": 1}], Path("step1.jsonl")),
                "step2": StepFixture("step2", [{"b": 2}], Path("step2.jsonl")),
            }
        )

        report = analyze_fixture_coverage(["step1", "step2"], fixture_set)

        assert report.steps_with_fixtures == ["step1", "step2"]
        assert report.steps_without_fixtures == []
        assert len(report.fixture_paths) == 2

    def test_partial_coverage(self):
        """Some steps have fixtures."""
        fixture_set = FixtureSet(
            fixtures={
                "step1": StepFixture("step1", [{"a": 1}], Path("step1.jsonl")),
            }
        )

        report = analyze_fixture_coverage(["step1", "step2", "step3"], fixture_set)

        assert report.steps_with_fixtures == ["step1"]
        assert report.steps_without_fixtures == ["step2", "step3"]

    def test_no_coverage(self):
        """No steps have fixtures."""
        fixture_set = FixtureSet()

        report = analyze_fixture_coverage(["step1", "step2"], fixture_set)

        assert report.steps_with_fixtures == []
        assert report.steps_without_fixtures == ["step1", "step2"]

    def test_to_dict(self):
        """FixtureReport converts to dict correctly."""
        fixture_set = FixtureSet(
            fixtures={
                "step1": StepFixture("step1", [], Path("/path/step1.jsonl")),
            }
        )

        report = analyze_fixture_coverage(["step1", "step2"], fixture_set)
        d = report.to_dict()

        assert d["steps_with_fixtures"] == ["step1"]
        assert d["steps_without_fixtures"] == ["step2"]
        assert d["coverage"] == 0.5
        assert "/path/step1.jsonl" in d["fixture_paths"]["step1"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestFixtureIntegration:
    """Integration tests for fixture loading workflow."""

    def test_full_workflow(self, sample_fixture_files: Path):
        """Complete fixture loading workflow."""
        # 1. Discover available fixtures
        discovered = discover_fixture_steps(sample_fixture_files)
        assert len(discovered) == 3

        # 2. Define workflow steps
        workflow_steps = ["discover", "fetch", "transform", "write"]

        # 3. Load fixtures for workflow
        fixture_set = load_fixtures(
            sample_fixture_files,
            step_names=workflow_steps,
            strict=False,
        )

        # 4. Analyze coverage
        report = analyze_fixture_coverage(workflow_steps, fixture_set)

        # 5. Verify results
        assert len(report.steps_with_fixtures) == 2  # discover, fetch
        assert len(report.steps_without_fixtures) == 2  # transform, write

        # 6. Access fixture data
        discover_data = fixture_set.get_output_data("discover")
        assert len(discover_data) == 3

        fetch_data = fixture_set.get_output_data("fetch")
        assert len(fetch_data) == 2

        # 7. Missing fixture returns empty
        transform_data = fixture_set.get_output_data("transform")
        assert transform_data == []

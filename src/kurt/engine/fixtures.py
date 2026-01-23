"""
Fixture loading for workflow testing.

Loads fixture files matching step names to skip actual tool execution
and use pre-recorded output data instead.

Fixture Format:
    fixtures/
        discover.output.jsonl   # Output for 'discover' step
        fetch.output.jsonl      # Output for 'fetch' step
        ...

Each .jsonl file contains one JSON object per line representing
the output records for that step.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FixtureLoadError(Exception):
    """Raised when a fixture file cannot be loaded."""

    def __init__(self, step_name: str, path: Path, reason: str):
        self.step_name = step_name
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load fixture for step '{step_name}' from {path}: {reason}")


class FixtureNotFoundError(Exception):
    """Raised when a required fixture is not found."""

    def __init__(self, step_name: str, search_paths: list[Path]):
        self.step_name = step_name
        self.search_paths = search_paths
        paths_str = ", ".join(str(p) for p in search_paths)
        super().__init__(f"No fixture found for step '{step_name}'. Searched: {paths_str}")


@dataclass
class StepFixture:
    """
    Fixture data for a single step.

    Attributes:
        step_name: Name of the step this fixture is for
        output_data: List of output records (loaded from JSONL)
        source_path: Path to the fixture file
        metadata: Optional metadata from fixture (e.g., timing info)
    """

    step_name: str
    output_data: list[dict[str, Any]]
    source_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FixtureSet:
    """
    Collection of fixtures for a workflow test.

    Attributes:
        fixtures: Mapping of step names to StepFixture objects
        base_path: Base directory where fixtures were loaded from
    """

    fixtures: dict[str, StepFixture] = field(default_factory=dict)
    base_path: Path | None = None

    def has_fixture(self, step_name: str) -> bool:
        """Check if a fixture exists for a step."""
        return step_name in self.fixtures

    def get_fixture(self, step_name: str) -> StepFixture | None:
        """Get fixture for a step, or None if not found."""
        return self.fixtures.get(step_name)

    def get_output_data(self, step_name: str) -> list[dict[str, Any]]:
        """Get output data for a step, or empty list if no fixture."""
        fixture = self.fixtures.get(step_name)
        return fixture.output_data if fixture else []

    @property
    def step_names(self) -> list[str]:
        """List of step names that have fixtures."""
        return list(self.fixtures.keys())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """
    Load records from a JSONL file.

    Args:
        path: Path to the JSONL file

    Returns:
        List of parsed JSON objects

    Raises:
        FixtureLoadError: If file cannot be read or parsed
    """
    records: list[dict[str, Any]] = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Skip empty lines and comments

                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        raise FixtureLoadError(
                            step_name="",
                            path=path,
                            reason=f"Line {line_num}: Expected object, got {type(obj).__name__}",
                        )
                    records.append(obj)
                except json.JSONDecodeError as e:
                    raise FixtureLoadError(
                        step_name="",
                        path=path,
                        reason=f"Line {line_num}: Invalid JSON: {e}",
                    )

    except FileNotFoundError:
        raise FixtureLoadError(step_name="", path=path, reason="File not found")
    except PermissionError:
        raise FixtureLoadError(step_name="", path=path, reason="Permission denied")
    except OSError as e:
        raise FixtureLoadError(step_name="", path=path, reason=str(e))

    return records


def load_fixture(
    step_name: str,
    fixtures_dir: Path,
    *,
    extensions: tuple[str, ...] = (".jsonl", ".json"),
) -> StepFixture:
    """
    Load a fixture for a specific step.

    Searches for files matching:
    - {step_name}.output.jsonl
    - {step_name}.output.json
    - {step_name}.jsonl
    - {step_name}.json

    Args:
        step_name: Name of the step
        fixtures_dir: Directory containing fixture files
        extensions: File extensions to try

    Returns:
        StepFixture with loaded output data

    Raises:
        FixtureNotFoundError: If no fixture file is found
        FixtureLoadError: If fixture file cannot be loaded
    """
    search_paths: list[Path] = []

    # Try with .output suffix first
    for ext in extensions:
        path = fixtures_dir / f"{step_name}.output{ext}"
        search_paths.append(path)
        if path.exists():
            records = load_jsonl(path)
            return StepFixture(
                step_name=step_name,
                output_data=records,
                source_path=path,
            )

    # Try without .output suffix
    for ext in extensions:
        path = fixtures_dir / f"{step_name}{ext}"
        search_paths.append(path)
        if path.exists():
            records = load_jsonl(path)
            return StepFixture(
                step_name=step_name,
                output_data=records,
                source_path=path,
            )

    raise FixtureNotFoundError(step_name, search_paths)


def load_fixtures(
    fixtures_dir: str | Path,
    step_names: list[str] | None = None,
    *,
    strict: bool = False,
) -> FixtureSet:
    """
    Load fixtures from a directory.

    Args:
        fixtures_dir: Path to directory containing fixture files
        step_names: Optional list of step names to load. If None, loads all
                   fixtures found in the directory.
        strict: If True, raise error when a step has no fixture.
               If False, steps without fixtures are skipped.

    Returns:
        FixtureSet with loaded fixtures

    Raises:
        FixtureNotFoundError: If strict=True and a step has no fixture
        FixtureLoadError: If a fixture file cannot be loaded
    """
    fixtures_dir = Path(fixtures_dir)

    if not fixtures_dir.exists():
        if strict:
            raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")
        return FixtureSet(base_path=fixtures_dir)

    if not fixtures_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {fixtures_dir}")

    fixture_set = FixtureSet(base_path=fixtures_dir)

    # If no step names provided, discover from directory
    if step_names is None:
        step_names = discover_fixture_steps(fixtures_dir)

    for step_name in step_names:
        try:
            fixture = load_fixture(step_name, fixtures_dir)
            fixture_set.fixtures[step_name] = fixture
            logger.debug("Loaded fixture for step '%s' from %s", step_name, fixture.source_path)
        except FixtureNotFoundError:
            if strict:
                raise
            logger.debug("No fixture found for step '%s'", step_name)
        except FixtureLoadError:
            # Always re-raise load errors (file exists but is invalid)
            raise

    return fixture_set


def discover_fixture_steps(fixtures_dir: Path) -> list[str]:
    """
    Discover step names from fixture files in a directory.

    Looks for files matching:
    - {step_name}.output.jsonl
    - {step_name}.output.json
    - {step_name}.jsonl
    - {step_name}.json

    Args:
        fixtures_dir: Directory to scan

    Returns:
        List of discovered step names
    """
    step_names: set[str] = set()

    for path in fixtures_dir.iterdir():
        if not path.is_file():
            continue

        name = path.name

        # Handle .output.jsonl and .output.json
        if name.endswith(".output.jsonl"):
            step_name = name[:-13]  # Remove ".output.jsonl"
            step_names.add(step_name)
        elif name.endswith(".output.json"):
            step_name = name[:-12]  # Remove ".output.json"
            step_names.add(step_name)
        elif name.endswith(".jsonl"):
            step_name = name[:-6]  # Remove ".jsonl"
            step_names.add(step_name)
        elif name.endswith(".json"):
            step_name = name[:-5]  # Remove ".json"
            step_names.add(step_name)

    return sorted(step_names)


@dataclass
class FixtureReport:
    """
    Report of fixture usage for a workflow test.

    Attributes:
        steps_with_fixtures: Steps that used fixture data
        steps_without_fixtures: Steps that would execute (no fixture)
        fixture_paths: Mapping of step names to fixture file paths
    """

    steps_with_fixtures: list[str] = field(default_factory=list)
    steps_without_fixtures: list[str] = field(default_factory=list)
    fixture_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "steps_with_fixtures": self.steps_with_fixtures,
            "steps_without_fixtures": self.steps_without_fixtures,
            "fixture_paths": {k: str(v) for k, v in self.fixture_paths.items()},
            "coverage": (
                len(self.steps_with_fixtures)
                / max(1, len(self.steps_with_fixtures) + len(self.steps_without_fixtures))
            ),
        }


def analyze_fixture_coverage(
    step_names: list[str],
    fixture_set: FixtureSet,
) -> FixtureReport:
    """
    Analyze which steps have fixtures and which don't.

    Args:
        step_names: All step names in the workflow
        fixture_set: Loaded fixtures

    Returns:
        FixtureReport with coverage information
    """
    report = FixtureReport()

    for step_name in step_names:
        fixture = fixture_set.get_fixture(step_name)
        if fixture:
            report.steps_with_fixtures.append(step_name)
            report.fixture_paths[step_name] = fixture.source_path
        else:
            report.steps_without_fixtures.append(step_name)

    return report

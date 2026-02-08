"""
Database assertion helpers for E2E tests.

These helpers verify database state after command execution,
ensuring that CLI commands actually modify the database correctly.

Usage:
    def test_map_creates_documents(cli_runner, tmp_project):
        result = invoke_cli(cli_runner, map_cmd, ["https://example.com"])
        assert_cli_success(result)

        # Verify database state
        with managed_session() as session:
            assert_map_document_exists(session, "https://example.com/page1")
            assert_row_count(session, MapDocument, 5)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from sqlmodel import Session, select

if TYPE_CHECKING:
    from sqlmodel import SQLModel

    from kurt.observability.models import WorkflowRun
    from kurt.tools.fetch.models import FetchDocument
    from kurt.tools.map.models import MapDocument

T = TypeVar("T", bound="SQLModel")


# =============================================================================
# Map Document Assertions
# =============================================================================


def assert_map_document_exists(
    session: Session,
    url: str,
    *,
    status: str | None = None,
    discovery_method: str | None = None,
) -> "MapDocument":
    """
    Assert that a MapDocument exists with the given URL.

    Args:
        session: Database session
        url: Source URL to check
        status: Optional status to verify
        discovery_method: Optional discovery method to verify

    Returns:
        The MapDocument if found

    Raises:
        AssertionError: If document not found or doesn't match criteria
    """
    from kurt.tools.map.models import MapDocument

    doc = session.exec(select(MapDocument).where(MapDocument.source_url == url)).first()

    if doc is None:
        raise AssertionError(f"MapDocument with URL '{url}' not found in database")

    if status is not None and doc.status.value != status:
        raise AssertionError(
            f"MapDocument status mismatch: expected '{status}', got '{doc.status.value}'"
        )

    if discovery_method is not None and doc.discovery_method != discovery_method:
        raise AssertionError(
            f"MapDocument discovery_method mismatch: expected '{discovery_method}', "
            f"got '{doc.discovery_method}'"
        )

    return doc


def assert_map_document_not_exists(session: Session, url: str) -> None:
    """
    Assert that no MapDocument exists with the given URL.

    Args:
        session: Database session
        url: Source URL to check

    Raises:
        AssertionError: If document exists
    """
    from kurt.tools.map.models import MapDocument

    doc = session.exec(select(MapDocument).where(MapDocument.source_url == url)).first()

    if doc is not None:
        raise AssertionError(f"MapDocument with URL '{url}' unexpectedly exists in database")


def assert_map_document_count(
    session: Session,
    expected: int,
    *,
    status: str | None = None,
    discovery_method: str | None = None,
) -> None:
    """
    Assert the count of MapDocuments matches expected.

    Args:
        session: Database session
        expected: Expected count
        status: Optional status to filter by
        discovery_method: Optional discovery method to filter by

    Raises:
        AssertionError: If count doesn't match
    """
    from kurt.tools.map.models import MapDocument, MapStatus

    query = select(MapDocument)

    if status is not None:
        status_enum = MapStatus(status) if isinstance(status, str) else status
        query = query.where(MapDocument.status == status_enum)

    if discovery_method is not None:
        query = query.where(MapDocument.discovery_method == discovery_method)

    docs = session.exec(query).all()
    actual = len(docs)

    if actual != expected:
        raise AssertionError(f"MapDocument count mismatch: expected {expected}, got {actual}")


# =============================================================================
# Fetch Document Assertions
# =============================================================================


def assert_fetch_document_exists(
    session: Session,
    doc_id: str,
    *,
    status: str | None = None,
    engine: str | None = None,
) -> "FetchDocument":
    """
    Assert that a FetchDocument exists with the given document ID.

    Args:
        session: Database session
        doc_id: Document ID to check
        status: Optional status to verify
        engine: Optional fetch engine to verify

    Returns:
        The FetchDocument if found

    Raises:
        AssertionError: If document not found or doesn't match criteria
    """
    from kurt.tools.fetch.models import FetchDocument

    doc = session.exec(select(FetchDocument).where(FetchDocument.document_id == doc_id)).first()

    if doc is None:
        raise AssertionError(f"FetchDocument with ID '{doc_id}' not found in database")

    if status is not None and doc.status.value != status:
        raise AssertionError(
            f"FetchDocument status mismatch: expected '{status}', got '{doc.status.value}'"
        )

    if engine is not None and doc.fetch_engine != engine:
        raise AssertionError(
            f"FetchDocument engine mismatch: expected '{engine}', got '{doc.fetch_engine}'"
        )

    return doc


def assert_fetch_document_not_exists(session: Session, doc_id: str) -> None:
    """
    Assert that no FetchDocument exists with the given document ID.

    Args:
        session: Database session
        doc_id: Document ID to check

    Raises:
        AssertionError: If document exists
    """
    from kurt.tools.fetch.models import FetchDocument

    doc = session.exec(select(FetchDocument).where(FetchDocument.document_id == doc_id)).first()

    if doc is not None:
        raise AssertionError(f"FetchDocument with ID '{doc_id}' unexpectedly exists in database")


def assert_fetch_document_count(
    session: Session,
    expected: int,
    *,
    status: str | None = None,
    engine: str | None = None,
) -> None:
    """
    Assert the count of FetchDocuments matches expected.

    Args:
        session: Database session
        expected: Expected count
        status: Optional status to filter by
        engine: Optional engine to filter by

    Raises:
        AssertionError: If count doesn't match
    """
    from kurt.tools.fetch.models import FetchDocument, FetchStatus

    query = select(FetchDocument)

    if status is not None:
        status_enum = FetchStatus(status) if isinstance(status, str) else status
        query = query.where(FetchDocument.status == status_enum)

    if engine is not None:
        query = query.where(FetchDocument.fetch_engine == engine)

    docs = session.exec(query).all()
    actual = len(docs)

    if actual != expected:
        raise AssertionError(f"FetchDocument count mismatch: expected {expected}, got {actual}")


def assert_fetch_has_content(session: Session, doc_id: str, min_length: int = 1) -> None:
    """
    Assert that a FetchDocument has content of at least the specified length.

    Args:
        session: Database session
        doc_id: Document ID to check
        min_length: Minimum content length

    Raises:
        AssertionError: If document not found or content too short
    """
    from kurt.tools.fetch.models import FetchDocument

    doc = session.exec(select(FetchDocument).where(FetchDocument.document_id == doc_id)).first()

    if doc is None:
        raise AssertionError(f"FetchDocument with ID '{doc_id}' not found")

    if doc.content_length is None or doc.content_length < min_length:
        raise AssertionError(
            f"FetchDocument content length mismatch: expected >= {min_length}, "
            f"got {doc.content_length}"
        )


# =============================================================================
# Workflow Run Assertions
# =============================================================================


def assert_workflow_run_exists(
    session: Session,
    run_id: str,
    *,
    status: str | None = None,
    workflow_name: str | None = None,
) -> "WorkflowRun":
    """
    Assert that a workflow run exists with the given ID.

    Args:
        session: Database session
        run_id: Workflow run ID
        status: Optional status to verify
        workflow_name: Optional workflow name to verify

    Returns:
        The WorkflowRun if found

    Raises:
        AssertionError: If run not found or doesn't match criteria
    """
    from kurt.observability.models import WorkflowRun

    run = session.exec(select(WorkflowRun).where(WorkflowRun.id == run_id)).first()

    if run is None:
        raise AssertionError(f"WorkflowRun with ID '{run_id}' not found in database")

    if status is not None and run.status != status:
        raise AssertionError(
            f"WorkflowRun status mismatch: expected '{status}', got '{run.status}'"
        )

    if workflow_name is not None and run.workflow != workflow_name:
        raise AssertionError(
            f"WorkflowRun name mismatch: expected '{workflow_name}', got '{run.workflow}'"
        )

    return run


def assert_workflow_status(session: Session, run_id: str, expected_status: str) -> None:
    """
    Assert that a workflow run has the expected status.

    Args:
        session: Database session
        run_id: Workflow run ID
        expected_status: Expected status (pending, running, completed, failed, canceled)

    Raises:
        AssertionError: If status doesn't match
    """
    from kurt.observability.models import WorkflowRun

    run = session.exec(select(WorkflowRun).where(WorkflowRun.id == run_id)).first()

    if run is None:
        raise AssertionError(f"WorkflowRun with ID '{run_id}' not found")

    if run.status != expected_status:
        raise AssertionError(
            f"WorkflowRun status mismatch: expected '{expected_status}', got '{run.status}'"
        )


def assert_workflow_run_count(
    session: Session,
    expected: int,
    *,
    status: str | None = None,
    workflow_name: str | None = None,
) -> None:
    """
    Assert the count of workflow runs matches expected.

    Args:
        session: Database session
        expected: Expected count
        status: Optional status to filter by
        workflow_name: Optional workflow name to filter by

    Raises:
        AssertionError: If count doesn't match
    """
    from kurt.observability.models import WorkflowRun

    query = select(WorkflowRun)

    if status is not None:
        query = query.where(WorkflowRun.status == status)

    if workflow_name is not None:
        query = query.where(WorkflowRun.workflow == workflow_name)

    runs = session.exec(query).all()
    actual = len(runs)

    if actual != expected:
        raise AssertionError(f"WorkflowRun count mismatch: expected {expected}, got {actual}")


# =============================================================================
# Generic Model Assertions
# =============================================================================


def assert_row_count(session: Session, model: type[T], expected: int) -> None:
    """
    Assert the count of rows in a table matches expected.

    Args:
        session: Database session
        model: SQLModel class
        expected: Expected row count

    Raises:
        AssertionError: If count doesn't match
    """
    rows = session.exec(select(model)).all()
    actual = len(rows)

    if actual != expected:
        raise AssertionError(f"{model.__name__} count mismatch: expected {expected}, got {actual}")


def assert_table_empty(session: Session, model: type[T]) -> None:
    """
    Assert that a table is empty.

    Args:
        session: Database session
        model: SQLModel class

    Raises:
        AssertionError: If table has rows
    """
    rows = session.exec(select(model)).all()

    if rows:
        raise AssertionError(
            f"Table {model.__name__} expected to be empty but has {len(rows)} rows"
        )


def assert_table_not_empty(session: Session, model: type[T]) -> None:
    """
    Assert that a table is not empty.

    Args:
        session: Database session
        model: SQLModel class

    Raises:
        AssertionError: If table is empty
    """
    rows = session.exec(select(model)).all()

    if not rows:
        raise AssertionError(f"Table {model.__name__} is empty but expected rows")


# =============================================================================
# Filesystem Assertions
# =============================================================================


def assert_file_exists(path: str | Path) -> Path:
    """
    Assert that a file exists at the given path.

    Args:
        path: Path to check

    Returns:
        Path object for the file

    Raises:
        AssertionError: If file doesn't exist
    """
    p = Path(path)
    if not p.exists():
        raise AssertionError(f"File not found: {path}")
    if not p.is_file():
        raise AssertionError(f"Path is not a file: {path}")
    return p


def assert_file_not_exists(path: str | Path) -> None:
    """
    Assert that a file does not exist at the given path.

    Args:
        path: Path to check

    Raises:
        AssertionError: If file exists
    """
    p = Path(path)
    if p.exists():
        raise AssertionError(f"File unexpectedly exists: {path}")


def assert_directory_exists(path: str | Path) -> Path:
    """
    Assert that a directory exists at the given path.

    Args:
        path: Path to check

    Returns:
        Path object for the directory

    Raises:
        AssertionError: If directory doesn't exist
    """
    p = Path(path)
    if not p.exists():
        raise AssertionError(f"Directory not found: {path}")
    if not p.is_dir():
        raise AssertionError(f"Path is not a directory: {path}")
    return p


def assert_file_contains(path: str | Path, text: str) -> None:
    """
    Assert that a file contains the specified text.

    Args:
        path: Path to file
        text: Text to search for

    Raises:
        AssertionError: If file doesn't contain text
    """
    p = assert_file_exists(path)
    content = p.read_text()

    if text not in content:
        raise AssertionError(
            f"File {path} does not contain expected text: {text!r}\n"
            f"Actual content: {content[:500]}..."
        )


def assert_file_content_matches(path: str | Path, expected: str) -> None:
    """
    Assert that a file's content exactly matches expected.

    Args:
        path: Path to file
        expected: Expected content

    Raises:
        AssertionError: If content doesn't match
    """
    p = assert_file_exists(path)
    actual = p.read_text()

    if actual != expected:
        raise AssertionError(
            f"File content mismatch:\nExpected: {expected[:200]}...\nActual: {actual[:200]}..."
        )


# =============================================================================
# Count Helpers
# =============================================================================


def count_documents_by_status(session: Session, status: str, model_type: str = "map") -> int:
    """
    Count documents with the given status.

    Args:
        session: Database session
        status: Status to count
        model_type: "map" or "fetch"

    Returns:
        Count of documents with status
    """
    if model_type == "map":
        from kurt.tools.map.models import MapDocument, MapStatus

        status_enum = MapStatus(status)
        docs = session.exec(select(MapDocument).where(MapDocument.status == status_enum)).all()
    else:
        from kurt.tools.fetch.models import FetchDocument, FetchStatus

        status_enum = FetchStatus(status)
        docs = session.exec(select(FetchDocument).where(FetchDocument.status == status_enum)).all()

    return len(docs)


def count_documents_by_domain(session: Session, domain: str) -> int:
    """
    Count MapDocuments with URLs containing the given domain.

    Args:
        session: Database session
        domain: Domain to match (e.g., "example.com")

    Returns:
        Count of documents from domain
    """
    from kurt.tools.map.models import MapDocument

    docs = session.exec(select(MapDocument).where(MapDocument.source_url.contains(domain))).all()

    return len(docs)


__all__ = [
    # Map document assertions
    "assert_map_document_exists",
    "assert_map_document_not_exists",
    "assert_map_document_count",
    # Fetch document assertions
    "assert_fetch_document_exists",
    "assert_fetch_document_not_exists",
    "assert_fetch_document_count",
    "assert_fetch_has_content",
    # Workflow assertions
    "assert_workflow_run_exists",
    "assert_workflow_status",
    "assert_workflow_run_count",
    # Generic assertions
    "assert_row_count",
    "assert_table_empty",
    "assert_table_not_empty",
    # Filesystem assertions
    "assert_file_exists",
    "assert_file_not_exists",
    "assert_directory_exists",
    "assert_file_contains",
    "assert_file_content_matches",
    # Count helpers
    "count_documents_by_status",
    "count_documents_by_domain",
]

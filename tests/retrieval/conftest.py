"""Fixtures for retrieval integration tests."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from kurt.db.database import get_session


@pytest.fixture
def motherduck_project(tmp_project):
    """
    Load the MotherDuck mock project into a temporary Kurt project.

    This fixture:
    - Uses tmp_project to create isolated test environment
    - Loads documents, entities, and relationships from motherduck dump
    - Returns the project directory path

    Usage:
        def test_retrieval(motherduck_project):
            # Database is populated with motherduck data
            result = await retrieve("DuckDB embeddings")
    """
    # Path to mock project dump
    dump_dir = (
        Path(__file__).parent.parent.parent
        / "eval"
        / "mock"
        / "projects"
        / "motherduck"
        / "database"
    )

    if not dump_dir.exists():
        pytest.skip(f"MotherDuck dump not found at {dump_dir}")

    # Tables to load in dependency order
    tables = [
        "documents",
        "entities",
        "document_entities",
        "entity_relationships",
    ]

    session = get_session()

    try:
        for table_name in tables:
            input_file = dump_dir / f"{table_name}.jsonl"

            if not input_file.exists():
                continue

            # Get valid columns for this table
            pragma_query = text(f"PRAGMA table_info({table_name})")
            table_columns_info = session.execute(pragma_query).fetchall()
            valid_columns = {col[1] for col in table_columns_info}

            # Read and insert records
            count = 0
            with open(input_file, "r") as f:
                for line in f:
                    record = json.loads(line)

                    # Filter to valid columns only
                    filtered_record = {k: v for k, v in record.items() if k in valid_columns}

                    if not filtered_record:
                        continue

                    # Build INSERT statement
                    columns = list(filtered_record.keys())
                    placeholders = [f":{col}" for col in columns]

                    insert_sql = text(
                        f"INSERT OR REPLACE INTO {table_name} "
                        f"({', '.join(columns)}) "
                        f"VALUES ({', '.join(placeholders)})"
                    )

                    session.execute(insert_sql, filtered_record)
                    count += 1

            session.commit()

        yield tmp_project

    finally:
        session.close()


@pytest.fixture
def mock_retrieval_llm(mock_dspy_signature):
    """
    Mock LLM calls for retrieval query analysis.

    Returns predictable query analysis results without calling the LLM.
    """
    from unittest.mock import MagicMock, patch

    # Mock the query analyzer output
    mock_analysis = MagicMock()
    mock_analysis.intent = "technical_question"
    mock_analysis.entities = ["DuckDB", "embeddings", "MotherDuck"]
    mock_analysis.keywords = ["vector", "similarity", "search"]

    with patch("dspy.ChainOfThought") as mock_cot:
        mock_module = MagicMock()
        mock_module.return_value = mock_analysis
        mock_cot.return_value = mock_module
        yield mock_analysis

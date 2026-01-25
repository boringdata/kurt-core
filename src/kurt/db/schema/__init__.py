"""
SQL schema definitions for tool-owned tables.

Each tool owns its table:
- document_registry.sql - Central registry
- map_results.sql - MapTool output
- fetch_results.sql - FetchTool output
- embed_results.sql - EmbedTool output
- documents_view.sql - Unified VIEW

See spec: kurt-core-5v6 "Tool-Owned Tables with Pydantic Schemas"
"""

from pathlib import Path

SCHEMA_DIR = Path(__file__).parent

# Schema files in order of dependency
SCHEMA_FILES = [
    "schema_migrations.sql",
    "document_registry.sql",
    "map_results.sql",
    "fetch_results.sql",
    "embed_results.sql",
    "documents_view.sql",
]


def get_schema_file(name: str) -> Path:
    """Get path to a schema file."""
    return SCHEMA_DIR / name


def get_all_schema_sql() -> str:
    """Get all schema SQL in dependency order."""
    sql_parts = []
    for filename in SCHEMA_FILES:
        path = SCHEMA_DIR / filename
        if path.exists():
            sql_parts.append(path.read_text())
    return "\n\n".join(sql_parts)

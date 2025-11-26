#!/usr/bin/env python3
"""Create database dumps from an existing Kurt project.

Usage:
    python create_dump.py /path/to/kurt/project dump_name
"""

import json
import shutil
import sys
from pathlib import Path

# Add src to path to import kurt modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from sqlalchemy import text

from kurt.db.database import get_session


def create_dump(project_path: Path, dump_name: str):
    """Create JSONL dumps of all tables from a Kurt project."""
    db_path = project_path / ".kurt" / "kurt.sqlite"

    if not db_path.exists():
        raise FileNotFoundError(f"No database found at {db_path}")

    # Create project directory in mock/projects/{dump_name}
    project_dir = Path(__file__).parent.parent / "projects" / dump_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create database subdirectory
    dump_dir = project_dir / "database"
    dump_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating dump from: {project_path}")
    print(f"Output directory: {project_dir}")

    # Tables to export (we'll get columns dynamically from the schema)
    tables = ["documents", "entities", "document_entities", "entity_relationships"]

    session = get_session()

    try:
        for table_name in tables:
            output_file = dump_dir / f"{table_name}.jsonl"

            # Get all columns from the table dynamically
            pragma_query = text(f"PRAGMA table_info({table_name})")
            columns_info = session.execute(pragma_query).fetchall()

            # Skip binary/blob columns (like embedding)
            columns = [
                col[1]
                for col in columns_info
                if col[2].upper() not in ["BLOB"]  # col[1] is name, col[2] is type
            ]

            # Query all rows
            cols_str = ", ".join(columns)
            query = text(f"SELECT {cols_str} FROM {table_name}")
            result = session.execute(query)

            # Write to JSONL
            count = 0
            with open(output_file, "w") as f:
                for row in result:
                    record = dict(zip(columns, row))
                    f.write(json.dumps(record, default=str) + "\n")
                    count += 1

            print(f"✓ Exported {count} rows from {table_name}")

        # Copy source files - check both .kurt/sources/ and sources/ directories
        target_sources = project_dir / "sources"

        # Try .kurt/sources/ first (newer Kurt projects)
        sources_dir = project_path / ".kurt" / "sources"
        if not sources_dir.exists():
            # Fall back to sources/ (legacy location)
            sources_dir = project_path / "sources"

        if sources_dir.exists():
            if target_sources.exists():
                shutil.rmtree(target_sources)
            shutil.copytree(sources_dir, target_sources)

            # Count files
            file_count = sum(1 for _ in target_sources.rglob("*") if _.is_file())
            print(
                f"✓ Copied {file_count} source files from {sources_dir.relative_to(project_path)}"
            )
        else:
            print("⚠ No source files found - skipping")

        print(f"\n✅ Dump created successfully in {project_dir}")
        print("\nUsage in scenarios:")
        print("  setup_commands:")
        print("    - KURT_TELEMETRY_DISABLED=1 uv run kurt init")
        print(f"    - python eval/mock/generators/load_dump.py {dump_name}")

    finally:
        session.close()


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python create_dump.py /path/to/kurt/project dump_name")
        print("\nExample:")
        print("  python create_dump.py ~/my-kurt-project my-demo")
        print("\nThis will create:")
        print("  eval/mock/projects/my-demo/")
        print("    ├── database/")
        print("    │   ├── documents.jsonl")
        print("    │   ├── entities.jsonl")
        print("    │   ├── document_entities.jsonl")
        print("    │   └── entity_relationships.jsonl")
        print("    └── sources/  (content files)")
        sys.exit(1)

    project_path = Path(sys.argv[1]).expanduser().resolve()
    dump_name = sys.argv[2]

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    create_dump(project_path, dump_name)


if __name__ == "__main__":
    main()

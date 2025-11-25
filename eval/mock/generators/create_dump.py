#!/usr/bin/env python3
"""Create database dumps from an existing Kurt project.

Usage:
    python create_dump.py /path/to/kurt/project dump_name
"""

import json
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

    # Create dump directory
    dump_dir = Path(__file__).parent / dump_name
    dump_dir.mkdir(exist_ok=True)

    print(f"Creating dump from: {db_path}")
    print(f"Output directory: {dump_dir}")

    # Tables to export
    tables = {
        "documents": [
            "id",
            "source_url",
            "title",
            "content_path",
            "ingestion_status",
            "content_type",
            "discovered_at",
            "fetched_at",
            "indexed_at",
        ],
        "entities": [
            "id",
            "name",
            "entity_type",
            "canonical_name",
            "description",
            "confidence_score",
            "source_mentions",
            "created_at",
        ],
        "document_entities": [
            "document_id",
            "entity_id",
            "mention_count",
            "confidence",
            "created_at",
        ],
        "entity_relationships": [
            "id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "confidence",
            "evidence_count",
            "context",
            "created_at",
        ],
    }

    session = get_session()

    try:
        for table_name, columns in tables.items():
            output_file = dump_dir / f"{table_name}.jsonl"

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

        print(f"\n✅ Dump created successfully in {dump_dir}")
        print("\nUsage in scenarios:")
        print("  setup_commands:")
        print("    - KURT_TELEMETRY_DISABLED=1 uv run kurt init")
        print(f"    - python eval/mock/db_dumps/load_dump.py {dump_name}")

    finally:
        session.close()


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python create_dump.py /path/to/kurt/project dump_name")
        print("\nExample:")
        print("  python create_dump.py ~/my-kurt-project acme_docs")
        sys.exit(1)

    project_path = Path(sys.argv[1]).expanduser().resolve()
    dump_name = sys.argv[2]

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    create_dump(project_path, dump_name)


if __name__ == "__main__":
    main()

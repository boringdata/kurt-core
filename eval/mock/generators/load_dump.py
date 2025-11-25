#!/usr/bin/env python3
"""Load database dumps into current Kurt project.

Usage:
    python load_dump.py dump_name
"""

import json
import sys
from pathlib import Path

# Add src to path to import kurt modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from sqlalchemy import text

from kurt.db.database import get_session


def load_dump(dump_name: str):
    """Load JSONL dumps into the current Kurt project database."""
    # Look for dump in mock/data/db/{dump_name}/
    dump_dir = Path(__file__).parent.parent / "data" / "db" / dump_name

    if not dump_dir.exists():
        raise FileNotFoundError(f"Dump directory not found: {dump_dir}")

    # Check that we're in a Kurt project
    if not Path(".kurt/kurt.sqlite").exists():
        raise RuntimeError("No Kurt database found. Run 'kurt init' first.")

    print(f"Loading dump from: {dump_dir}")

    # Tables to import (in dependency order)
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
                print(f"⚠ Skipping {table_name} (file not found)")
                continue

            # Read JSONL and insert rows
            count = 0
            with open(input_file, "r") as f:
                for line in f:
                    record = json.loads(line)

                    # Build INSERT statement
                    columns = list(record.keys())
                    placeholders = [f":{col}" for col in columns]

                    insert_sql = text(
                        f"INSERT OR REPLACE INTO {table_name} "
                        f"({', '.join(columns)}) "
                        f"VALUES ({', '.join(placeholders)})"
                    )

                    session.execute(insert_sql, record)
                    count += 1

            session.commit()
            print(f"✓ Loaded {count} rows into {table_name}")

        print("\n✅ Dump loaded successfully!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error loading dump: {e}")
        raise
    finally:
        session.close()


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python load_dump.py dump_name")
        print("\nExample:")
        print("  python load_dump.py acme-docs")
        print("\nAvailable dumps:")
        dumps_dir = Path(__file__).parent.parent / "data" / "db"
        for item in dumps_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                print(f"  - {item.name}")
        sys.exit(1)

    dump_name = sys.argv[1]
    load_dump(dump_name)


if __name__ == "__main__":
    main()

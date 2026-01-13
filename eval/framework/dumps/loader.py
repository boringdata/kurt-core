#!/usr/bin/env python3
"""Load database dumps into current Kurt project.

Usage:
    python load_dump.py dump_name
"""

import base64
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add src to path to import kurt modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from sqlalchemy import text

from kurt.db.database import get_session


def _migrate_old_documents_to_new_schema(dump_dir: Path, session) -> int:
    """Migrate old 'documents' table format to new map_documents + fetch_documents.

    Old schema had a single 'documents' table. New schema splits into:
    - map_documents: discovery/mapping info (source_url, title, discovery_method)
    - fetch_documents: fetch status and content (content_path, embedding, status)

    Returns number of documents migrated.
    """
    input_file = dump_dir / "documents.jsonl"
    if not input_file.exists():
        return 0

    print("  Migrating old documents schema to map_documents + fetch_documents...")

    # Field mappings from old -> new
    # Old 'id' -> new 'document_id'
    # Old 'ingestion_status' -> fetch_documents 'status' (FETCHED -> SUCCESS, etc.)

    map_count = 0
    fetch_count = 0

    with open(input_file, "r") as f:
        for line in f:
            record = json.loads(line)

            # Get document ID (old schema used 'id', new uses 'document_id')
            doc_id = record.get("id") or record.get("document_id")
            if not doc_id:
                continue

            now = datetime.utcnow().isoformat()

            # Build map_documents record
            map_record = {
                "document_id": doc_id,
                "source_url": record.get("source_url", ""),
                "source_type": (record.get("source_type") or "url").lower(),
                "discovery_method": record.get("discovery_method") or "",
                "discovery_url": record.get("discovery_url"),
                "status": "SUCCESS",  # If it was in old dump, it was mapped
                "is_new": False,
                "title": record.get("title"),
                "content_hash": record.get("content_hash"),
                "created_at": record.get("created_at") or now,
                "updated_at": record.get("updated_at") or now,
            }

            # Insert into map_documents
            map_cols = list(map_record.keys())
            map_placeholders = [f":{col}" for col in map_cols]
            map_sql = text(
                f"INSERT OR REPLACE INTO map_documents "
                f"({', '.join(map_cols)}) VALUES ({', '.join(map_placeholders)})"
            )
            session.execute(map_sql, map_record)
            map_count += 1

            # Build fetch_documents record (only if content was fetched)
            old_status = record.get("ingestion_status", "")
            if old_status in ("FETCHED", "INDEXED", "SUCCESS"):
                # Handle embedding - decode base64 if present
                embedding = record.get("embedding")
                if embedding and isinstance(embedding, str):
                    embedding = base64.b64decode(embedding)

                fetch_record = {
                    "document_id": doc_id,
                    "status": "SUCCESS",
                    "content_length": 0,
                    "content_hash": record.get("content_hash"),
                    "content_path": record.get("content_path"),
                    "embedding": embedding,
                    "created_at": record.get("created_at") or now,
                    "updated_at": record.get("updated_at") or now,
                }

                fetch_cols = list(fetch_record.keys())
                fetch_placeholders = [f":{col}" for col in fetch_cols]
                fetch_sql = text(
                    f"INSERT OR REPLACE INTO fetch_documents "
                    f"({', '.join(fetch_cols)}) VALUES ({', '.join(fetch_placeholders)})"
                )
                session.execute(fetch_sql, fetch_record)
                fetch_count += 1

    session.commit()
    print(f"  ✓ Migrated {map_count} to map_documents, {fetch_count} to fetch_documents")
    return map_count


def load_dump(dump_name: str, skip_entities: bool = False):
    """Load JSONL dumps into the current Kurt project database.

    The load is schema-adaptive - it only inserts columns that exist in the
    target database, so dumps from different schema versions will work.

    Also handles migration from old 'documents' schema to new split schema
    (map_documents + fetch_documents).

    Args:
        dump_name: Name of the dump to load (project name)
        skip_entities: If True, skip loading entity-related tables
    """
    # Look for dump in mock/projects/{dump_name}/
    # Go up from framework/dumps/ to eval/ then to mock/projects/
    project_dir = Path(__file__).parent.parent.parent / "mock" / "projects" / dump_name

    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    # Database dumps are in the database/ subdirectory
    dump_dir = project_dir / "database"
    if not dump_dir.exists():
        raise FileNotFoundError(f"Database directory not found: {dump_dir}")

    # Check that we're in a Kurt project
    if not Path(".kurt/kurt.sqlite").exists():
        raise RuntimeError("No Kurt database found. Run 'kurt init' first.")

    print(f"Loading dump from: {dump_dir}")
    if skip_entities:
        print("⚠ Skipping entity-related tables (--skip-entities)")

    session = get_session()

    try:
        # Check if we need to migrate old documents schema
        # Old schema: documents.jsonl with 'id' field
        # New schema: map_documents.jsonl + fetch_documents.jsonl
        old_docs_file = dump_dir / "documents.jsonl"
        new_map_file = dump_dir / "map_documents.jsonl"

        if old_docs_file.exists() and not new_map_file.exists():
            # Old schema - need to migrate
            _migrate_old_documents_to_new_schema(dump_dir, session)
        elif new_map_file.exists():
            # New schema - load directly
            pass  # Will be handled by normal table loading below

        # Tables to import (in dependency order) - new schema
        if skip_entities:
            tables = ["map_documents", "fetch_documents"]
        else:
            tables = [
                "map_documents",
                "fetch_documents",
                "entities",
                "claims",
                "claim_entities",
                "document_entities",
                "entity_relationships",
                "claim_relationships",
            ]

        for table_name in tables:
            input_file = dump_dir / f"{table_name}.jsonl"

            if not input_file.exists():
                print(f"⚠ Skipping {table_name} (file not found)")
                continue

            # Get the actual columns in the target table
            pragma_query = text(f"PRAGMA table_info({table_name})")
            table_columns_info = session.execute(pragma_query).fetchall()
            valid_columns = {col[1] for col in table_columns_info}  # col[1] is column name

            # Track which columns are BLOB type (for base64 decoding)
            blob_columns = {col[1] for col in table_columns_info if col[2].upper() == "BLOB"}

            # Build a map of required columns (NOT NULL without default)
            # col = (cid, name, type, notnull, dflt_value, pk)
            required_columns = {
                col[1]: col[2]  # name -> type
                for col in table_columns_info
                if col[3] == 1 and col[4] is None and col[5] == 0  # notnull=1, no default, not pk
            }

            # Read JSONL and insert rows
            count = 0
            with open(input_file, "r") as f:
                for line in f:
                    record = json.loads(line)

                    # Only use columns that exist in the target table
                    filtered_record = {}
                    for k, v in record.items():
                        if k not in valid_columns:
                            continue
                        # Decode base64-encoded BLOB columns
                        if k in blob_columns and v is not None and isinstance(v, str):
                            filtered_record[k] = base64.b64decode(v)
                        else:
                            filtered_record[k] = v

                    # Add default values for missing required columns
                    for col_name, col_type in required_columns.items():
                        if col_name not in filtered_record:
                            # Provide empty/zero defaults based on type
                            if col_type == "BLOB":
                                filtered_record[col_name] = b""  # Empty blob for embeddings
                            elif "INT" in col_type.upper():
                                filtered_record[col_name] = 0
                            elif "FLOAT" in col_type.upper() or "REAL" in col_type.upper():
                                filtered_record[col_name] = 0.0
                            else:
                                filtered_record[col_name] = ""  # Empty string for VARCHAR/TEXT

                    if not filtered_record:
                        print(f"⚠ No matching columns for record in {table_name}")
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
            print(f"✓ Loaded {count} rows into {table_name}")

        # Copy source files if they exist in the project
        sources_dir = project_dir / "sources"
        if sources_dir.exists():
            target_sources = Path(".kurt") / "sources"
            target_sources.mkdir(parents=True, exist_ok=True)

            # Copy all files from dump sources to .kurt/sources
            for item in sources_dir.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(sources_dir)
                    target_file = target_sources / rel_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_file)

            file_count = sum(1 for _ in target_sources.rglob("*") if _.is_file())
            print(f"✓ Restored {file_count} source files to .kurt/sources/")
        else:
            print("⚠ No sources in dump - skipping")

        print("\n✅ Dump loaded successfully!")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error loading dump: {e}")
        raise
    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Load database dumps into current Kurt project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("dump_name", nargs="?", help="Name of the dump to load")
    parser.add_argument(
        "--skip-entities",
        action="store_true",
        help="Skip loading entity-related tables (for vector search baseline)",
    )

    args = parser.parse_args()

    # If no dump name provided, show available dumps
    if not args.dump_name:
        print("Usage: python load_dump.py dump_name [--skip-entities]")
        print("\nExample:")
        print("  python load_dump.py acme-docs")
        print("  python load_dump.py motherduck --skip-entities")
        print("\nAvailable project dumps:")

        # List all project dumps
        projects_dir = Path(__file__).parent.parent / "projects"
        if projects_dir.exists():
            for item in sorted(projects_dir.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    # Show summary of what's in the dump
                    db_dir = item / "database"
                    jsonl_files = list(db_dir.glob("*.jsonl")) if db_dir.exists() else []
                    has_sources = (item / "sources").exists()
                    info = f"{len(jsonl_files)} tables"
                    if has_sources:
                        source_count = sum(1 for _ in (item / "sources").rglob("*") if _.is_file())
                        info += f", {source_count} sources"
                    print(f"  - {item.name} ({info})")
        else:
            print("  (no dumps found)")
        sys.exit(1)

    load_dump(args.dump_name, skip_entities=args.skip_entities)


if __name__ == "__main__":
    main()

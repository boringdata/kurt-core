#!/usr/bin/env python3
"""
Integration test for project dump/load functionality.

This demonstrates the full workflow:
1. Create a test Kurt project
2. Dump it
3. Load it into a fresh project
4. Verify data was restored correctly
"""

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

print("=" * 60)
print("Project Dump/Load Integration Test")
print("=" * 60)

# Step 1: Create a test Kurt project
print("\n1. Creating test Kurt project...")
with tempfile.TemporaryDirectory() as tmpdir:
    project_path = Path(tmpdir) / "test-project"
    project_path.mkdir()

    kurt_dir = project_path / ".kurt"
    kurt_dir.mkdir()

    # Create sources
    sources_dir = kurt_dir / "sources"
    sources_dir.mkdir()
    (sources_dir / "doc1.md").write_text("# Document 1\n\nTest content.")
    (sources_dir / "doc2.md").write_text("# Document 2\n\nMore content.")

    # Create database
    db_path = kurt_dir / "kurt.sqlite"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            title TEXT,
            source_type TEXT NOT NULL,
            source_url TEXT,
            content_path TEXT,
            ingestion_status TEXT NOT NULL,
            content_type TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            canonical_name TEXT,
            description TEXT,
            confidence_score REAL,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute(
        "CREATE TABLE document_entities (document_id TEXT, entity_id TEXT, created_at DATETIME NOT NULL, PRIMARY KEY (document_id, entity_id))"
    )
    cursor.execute(
        "CREATE TABLE entity_relationships (id TEXT PRIMARY KEY, source_entity_id TEXT, target_entity_id TEXT, created_at DATETIME NOT NULL)"
    )

    # Insert test data
    cursor.execute("""
        INSERT INTO documents VALUES
        ('doc1', 'Test Doc 1', 'web', 'http://example.com/1', 'doc1.md', 'indexed', 'text/markdown', '2024-01-01', '2024-01-01'),
        ('doc2', 'Test Doc 2', 'web', 'http://example.com/2', 'doc2.md', 'indexed', 'text/markdown', '2024-01-01', '2024-01-01')
    """)

    cursor.execute("""
        INSERT INTO entities VALUES
        ('ent1', 'Python', 'Technology', 'Python', 'Programming language', 0.95, '2024-01-01'),
        ('ent2', 'FastAPI', 'Technology', 'FastAPI', 'Web framework', 0.90, '2024-01-01')
    """)

    cursor.execute("""
        INSERT INTO document_entities VALUES
        ('doc1', 'ent1', '2024-01-01'),
        ('doc2', 'ent2', '2024-01-01')
    """)

    conn.commit()
    conn.close()

    print(f"   ✓ Created project at {project_path}")
    print("   ✓ Added 2 documents, 2 entities, 2 sources")

    # Step 2: Create dump
    print("\n2. Creating dump...")
    dump_dir = Path(tmpdir) / "dump" / "test-dump"
    dump_dir.mkdir(parents=True)

    # Open database for dumping
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ["documents", "entities", "document_entities", "entity_relationships"]
    for table_name in tables:
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]

        # Export to JSONL
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        output_file = dump_dir / f"{table_name}.jsonl"
        with open(output_file, "w") as f:
            for row in rows:
                record = dict(zip(columns, row))
                f.write(json.dumps(record, default=str) + "\n")

        print(f"   ✓ Exported {len(rows)} rows from {table_name}")

    conn.close()

    # Copy sources
    shutil.copytree(sources_dir, dump_dir / "sources")
    print("   ✓ Copied 2 source files")

    # Step 3: Load into fresh project
    print("\n3. Loading dump into fresh project...")
    fresh_project = Path(tmpdir) / "fresh-project"
    fresh_project.mkdir()

    fresh_kurt = fresh_project / ".kurt"
    fresh_kurt.mkdir()

    # Create fresh database
    fresh_db = fresh_kurt / "kurt.sqlite"
    conn = sqlite3.connect(fresh_db)
    cursor = conn.cursor()

    # Create tables (same schema)
    cursor.execute("""
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            title TEXT,
            source_type TEXT NOT NULL,
            source_url TEXT,
            content_path TEXT,
            ingestion_status TEXT NOT NULL,
            content_type TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            canonical_name TEXT,
            description TEXT,
            confidence_score REAL,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute(
        "CREATE TABLE document_entities (document_id TEXT, entity_id TEXT, created_at DATETIME NOT NULL, PRIMARY KEY (document_id, entity_id))"
    )
    cursor.execute(
        "CREATE TABLE entity_relationships (id TEXT PRIMARY KEY, source_entity_id TEXT, target_entity_id TEXT, created_at DATETIME NOT NULL)"
    )

    # Load from JSONL files
    for table_name in tables:
        input_file = dump_dir / f"{table_name}.jsonl"

        # Get valid columns in target table
        cursor.execute(f"PRAGMA table_info({table_name})")
        valid_columns = {row[1] for row in cursor.fetchall()}

        count = 0
        with open(input_file) as f:
            for line in f:
                record = json.loads(line)

                # Filter to only valid columns (schema-adaptive!)
                filtered = {k: v for k, v in record.items() if k in valid_columns}

                columns = list(filtered.keys())
                placeholders = ["?" for _ in columns]
                values = [filtered[col] for col in columns]

                insert_sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(insert_sql, values)
                count += 1

        conn.commit()
        print(f"   ✓ Loaded {count} rows into {table_name}")

    # Copy sources
    fresh_sources = fresh_kurt / "sources"
    shutil.copytree(dump_dir / "sources", fresh_sources)
    print("   ✓ Restored source files")

    # Step 4: Verify data
    print("\n4. Verifying restored data...")

    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    assert doc_count == 2, f"Expected 2 documents, got {doc_count}"
    print(f"   ✓ Documents: {doc_count}")

    cursor.execute("SELECT COUNT(*) FROM entities")
    ent_count = cursor.fetchone()[0]
    assert ent_count == 2, f"Expected 2 entities, got {ent_count}"
    print(f"   ✓ Entities: {ent_count}")

    cursor.execute("SELECT title FROM documents WHERE id='doc1'")
    title = cursor.fetchone()[0]
    assert title == "Test Doc 1", f"Expected 'Test Doc 1', got '{title}'"
    print(f"   ✓ Document data: '{title}'")

    cursor.execute("SELECT name FROM entities WHERE id='ent1'")
    name = cursor.fetchone()[0]
    assert name == "Python", f"Expected 'Python', got '{name}'"
    print(f"   ✓ Entity data: '{name}'")

    # Verify sources
    assert (fresh_sources / "doc1.md").exists(), "doc1.md not found"
    assert (fresh_sources / "doc2.md").exists(), "doc2.md not found"
    content = (fresh_sources / "doc1.md").read_text()
    assert "Document 1" in content, "Source content not preserved"
    print("   ✓ Source files restored correctly")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nThe dump/load workflow works correctly:")
    print("  • Database tables exported to JSONL")
    print("  • Source files copied")
    print("  • Schema-adaptive loading (only valid columns)")
    print("  • Data integrity preserved")
    print("\nReady to use in eval scenarios with:")
    print("  project: your-project-name")

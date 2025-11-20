#!/usr/bin/env python3
"""
Generate PostgreSQL schema SQL from kurt-core SQLModel models.

This script is used by kurt-cloud to generate Supabase migrations
from the single source of truth (kurt-core models).

Usage:
    python scripts/generate_postgres_schema.py > migration.sql
"""

import sys
from io import StringIO

from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable
from sqlmodel import SQLModel

# Import all models to register them with SQLModel


def generate_schema_sql() -> str:
    """Generate CREATE TABLE statements from SQLModel models."""

    # Use PostgreSQL dialect
    engine = create_engine("postgresql://dummy", strategy="mock", executor=lambda sql, *_: None)

    output = StringIO()

    # Header
    output.write("-- Generated from kurt-core models\n")
    output.write("-- DO NOT EDIT MANUALLY\n")
    output.write("-- Source: kurt-core/src/kurt/db/models.py\n\n")

    # Extensions
    output.write("-- Enable pgvector extension\n")
    output.write("CREATE EXTENSION IF NOT EXISTS vector;\n\n")

    # Create tables in dependency order
    metadata = SQLModel.metadata

    output.write("-- Create tables\n\n")
    for table in metadata.sorted_tables:
        create_stmt = CreateTable(table, if_not_exists=True)
        sql = str(create_stmt.compile(engine)).strip()
        output.write(f"{sql};\n\n")

    # Add indexes
    output.write("-- Create indexes\n\n")
    output.write("CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id);\n")
    output.write("CREATE INDEX IF NOT EXISTS idx_documents_source_url ON documents(source_url);\n")
    output.write(
        "CREATE INDEX IF NOT EXISTS idx_documents_ingestion_status ON documents(ingestion_status);\n"
    )
    output.write("CREATE INDEX IF NOT EXISTS idx_entities_tenant_id ON entities(tenant_id);\n")
    output.write("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);\n")
    output.write("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);\n")
    output.write(
        "CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);\n"
    )
    output.write(
        "CREATE INDEX IF NOT EXISTS idx_document_entities_entity_id ON document_entities(entity_id);\n"
    )
    output.write(
        "CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_id);\n"
    )
    output.write(
        "CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_id);\n\n"
    )

    # Add RLS policies (placeholder - kurt-cloud will customize)
    output.write("-- Row-Level Security policies\n")
    output.write("-- Note: These are basic templates. Customize in kurt-cloud.\n\n")

    # Enable RLS on tables with tenant_id
    rls_tables = ["documents", "entities", "document_entities", "entity_relationships"]
    for table in rls_tables:
        output.write(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;\n")

    output.write("\n-- Example RLS policy (customize for your auth setup)\n")
    output.write("-- CREATE POLICY tenant_isolation ON documents\n")
    output.write("--   FOR ALL\n")
    output.write("--   USING (tenant_id = (auth.jwt() ->> 'workspace_id')::uuid);\n\n")

    return output.getvalue()


def main():
    """Generate and print schema SQL."""
    try:
        schema_sql = generate_schema_sql()
        print(schema_sql)
    except Exception as e:
        print(f"Error generating schema: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

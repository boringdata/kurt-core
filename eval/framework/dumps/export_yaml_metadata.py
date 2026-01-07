#!/usr/bin/env python3
"""Export entities and claims to grep-friendly text files for fast retrieval.

This script reads from the JSONL database dumps and creates two files:
- entities.txt: One entity per line, grep-friendly format
- claims.txt: One claim per line, grep-friendly format

The format is optimized for:
1. Single grep to find relevant entries (one entry = one line)
2. Line numbers for targeted file reads
3. All searchable info on one line

Usage:
    python export_yaml_metadata.py motherduck
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def load_jsonl(filepath: Path) -> list[dict]:
    """Load records from a JSONL file."""
    records = []
    with open(filepath) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def char_offset_to_line(content: str, char_offset: int) -> int:
    """Convert character offset to line number (1-indexed)."""
    if char_offset <= 0:
        return 1
    return content[:char_offset].count("\n") + 1


def find_claim_line_number(
    content: str, statement: str, source_quote: str | None = None
) -> tuple[int, int]:
    """Find the line number where a claim appears in document.

    Uses source_quote first (actual text from doc), then falls back to statement.
    Returns (start_line, end_line) or (1, 50) if not found.
    """
    lines = content.split("\n")

    # Try source_quote first (it's the actual text from the document)
    search_texts = []
    if source_quote:
        search_texts.append(source_quote.lower().strip())
    search_texts.append(statement.lower().strip())

    for search_text in search_texts:
        # Take first 60 chars for matching
        search_prefix = search_text[:60]

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            # Try exact substring match
            if search_text in line_lower:
                return (i, min(i + 10, len(lines)))
            # Try prefix match
            if search_prefix in line_lower:
                return (i, min(i + 10, len(lines)))

        # Try matching key phrases (first 4 significant words)
        words = [w for w in search_text.split() if len(w) > 3][:6]
        if len(words) >= 3:
            # Escape regex special chars in words
            escaped_words = [re.escape(w) for w in words[:4]]
            pattern = r".*".join(escaped_words)
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line.lower()):
                    return (i, min(i + 10, len(lines)))

    return (1, 50)  # Not found


def load_doc_contents(sources_dir: Path, documents: dict) -> dict:
    """Load document contents to calculate line numbers."""
    doc_contents = {}
    for doc_id, doc in documents.items():
        content_path = doc.get("content_path", "")
        if not content_path:
            continue

        # Build full path
        if "sources/" in content_path:
            rel_path = content_path.split("sources/", 1)[1]
        else:
            rel_path = content_path

        full_path = sources_dir / rel_path
        if full_path.exists():
            try:
                doc_contents[doc_id] = full_path.read_text()
            except Exception:
                doc_contents[doc_id] = ""
    return doc_contents


def export_yaml_metadata(project_name: str, output_dir: Path = None):
    """Export entities and claims to grep-friendly text files.

    Args:
        project_name: Name of the project (e.g., 'motherduck')
        output_dir: Output directory for files (defaults to project sources)
    """
    project_dir = Path(__file__).parent.parent.parent / "mock" / "projects" / project_name
    if not project_dir.exists():
        raise FileNotFoundError(f"Project not found: {project_dir}")

    db_dir = project_dir / "database"
    sources_dir = project_dir / "sources"

    if output_dir is None:
        output_dir = sources_dir / "motherduck.com" / ".metadata"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {db_dir}")

    # Load all tables
    documents = {d["id"]: d for d in load_jsonl(db_dir / "documents.jsonl")}
    entities = {e["id"]: e for e in load_jsonl(db_dir / "entities.jsonl")}
    claims = load_jsonl(db_dir / "claims.jsonl")
    doc_entities = load_jsonl(db_dir / "document_entities.jsonl")

    print(f"Loaded: {len(documents)} documents, {len(entities)} entities, {len(claims)} claims")

    # Load document contents for line number calculation
    print("Loading document contents for line number calculation...")
    doc_contents = load_doc_contents(sources_dir, documents)
    print(f"Loaded content for {len(doc_contents)} documents")

    # Build entity -> documents mapping
    entity_docs = defaultdict(list)
    for de in doc_entities:
        entity_id = de["entity_id"]
        doc_id = de["document_id"]
        if doc_id in documents and entity_id in entities:
            doc = documents[doc_id]
            content_path = doc.get("content_path", "")
            if content_path:
                if "sources/" in content_path:
                    rel_path = content_path.split("sources/", 1)[1]
                else:
                    rel_path = content_path
                entity_docs[entity_id].append(rel_path)

    # ==========================================================================
    # Export entities.txt - ONE LINE PER ENTITY
    # Format: ENTITY | type | description | keywords: k1,k2,k3 | docs: doc1.md, doc2.md
    # ==========================================================================
    entities_file = output_dir / "entities.txt"
    entity_lines = []

    for entity_id, entity in entities.items():
        if entity_id not in entity_docs:
            continue

        name = entity["name"]
        etype = entity.get("entity_type", "")
        desc = entity.get("description", "").replace("\n", " ")[:100]

        # Unique docs (limit to 5)
        docs = list(dict.fromkeys(entity_docs[entity_id]))[:5]

        # Build single line
        line = f"{name} | {etype} | {desc} | docs: {', '.join(docs)}"
        entity_lines.append((name.lower(), line))

    # Sort by name
    entity_lines.sort(key=lambda x: x[0])

    with open(entities_file, "w") as f:
        f.write("# ENTITIES INDEX - One entity per line, grep-friendly\n")
        f.write("# Format: NAME | type | description | docs: doc1.md, doc2.md\n")
        f.write(f"# Total: {len(entity_lines)} entities\n")
        f.write("# Usage: grep -i 'dbt' entities.txt\n")
        f.write("#\n")
        for _, line in entity_lines:
            f.write(line + "\n")

    print(f"✓ Exported {len(entity_lines)} entities to {entities_file}")

    # ==========================================================================
    # Export claims.txt - ONE LINE PER CLAIM
    # Format: CLAIM_TEXT | type | entity | doc: path.md | lines: 10-25 | keywords: k1,k2
    # ==========================================================================
    claims_file = output_dir / "claims.txt"
    claim_lines = []

    for claim in claims:
        doc_id = claim.get("source_document_id")
        entity_id = claim.get("subject_entity_id")

        if doc_id not in documents:
            continue

        doc = documents[doc_id]
        content_path = doc.get("content_path", "")
        if not content_path:
            continue

        if "sources/" in content_path:
            rel_path = content_path.split("sources/", 1)[1]
        else:
            rel_path = content_path

        # Get entity name
        entity_name = entities.get(entity_id, {}).get("name", "unknown")

        # Clean statement (single line)
        statement = claim["statement"].replace("\n", " ").strip()

        # Get source_quote (actual text from document)
        source_quote = claim.get("source_quote")

        # Find actual line numbers by searching for claim text in document
        # Uses source_quote first (actual doc text), then falls back to statement
        if doc_id in doc_contents and doc_contents[doc_id]:
            content = doc_contents[doc_id]
            line_start, line_end = find_claim_line_number(content, statement, source_quote)
        else:
            line_start = 1
            line_end = 50  # Default range

        # Claim type
        claim_type = claim.get("claim_type", "").lower()

        # Build single line
        line = f"{statement} | {claim_type} | entity: {entity_name} | doc: {rel_path} | lines: {line_start}-{line_end}"

        # Sort key: entity name, then statement
        claim_lines.append((entity_name.lower(), statement.lower(), line))

    # Sort by entity then statement
    claim_lines.sort(key=lambda x: (x[0], x[1]))

    with open(claims_file, "w") as f:
        f.write("# CLAIMS INDEX - One claim per line, grep-friendly\n")
        f.write("# Format: STATEMENT | type | entity: name | doc: path.md | lines: N-M\n")
        f.write(f"# Total: {len(claim_lines)} claims\n")
        f.write("# Usage: grep -i 'dbt' claims.txt  OR  grep -i 'limitation' claims.txt\n")
        f.write("#\n")
        for _, _, line in claim_lines:
            f.write(line + "\n")

    print(f"✓ Exported {len(claim_lines)} claims to {claims_file}")

    return entities_file, claims_file


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python export_yaml_metadata.py <project_name>")
        print("\nExample:")
        print("  python export_yaml_metadata.py motherduck")
        sys.exit(1)

    project_name = sys.argv[1]
    export_yaml_metadata(project_name)


if __name__ == "__main__":
    main()

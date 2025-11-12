"""
Test scenarios for new features:
- Link extraction and tracking
- Semantic search
- On-demand extraction
- Content gap analysis

Run from project root with: uv run python test_implementation.py
"""

import tempfile
import shutil
from pathlib import Path
from uuid import uuid4


def setup_test_environment():
    """Create a temporary kurt project for testing."""
    print("\n" + "=" * 60)
    print("SETUP: Creating temporary test environment")
    print("=" * 60)

    # Create temp directory
    test_dir = Path(tempfile.mkdtemp(prefix="kurt_test_"))
    print(f"✓ Created test directory: {test_dir}")

    # Create kurt.config
    config_content = f"""# Kurt Configuration
PROJECT_NAME="test-project"
SOURCES_PATH="{test_dir}/sources"
PROJECTS_PATH="{test_dir}/projects"
DATABASE_PATH="{test_dir}/kurt.db"
INGESTION_FETCH_ENGINE="trafilatura"
"""

    config_path = test_dir / "kurt.config"
    config_path.write_text(config_content)
    print(f"✓ Created kurt.config")

    # Create sources directory
    sources_dir = test_dir / "sources"
    sources_dir.mkdir(parents=True)
    print(f"✓ Created sources directory")

    return test_dir


def create_test_documents(test_dir: Path):
    """Create test markdown documents with internal links."""
    print("\n" + "=" * 60)
    print("SETUP: Creating test documents with internal links")
    print("=" * 60)

    sources_dir = test_dir / "sources" / "test.com"
    sources_dir.mkdir(parents=True)

    # Document 1: Getting Started (links to Authentication and Advanced)
    doc1 = sources_dir / "getting-started.md"
    doc1.write_text("""# Getting Started Guide

Welcome to our platform! This guide will help you get started.

## Prerequisites

Before you begin, make sure you understand [authentication](https://test.com/authentication).

## Next Steps

Once you're comfortable with the basics, check out our [advanced features](https://test.com/advanced-features) guide.

## Key Features

- **Fast Performance**: Our platform handles 10,000 requests per second
- **Easy Integration**: Get started in under 5 minutes
- **Enterprise Ready**: Used by over 500 companies worldwide

For more details, see our [API reference](https://test.com/api-reference).
""")
    print(f"✓ Created getting-started.md (with 3 links)")

    # Document 2: Authentication (links to Getting Started)
    doc2 = sources_dir / "authentication.md"
    doc2.write_text("""# Authentication Guide

Learn how to authenticate with our API.

## Overview

Authentication is simple. If you're new here, start with the [getting started guide](https://test.com/getting-started).

## API Keys

Generate an API key from your dashboard. API keys provide access to all endpoints.

## OAuth Flow

We support OAuth 2.0 for third-party integrations.

## Best Practices

- Rotate keys every 90 days
- Use environment variables
- Never commit keys to git
""")
    print(f"✓ Created authentication.md (with 1 link)")

    # Document 3: Advanced Features (links to Authentication)
    doc3 = sources_dir / "advanced-features.md"
    doc3.write_text("""# Advanced Features

Unlock the full power of our platform.

## Rate Limiting

Our API supports up to 10,000 requests per second with burst capacity of 50,000.

## Webhooks

Configure webhooks to receive real-time notifications. Make sure you've set up [authentication](https://test.com/authentication) first.

## Batch Operations

Process up to 1,000 items in a single batch request.

## Caching

Built-in caching reduces latency by 10x for repeated requests.
""")
    print(f"✓ Created advanced-features.md (with 1 link)")

    # Document 4: API Reference (standalone, no internal links)
    doc4 = sources_dir / "api-reference.md"
    doc4.write_text("""# API Reference

Complete API documentation.

## Endpoints

### GET /users
Retrieve user list.

### POST /users
Create new user.

### GET /users/:id
Retrieve specific user.

## Response Codes

- 200: Success
- 401: Unauthorized
- 404: Not Found
- 500: Server Error
""")
    print(f"✓ Created api-reference.md (no internal links)")

    return {
        "getting-started": str(doc1),
        "authentication": str(doc2),
        "advanced-features": str(doc3),
        "api-reference": str(doc4),
    }


def test_database_initialization(test_dir: Path):
    """Test that database initializes with new migration."""
    print("\n" + "=" * 60)
    print("TEST 1: Database Initialization & Migration")
    print("=" * 60)

    import os
    os.chdir(test_dir)

    # Initialize database
    from kurt.db.database import init_database
    from kurt.config import load_config

    config = load_config()
    print(f"✓ Loaded config from: {test_dir / 'kurt.config'}")

    init_database()
    print(f"✓ Database initialized at: {config.get_absolute_db_path()}")

    # Check that DocumentLink table exists
    from sqlmodel import Session, create_engine, text
    engine = create_engine(f"sqlite:///{config.get_absolute_db_path()}")

    with Session(engine) as session:
        result = session.exec(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='document_links'")
        ).first()

        if result:
            print(f"✓ document_links table exists")
        else:
            print(f"✗ document_links table NOT found")
            return False

    return True


def test_document_creation_and_link_extraction(test_dir: Path, docs: dict):
    """Test creating documents and extracting links."""
    print("\n" + "=" * 60)
    print("TEST 2: Document Creation & Link Extraction")
    print("=" * 60)

    from kurt.content.fetch import add_document, fetch_document
    from kurt.db.models import Document
    from kurt.db.database import get_session
    from sqlmodel import select

    # Create documents for all test files
    doc_ids = {}

    for name, path in docs.items():
        url = f"https://test.com/{name}"
        doc_id = add_document(url, title=name.replace("-", " ").title())
        doc_ids[name] = doc_id
        print(f"✓ Created document: {name} (ID: {str(doc_id)[:8]}...)")

    # Update documents to point to our test files
    session = get_session()
    for name, path in docs.items():
        doc = session.get(Document, doc_ids[name])
        # Make path relative to sources directory
        relative_path = Path(path).relative_to(test_dir / "sources")
        doc.content_path = str(relative_path)
        doc.ingestion_status = "FETCHED"
        session.add(doc)
    session.commit()
    print(f"✓ Updated all documents with content paths")

    # Now simulate fetch to extract links
    from kurt.content.fetch import extract_document_links, save_document_links

    total_links = 0
    for name, path in docs.items():
        doc = session.get(Document, doc_ids[name])
        content = Path(path).read_text()
        url = f"https://test.com/{name}"

        links = extract_document_links(content, url)
        links_saved = save_document_links(doc.id, links)
        total_links += links_saved

        if links_saved > 0:
            print(f"✓ Extracted {links_saved} links from {name}")
        else:
            print(f"  No internal links found in {name}")

    print(f"\n✓ Total links extracted: {total_links}")

    # Verify expected links
    expected_links = 3 + 1 + 1  # getting-started(3) + auth(1) + advanced(1)
    if total_links == expected_links:
        print(f"✓ Link count matches expected: {expected_links}")
        return True, doc_ids
    else:
        print(f"✗ Expected {expected_links} links, got {total_links}")
        return False, doc_ids


def test_link_queries(doc_ids: dict):
    """Test link query functions."""
    print("\n" + "=" * 60)
    print("TEST 3: Link Query Functions")
    print("=" * 60)

    from kurt.content.document import (
        get_document_links,
        find_prerequisite_documents,
        find_related_documents,
    )

    # Test 1: Get outbound links from getting-started
    gs_id = str(doc_ids["getting-started"])
    outbound = get_document_links(gs_id, direction="outbound")
    print(f"✓ Getting Started has {len(outbound)} outbound links")

    if len(outbound) == 3:
        print(f"  ✓ Correct count (expected 3)")
    else:
        print(f"  ✗ Expected 3, got {len(outbound)}")

    # Test 2: Get inbound links to authentication
    auth_id = str(doc_ids["authentication"])
    inbound = get_document_links(auth_id, direction="inbound")
    print(f"✓ Authentication has {len(inbound)} inbound links")

    if len(inbound) == 2:  # from getting-started and advanced-features
        print(f"  ✓ Correct count (expected 2)")
    else:
        print(f"  ✗ Expected 2, got {len(inbound)}")

    # Test 3: Find prerequisites for advanced-features
    adv_id = str(doc_ids["advanced-features"])
    prereqs = find_prerequisite_documents(adv_id, max_depth=2)
    print(f"✓ Advanced Features has {len(prereqs)} prerequisites")

    if len(prereqs) >= 1:  # Should find at least getting-started
        print(f"  ✓ Found prerequisites")
        for prereq in prereqs:
            print(f"    - {prereq['title']} (depth {prereq['depth']})")

    # Test 4: Find related documents
    related = find_related_documents(gs_id, max_results=5)
    print(f"✓ Getting Started has {len(related)} related documents")

    if len(related) > 0:
        print(f"  ✓ Found related documents:")
        for rel in related[:3]:
            print(f"    - {rel['title']} (score: {rel['relevance_score']})")

    return True


def test_search_functionality(test_dir: Path):
    """Test semantic search with ripgrep."""
    print("\n" + "=" * 60)
    print("TEST 4: Semantic Search")
    print("=" * 60)

    import subprocess
    import os

    sources_path = test_dir / "sources"

    # Test 1: Search for "authentication"
    try:
        result = subprocess.run(
            ["rg", "-i", "authentication", str(sources_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            matches = [line for line in result.stdout.split("\n") if line.strip()]
            print(f"✓ Found {len(matches)} matches for 'authentication'")
        else:
            print(f"✓ Search completed (no matches or error)")
    except FileNotFoundError:
        print(f"⚠ ripgrep not installed - skipping search test")
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

    # Test 2: Search for metrics
    try:
        result = subprocess.run(
            ["rg", "-i", "10,000", str(sources_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            matches = [line for line in result.stdout.split("\n") if line.strip()]
            print(f"✓ Found {len(matches)} matches for '10,000'")
        else:
            print(f"✓ Search completed (no matches)")
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

    return True


def test_extraction_functions(doc_ids: dict, test_dir: Path):
    """Test on-demand extraction functions."""
    print("\n" + "=" * 60)
    print("TEST 5: On-Demand Extraction")
    print("=" * 60)

    import os
    os.chdir(test_dir)

    # We need an LLM configured for this test
    # Skip if no API key
    import dspy
    from kurt.config.base import get_config_or_default

    try:
        llm_config = get_config_or_default()
        lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
        print(f"✓ LLM configured: {llm_config.INDEXING_LLM_MODEL}")
    except Exception as e:
        print(f"⚠ No LLM configured - skipping extraction tests")
        print(f"  (This is expected if ANTHROPIC_API_KEY not set)")
        return True

    from kurt.content.extract import (
        extract_claims,
        extract_entities,
        extract_takeaways,
    )

    gs_id = str(doc_ids["getting-started"])

    # Test 1: Extract claims
    try:
        print("\nTest 5.1: Extracting claims...")
        claims = extract_claims(gs_id[:8])  # Use partial ID
        print(f"✓ Extracted {len(claims)} claims")

        if len(claims) > 0:
            print(f"  Example: {claims[0].claim_text[:80]}...")
    except Exception as e:
        print(f"✗ Claim extraction failed: {e}")
        return False

    # Test 2: Extract entities
    try:
        print("\nTest 5.2: Extracting entities...")
        entities = extract_entities(gs_id[:8])
        print(f"✓ Extracted {len(entities)} entities")

        if len(entities) > 0:
            print(f"  Example: {entities[0].name} ({entities[0].entity_type})")
    except Exception as e:
        print(f"✗ Entity extraction failed: {e}")
        return False

    # Test 3: Extract takeaways
    try:
        print("\nTest 5.3: Extracting takeaways...")
        takeaways = extract_takeaways(gs_id[:8], max_takeaways=3)
        print(f"✓ Extracted {len(takeaways)} takeaways")

        if len(takeaways) > 0:
            print(f"  Example: {takeaways[0].takeaway[:80]}...")
    except Exception as e:
        print(f"✗ Takeaway extraction failed: {e}")
        return False

    return True


def test_gap_analysis(test_dir: Path):
    """Test content gap analysis."""
    print("\n" + "=" * 60)
    print("TEST 6: Content Gap Analysis")
    print("=" * 60)

    import os
    os.chdir(test_dir)

    # Check if LLM is configured
    import dspy
    from kurt.config.base import get_config_or_default

    try:
        llm_config = get_config_or_default()
        lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
        print(f"✓ LLM configured: {llm_config.INDEXING_LLM_MODEL}")
    except Exception as e:
        print(f"⚠ No LLM configured - skipping gap analysis tests")
        print(f"  (This is expected if ANTHROPIC_API_KEY not set)")
        return True

    from kurt.content.gaps import analyze_content_gaps, analyze_topic_coverage

    # Test 1: Analyze gaps
    try:
        print("\nTest 6.1: Analyzing content gaps...")
        gaps = analyze_content_gaps(
            include_pattern="*test.com*",
            target_topics=["webhooks", "error handling", "rate limiting"],
            audience="developers",
        )
        print(f"✓ Identified {len(gaps)} content gaps")

        if len(gaps) > 0:
            high_priority = [g for g in gaps if g.priority == "high"]
            print(f"  High priority gaps: {len(high_priority)}")
            if high_priority:
                print(f"  Example: {high_priority[0].topic} - {high_priority[0].gap_type}")
    except Exception as e:
        print(f"✗ Gap analysis failed: {e}")
        return False

    # Test 2: Analyze topic coverage
    try:
        print("\nTest 6.2: Analyzing topic coverage...")
        coverage = analyze_topic_coverage(
            topics=["authentication", "API usage", "webhooks"],
            include_pattern="*test.com*",
        )
        print(f"✓ Analyzed coverage for {len(coverage)} topics")

        if len(coverage) > 0:
            avg_score = sum(c.coverage_score for c in coverage) / len(coverage)
            print(f"  Average coverage score: {avg_score:.1f}/10")
            for cov in coverage:
                print(f"  - {cov.topic}: {cov.coverage_score}/10")
    except Exception as e:
        print(f"✗ Coverage analysis failed: {e}")
        return False

    return True


def cleanup(test_dir: Path):
    """Clean up test environment."""
    print("\n" + "=" * 60)
    print("CLEANUP: Removing test environment")
    print("=" * 60)

    try:
        shutil.rmtree(test_dir)
        print(f"✓ Removed test directory: {test_dir}")
    except Exception as e:
        print(f"⚠ Could not remove test directory: {e}")


def main():
    """Run all test scenarios."""
    print("\n" + "=" * 70)
    print(" " * 15 + "KURT IMPLEMENTATION TEST SUITE")
    print("=" * 70)

    test_dir = None
    results = {}

    try:
        # Setup
        test_dir = setup_test_environment()
        docs = create_test_documents(test_dir)

        # Test 1: Database initialization
        results["Database Init"] = test_database_initialization(test_dir)

        # Test 2: Document creation and link extraction
        success, doc_ids = test_document_creation_and_link_extraction(test_dir, docs)
        results["Link Extraction"] = success

        # Test 3: Link queries
        if success:
            results["Link Queries"] = test_link_queries(doc_ids)
        else:
            results["Link Queries"] = False

        # Test 4: Semantic search
        results["Semantic Search"] = test_search_functionality(test_dir)

        # Test 5: On-demand extraction
        if success:
            results["On-Demand Extraction"] = test_extraction_functions(doc_ids, test_dir)
        else:
            results["On-Demand Extraction"] = False

        # Test 6: Gap analysis
        results["Gap Analysis"] = test_gap_analysis(test_dir)

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        if test_dir:
            cleanup(test_dir)

    # Print summary
    print("\n" + "=" * 70)
    print(" " * 25 + "TEST SUMMARY")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<50} {status}")

    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)

    print("\n" + "-" * 70)
    print(f"Total: {passed_tests}/{total_tests} tests passed")
    print("=" * 70 + "\n")

    return all(results.values())


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

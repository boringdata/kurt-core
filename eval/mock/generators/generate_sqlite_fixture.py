#!/usr/bin/env python3
"""Generate database fixtures for evaluation scenarios.

This script creates pre-populated Kurt databases that can be copied
into test scenarios for fast setup without fetching/indexing.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_command(cmd: str, cwd: Path, project_root: Path) -> None:
    """Run a shell command and check for errors."""
    print(f"Running: {cmd}")
    # Run from project root to access kurt command
    full_cmd = f"cd {project_root} && cd {cwd} && {cmd}"
    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=True,
        text=True,
        env={**os.environ, "KURT_TELEMETRY_DISABLED": "1"},
    )
    if result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    print(result.stdout)


def generate_acme_docs_fixture():
    """Generate fixture with ACME documentation indexed."""
    print("\n=== Generating acme_docs_indexed fixture ===\n")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        print(f"Working in: {tmppath}")

        # Get project root (assuming we're in eval/fixtures/)
        fixtures_dir = Path(__file__).parent

        # Initialize Kurt project
        run_command("uv run kurt init", tmppath)

        # Fetch and index ACME docs
        run_command(
            "uv run kurt content map url http://docs.acme-corp.com",
            tmppath,
        )
        run_command(
            'uv run kurt content fetch --include "http://docs.acme-corp.com*"',
            tmppath,
        )
        run_command(
            'uv run kurt content index --include "http://docs.acme-corp.com*"',
            tmppath,
        )

        # Verify entities were created
        db_path = tmppath / ".kurt" / "kurt.sqlite"
        if not db_path.exists():
            raise RuntimeError("Database not created!")

        # Count entities using sqlite3
        result = subprocess.run(
            f'sqlite3 {db_path} "SELECT COUNT(*) FROM entities"',
            shell=True,
            capture_output=True,
            text=True,
        )
        entity_count = int(result.stdout.strip())
        print(f"✓ Database created with {entity_count} entities")

        if entity_count < 5:
            raise RuntimeError(f"Expected at least 5 entities, got {entity_count}")

        # Copy database to fixtures directory
        fixture_db = fixtures_dir / "acme_docs_indexed.sqlite"
        shutil.copy(db_path, fixture_db)
        print(f"✓ Saved database fixture: {fixture_db}")

        # Copy sources directory (contains fetched markdown files)
        sources_src = tmppath / "sources"
        sources_dst = fixtures_dir / "sources"
        if sources_dst.exists():
            shutil.rmtree(sources_dst)
        if sources_src.exists():
            shutil.copytree(sources_src, sources_dst)
            print(f"✓ Saved sources fixture: {sources_dst}")

    print("\n✅ Fixture generation complete!\n")


def main():
    """Generate all fixtures."""
    print("Generating evaluation fixtures...")
    print("This may take a few minutes.\n")

    try:
        generate_acme_docs_fixture()
        print("\nAll fixtures generated successfully!")
        print("\nUsage in scenarios:")
        print("  setup_commands:")
        print("    - KURT_TELEMETRY_DISABLED=1 uv run kurt init")
        print("    - cp eval/fixtures/acme_docs_indexed.sqlite .kurt/kurt.sqlite")
        print("    - cp -r eval/fixtures/sources ./sources")
    except Exception as e:
        print(f"\n❌ Error generating fixtures: {e}")
        raise


if __name__ == "__main__":
    main()

"""Status service - business logic for Kurt project status."""

from pathlib import Path
from typing import Dict, List

from kurt.config import load_config
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus


def get_document_counts() -> Dict[str, int]:
    """Get document counts by status."""
    try:
        session = get_session()

        total = session.query(Document).count()
        not_fetched = (
            session.query(Document)
            .filter(Document.ingestion_status == IngestionStatus.NOT_FETCHED)
            .count()
        )
        fetched = (
            session.query(Document)
            .filter(Document.ingestion_status == IngestionStatus.FETCHED)
            .count()
        )
        error = (
            session.query(Document)
            .filter(Document.ingestion_status == IngestionStatus.ERROR)
            .count()
        )

        return {
            "total": total,
            "not_fetched": not_fetched,
            "fetched": fetched,
            "error": error,
        }
    except Exception:
        return {
            "total": 0,
            "not_fetched": 0,
            "fetched": 0,
            "error": 0,
        }


def get_documents_by_domain() -> List[Dict[str, any]]:
    """Get document counts grouped by domain."""
    try:
        from collections import Counter
        from urllib.parse import urlparse

        session = get_session()
        docs = session.query(Document).all()

        domains = []
        for doc in docs:
            if doc.source_url:
                parsed = urlparse(doc.source_url)
                domains.append(parsed.netloc)

        domain_counts = Counter(domains)
        return [{"domain": domain, "count": count} for domain, count in domain_counts.most_common()]
    except Exception:
        return []


def get_cluster_count() -> int:
    """Get total number of topic clusters."""
    try:
        from kurt.db.models import TopicCluster

        session = get_session()
        return session.query(TopicCluster).count()
    except Exception:
        return 0


def get_project_summaries() -> List[Dict[str, str]]:
    """Get summary of all projects."""
    try:
        import re

        config = load_config()
        projects_path = Path(config.PATH_PROJECTS)

        if not projects_path.exists():
            return []

        project_dirs = [d for d in projects_path.iterdir() if d.is_dir()]
        projects = []

        for project_dir in sorted(project_dirs):
            project_name = project_dir.name
            project_md = project_dir / "project.md"

            project_info = {"name": project_name}

            if project_md.exists():
                try:
                    content = project_md.read_text()

                    # Extract title from first H1
                    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
                    if title_match:
                        project_info["title"] = title_match.group(1)

                    # Extract goal - first non-empty line after ## Goal
                    goal_match = re.search(
                        r"^## Goal\s*\n(.+?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL
                    )
                    if goal_match:
                        goal_lines = goal_match.group(1).strip().split("\n")
                        project_info["goal"] = goal_lines[0].strip()

                    # Extract intent
                    intent_match = re.search(
                        r"^## Intent Category\s*\n(.+?)(?=\n##|\Z)",
                        content,
                        re.MULTILINE | re.DOTALL,
                    )
                    if intent_match:
                        intent_lines = intent_match.group(1).strip().split("\n")
                        project_info["intent"] = intent_lines[0].strip()

                except Exception:
                    pass

            projects.append(project_info)

        return projects

    except Exception:
        return []


def check_pending_migrations() -> Dict[str, any]:
    """Check if there are pending database migrations.

    Returns:
        Dict with 'has_pending', 'count', and 'migrations' keys
    """
    try:
        from kurt.db.migrations.utils import (
            check_migrations_needed,
            get_pending_migrations,
        )

        has_pending = check_migrations_needed()
        if has_pending:
            pending = get_pending_migrations()
            return {
                "has_pending": True,
                "count": len(pending),
                "migrations": [m["name"] for m in pending],
            }

        return {"has_pending": False, "count": 0, "migrations": []}
    except ImportError:
        # Migration system not available
        return {"has_pending": False, "count": 0, "migrations": []}
    except Exception:
        # Error checking migrations
        return {"has_pending": False, "count": 0, "migrations": []}


def is_kurt_plugin_installed() -> bool:
    """Check if Kurt plugin is installed in Claude Code."""
    try:
        import subprocess

        # Check using claude CLI command
        result = subprocess.run(
            ["claude", "plugin", "marketplace", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Check if "kurt" appears in the marketplace list
            return "kurt" in result.stdout.lower()

        return False
    except FileNotFoundError:
        # Claude Code CLI not installed
        return False
    except Exception:
        # Claude Code might not be installed or accessible
        return False


def generate_status_markdown() -> str:
    """Generate status output as markdown string."""
    output_lines = []

    # Header
    output_lines.append("# Kurt Project Status\n")

    # Initialization status
    output_lines.append("✓ **Kurt project initialized**")
    output_lines.append("- Config: `kurt.config` found")
    output_lines.append("- Database: `.kurt/kurt.sqlite` exists")

    # Check for pending migrations
    migration_status = check_pending_migrations()
    if migration_status["has_pending"]:
        output_lines.append(f"\n⚠ **{migration_status['count']} pending database migration(s)**")
        output_lines.append("- Run: `kurt migrate apply` to update the database")
        for migration_name in migration_status["migrations"]:
            output_lines.append(f"  - `{migration_name}`")
    output_lines.append("")

    # Claude Code plugin status
    plugin_installed = is_kurt_plugin_installed()
    output_lines.append("## Claude Code Integration")
    if plugin_installed:
        output_lines.append("✓ **Kurt plugin installed**")
        output_lines.append("- Claude Code can interact with Kurt")
        output_lines.append(
            "- **Agent: Check if you can see `/create-project` command in your available commands**\n"
        )
    else:
        output_lines.append("⚠ **Kurt plugin not detected**")
        output_lines.append("- Install from Claude Code plugin marketplace")
        output_lines.append("- Use `/plugin` command in Claude Code\n")

    # Documents
    doc_counts = get_document_counts()
    domains = get_documents_by_domain()

    output_lines.append("## Documents")
    if doc_counts["total"] > 0:
        output_lines.append(f"**Total documents ingested: {doc_counts['total']}**\n")

        if domains:
            output_lines.append("Documents by source:")
            for domain_info in domains[:10]:
                output_lines.append(
                    f"- `{domain_info['domain']}`: {domain_info['count']} documents"
                )
            if len(domains) > 10:
                output_lines.append(f"... and {len(domains) - 10} more sources")
            output_lines.append("")
    else:
        output_lines.append("⚠ **No documents ingested yet**")
        output_lines.append("- Run: `kurt content add <url>` to add content\n")

    # Clusters
    cluster_count = get_cluster_count()
    output_lines.append("## Topic Clusters")
    if cluster_count > 0:
        output_lines.append(f"**{cluster_count} topic clusters computed**")
        output_lines.append("- View with: `kurt content cluster --url-starts-with <url>`\n")
    else:
        if doc_counts["total"] > 0:
            output_lines.append("⚠ **No clusters computed yet**")
            output_lines.append(
                "- Run: `kurt content cluster --url-starts-with <url>` to analyze content\n"
            )
        else:
            output_lines.append("No clusters (no documents to analyze)\n")

    # Projects
    projects = get_project_summaries()
    output_lines.append("## Projects")
    if projects:
        output_lines.append(f"**Found {len(projects)} project(s):**\n")

        for proj in projects:
            output_lines.append(f"### `{proj['name']}`")
            if proj.get("title"):
                output_lines.append(f"**{proj['title']}**")
            if proj.get("goal"):
                output_lines.append(f"- Goal: {proj['goal']}")
            if proj.get("intent"):
                output_lines.append(f"- Intent: {proj['intent']}")
            output_lines.append("")
    else:
        output_lines.append("⚠ **No projects created yet**")
        output_lines.append("- Create a project manually in the `projects/` directory\n")

    # Recommendations
    output_lines.append("---\n")
    output_lines.append("## Recommended Next Steps\n")

    if projects:
        output_lines.append("**You have existing projects.** Would you like to:")
        output_lines.append("- View project status: `kurt project status`")
        output_lines.append("- Add more content: `kurt content add <url>`")
    elif doc_counts["total"] > 0 and cluster_count > 0:
        output_lines.append("**Content ingested and analyzed.** Consider:")
        output_lines.append("- Create a project in the `projects/` directory")
        output_lines.append("- View documents: `kurt content list`")
    elif doc_counts["total"] > 0:
        output_lines.append("**Content ingested but not analyzed.** Next:")
        output_lines.append(
            "- Run: `kurt content cluster --url-starts-with <url>` to discover topics"
        )
    else:
        output_lines.append("**Ready to start!** Choose an approach:")
        output_lines.append("- Add content: `kurt content add <url>`")
        output_lines.append("- Initialize: `kurt init` (if needed)")

    return "\n".join(output_lines)

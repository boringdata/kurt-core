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
    except RuntimeError:
        # Re-raise RuntimeError with specific database access issues
        raise
    except Exception as e:
        # Log the actual error for debugging
        import logging

        logging.debug(f"Error getting document counts: {e}")
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
    except RuntimeError:
        # Re-raise RuntimeError with specific database access issues
        raise
    except Exception as e:
        # Log the actual error for debugging
        import logging

        logging.debug(f"Error getting documents by domain: {e}")
        return []


def get_cluster_count() -> int:
    """Get total number of topic clusters."""
    try:
        from kurt.db.models import TopicCluster

        session = get_session()
        return session.query(TopicCluster).count()
    except RuntimeError:
        # Re-raise RuntimeError with specific database access issues
        raise
    except Exception as e:
        # Log the actual error for debugging
        import logging

        logging.debug(f"Error getting cluster count: {e}")
        return 0


def profile_exists() -> bool:
    """Check if a profile exists in .kurt/profile.md."""
    try:
        config = load_config()
        # Get the .kurt directory (parent of database file)
        kurt_dir = config.get_db_directory()
        profile_path = kurt_dir / "profile.md"
        return profile_path.exists()
    except Exception:
        return False


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


def get_stale_analytics_domains(threshold_days: int = 7) -> List[Dict[str, any]]:
    """Get analytics domains with stale data (not synced recently).

    Args:
        threshold_days: Number of days after which analytics are considered stale

    Returns:
        List of dicts with domain, platform, and days_since_sync
    """
    try:
        from datetime import datetime

        from kurt.db.models import AnalyticsDomain

        session = get_session()
        domains = session.query(AnalyticsDomain).all()

        if not domains:
            return []

        stale_domains = []
        for domain in domains:
            if domain.last_synced_at:
                days_since_sync = (datetime.utcnow() - domain.last_synced_at).days
                if days_since_sync > threshold_days:
                    stale_domains.append(
                        {
                            "domain": domain.domain,
                            "platform": domain.platform,
                            "days_since_sync": days_since_sync,
                        }
                    )
            else:
                # Never synced
                stale_domains.append(
                    {
                        "domain": domain.domain,
                        "platform": domain.platform,
                        "days_since_sync": None,
                    }
                )

        return stale_domains
    except Exception:
        return []


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
        output_lines.append("- Run: `kurt admin migrate apply` to update the database")
        for migration_name in migration_status["migrations"]:
            output_lines.append(f"  - `{migration_name}`")
    output_lines.append("")

    # Claude Code plugin status
    plugin_installed = is_kurt_plugin_installed()
    output_lines.append("## Claude Code Integration")
    if plugin_installed:
        output_lines.append("✓ **Kurt plugin installed**")
        output_lines.append("- Claude Code can interact with Kurt")
        output_lines.append("- Resume projects by @ mentioning their `project.md` file\n")
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
        output_lines.append("- Run: `kurt content fetch <url>` to add content\n")

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
        output_lines.append("- Describe your content goals to Claude Code to create a project\n")

    # Analytics
    stale_analytics = get_stale_analytics_domains(threshold_days=7)
    if stale_analytics:
        output_lines.append("## Analytics")
        output_lines.append(f"📊 **{len(stale_analytics)} domain(s) have stale analytics data:**\n")

        for domain_info in stale_analytics:
            if domain_info["days_since_sync"] is None:
                output_lines.append(f"- `{domain_info['domain']}`: Never synced")
            else:
                output_lines.append(
                    f"- `{domain_info['domain']}`: {domain_info['days_since_sync']} days old"
                )

        output_lines.append("\n*Sync analytics for accurate content prioritization:*")
        output_lines.append("- Sync specific domain: `kurt integrations analytics sync <domain>`\n")

    # Recommendations - prioritize Claude Code slash commands
    output_lines.append("---\n")
    output_lines.append("## Recommended Next Steps\n")

    # Check for profile and guide to proper onboarding flow
    has_profile = profile_exists()

    if not has_profile:
        # No profile - guide to onboarding
        output_lines.append("🎯 **Start your Kurt journey:**")
        output_lines.append(
            "- Describe your organization and content goals to Claude Code to create a profile\n"
        )
    elif not projects:
        # Profile exists but no projects - guide to project creation
        output_lines.append("✓ **Profile created!** Ready to start a content project:")
        output_lines.append("- Describe your content goals to Claude Code to create a project\n")
    else:
        # Has projects - guide to resuming work
        output_lines.append("📝 **You have active projects.** Continue your work:")
        output_lines.append(
            "- Resume a project by @ mentioning its `project.md` file in Claude Code\n"
        )

        # Add content management suggestions if needed
        if doc_counts["total"] == 0:
            output_lines.append("\n💡 **Tip:** Add content sources to enrich your projects:")
            output_lines.append("- Run: `kurt content fetch <url>`")
        elif stale_analytics:
            output_lines.append("\n💡 **Tip:** Sync analytics for data-driven content decisions:")
            output_lines.append("- Run: `kurt integrations analytics sync <domain>`")

    return "\n".join(output_lines)

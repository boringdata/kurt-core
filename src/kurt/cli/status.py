"""Kurt status command - comprehensive project status."""

from __future__ import annotations

import json
import os

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    help="Output format",
)
@click.option(
    "--hook-cc",
    is_flag=True,
    help="Output in Claude Code hook format",
)
@track_command
def status(output_format: str, hook_cc: bool):
    """
    Show comprehensive Kurt project status.

    Displays initialization status, document counts, and project summaries.

    Examples:
        kurt status
        kurt status --format json
        kurt status --hook-cc
    """
    from kurt.config import config_file_exists, load_config

    # Check if Kurt is initialized
    if not config_file_exists():
        if hook_cc:
            _auto_init_hook()
            return

        message = "Kurt project not initialized. Run: kurt init"
        if output_format == "json":
            print(json.dumps({"initialized": False, "message": message}, indent=2))
        else:
            console.print(f"[yellow]{message}[/yellow]")
        return

    try:
        config = load_config()
        db_path = config.PATH_DB

        # Check if database exists
        if not os.path.exists(db_path):
            if hook_cc:
                _init_database_hook()
                return

            message = "Database not found. Run: kurt init"
            if output_format == "json":
                print(
                    json.dumps(
                        {"initialized": False, "config_exists": True, "database_exists": False},
                        indent=2,
                    )
                )
            else:
                console.print(f"[yellow]{message}[/yellow]")
            return

        # Hook mode: auto-apply migrations + generate status
        if hook_cc:
            _handle_hook_output()
            return

        # Check for pending migrations
        migration_info = _check_pending_migrations()

        # Get status data
        status_data = _get_status_data()
        status_data["migrations"] = migration_info

        if output_format == "json":
            print(json.dumps(status_data, indent=2, default=str))
        else:
            _print_pretty_status(status_data, migration_info)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if os.environ.get("KURT_DEBUG"):
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


def _auto_init_hook():
    """Auto-initialize Kurt in hook mode."""
    from kurt.config import create_config
    from kurt.db import init_database

    create_config()
    init_database()

    output = {
        "systemMessage": "Kurt project initialized!",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "**Kurt initialized**\n\n"
                "- Configuration: `kurt.config`\n"
                "- Database: `.kurt/kurt.sqlite`\n\n"
                "Get started: `kurt content fetch <url>`"
            ),
        },
    }
    print(json.dumps(output, indent=2))


def _init_database_hook():
    """Initialize database in hook mode."""
    from kurt.db import init_database

    init_database()

    output = {
        "systemMessage": "Database initialized!",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "Database created at `.kurt/kurt.sqlite`",
        },
    }
    print(json.dumps(output, indent=2))


def _handle_hook_output():
    """Generate hook-compatible output with status."""
    status_data = _get_status_data()

    # Build user-facing summary
    doc_counts = status_data.get("documents", {})
    total_docs = doc_counts.get("total", 0)

    status_parts = ["**Kurt Status:**", f"Documents: {total_docs}"]

    user_message = " | ".join(status_parts)

    # Build detailed markdown
    markdown = _generate_status_markdown(status_data)

    output = {
        "systemMessage": user_message,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": markdown,
        },
    }
    print(json.dumps(output, indent=2))


class BaseStatusRepository:
    """Base class for status queries - abstracts SQL vs Cloud differences."""

    def __init__(self, session):
        self._session = session

    def count_total_documents(self) -> int:
        """Count total documents in map table."""
        raise NotImplementedError

    def count_fetched_documents(self) -> int:
        """Count successfully fetched documents."""
        raise NotImplementedError

    def count_error_documents(self) -> int:
        """Count documents with fetch errors."""
        raise NotImplementedError

    def get_all_source_urls(self, limit: int = 10000) -> list[str]:
        """Get all source URLs for domain distribution."""
        raise NotImplementedError


class SQLStatusRepository(BaseStatusRepository):
    """Status repository for SQLite/PostgreSQL using SQLAlchemy."""

    def count_total_documents(self) -> int:
        from sqlmodel import func, select

        from kurt.workflows.map.models import MapDocument

        return self._session.exec(select(func.count()).select_from(MapDocument)).one()

    def count_fetched_documents(self) -> int:
        from sqlmodel import func, select

        from kurt.workflows.fetch.models import FetchDocument, FetchStatus

        return self._session.exec(
            select(func.count())
            .select_from(FetchDocument)
            .where(FetchDocument.status == FetchStatus.SUCCESS)
        ).one()

    def count_error_documents(self) -> int:
        from sqlmodel import func, select

        from kurt.workflows.fetch.models import FetchDocument, FetchStatus

        return self._session.exec(
            select(func.count())
            .select_from(FetchDocument)
            .where(FetchDocument.status == FetchStatus.ERROR)
        ).one()

    def get_all_source_urls(self, limit: int = 10000) -> list[str]:
        from sqlmodel import select

        from kurt.workflows.map.models import MapDocument

        return self._session.exec(select(MapDocument.source_url).limit(limit)).all()


class CloudStatusRepository(BaseStatusRepository):
    """Status repository for PostgREST/Supabase cloud mode."""

    def count_total_documents(self) -> int:
        # Direct PostgREST count call
        return self._session._client.count("map_documents")

    def count_fetched_documents(self) -> int:
        from kurt.workflows.fetch.models import FetchStatus

        return self._session._client.count("fetch_documents", {"status": FetchStatus.SUCCESS.value})

    def count_error_documents(self) -> int:
        from kurt.workflows.fetch.models import FetchStatus

        return self._session._client.count("fetch_documents", {"status": FetchStatus.ERROR.value})

    def get_all_source_urls(self, limit: int = 10000) -> list[str]:
        rows = self._session._client.select("map_documents", columns="source_url", limit=limit)
        return [row["source_url"] for row in rows if "source_url" in row and row["source_url"]]


def _get_status_repository(session) -> BaseStatusRepository:
    """Factory to get the right repository based on session type."""
    from kurt.db.cloud import SupabaseSession

    if isinstance(session, SupabaseSession):
        return CloudStatusRepository(session)
    else:
        return SQLStatusRepository(session)


def _get_status_data() -> dict:
    """Gather all status information."""
    from urllib.parse import urlparse

    from kurt.db import managed_session

    with managed_session() as session:
        repo = _get_status_repository(session)

        # Get counts
        total = repo.count_total_documents()
        fetched = repo.count_fetched_documents()
        error = repo.count_error_documents()
        not_fetched = total - fetched - error

        # Documents by domain
        urls = repo.get_all_source_urls()
        domains: dict[str, int] = {}
        for url in urls:
            if url:
                try:
                    domain = urlparse(url).netloc
                    domains[domain] = domains.get(domain, 0) + 1
                except Exception:
                    pass

    return {
        "initialized": True,
        "documents": {
            "total": total,
            "by_status": {
                "fetched": fetched,
                "not_fetched": not_fetched,
                "error": error,
            },
            "by_domain": domains,
        },
    }


def _generate_status_markdown(data: dict) -> str:
    """Generate markdown summary of status."""
    lines = ["# Kurt Status", ""]

    docs = data.get("documents", {})
    lines.append(f"## Documents: {docs.get('total', 0)}")
    lines.append("")

    by_status = docs.get("by_status", {})
    lines.append(f"- Fetched: {by_status.get('fetched', 0)}")
    lines.append(f"- Not fetched: {by_status.get('not_fetched', 0)}")
    lines.append(f"- Error: {by_status.get('error', 0)}")

    by_domain = docs.get("by_domain", {})
    if by_domain:
        lines.append("")
        lines.append("## By Domain")
        lines.append("")
        for domain, count in sorted(by_domain.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"- {domain}: {count}")

    return "\n".join(lines)


def _check_pending_migrations() -> dict:
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
                "migrations": [revision_id for revision_id, _ in pending],
            }

        return {"has_pending": False, "count": 0, "migrations": []}
    except ImportError:
        return {"has_pending": False, "count": 0, "migrations": []}
    except Exception:
        return {"has_pending": False, "count": 0, "migrations": []}


def _print_pretty_status(data: dict, migration_info: dict):
    """Print status in human-readable format."""
    from rich.markdown import Markdown

    # Show migration warning first if needed
    if migration_info.get("has_pending"):
        console.print()
        console.print(f"[yellow]⚠ {migration_info['count']} pending database migration(s)[/yellow]")
        console.print("[dim]Run: `kurt admin migrate apply` to update the database[/dim]")
        for migration_name in migration_info.get("migrations", []):
            console.print(f"[dim]  - {migration_name}[/dim]")
        console.print()

    markdown = _generate_status_markdown(data)
    console.print(Markdown(markdown))

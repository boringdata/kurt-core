"""Kurt status command - comprehensive project status."""

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.status import (
    check_pending_migrations,
    generate_status_markdown,
    get_cluster_count,
    get_document_counts,
    get_documents_by_domain,
    get_project_summaries,
    is_kurt_plugin_installed,
    profile_exists,
)
from kurt.admin.telemetry.decorators import track_command
from kurt.config import config_exists, load_config

console = Console()


# ============================================================================
# Status Command
# ============================================================================


@click.command()
@click.option(
    "--format",
    type=click.Choice(["pretty", "json"], case_sensitive=False),
    default="pretty",
    help="Output format",
)
@click.option(
    "--hook-cc",
    is_flag=True,
    help="Output in Claude Code hook format (systemMessage + additionalContext)",
)
@track_command
def status(format: str, hook_cc: bool):
    """
    Show comprehensive Kurt project status.

    Displays:
    - Initialization status
    - Document counts and sources
    - Topic clusters
    - Project summaries
    - Recommended next steps

    Examples:
        kurt status
        kurt status --format json
        kurt status --hook-cc  # For Claude Code hooks
    """
    # Check if Kurt is initialized
    if not config_exists():
        # Auto-initialize when using --hook-cc flag
        if hook_cc:
            from kurt.config import create_config
            from kurt.db.database import init_database

            # Step 1: Create configuration
            config = create_config()

            # Step 2: Initialize database
            init_database()

            # Step 3: Apply migrations (if available)
            try:
                from kurt.db.migrations.utils import apply_migrations

                apply_migrations(auto_confirm=True)
            except Exception:
                pass  # Continue if migrations fail

            # Generate success message
            message = (
                "✨ **Kurt project initialized automatically**\n\n"
                "Created:\n"
                "- Configuration file: `kurt.config`\n"
                "- Database: `.kurt/kurt.sqlite`\n"
                "- Directories: `sources/`, `projects/`, `rules/`\n\n"
                "🎯 **Get started:**\n"
                "- Add content sources: `kurt content fetch <url>`\n"
                "- Or explore Kurt commands: `kurt --help`"
            )
            output = {
                "systemMessage": "✨ Kurt project initialized! Explore commands with `kurt --help`.",
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": message,
                },
            }
            print(json.dumps(output, indent=2))
            return

        # Non-hook mode: show manual init message
        message = (
            "⚠ **Kurt project not initialized**\n\n"
            "You need to initialize Kurt before using it.\n\n"
            "Run: `kurt init`"
        )

        if format == "json":
            output = {
                "initialized": False,
                "message": message,
            }
            print(json.dumps(output, indent=2))
        else:
            console.print(f"[yellow]{message}[/yellow]")
        return

    try:
        config = load_config()
        db_path = Path(config.PATH_DB)

        # Check if database exists
        if not db_path.exists():
            # Auto-initialize database when using --hook-cc flag
            if hook_cc:
                from kurt.db.database import init_database

                # Initialize database
                init_database()

                # Apply migrations (if available)
                try:
                    from kurt.db.migrations.utils import apply_migrations

                    apply_migrations(auto_confirm=True)
                except Exception:
                    pass  # Continue if migrations fail

                # Generate success message
                message = (
                    "✨ **Database initialized automatically**\n\n"
                    "Created:\n"
                    "- Database: `.kurt/kurt.sqlite`\n\n"
                    "🎯 **Get started:**\n"
                    "- Add content sources: `kurt content fetch <url>`\n"
                    "- Or explore Kurt commands: `kurt --help`"
                )
                user_msg = "✨ Database initialized! Explore commands with `kurt --help`."
                output = {
                    "systemMessage": user_msg,
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": message,
                    },
                }
                print(json.dumps(output, indent=2))
                return

            # Non-hook mode: show manual init message
            message = (
                "⚠ **Kurt project not fully initialized**\n\n"
                "Config exists but database missing.\n\n"
                "Run: `kurt init`"
            )

            if format == "json":
                output = {
                    "initialized": False,
                    "config_exists": True,
                    "database_exists": False,
                    "message": message,
                }
                print(json.dumps(output, indent=2))
            else:
                console.print(f"[yellow]{message}[/yellow]")
            return

        # Handle --hook-cc flag: auto-apply migrations + generate status
        if hook_cc:
            # Auto-apply any pending migrations
            try:
                migration_status = check_pending_migrations()
                if migration_status["has_pending"]:
                    from kurt.db.migrations.utils import apply_migrations

                    apply_migrations(auto_confirm=True)
            except Exception:
                pass  # Continue if migration check/apply fails

            # Generate status markdown
            markdown_output = generate_status_markdown()

            # Create user-facing summary message
            doc_counts = get_document_counts()
            projects = get_project_summaries()
            has_profile = profile_exists()

            # Build concise status message for user
            status_parts = []
            status_parts.append("**Kurt Status:**")
            status_parts.append(f"📄 Documents: {doc_counts['total']}")
            status_parts.append(f"📁 Projects: {len(projects)}")
            if has_profile:
                status_parts.append("✓ Profile configured")

            user_message = " | ".join(status_parts)

            hook_output = {
                "systemMessage": user_message,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": markdown_output,
                },
            }
            print(json.dumps(hook_output, indent=2))
            return

        if format == "json":
            # Gather all status information for JSON output
            doc_counts = get_document_counts()
            domains = get_documents_by_domain()
            cluster_count = get_cluster_count()
            projects = get_project_summaries()
            migration_status = check_pending_migrations()
            output = {
                "initialized": True,
                "config_exists": True,
                "database_exists": True,
                "database_path": str(db_path),
                "migrations": {
                    "has_pending": migration_status["has_pending"],
                    "count": migration_status["count"],
                    "pending": migration_status["migrations"],
                },
                "claude_code_integration": {
                    "plugin_installed": is_kurt_plugin_installed(),
                },
                "documents": {
                    "total": doc_counts["total"],
                    "by_status": {
                        "not_fetched": doc_counts["not_fetched"],
                        "fetched": doc_counts["fetched"],
                        "error": doc_counts["error"],
                    },
                    "by_domain": domains,
                },
                "clusters": {
                    "total": cluster_count,
                },
                "projects": {
                    "total": len(projects),
                    "list": projects,
                },
            }
            print(json.dumps(output, indent=2))
        else:
            # Pretty format - use service layer to generate markdown, then render with Rich
            from rich.markdown import Markdown

            markdown_output = generate_status_markdown()
            console.print(Markdown(markdown_output))

    except RuntimeError as e:
        # Display user-friendly error message for known database issues
        console.print(f"[red]Database Error:[/red] {e}")

        # Provide helpful suggestions based on error type
        error_msg = str(e)
        if "Database file does not exist" in error_msg:
            console.print(
                "\n[yellow]Suggestion:[/yellow] Run 'kurt init' to initialize the project"
            )
        elif "permission denied" in error_msg:
            console.print("\n[yellow]Suggestion:[/yellow] Check file/directory permissions")
        elif "Database is locked" in error_msg:
            console.print("\n[yellow]Suggestion:[/yellow] Wait for other operations to complete")
        elif "disk I/O error" in error_msg:
            console.print("\n[yellow]Suggestion:[/yellow] Check disk space and file system")

        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Unexpected Error:[/red] {e}")
        import traceback

        # Only show traceback in verbose mode or when debugging
        if "--debug" in sys.argv or os.environ.get("KURT_DEBUG"):
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        else:
            console.print("[dim]Use --debug flag for more details[/dim]")
        raise click.Abort()

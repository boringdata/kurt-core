"""Database management CLI commands.

Provides commands for:
- Exporting local SQLite data to JSON
- Importing data into PostgreSQL (with tenant context)
- Checking database status
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


# Tables to export/import (in dependency order)
MIGRATABLE_TABLES = [
    "map_documents",
    "fetch_documents",
    "research_documents",
    "monitoring_signals",
]

# Optional tables (can be large)
OPTIONAL_TABLES = [
    "llm_traces",
]


@click.group(name="db")
def db_group():
    """Database management commands."""
    pass


@db_group.command(name="export")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (default: kurt-export-{timestamp}.json)",
)
@click.option(
    "--include-traces",
    is_flag=True,
    default=False,
    help="Include LLM traces (can be large)",
)
@click.option(
    "--pretty",
    is_flag=True,
    default=False,
    help="Pretty-print JSON output",
)
def export_cmd(output: Optional[str], include_traces: bool, pretty: bool):
    """Export local SQLite database to JSON.

    Exports all documents and metadata from the local SQLite database
    to a JSON file that can be imported into PostgreSQL.

    Example:
        kurt db export
        kurt db export -o my-backup.json --include-traces
    """
    from sqlalchemy import text

    from kurt.db import get_mode, managed_session

    # Check we're in SQLite mode
    mode = get_mode()
    if mode != "sqlite":
        console.print("[red]Error: Export only works in local SQLite mode[/red]")
        console.print(f"[dim]Current mode: {mode}[/dim]")
        raise click.Abort()

    # Generate output filename
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"kurt-export-{timestamp}.json"

    output_path = Path(output)

    tables_to_export = MIGRATABLE_TABLES.copy()
    if include_traces:
        tables_to_export.extend(OPTIONAL_TABLES)

    export_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "tables": {},
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting...", total=len(tables_to_export))

        with managed_session() as session:
            for table_name in tables_to_export:
                progress.update(task, description=f"Exporting {table_name}...")

                try:
                    # Get all rows from the table
                    result = session.execute(text(f"SELECT * FROM {table_name}"))
                    columns = result.keys()
                    rows = result.fetchall()

                    # Convert to list of dicts
                    records = []
                    for row in rows:
                        record = {}
                        for col, val in zip(columns, row):
                            # Handle special types
                            if isinstance(val, datetime):
                                val = val.isoformat()
                            elif isinstance(val, bytes):
                                # Skip binary data like embeddings
                                continue
                            record[col] = val
                        records.append(record)

                    export_data["tables"][table_name] = {
                        "count": len(records),
                        "records": records,
                    }

                except Exception as e:
                    console.print(f"[yellow]Warning: Could not export {table_name}: {e}[/yellow]")

                progress.advance(task)

    # Write to file
    indent = 2 if pretty else None
    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=indent, default=str)

    # Summary
    console.print()
    console.print(f"[green]✓ Exported to {output_path}[/green]")
    console.print()

    table = Table(title="Export Summary")
    table.add_column("Table", style="cyan")
    table.add_column("Records", justify="right")

    total = 0
    for table_name, data in export_data["tables"].items():
        table.add_row(table_name, str(data["count"]))
        total += data["count"]

    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)


@db_group.command(name="import")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--workspace-id",
    "-w",
    type=str,
    required=True,
    help="Target workspace ID for imported data",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be imported without making changes",
)
@click.option(
    "--skip-duplicates",
    is_flag=True,
    default=True,
    help="Skip records that already exist (default: true)",
)
def import_cmd(
    input_file: str,
    workspace_id: str,
    dry_run: bool,
    skip_duplicates: bool,
):
    """Import data from JSON export into PostgreSQL.

    Imports data exported with 'kurt db export' into the current
    database, tagged with the specified workspace ID.

    Kurt Cloud API import (DATABASE_URL="kurt") is not supported.
    Use a direct PostgreSQL connection instead.

    For local PostgreSQL:
    - DATABASE_URL pointing to PostgreSQL
    - DATABASE_URL="kurt" in kurt.config
    - Valid authentication (kurt cloud login)

    Example:
        kurt db import kurt-export.json --workspace-id ws-123
    """
    from kurt.db import get_mode, get_user_id, is_cloud_mode, set_workspace_context

    # Check database mode
    mode = get_mode()
    if mode == "sqlite":
        console.print("[red]Error: Import requires PostgreSQL or cloud database[/red]")
        console.print("[dim]Set DATABASE_URL to PostgreSQL or 'kurt' for cloud mode[/dim]")
        raise click.Abort()

    # Load credentials for user_id
    from kurt.db.tenant import load_context_from_credentials

    if not load_context_from_credentials():
        console.print("[red]Error: Not logged in[/red]")
        console.print("[dim]Run 'kurt cloud login' first[/dim]")
        raise click.Abort()

    user_id = get_user_id()
    if not user_id:
        console.print("[red]Error: Could not determine user ID[/red]")
        raise click.Abort()

    # Load export file
    with open(input_file) as f:
        export_data = json.load(f)

    console.print(f"[dim]Export version: {export_data.get('version', 'unknown')}[/dim]")
    console.print(f"[dim]Exported at: {export_data.get('exported_at', 'unknown')}[/dim]")
    console.print(f"[dim]Mode: {mode}[/dim]")
    console.print()

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
        console.print()

    # Set workspace context for import
    set_workspace_context(workspace_id=workspace_id, user_id=user_id)

    results = {}

    # Use different import strategies based on mode
    cloud_mode = is_cloud_mode()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        tables = export_data.get("tables", {})
        task = progress.add_task("Importing...", total=len(tables))

        for table_name, table_data in tables.items():
            progress.update(task, description=f"Importing {table_name}...")

            records = table_data.get("records", [])
            imported = 0
            skipped = 0
            errors = 0

            if not dry_run:
                if cloud_mode:
                    # Cloud mode no longer uses PostgREST - use direct PostgreSQL connection
                    console.print(
                        "[red]Error: Cloud mode (DATABASE_URL='kurt') is not supported for import.[/red]"
                    )
                    console.print("\n[dim]To import data into Kurt Cloud:[/dim]")
                    console.print("[dim]1. Set DATABASE_URL to direct PostgreSQL connection[/dim]")
                    console.print("[dim]2. Re-run this command[/dim]")
                    raise click.Abort()
                else:
                    # PostgreSQL mode: use raw SQL
                    imported, skipped, errors = _import_via_sql(
                        table_name, records, workspace_id, user_id, skip_duplicates
                    )
            else:
                imported = len(records)

            results[table_name] = {"imported": imported, "skipped": skipped, "errors": errors}
            progress.advance(task)

    # Summary
    console.print()
    if dry_run:
        console.print("[yellow]DRY RUN - Would import:[/yellow]")
    else:
        console.print("[green]✓ Import complete[/green]")
    console.print()

    table = Table(title="Import Summary")
    table.add_column("Table", style="cyan")
    table.add_column("Imported", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_column("Errors", justify="right", style="red")

    total_imported = 0
    total_skipped = 0
    total_errors = 0
    for table_name, counts in results.items():
        table.add_row(
            table_name,
            str(counts["imported"]),
            str(counts["skipped"]),
            str(counts.get("errors", 0)),
        )
        total_imported += counts["imported"]
        total_skipped += counts["skipped"]
        total_errors += counts.get("errors", 0)

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_imported}[/bold]",
        f"[bold]{total_skipped}[/bold]",
        f"[bold]{total_errors}[/bold]",
    )
    console.print(table)

    console.print()
    console.print(f"[dim]Data imported to workspace: {workspace_id}[/dim]")
    console.print(f"[dim]User ID: {user_id}[/dim]")


def _import_via_sql(
    table_name: str,
    records: list[dict],
    workspace_id: str,
    user_id: str,
    skip_duplicates: bool,
) -> tuple[int, int, int]:
    """Import records via raw SQL (PostgreSQL mode).

    Returns (imported, skipped, errors) counts.
    """
    from sqlalchemy import text

    from kurt.db import managed_session

    imported = 0
    skipped = 0
    errors = 0

    with managed_session() as session:
        for record in records:
            try:
                # Add tenant fields
                record["user_id"] = user_id
                record["workspace_id"] = workspace_id

                # Build INSERT statement
                columns = list(record.keys())
                placeholders = [f":{col}" for col in columns]

                sql = f"""
                    INSERT INTO {table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT DO NOTHING
                """

                result = session.execute(text(sql), record)
                if result.rowcount > 0:
                    imported += 1
                else:
                    skipped += 1

            except Exception as e:
                if skip_duplicates:
                    skipped += 1
                else:
                    console.print(f"[red]Error importing record: {e}[/red]")
                    errors += 1

    return imported, skipped, errors


@db_group.command(name="status")
def status_cmd():
    """Show database status and mode.

    Displays:
    - Current operating mode (sqlite, postgres, kurt-cloud)
    - Database connection info
    - Table counts
    """
    from sqlalchemy import text

    from kurt.db import (
        KurtCloudAuthError,
        get_database_client,
        get_mode,
        is_cloud_mode,
        is_postgres,
        managed_session,
    )

    # Try to get database client first (validates cloud auth if DATABASE_URL="kurt")
    try:
        get_database_client()
    except KurtCloudAuthError as e:
        console.print()
        console.print(f"[red]✗ {e}[/red]")
        console.print()
        console.print('[dim]DATABASE_URL="kurt" requires authentication.[/dim]')
        raise click.Abort()

    mode = get_mode()

    console.print()
    console.print("[bold]Database Status[/bold]")
    console.print()

    # Mode info
    mode_colors = {
        "sqlite": "blue",
        "postgres": "yellow",
        "kurt-cloud": "green",
    }
    color = mode_colors.get(mode, "white")
    console.print(f"Mode: [{color}]{mode}[/{color}]")
    console.print(f"PostgreSQL: {'Yes' if is_postgres() else 'No'}")
    console.print(f"Cloud Mode: {'Yes' if is_cloud_mode() else 'No'}")

    if is_postgres():
        db_url = os.environ.get("DATABASE_URL", "")
        # Mask password
        if "@" in db_url:
            parts = db_url.split("@")
            host_part = parts[-1]
            console.print(f"Host: {host_part.split('/')[0]}")

    console.print()

    # Table counts
    table = Table(title="Table Statistics")
    table.add_column("Table", style="cyan")
    table.add_column("Records", justify="right")

    try:
        if is_cloud_mode():
            # Cloud mode no longer uses PostgREST - use direct PostgreSQL connection
            console.print(
                "\n[yellow]Warning: 'db info' not available in cloud mode (DATABASE_URL='kurt')[/yellow]"
            )
            console.print(
                "[dim]Set DATABASE_URL to direct PostgreSQL connection to view table statistics.[/dim]\n"
            )
        else:
            # Use raw SQL for local databases
            with managed_session() as session:
                for table_name in MIGRATABLE_TABLES + OPTIONAL_TABLES:
                    try:
                        result = session.execute(
                            text(f"SELECT COUNT(*) FROM {table_name}")
                        ).scalar()
                        table.add_row(table_name, str(result))
                    except Exception:
                        table.add_row(table_name, "[dim]N/A[/dim]")

        console.print(table)
    except Exception as e:
        console.print(f"[red]Could not query tables: {e}[/red]")

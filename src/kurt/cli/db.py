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
    if mode != "local_sqlite":
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
    PostgreSQL database, tagged with the specified workspace ID.

    Requires:
    - DATABASE_URL pointing to PostgreSQL
    - KURT_CLOUD_AUTH=true for cloud mode
    - Valid authentication (kurt auth login)

    Example:
        export DATABASE_URL="postgresql://..."
        export KURT_CLOUD_AUTH=true
        kurt db import kurt-export.json --workspace-id ws-123
    """
    from sqlalchemy import text

    from kurt.db import get_mode, get_user_id, managed_session, set_workspace_context

    # Check we're in PostgreSQL mode
    mode = get_mode()
    if mode == "local_sqlite":
        console.print("[red]Error: Import requires PostgreSQL database[/red]")
        console.print("[dim]Set DATABASE_URL to a PostgreSQL connection string[/dim]")
        raise click.Abort()

    # Load credentials for user_id
    from kurt.db.tenant import load_context_from_credentials

    if not load_context_from_credentials():
        console.print("[red]Error: Not logged in[/red]")
        console.print("[dim]Run 'kurt auth login' first[/dim]")
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
    console.print()

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
        console.print()

    # Set workspace context for import
    set_workspace_context(workspace_id=workspace_id, user_id=user_id)

    results = {}

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

            if not dry_run:
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
                                raise

            else:
                imported = len(records)

            results[table_name] = {"imported": imported, "skipped": skipped}
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

    total_imported = 0
    total_skipped = 0
    for table_name, counts in results.items():
        table.add_row(table_name, str(counts["imported"]), str(counts["skipped"]))
        total_imported += counts["imported"]
        total_skipped += counts["skipped"]

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_imported}[/bold]",
        f"[bold]{total_skipped}[/bold]",
    )
    console.print(table)

    console.print()
    console.print(f"[dim]Data imported to workspace: {workspace_id}[/dim]")
    console.print(f"[dim]User ID: {user_id}[/dim]")


@db_group.command(name="status")
def status_cmd():
    """Show database status and mode.

    Displays:
    - Current operating mode (local_sqlite, local_postgres, cloud_postgres)
    - Database connection info
    - Table counts
    """
    from sqlalchemy import text

    from kurt.db import get_mode, is_cloud_mode, is_postgres, managed_session

    mode = get_mode()

    console.print()
    console.print("[bold]Database Status[/bold]")
    console.print()

    # Mode info
    mode_colors = {
        "local_sqlite": "blue",
        "local_postgres": "yellow",
        "cloud_postgres": "green",
    }
    color = mode_colors.get(mode, "white")
    console.print(f"Mode: [{color}]{mode}[/{color}]")
    console.print(f"PostgreSQL: {'Yes' if is_postgres() else 'No'}")
    console.print(f"Cloud Auth: {'Enabled' if is_cloud_mode() else 'Disabled'}")

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
        with managed_session() as session:
            for table_name in MIGRATABLE_TABLES + OPTIONAL_TABLES:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    table.add_row(table_name, str(result))
                except Exception:
                    table.add_row(table_name, "[dim]N/A[/dim]")

        console.print(table)
    except Exception as e:
        console.print(f"[red]Could not query tables: {e}[/red]")

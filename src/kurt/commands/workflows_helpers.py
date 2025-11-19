"""Helper CLI commands for workflows.

Commands for common workflow operations like exporting data, validating schemas, etc.
These commands are designed to be used within workflow YAML files.
"""

import json
from pathlib import Path
from typing import Any, Dict

import click
from rich.console import Console

console = Console()


@click.group(name="workflows")
def workflows_helpers():
    """Workflow helper commands"""
    pass


@workflows_helpers.command(name="export")
@click.option("--data", required=True, help="JSON data to export")
@click.option("--output-dir", required=True, type=click.Path(), help="Output directory")
@click.option(
    "--format",
    type=click.Choice(["markdown", "json", "yaml"]),
    default="markdown",
    help="Output format",
)
@click.option("--template", help="Template name (for markdown format)")
@click.option("--suffix", default="", help="File suffix (e.g., .schema)")
def export_data(data: str, output_dir: str, format: str, template: str, suffix: str):
    """
    Export workflow data to files.

    This command takes JSON data and exports it to files in various formats.
    Useful for saving workflow results without writing custom scripts.

    Examples:
        # Export FAQ pages as markdown
        kurt workflows export --data '${faq_pages}' --output-dir content/faqs --format markdown --template faq

        # Export schema as JSON
        kurt workflows export --data '${schema}' --output-dir content/faqs --format json --suffix .schema
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        data_obj = json.loads(data)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing JSON data:[/red] {e}")
        raise click.Abort()

    # Handle list of items
    if isinstance(data_obj, list):
        files_created = []

        for item in data_obj:
            if format == "markdown" and template == "faq":
                file_path = _export_faq_markdown(item, output_path)
                files_created.append(str(file_path))
            elif format == "json":
                slug = item.get("slug", f"item_{len(files_created)}")
                file_path = output_path / f"{slug}{suffix}.json"
                with open(file_path, "w") as f:
                    json.dump(item, f, indent=2)
                files_created.append(str(file_path))
            else:
                console.print(f"[yellow]Unsupported format/template: {format}/{template}[/yellow]")
                raise click.Abort()

        console.print(f"[green]✓[/green] Exported {len(files_created)} files to {output_path}")

        # Return file list as JSON for workflow
        click.echo(json.dumps({"files": files_created, "count": len(files_created)}))

    else:
        # Single item
        if format == "json":
            file_path = output_path / f"data{suffix}.json"
            with open(file_path, "w") as f:
                json.dump(data_obj, f, indent=2)
            console.print(f"[green]✓[/green] Exported to {file_path}")
            click.echo(json.dumps({"file": str(file_path)}))
        else:
            console.print("[yellow]Single item export only supports JSON format[/yellow]")
            raise click.Abort()


def _export_faq_markdown(faq_page: Dict[str, Any], output_dir: Path) -> Path:
    """Export a single FAQ page to markdown."""
    slug = faq_page.get("slug", "faq")
    file_path = output_dir / f"{slug}.md"

    with open(file_path, "w") as f:
        f.write(f"# {faq_page['title']}\n\n")

        if "meta_description" in faq_page:
            f.write(f"> {faq_page['meta_description']}\n\n")

        if "introduction" in faq_page:
            f.write(f"{faq_page['introduction']}\n\n")

        f.write("---\n\n")

        for faq in faq_page.get("faqs", []):
            f.write(f"## {faq['question']}\n\n")
            f.write(f"{faq['answer']}\n\n")

        if "related_topics" in faq_page and faq_page["related_topics"]:
            f.write("---\n\n")
            f.write("## Related Topics\n\n")
            for topic in faq_page["related_topics"]:
                f.write(f"- {topic}\n")

    return file_path


@workflows_helpers.command(name="validate-schema")
@click.option(
    "--schema-dir", required=True, type=click.Path(exists=True), help="Directory with schema files"
)
@click.option("--schema-type", default="FAQPage", help="Expected schema type")
def validate_schema(schema_dir: str, schema_type: str):
    """
    Validate JSON-LD schema markup files.

    Checks schema files for:
    - Valid JSON syntax
    - Required schema.org fields
    - Proper structure

    Example:
        kurt workflows validate-schema --schema-dir content/faqs --schema-type FAQPage
    """
    schema_path = Path(schema_dir)
    schema_files = list(schema_path.glob("*.schema.json"))

    if not schema_files:
        console.print(f"[yellow]No schema files found in {schema_dir}[/yellow]")
        click.echo(json.dumps({"valid": True, "files_checked": 0, "errors": []}))
        return

    errors = []
    valid_count = 0

    for schema_file in schema_files:
        try:
            with open(schema_file) as f:
                schema = json.load(f)

            # Basic validation
            if "@context" not in schema:
                errors.append(f"{schema_file.name}: Missing @context")
                continue

            if "@type" not in schema:
                errors.append(f"{schema_file.name}: Missing @type")
                continue

            if schema.get("@type") != schema_type:
                errors.append(
                    f"{schema_file.name}: Expected @type={schema_type}, got {schema.get('@type')}"
                )
                continue

            # Type-specific validation
            if schema_type == "FAQPage":
                if "mainEntity" not in schema:
                    errors.append(f"{schema_file.name}: FAQPage missing mainEntity")
                    continue

            valid_count += 1

        except json.JSONDecodeError as e:
            errors.append(f"{schema_file.name}: Invalid JSON - {e}")
        except Exception as e:
            errors.append(f"{schema_file.name}: {e}")

    if errors:
        console.print(f"[yellow]⚠ Found {len(errors)} validation errors:[/yellow]")
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")
    else:
        console.print(f"[green]✓[/green] All {valid_count} schema files are valid")

    result = {"valid": len(errors) == 0, "files_checked": len(schema_files), "errors": errors}

    click.echo(json.dumps(result))


@workflows_helpers.command(name="report")
@click.option("--workflow-name", required=True, help="Workflow name")
@click.option("--output-path", required=True, type=click.Path(), help="Output directory")
@click.option("--stats", required=True, help="Workflow statistics (JSON)")
def generate_report(workflow_name: str, output_path: str, stats: str):
    """
    Generate a workflow execution report.

    Creates a markdown report summarizing the workflow results.

    Example:
        kurt workflows report --workflow-name "AEO FAQ" --output-path content/faqs --stats '{"questions": 50}'
    """
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        stats_obj = json.loads(stats)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing stats JSON:[/red] {e}")
        raise click.Abort()

    from datetime import datetime

    report_path = output_dir / "WORKFLOW_REPORT.md"

    with open(report_path, "w") as f:
        f.write(f"# {workflow_name} Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## Summary\n\n")
        for key, value in stats_obj.items():
            formatted_key = key.replace("_", " ").title()

            # Handle different value types
            if isinstance(value, dict) and "count" in value:
                f.write(f"- **{formatted_key}**: {value['count']}\n")
            elif isinstance(value, (list, dict)):
                # Skip complex objects in summary
                pass
            else:
                f.write(f"- **{formatted_key}**: {value}\n")

        f.write("\n---\n\n")
        f.write("## Output Files\n\n")
        f.write(f"All files are located in: `{output_dir}`\n\n")

        # List files
        files = list(output_dir.glob("*"))
        for file in sorted(files):
            if file.name != "WORKFLOW_REPORT.md":
                f.write(f"- `{file.name}`\n")

        f.write("\n---\n\n")
        f.write("## Next Steps\n\n")
        f.write("1. Review generated content\n")
        f.write("2. Validate schema markup\n")
        f.write("3. Deploy to your website\n")
        f.write("4. Track performance and citations\n")

    console.print(f"[green]✓[/green] Report generated: {report_path}")
    click.echo(json.dumps({"report_path": str(report_path)}))


__all__ = ["workflows_helpers", "export_data", "validate_schema", "generate_report"]

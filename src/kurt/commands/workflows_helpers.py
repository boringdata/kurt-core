"""Generic helper CLI commands for workflows.

Provides composable, generic operations that can be used in any workflow:
- File I/O (read/write JSON, YAML, Markdown)
- Template rendering
- Data transformation
- Validation
"""

import json
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group(name="workflows")
def workflows_helpers():
    """Workflow helper commands"""
    pass


@workflows_helpers.command(name="write")
@click.option("--data", required=True, help="Data to write (JSON string or reference)")
@click.option("--output", required=True, type=click.Path(), help="Output file path")
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "text"]),
    default="json",
    help="Output format",
)
@click.option("--template", type=click.Path(exists=True), help="Template file (for text format)")
@click.option("--append", is_flag=True, help="Append to file instead of overwriting")
def write_file(data: str, output: str, format: str, template: str, append: bool):
    """
    Write data to a file.

    Generic file writing with format conversion and templating support.

    Examples:
        # Write JSON
        kurt workflows write --data '{"key": "value"}' --output data.json

        # Write using template
        kurt workflows write --data '${faq_data}' --output page.md --format text --template faq.md.j2

        # Append to file
        kurt workflows write --data "New line" --output log.txt --format text --append
    """
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Parse data if JSON
        if format in ["json", "yaml"]:
            data_obj = json.loads(data) if isinstance(data, str) else data
        else:
            data_obj = data

        # Apply template if provided
        if template:
            from string import Template

            with open(template) as f:
                tmpl = Template(f.read())

            content = tmpl.safe_substitute(
                data_obj if isinstance(data_obj, dict) else {"data": data_obj}
            )
        else:
            # Format output
            if format == "json":
                content = json.dumps(data_obj, indent=2)
            elif format == "yaml":
                import yaml

                content = yaml.dump(data_obj, default_flow_style=False)
            else:
                content = str(data_obj)

        # Write to file
        mode = "a" if append else "w"
        with open(output_path, mode) as f:
            f.write(content)
            if append:
                f.write("\n")

        console.print(f"[green]✓[/green] Written to {output_path}")
        click.echo(json.dumps({"file": str(output_path)}))

    except Exception as e:
        console.print(f"[red]Error writing file:[/red] {e}")
        raise click.Abort()


@workflows_helpers.command(name="read")
@click.option(
    "--input", "input_file", required=True, type=click.Path(exists=True), help="Input file"
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "text", "auto"]),
    default="auto",
    help="Input format (auto-detect by extension)",
)
def read_file(input_file: str, format: str):
    """
    Read data from a file.

    Outputs data as JSON for use in workflows.

    Examples:
        kurt workflows read --input data.json
        kurt workflows read --input config.yaml --format yaml
    """
    file_path = Path(input_file)

    # Auto-detect format
    if format == "auto":
        ext = file_path.suffix.lower()
        if ext in [".json"]:
            format = "json"
        elif ext in [".yaml", ".yml"]:
            format = "yaml"
        else:
            format = "text"

    try:
        with open(file_path) as f:
            if format == "json":
                data = json.load(f)
            elif format == "yaml":
                import yaml

                data = yaml.safe_load(f)
            else:
                data = f.read()

        # Output as JSON
        click.echo(json.dumps(data))

    except Exception as e:
        console.print(f"[red]Error reading file:[/red] {e}")
        raise click.Abort()


@workflows_helpers.command(name="transform")
@click.option("--data", required=True, help="Input data (JSON)")
@click.option("--jq", "jq_filter", help="jq-style filter expression")
@click.option("--map", "map_expr", help="Map expression (Python)")
@click.option("--filter", "filter_expr", help="Filter expression (Python)")
def transform_data(data: str, jq_filter: str, map_expr: str, filter_expr: str):
    """
    Transform JSON data.

    Apply filters and transformations to JSON data.

    Examples:
        # Filter list items
        kurt workflows transform --data '${items}' --filter "item['count'] > 10"

        # Map to extract fields
        kurt workflows transform --data '${items}' --map "{'name': item['name'], 'id': item['id']}"
    """
    try:
        data_obj = json.loads(data)

        result = data_obj

        # Apply filter
        if filter_expr and isinstance(result, list):
            result = [item for item in result if eval(filter_expr, {"item": item})]

        # Apply map
        if map_expr and isinstance(result, list):
            result = [eval(map_expr, {"item": item}) for item in result]

        # Output result
        click.echo(json.dumps(result))

    except Exception as e:
        console.print(f"[red]Error transforming data:[/red] {e}")
        raise click.Abort()


@workflows_helpers.command(name="validate")
@click.option("--data", required=True, help="Data to validate (JSON)")
@click.option("--schema", type=click.Path(exists=True), help="JSON Schema file")
@click.option("--type", "check_type", help="Expected type (object, array, string)")
@click.option("--required", multiple=True, help="Required fields (for objects)")
def validate_data(data: str, schema: str, check_type: str, required: tuple):
    """
    Validate data structure.

    Generic validation for JSON data.

    Examples:
        # Check type
        kurt workflows validate --data '${result}' --type object

        # Check required fields
        kurt workflows validate --data '${page}' --required title --required content

        # Validate against JSON schema
        kurt workflows validate --data '${data}' --schema page-schema.json
    """
    try:
        data_obj = json.loads(data)
        errors = []

        # Type check
        if check_type:
            expected_types = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "boolean": bool,
            }
            if check_type in expected_types:
                if not isinstance(data_obj, expected_types[check_type]):
                    errors.append(f"Expected type {check_type}, got {type(data_obj).__name__}")

        # Required fields check
        if required and isinstance(data_obj, dict):
            for field in required:
                if field not in data_obj:
                    errors.append(f"Missing required field: {field}")

        # JSON Schema validation
        if schema:
            import jsonschema

            with open(schema) as f:
                schema_obj = json.load(f)

            try:
                jsonschema.validate(data_obj, schema_obj)
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")

        # Output result
        result = {"valid": len(errors) == 0, "errors": errors}

        if errors:
            console.print(f"[yellow]⚠ Validation failed with {len(errors)} error(s)[/yellow]")
            for error in errors:
                console.print(f"  [red]✗[/red] {error}")
        else:
            console.print("[green]✓[/green] Validation passed")

        click.echo(json.dumps(result))

    except Exception as e:
        console.print(f"[red]Error validating data:[/red] {e}")
        click.echo(json.dumps({"valid": False, "errors": [str(e)]}))
        raise click.Abort()


@workflows_helpers.command(name="foreach")
@click.option("--data", required=True, help="Array data (JSON)")
@click.option("--command", required=True, help="Command to run for each item")
@click.option("--var-name", default="item", help="Variable name for item (default: item)")
def foreach_item(data: str, command: str, var_name: str):
    r"""
    Execute command for each item in array.

    Useful for batch operations.

    Examples:
        # Process each file
        kurt workflows foreach --data '${files}' --command "workflows write --data \${item} --output files/\${item.slug}.md"
    """
    try:
        data_obj = json.loads(data)

        if not isinstance(data_obj, list):
            console.print("[red]Data must be an array[/red]")
            raise click.Abort()

        results = []
        for i, item in enumerate(data_obj):
            console.print(f"[cyan]Processing item {i+1}/{len(data_obj)}[/cyan]")

            # TODO: Execute command with item context
            # This requires subprocess execution with variable substitution
            results.append({"index": i, "status": "pending"})

        click.echo(json.dumps({"processed": len(results), "results": results}))

    except Exception as e:
        console.print(f"[red]Error in foreach:[/red] {e}")
        raise click.Abort()


__all__ = [
    "workflows_helpers",
    "write_file",
    "read_file",
    "transform_data",
    "validate_data",
    "foreach_item",
]

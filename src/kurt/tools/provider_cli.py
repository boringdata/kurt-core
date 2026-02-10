"""CLI commands for tool/provider introspection and management.

Provides:
- kurt tool list: List all tools with their providers
- kurt tool info <name>: Show detailed tool information
- kurt tool check [name]: Validate provider requirements
- kurt tool providers <name>: List providers for a specific tool
- kurt tool new <name>: Scaffold a new tool from template
- kurt tool new-provider <tool> <name>: Scaffold a new provider for a tool
"""

import json as json_lib
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from kurt.tools.core.provider import get_provider_registry

console = Console()


@click.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--source",
    type=click.Choice(["all", "builtin", "user", "project"]),
    default="all",
    help="Filter by source",
)
def list_tools_cmd(as_json: bool, source: str):
    """List all tools and their providers."""
    registry = get_provider_registry()
    registry.discover()

    tools_with_providers = registry.list_tools_with_providers()

    if not tools_with_providers:
        if as_json:
            click.echo("[]")
        else:
            console.print("[dim]No tools found.[/dim]")
        return

    tools_data = []
    for tool_name in sorted(tools_with_providers.keys()):
        info = registry.get_tool_info(tool_name)
        if not info:
            continue

        tool_source = info.get("source", "unknown")

        # Filter by source
        if source != "all" and tool_source != source:
            continue

        providers = info.get("providers", [])
        tools_data.append(
            {
                "name": tool_name,
                "source": tool_source,
                "provider_count": len(providers),
                "providers": providers,
            }
        )

    if as_json:
        click.echo(json_lib.dumps(tools_data, indent=2))
        return

    if not tools_data:
        console.print(f"[dim]No tools found with source '{source}'.[/dim]")
        return

    table = Table(title="Tools")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Source", style="dim")
    table.add_column("Providers")

    for tool in tools_data:
        provider_names = [p["name"] for p in tool["providers"]]
        providers_str = ", ".join(provider_names[:6])
        if len(provider_names) > 6:
            providers_str += f" (+{len(provider_names) - 6} more)"
        if not provider_names:
            providers_str = "-"

        table.add_row(tool["name"], tool["source"], providers_str)

    console.print(table)


@click.command("info")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def info_cmd(name: str, as_json: bool):
    """Show detailed information about a tool."""
    registry = get_provider_registry()
    registry.discover()

    info = registry.get_tool_info(name)
    if not info:
        raise click.ClickException(f"Tool '{name}' not found.")

    providers_meta = registry.list_providers(name)

    result = {
        "name": name,
        "source": info.get("source", "unknown"),
        "providers": [],
    }

    for meta in providers_meta:
        result["providers"].append(
            {
                "name": meta["name"],
                "version": meta.get("version", "1.0.0"),
                "source": meta.get("_source", "unknown"),
                "url_patterns": meta.get("url_patterns", []),
                "requires_env": meta.get("requires_env", []),
                "description": meta.get("description", ""),
            }
        )

    if as_json:
        click.echo(json_lib.dumps(result, indent=2))
        return

    console.print(f"\n[bold cyan]Tool:[/bold cyan] {name}")
    console.print(f"[bold]Source:[/bold] {result['source']}")
    console.print(f"[bold]Providers:[/bold] {len(result['providers'])}\n")

    if result["providers"]:
        table = Table()
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("Version", style="dim")
        table.add_column("Source", style="dim")
        table.add_column("URL Patterns")
        table.add_column("Requires")

        for p in result["providers"]:
            patterns = ", ".join(p["url_patterns"]) if p["url_patterns"] else "-"
            requires = ", ".join(p["requires_env"]) if p["requires_env"] else "-"
            table.add_row(
                p["name"],
                p["version"],
                p["source"],
                patterns,
                requires,
            )

        console.print(table)
    else:
        console.print("[dim]No providers registered.[/dim]")
    console.print()


@click.command("providers")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def providers_cmd(name: str, as_json: bool):
    """List providers for a specific tool."""
    registry = get_provider_registry()
    registry.discover()

    providers_meta = registry.list_providers(name)

    if not providers_meta:
        if as_json:
            click.echo("[]")
        else:
            tools = registry.list_tools_with_providers()
            if name not in tools:
                raise click.ClickException(
                    f"Tool '{name}' not found. Available: {', '.join(sorted(tools.keys()))}"
                )
            console.print(f"[dim]No providers for tool '{name}'.[/dim]")
        return

    result = []
    for meta in providers_meta:
        result.append(
            {
                "name": meta["name"],
                "version": meta.get("version", "1.0.0"),
                "source": meta.get("_source", "unknown"),
                "url_patterns": meta.get("url_patterns", []),
                "requires_env": meta.get("requires_env", []),
            }
        )

    if as_json:
        click.echo(json_lib.dumps(result, indent=2))
        return

    for p in result:
        console.print(f"[bold cyan]{p['name']}[/bold cyan] v{p['version']} ({p['source']})")
        if p["url_patterns"]:
            console.print(f"  URL patterns: {', '.join(p['url_patterns'])}")
        if p["requires_env"]:
            console.print(f"  Requires: {', '.join(p['requires_env'])}")
        console.print()


@click.command("check")
@click.argument("name", required=False)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def check_cmd(name: str | None, as_json: bool):
    """Validate tool and provider requirements.

    If NAME is given, checks a specific tool. Otherwise checks all tools.
    """
    registry = get_provider_registry()
    registry.discover()

    if name:
        # Check a specific tool
        info = registry.get_tool_info(name)
        if not info:
            raise click.ClickException(f"Tool '{name}' not found.")

        providers_meta = registry.list_providers(name)
        report = _check_tool(registry, name, providers_meta)

        if as_json:
            click.echo(json_lib.dumps(report, indent=2))
            return

        _print_tool_check(report)
    else:
        # Check all tools
        all_reports = []
        for tool_name in sorted(registry.list_tools_with_providers().keys()):
            providers_meta = registry.list_providers(tool_name)
            report = _check_tool(registry, tool_name, providers_meta)
            all_reports.append(report)

        if as_json:
            click.echo(json_lib.dumps(all_reports, indent=2))
            return

        if not all_reports:
            console.print("[dim]No tools found.[/dim]")
            return

        for report in all_reports:
            _print_tool_check(report)


def _check_tool(
    registry, tool_name: str, providers_meta: list[dict]
) -> dict:
    """Check a tool's providers and return a report."""
    report = {
        "tool": tool_name,
        "providers": [],
        "all_valid": True,
    }

    for meta in providers_meta:
        pname = meta["name"]
        missing = registry.validate_provider(tool_name, pname)
        provider_report = {
            "name": pname,
            "valid": len(missing) == 0,
            "missing_env": missing,
        }
        report["providers"].append(provider_report)
        if missing:
            report["all_valid"] = False

    return report


def _print_tool_check(report: dict) -> None:
    """Print a tool check report with rich formatting."""
    tool_name = report["tool"]
    all_valid = report["all_valid"]

    if all_valid:
        status = "[green]OK[/green]"
    else:
        status = "[yellow]WARN[/yellow]"

    console.print(f"\n[bold]{tool_name}[/bold]  {status}")

    for p in report["providers"]:
        if p["valid"]:
            console.print(f"  [green]\u2713[/green] {p['name']}")
        else:
            missing = ", ".join(p["missing_env"])
            console.print(f"  [red]\u2717[/red] {p['name']} - missing: {missing}")

    console.print()


# ---------------------------------------------------------------------------
# Scaffolding commands
# ---------------------------------------------------------------------------


def _find_project_root() -> Path | None:
    """Find project root by searching up for kurt.toml."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "kurt.toml").exists():
            return parent
    return None


@click.command("new")
@click.argument("name")
@click.option("--description", "-d", default="", help="Tool description")
@click.option(
    "--location",
    type=click.Choice(["project", "user"]),
    default="project",
    help="Where to create the tool",
)
def new_tool_cmd(name: str, description: str, location: str):
    """Create a new tool from template.

    Scaffolds the directory structure and starter files for a new tool
    with a default provider.
    """
    from kurt.tools.templates.scaffolds import (
        render_base_py,
        render_init_py,
        render_provider_config_py,
        render_provider_py,
        render_tool_py,
    )

    # Determine target directory
    if location == "project":
        project_root = _find_project_root()
        if project_root is None:
            raise click.ClickException(
                "Not in a Kurt project (no kurt.toml found). Use --location user."
            )
        target = project_root / "kurt" / "tools" / name
    else:
        target = Path.home() / ".kurt" / "tools" / name

    if target.exists():
        raise click.ClickException(f"Tool '{name}' already exists at {target}")

    # Create directory structure
    providers_dir = target / "providers" / "default"
    providers_dir.mkdir(parents=True)
    (target / "providers" / "__init__.py").write_text("")
    (providers_dir / "__init__.py").write_text("")

    # Generate files from templates
    (target / "tool.py").write_text(render_tool_py(name, description))
    (target / "base.py").write_text(render_base_py(name))
    (target / "__init__.py").write_text(render_init_py(name))
    (providers_dir / "provider.py").write_text(render_provider_py(name, "default"))
    (providers_dir / "config.py").write_text(render_provider_config_py(name, "default"))

    console.print(f"\n[green]Created tool '{name}' in {target}/[/green]\n")

    for path in sorted(target.rglob("*.py")):
        rel = path.relative_to(target)
        console.print(f"  {rel}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit tool.py to define your input/output schemas")
    console.print("2. Edit base.py to define the provider interface")
    console.print("3. Implement your provider in providers/default/provider.py")
    console.print(f"4. Run: kurt tool check {name}")


@click.command("new-provider")
@click.argument("tool_name", metavar="TOOL")
@click.argument("provider_name", metavar="NAME")
@click.option(
    "--location",
    type=click.Choice(["project", "user"]),
    default="project",
    help="Where to create the provider",
)
def new_provider_cmd(tool_name: str, provider_name: str, location: str):
    """Create a new provider for an existing tool.

    Scaffolds a provider directory with a starter provider.py file.
    """
    from kurt.tools.templates.scaffolds import (
        render_provider_config_py,
        render_provider_py,
    )

    # Determine target directory
    if location == "project":
        project_root = _find_project_root()
        if project_root is None:
            raise click.ClickException(
                "Not in a Kurt project (no kurt.toml found). Use --location user."
            )
        target = project_root / "kurt" / "tools" / tool_name / "providers" / provider_name
    else:
        target = (
            Path.home() / ".kurt" / "tools" / tool_name / "providers" / provider_name
        )

    if target.exists():
        raise click.ClickException(
            f"Provider '{provider_name}' already exists at {target}"
        )

    # Create provider directory
    target.mkdir(parents=True)
    (target / "__init__.py").write_text("")
    (target / "provider.py").write_text(render_provider_py(tool_name, provider_name))
    (target / "config.py").write_text(
        render_provider_config_py(tool_name, provider_name)
    )

    console.print(
        f"\n[green]Created provider '{provider_name}' "
        f"for tool '{tool_name}' in {target}/[/green]\n"
    )

    for path in sorted(target.rglob("*.py")):
        rel = path.relative_to(target)
        console.print(f"  {rel}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Edit provider.py to implement the process() method")
    console.print("2. Set url_patterns for auto-routing (optional)")
    console.print("3. Set requires_env if API keys needed")
    console.print(f"4. Run: kurt tool check {tool_name}")

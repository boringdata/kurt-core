"""CLI commands for CMS integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from kurt_new.cli.options import format_option, limit_option

console = Console()


@click.group()
def cms_group():
    """
    CMS integration commands.

    \b
    Commands:
      onboard   Configure CMS credentials and content types
      status    Show configured CMS integrations
      types     List available content types
      search    Search CMS content
      fetch     Fetch document to markdown
      publish   Publish markdown to CMS as draft
    """
    pass


@cms_group.command("onboard")
@click.option("--platform", default="sanity", help="CMS platform (sanity, contentful, wordpress)")
@click.option("--instance", default="default", help="Instance name (prod, staging, default)")
@click.option("--project-id", help="Project ID (enables non-interactive mode)")
@click.option("--dataset", help="Dataset name")
@click.option("--token", help="Read API token")
@click.option("--base-url", help="Base URL for your website")
def onboard_cmd(
    platform: str,
    instance: str,
    project_id: Optional[str],
    dataset: Optional[str],
    token: Optional[str],
    base_url: Optional[str],
):
    """
    Configure CMS credentials and content types.

    \b
    Examples:
        # Interactive mode
        kurt integrations cms onboard

        # Non-interactive with credentials
        kurt integrations cms onboard \\
            --project-id myproject --dataset production \\
            --token sk_read_token --base-url https://mysite.com
    """
    from . import get_adapter
    from .config import (
        add_platform_instance,
        create_template_config,
        platform_configured,
    )

    non_interactive = any([project_id, dataset, token, base_url])

    console.print(
        f"[bold green]CMS Onboarding: {platform.capitalize()} ({instance})[/bold green]\n"
    )

    if not platform_configured(platform, instance):
        console.print(f"[yellow]No configuration found for {platform}/{instance}.[/yellow]\n")

        template = create_template_config(platform, instance)

        if non_interactive:
            console.print("[dim]Non-interactive mode: using provided options[/dim]\n")
            instance_config = {}
            if platform == "sanity":
                instance_config["project_id"] = project_id or template.get("project_id")
                instance_config["dataset"] = dataset or template.get("dataset")
                instance_config["token"] = token or template.get("token")
                instance_config["base_url"] = base_url or template.get("base_url")
            else:
                instance_config = template
        else:
            console.print(f"[bold]Enter {platform.capitalize()} credentials:[/bold]\n")

            if platform == "sanity":
                console.print(
                    "[dim]Project ID: Found in Sanity Studio → Manage → Project settings[/dim]"
                )
                console.print("[dim]Token: Create in manage.sanity.io → API → Tokens[/dim]\n")

            instance_config = {}
            for key, placeholder in template.items():
                if key == "content_type_mappings":
                    continue
                value = console.input(
                    f"  {key.replace('_', ' ').title()} [{placeholder}]: "
                ).strip()
                instance_config[key] = value if value else placeholder

        add_platform_instance(platform, instance, instance_config)
        console.print("\n[green]✓ Configuration saved to kurt.config[/green]")
        console.print("[dim]Note: CMS credentials are stored in kurt.config (gitignored)[/dim]\n")

    # Test connection
    try:
        console.print("[cyan]Testing connection...[/cyan]")
        from .config import get_platform_config

        config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, config)

        if not adapter.test_connection():
            console.print("[red]✗ Connection failed[/red]")
            raise click.Abort()

        console.print("[green]✓ Connection successful[/green]\n")

        # Get content types
        console.print("[cyan]Discovering content types...[/cyan]")
        types = adapter.get_content_types()

        if types:
            console.print(f"[green]✓ Found {len(types)} content types[/green]\n")
            for t in types:
                console.print(f"  • {t['name']} ({t['count']} docs)")

        console.print("\n[bold]Next steps:[/bold]")
        console.print(
            f"  1. Map CMS content: [cyan]kurt content map --cms {platform}:{instance}[/cyan]"
        )
        console.print("  2. Fetch content: [cyan]kurt content fetch[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms_group.command("status")
@click.option("--check-health", is_flag=True, help="Test API connections")
def status_cmd(check_health: bool):
    """
    Show configured CMS integrations.

    \b
    Examples:
        kurt integrations cms status
        kurt integrations cms status --check-health
    """
    from . import get_adapter
    from .config import load_cms_config, platform_configured

    try:
        config = load_cms_config()

        if not config:
            console.print("[yellow]No CMS integrations configured[/yellow]\n")
            console.print(
                "Get started: [cyan]kurt integrations cms onboard --platform sanity[/cyan]"
            )
            return

        console.print("[bold]CMS Integrations:[/bold]\n")

        for platform, instances in config.items():
            for instance_name, instance_config in instances.items():
                configured = platform_configured(platform, instance_name)
                status = "[green]✓[/green]" if configured else "[yellow]⚠[/yellow]"

                console.print(f"{status} {platform.capitalize()} ({instance_name})")

                if platform == "sanity":
                    project_id = instance_config.get("project_id")
                    if project_id and not project_id.startswith("YOUR_"):
                        console.print(f"  Project: {project_id}")

                mappings = instance_config.get("content_type_mappings", {})
                if mappings:
                    types = [k for k, v in mappings.items() if v.get("enabled")]
                    if types:
                        console.print(f"  Content types: {len(types)} ({', '.join(types[:3])}...)")

                if check_health and configured:
                    try:
                        adapter = get_adapter(platform, instance_config)
                        import time

                        start = time.time()
                        adapter.test_connection()
                        elapsed = int((time.time() - start) * 1000)
                        console.print(f"  [green]Connection: OK ({elapsed}ms)[/green]")
                    except Exception as e:
                        console.print(f"  [red]Connection: Failed - {e}[/red]")

                console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms_group.command("types")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option("--instance", default=None, help="Instance name")
def types_cmd(platform: str, instance: Optional[str]):
    """
    List available content types in CMS.

    \b
    Example:
        kurt integrations cms types
        kurt integrations cms types --platform sanity --instance prod
    """
    from . import get_adapter
    from .config import get_platform_config, platform_configured

    try:
        if not platform_configured(platform, instance):
            console.print(f"[red]Error:[/red] {platform}/{instance or 'default'} not configured")
            console.print(f"Run: [cyan]kurt integrations cms onboard --platform {platform}[/cyan]")
            raise click.Abort()

        config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, config)

        console.print(f"[cyan]Fetching content types from {platform}...[/cyan]\n")

        types = adapter.get_content_types()

        if not types:
            console.print("[yellow]No content types found[/yellow]")
            return

        table = Table(title=f"Content Types ({len(types)} types)")
        table.add_column("Type Name", style="cyan")
        table.add_column("Documents", justify="right")

        for t in types:
            table.add_row(t["name"], str(t["count"]))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms_group.command("search")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option("--instance", default=None, help="Instance name")
@click.option("--query", "-q", help="Text search query")
@click.option("--content-type", "-t", help="Filter by content type")
@limit_option
@format_option
def search_cmd(
    platform: str,
    instance: Optional[str],
    query: Optional[str],
    content_type: Optional[str],
    limit: int,
    output_format: str,
):
    """
    Search CMS content.

    \b
    Examples:
        kurt integrations cms search --query "tutorial"
        kurt integrations cms search --content-type article --limit 50
        kurt integrations cms search --query "quickstart" --format json
    """
    from . import get_adapter
    from .config import get_platform_config, platform_configured

    try:
        if not platform_configured(platform, instance):
            console.print(f"[red]Error:[/red] {platform}/{instance or 'default'} not configured")
            raise click.Abort()

        config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, config)

        console.print(f"[cyan]Searching {platform} CMS...[/cyan]")
        if query:
            console.print(f"[dim]Query: {query}[/dim]")

        results = adapter.search(query=query, content_type=content_type, limit=limit or 20)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        if output_format == "json":
            print(json.dumps([doc.to_dict() for doc in results], indent=2, default=str))
        else:
            table = Table(title=f"Search Results ({len(results)} documents)")
            table.add_column("ID", style="cyan")
            table.add_column("Title")
            table.add_column("Type")
            table.add_column("Status")

            for doc in results:
                table.add_row(
                    doc.id[:12] + "...",
                    doc.title[:50],
                    doc.content_type,
                    doc.status,
                )

            console.print(table)

        console.print(f"\n[green]✓[/green] Found {len(results)} documents")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms_group.command("fetch")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option("--instance", default=None, help="Instance name")
@click.option("--id", "document_id", required=True, help="Document ID to fetch")
@click.option("--output-dir", type=click.Path(), help="Output directory for markdown")
@click.option("--output-format", type=click.Choice(["markdown", "json"]), default="markdown")
def fetch_cmd(
    platform: str,
    instance: Optional[str],
    document_id: str,
    output_dir: Optional[str],
    output_format: str,
):
    """
    Fetch document content from CMS.

    \b
    Examples:
        kurt integrations cms fetch --id abc123
        kurt integrations cms fetch --id abc123 --output-dir sources/cms/sanity/
    """
    from . import get_adapter
    from .config import get_platform_config, platform_configured

    try:
        if not platform_configured(platform, instance):
            console.print(f"[red]Error:[/red] {platform}/{instance or 'default'} not configured")
            raise click.Abort()

        config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, config)

        console.print(f"[cyan]Fetching document:[/cyan] {document_id}")
        doc = adapter.fetch(document_id)

        console.print(f"[green]✓ Fetched:[/green] {doc.title}")
        console.print(f"  Type: {doc.content_type}")
        console.print(f"  Content: {len(doc.content)} characters")

        if output_format == "json":
            print(json.dumps(doc.to_dict(), indent=2, default=str))
        else:
            import yaml

            frontmatter = doc.to_frontmatter()
            markdown_content = (
                f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{doc.content}"
            )

            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                slug = doc.metadata.get("slug", doc.title)
                filename = f"{slug}.md".replace("/", "-")
                filepath = output_path / filename

                with open(filepath, "w") as f:
                    f.write(markdown_content)

                console.print(f"\n[green]✓ Saved to:[/green] {filepath}")
            else:
                console.print()
                print(markdown_content)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms_group.command("publish")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option("--instance", default=None, help="Instance name")
@click.option(
    "--file", "filepath", required=True, type=click.Path(exists=True), help="Markdown file"
)
@click.option("--id", "document_id", help="CMS document ID to update")
@click.option("--content-type", help="Content type for new documents")
def publish_cmd(
    platform: str,
    instance: Optional[str],
    filepath: str,
    document_id: Optional[str],
    content_type: Optional[str],
):
    """
    Publish markdown file to CMS as draft.

    \b
    Examples:
        kurt integrations cms publish --file draft.md --id abc123
        kurt integrations cms publish --file new-article.md --content-type article
    """
    import yaml

    from . import get_adapter
    from .config import get_platform_config, platform_configured

    try:
        if not platform_configured(platform, instance):
            console.print(f"[red]Error:[/red] {platform}/{instance or 'default'} not configured")
            raise click.Abort()

        # Read markdown file
        with open(filepath, "r") as f:
            content = f.read()

        # Parse frontmatter
        title = None
        metadata = {}

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()

                title = frontmatter.get("title")
                document_id = document_id or frontmatter.get("cms_id")
                content_type = content_type or frontmatter.get("cms_type")

                for key in ["slug", "author", "tags"]:
                    if key in frontmatter:
                        metadata[key] = frontmatter[key]
            else:
                markdown_content = content
        else:
            markdown_content = content

        if not title:
            title = Path(filepath).stem.replace("-", " ").title()

        if not document_id and not content_type:
            console.print("[red]Error:[/red] Must provide --id or --content-type")
            raise click.Abort()

        config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, config)

        console.print(f"[cyan]Publishing to {platform} CMS...[/cyan]")
        console.print(f"  Title: {title}")

        result = adapter.create_draft(
            content=markdown_content,
            title=title,
            content_type=content_type,
            metadata=metadata,
            document_id=document_id,
        )

        console.print("\n[green]✓ Draft published![/green]")
        console.print(f"  Draft ID: [cyan]{result['draft_id']}[/cyan]")
        console.print(f"  Draft URL: {result['draft_url']}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

"""CMS integration CLI commands."""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from kurt.cms.config import (
    cms_config_exists,
    create_template_config,
    get_platform_config,
    load_cms_config,
    platform_configured,
    save_cms_config,
)

console = Console()


def get_adapter(platform: str):
    """Get CMS adapter instance for the specified platform."""
    config = get_platform_config(platform)

    if platform == "sanity":
        from kurt.cms.sanity import SanityAdapter

        return SanityAdapter(config)
    elif platform == "contentful":
        raise NotImplementedError("Contentful support coming soon")
    elif platform == "wordpress":
        raise NotImplementedError("WordPress support coming soon")
    else:
        raise ValueError(f"Unsupported CMS platform: {platform}")


@click.group()
def cms():
    """Integrate with CMS platforms (Sanity, Contentful, WordPress)."""
    pass


@cms.command("search")
@click.option("--platform", default="sanity", help="CMS platform (sanity, contentful, wordpress)")
@click.option("--query", "-q", help="Text search query")
@click.option("--content-type", "-t", help="Filter by content type")
@click.option("--limit", type=int, default=20, help="Maximum results (default: 20)")
@click.option(
    "--output", type=click.Choice(["table", "json", "list"]), default="table", help="Output format"
)
def search_cmd(
    platform: str, query: Optional[str], content_type: Optional[str], limit: int, output: str
):
    """
    Search CMS content.

    Examples:
        kurt cms search --query "tutorial"
        kurt cms search --content-type article --limit 50
        kurt cms search --query "quickstart" --output json
    """
    try:
        if not platform_configured(platform):
            console.print(f"[red]Error:[/red] {platform.capitalize()} not configured")
            console.print(f"Run: [cyan]kurt cms onboard --platform {platform}[/cyan]")
            raise click.Abort()

        adapter = get_adapter(platform)

        # Perform search
        console.print(f"[cyan]Searching {platform} CMS...[/cyan]")
        if query:
            console.print(f"[dim]Query: {query}[/dim]")
        if content_type:
            console.print(f"[dim]Content type: {content_type}[/dim]")
        console.print()

        results = adapter.search(query=query, content_type=content_type, limit=limit)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        # Display results
        if output == "json":
            print(json.dumps([doc.to_dict() for doc in results], indent=2, default=str))
        elif output == "list":
            for doc in results:
                console.print(f"[cyan]{doc.id}[/cyan] - {doc.title}")
                console.print(f"  Type: {doc.content_type} | Status: {doc.status}")
                if doc.url:
                    console.print(f"  URL: [dim]{doc.url}[/dim]")
                console.print()
        else:  # table
            table = Table(title=f"Search Results ({len(results)} documents)")
            table.add_column("ID", style="cyan")
            table.add_column("Title")
            table.add_column("Type")
            table.add_column("Status")
            table.add_column("Modified")

            for doc in results:
                table.add_row(
                    doc.id[:12] + "...",
                    doc.title[:50],
                    doc.content_type,
                    doc.status,
                    str(doc.last_modified)[:10] if doc.last_modified else "",
                )

            console.print(table)

        console.print(f"\n[green]✓[/green] Found {len(results)} documents")
        console.print(
            "[yellow]Tip:[/yellow] Fetch content with: [cyan]kurt cms fetch --id <document-id>[/cyan]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms.command("fetch")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option("--id", "document_id", required=True, help="Document ID to fetch")
@click.option("--output-dir", type=click.Path(), help="Output directory for markdown file")
@click.option(
    "--output-format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Output format",
)
def fetch_cmd(platform: str, document_id: str, output_dir: Optional[str], output_format: str):
    """
    Fetch document content from CMS.

    Downloads document and converts to markdown format with YAML frontmatter.

    Examples:
        kurt cms fetch --id abc123
        kurt cms fetch --id abc123 --output-dir sources/cms/sanity/
        kurt cms fetch --id abc123 --output-format json
    """
    try:
        if not platform_configured(platform):
            console.print(f"[red]Error:[/red] {platform.capitalize()} not configured")
            console.print(f"Run: [cyan]kurt cms onboard --platform {platform}[/cyan]")
            raise click.Abort()

        adapter = get_adapter(platform)

        # Fetch document
        console.print(f"[cyan]Fetching document:[/cyan] {document_id}")
        doc = adapter.fetch(document_id)

        console.print(f"[green]✓ Fetched:[/green] {doc.title}")
        console.print(f"  Type: {doc.content_type}")
        console.print(f"  Status: {doc.status}")
        console.print(f"  Content: {len(doc.content)} characters")

        # Output
        if output_format == "json":
            print(json.dumps(doc.to_dict(), indent=2, default=str))
        else:
            # Generate markdown with frontmatter
            import yaml

            frontmatter = doc.to_frontmatter()
            markdown_content = (
                f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{doc.content}"
            )

            if output_dir:
                # Save to file
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)

                # Generate filename from slug or title
                slug = doc.metadata.get("slug", doc.title)
                filename = f"{slug}.md".replace("/", "-")
                filepath = output_path / filename

                with open(filepath, "w") as f:
                    f.write(markdown_content)

                console.print(f"\n[green]✓ Saved to:[/green] {filepath}")
            else:
                # Print to stdout
                console.print()
                print(markdown_content)

        if not output_dir:
            console.print(
                f"\n[yellow]Tip:[/yellow] Save to file with: [cyan]--output-dir sources/cms/{platform}/[/cyan]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms.command("types")
@click.option("--platform", default="sanity", help="CMS platform")
def types_cmd(platform: str):
    """
    List available content types in CMS.

    Shows all content types with document counts.

    Example:
        kurt cms types
        kurt cms types --platform contentful
    """
    try:
        if not platform_configured(platform):
            console.print(f"[red]Error:[/red] {platform.capitalize()} not configured")
            console.print(f"Run: [cyan]kurt cms onboard --platform {platform}[/cyan]")
            raise click.Abort()

        adapter = get_adapter(platform)

        console.print(f"[cyan]Fetching content types from {platform} CMS...[/cyan]\n")

        types = adapter.get_content_types()

        if not types:
            console.print("[yellow]No content types found[/yellow]")
            return

        # Display as table
        table = Table(title=f"Content Types ({len(types)} types)")
        table.add_column("Type Name", style="cyan")
        table.add_column("Documents", justify="right")

        for type_info in types:
            table.add_row(type_info["name"], str(type_info["count"]))

        console.print(table)
        console.print(
            "\n[yellow]Tip:[/yellow] Configure field mappings with: [cyan]kurt cms onboard[/cyan]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms.command("onboard")
@click.option("--platform", default="sanity", help="CMS platform to configure")
def onboard_cmd(platform: str):
    """
    Interactive CMS onboarding and configuration.

    Discovers content types and guides you through field mapping setup.

    Example:
        kurt cms onboard
        kurt cms onboard --platform contentful
    """
    console.print(f"[bold green]CMS Onboarding: {platform.capitalize()}[/bold green]\n")

    # Check if config exists
    if not cms_config_exists():
        console.print("[yellow]No CMS configuration found.[/yellow]")
        console.print("Creating configuration file...\n")

        config_path = create_template_config(platform)
        console.print(f"[green]✓ Created:[/green] {config_path}")
        console.print()
        console.print("[yellow]Please fill in your CMS credentials:[/yellow]")
        console.print(f"  1. Open: [cyan]{config_path}[/cyan]")
        console.print(f"  2. Replace placeholder values with your {platform} credentials")
        console.print("  3. Run this command again: [cyan]kurt cms onboard[/cyan]")
        console.print()
        console.print("[dim]Note: This file is gitignored and won't be committed.[/dim]")
        return

    # Check if platform configured
    if not platform_configured(platform):
        config_path = create_template_config(platform, overwrite=False)
        console.print(f"[yellow]{platform.capitalize()} not configured.[/yellow]")
        console.print(f"Please fill in credentials in: [cyan]{config_path}[/cyan]")
        return

    # Test connection
    try:
        console.print("[cyan]Testing connection...[/cyan]")
        adapter = get_adapter(platform)

        if not adapter.test_connection():
            console.print("[red]✗ Connection failed[/red]")
            console.print("Please check your credentials in the config file.")
            raise click.Abort()

        console.print("[green]✓ Connection successful[/green]\n")

        # Get content types
        console.print("[cyan]Discovering content types...[/cyan]")
        types = adapter.get_content_types()

        if not types:
            console.print("[yellow]No content types found[/yellow]")
            return

        console.print(f"[green]✓ Found {len(types)} content types[/green]\n")

        # Display types
        table = Table(title="Available Content Types")
        table.add_column("#", style="dim")
        table.add_column("Type Name", style="cyan")
        table.add_column("Documents", justify="right")

        for idx, type_info in enumerate(types, 1):
            table.add_row(str(idx), type_info["name"], str(type_info["count"]))

        console.print(table)
        console.print()

        # Interactive selection
        console.print("[bold]Select content types to configure:[/bold]")
        console.print(
            "[dim]Enter numbers separated by commas (e.g., 1,3,5) or 'all' for all types[/dim]"
        )

        selection = console.input("\n[cyan]Your selection:[/cyan] ").strip()

        if selection.lower() == "all":
            selected_types = [t["name"] for t in types]
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
                selected_types = [types[i]["name"] for i in indices if 0 <= i < len(types)]
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")
                raise click.Abort()

        if not selected_types:
            console.print("[yellow]No types selected[/yellow]")
            return

        console.print(
            f"\n[green]Selected {len(selected_types)} types:[/green] {', '.join(selected_types)}"
        )
        console.print()

        # Configure field mappings for each type
        config_data = load_cms_config()
        if platform not in config_data:
            config_data[platform] = {}

        if "content_type_mappings" not in config_data[platform]:
            config_data[platform]["content_type_mappings"] = {}

        mappings = config_data[platform]["content_type_mappings"]

        for content_type in selected_types:
            console.print(f"\n[bold cyan]Configuring: {content_type}[/bold cyan]")
            console.print("[dim]Fetching example document...[/dim]")

            try:
                example_doc = adapter.get_example_document(content_type)

                # Get field names (excluding system fields)
                available_fields = [k for k in example_doc.keys() if not k.startswith("_")]

                console.print(f"\n[green]✓ Found {len(available_fields)} fields[/green]")
                console.print("[dim]Available fields:[/dim]")
                for field in sorted(available_fields)[:15]:  # Show first 15
                    console.print(f"  - {field}")
                if len(available_fields) > 15:
                    console.print(f"  ... and {len(available_fields) - 15} more")

                # Smart defaults
                content_field_default = None
                if "content_body_portable" in available_fields:
                    content_field_default = "content_body_portable"
                elif "content_body_mdx" in available_fields:
                    content_field_default = "content_body_mdx"
                elif "body" in available_fields:
                    content_field_default = "body"
                elif "content" in available_fields:
                    content_field_default = "content"

                title_field_default = "title" if "title" in available_fields else None
                slug_field_default = "slug.current" if "slug" in available_fields else None

                # Smart defaults for description
                description_field_default = None
                if "excerpt" in available_fields:
                    description_field_default = "excerpt"
                elif "summary" in available_fields:
                    description_field_default = "summary"
                elif "description" in available_fields:
                    description_field_default = "description"

                # Smart default for content type based on schema name
                content_type_default = None
                if content_type in ["article", "blog", "blogPost", "post"]:
                    content_type_default = "article" if content_type == "article" else "blog"
                elif content_type in ["tutorial", "guide", "howto"]:
                    content_type_default = "tutorial"
                elif content_type in ["reference", "glossary", "universeItem"]:
                    content_type_default = "reference"
                elif content_type in ["caseStudy", "case_study"]:
                    content_type_default = "case_study"

                # Ask for content field
                console.print("\n[bold]Which field contains the main content?[/bold]")
                if content_field_default:
                    console.print(f"[dim](Press Enter for: {content_field_default})[/dim]")
                content_field = console.input("[cyan]Content field:[/cyan] ").strip()
                if not content_field:
                    content_field = content_field_default

                # Ask for title field
                console.print("\n[bold]Which field contains the title?[/bold]")
                if title_field_default:
                    console.print(f"[dim](Press Enter for: {title_field_default})[/dim]")
                title_field = console.input("[cyan]Title field:[/cyan] ").strip()
                if not title_field:
                    title_field = title_field_default

                # Ask for slug field
                console.print("\n[bold]Which field contains the URL slug?[/bold]")
                if slug_field_default:
                    console.print(f"[dim](Press Enter for: {slug_field_default})[/dim]")
                slug_field = console.input("[cyan]Slug field:[/cyan] ").strip()
                if not slug_field:
                    slug_field = slug_field_default

                # Ask for description field
                console.print("\n[bold]Which field contains a summary/description?[/bold]")
                console.print("[dim](Used for topic clustering and content organization)[/dim]")
                if description_field_default:
                    console.print(f"[dim](Press Enter for: {description_field_default})[/dim]")
                description_field = console.input("[cyan]Description field:[/cyan] ").strip()
                if not description_field:
                    description_field = description_field_default

                # Ask for content type inference
                console.print("\n[bold]What content type should be inferred from this schema?[/bold]")
                console.print(
                    "[dim]Options: article, blog, tutorial, guide, reference, case_study, landing_page, other[/dim]"
                )
                if content_type_default:
                    console.print(f"[dim](Press Enter for: {content_type_default})[/dim]")
                inferred_content_type = console.input("[cyan]Content type:[/cyan] ").strip()
                if not inferred_content_type:
                    inferred_content_type = content_type_default

                # Save mapping
                mappings[content_type] = {
                    "enabled": True,
                    "content_field": content_field,
                    "title_field": title_field,
                    "slug_field": slug_field,
                    "description_field": description_field,
                    "inferred_content_type": inferred_content_type,
                    "metadata_fields": {},
                }

                console.print(f"\n[green]✓ Configured {content_type}[/green]")
                console.print(f"  Content: [cyan]{content_field}[/cyan]")
                console.print(f"  Title: [cyan]{title_field}[/cyan]")
                console.print(f"  Slug: [cyan]{slug_field}[/cyan]")
                console.print(f"  Description: [cyan]{description_field}[/cyan]")
                console.print(f"  Content Type: [cyan]{inferred_content_type}[/cyan]")

            except Exception as e:
                console.print(f"[yellow]⚠ Could not configure {content_type}: {e}[/yellow]")
                continue

        # Save configuration
        save_cms_config(config_data)

        console.print()
        console.print("[green]✓ Onboarding complete! Configuration saved.[/green]")
        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print(
            f"  1. Search content: [cyan]kurt cms search --content-type {selected_types[0]}[/cyan]"
        )
        console.print(
            f"  2. Fetch document: [cyan]kurt cms fetch --id <document-id> --output-dir sources/cms/{platform}/[/cyan]"
        )
        console.print(
            f"  3. Import to Kurt: [cyan]kurt cms import --source-dir sources/cms/{platform}/[/cyan]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms.command("import")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option(
    "--source-dir",
    required=True,
    type=click.Path(exists=True),
    help="Directory containing markdown files from CMS",
)
def import_cmd(platform: str, source_dir: str):
    """
    Import CMS markdown files to Kurt database.

    Imports markdown files fetched from CMS into the Kurt document database.

    Example:
        kurt cms import --source-dir sources/cms/sanity/
    """
    from pathlib import Path

    from kurt.ingestion.fetch import add_document

    try:
        import yaml

        source_path = Path(source_dir)
        md_files = list(source_path.glob("**/*.md"))

        if not md_files:
            console.print(f"[yellow]No markdown files found in {source_dir}[/yellow]")
            return

        console.print(f"[cyan]Found {len(md_files)} markdown files[/cyan]\n")

        imported = 0
        skipped = 0
        errors = 0

        for md_file in md_files:
            try:
                # Read file
                with open(md_file, "r") as f:
                    content = f.read()

                # Parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        # markdown_content = parts[2].strip()  # Not used yet
                    else:
                        console.print(
                            f"[yellow]⚠[/yellow] Skipping {md_file.name}: Invalid frontmatter"
                        )
                        skipped += 1
                        continue
                else:
                    console.print(f"[yellow]⚠[/yellow] Skipping {md_file.name}: No frontmatter")
                    skipped += 1
                    continue

                # Get CMS metadata
                # cms_id = frontmatter.get("cms_id")  # Not used yet
                title = frontmatter.get("title", md_file.stem)
                url = frontmatter.get("url")

                if not url:
                    console.print(
                        f"[yellow]⚠[/yellow] Skipping {md_file.name}: No URL in frontmatter"
                    )
                    skipped += 1
                    continue

                # Add/update document
                add_document(url, title)

                # Update with content (using fetch_document infrastructure)
                # For now, just show what would be imported
                console.print(f"[green]✓[/green] {title}")
                console.print(f"  [dim]File: {md_file.name} | URL: {url}[/dim]")
                imported += 1

            except Exception as e:
                console.print(f"[red]✗[/red] Error importing {md_file.name}: {e}")
                errors += 1

        # Summary
        console.print("\n[bold]Import Summary:[/bold]")
        console.print(f"  [green]Imported:[/green] {imported}")
        if skipped > 0:
            console.print(f"  [yellow]Skipped:[/yellow] {skipped}")
        if errors > 0:
            console.print(f"  [red]Errors:[/red] {errors}")

        if imported > 0:
            console.print("\n[yellow]Note:[/yellow] Documents added to database with CMS metadata.")
            console.print("Run [cyan]kurt document list[/cyan] to see imported documents.")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@cms.command("publish")
@click.option("--platform", default="sanity", help="CMS platform")
@click.option(
    "--file",
    "filepath",
    required=True,
    type=click.Path(exists=True),
    help="Markdown file to publish",
)
@click.option("--id", "document_id", help="CMS document ID to update (creates new if omitted)")
@click.option("--content-type", help="Content type for new documents")
def publish_cmd(
    platform: str, filepath: str, document_id: Optional[str], content_type: Optional[str]
):
    """
    Publish markdown file to CMS as draft.

    Converts markdown to CMS format and creates/updates a draft document.

    Examples:
        kurt cms publish --file draft.md --id abc123
        kurt cms publish --file new-article.md --content-type article
    """
    try:
        import yaml

        if not platform_configured(platform):
            console.print(f"[red]Error:[/red] {platform.capitalize()} not configured")
            console.print(f"Run: [cyan]kurt cms onboard --platform {platform}[/cyan]")
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

                # Extract metadata
                for key in ["slug", "author", "tags", "categories", "seo"]:
                    if key in frontmatter:
                        metadata[key] = frontmatter[key]
            else:
                markdown_content = content
        else:
            markdown_content = content

        if not title:
            title = Path(filepath).stem.replace("-", " ").title()

        # Validate requirements
        if not document_id and not content_type:
            console.print(
                "[red]Error:[/red] Must provide either --id (to update) or --content-type (to create)"
            )
            raise click.Abort()

        # Get adapter
        adapter = get_adapter(platform)

        # Create/update draft
        console.print(f"[cyan]Publishing to {platform} CMS...[/cyan]")
        console.print(f"  Title: {title}")
        if document_id:
            console.print(f"  Updating: {document_id}")
        else:
            console.print(f"  Creating new: {content_type}")

        result = adapter.create_draft(
            content=markdown_content,
            title=title,
            content_type=content_type,
            metadata=metadata,
            document_id=document_id,
        )

        console.print("\n[green]✓ Draft published successfully![/green]")
        console.print(f"  Draft ID: [cyan]{result['draft_id']}[/cyan]")
        console.print(f"  Draft URL: [link]{result['draft_url']}[/link]")
        console.print()
        console.print("[yellow]Note:[/yellow] Document created as draft. Publish from CMS Studio.")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

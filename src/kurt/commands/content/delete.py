"""Delete command - Delete content from project."""

import click
from rich.console import Console

console = Console()


@click.command("delete")
@click.argument("identifier")
@click.option(
    "--delete-content",
    is_flag=True,
    help="Also delete content file from filesystem",
)
@click.option(
    "--yes",
    "-y",
    "yes_flag",
    is_flag=True,
    help="Skip confirmation prompt (for automation/CI)",
)
@click.option(
    "--force",
    is_flag=True,
    hidden=True,
    help="[DEPRECATED: use --yes/-y instead] Skip confirmation prompt",
)
def delete_document_cmd(identifier: str, delete_content: bool, yes_flag: bool, force: bool):
    """
    Delete content from your project.

    IDENTIFIER can be a document ID, URL, or file path.

    Examples:
        kurt content delete 550e8400-e29b-41d4-a716-446655440000
        kurt content delete 550e8400 --delete-content
        kurt content delete 550e8400 --force
        kurt content delete https://example.com/article
        kurt content delete ./docs/article.md
    """
    from kurt.content.document import delete_document, get_document
    from kurt.content.filtering import resolve_identifier_to_doc_id

    try:
        # Resolve identifier to document ID (supports partial UUIDs)
        doc_id = resolve_identifier_to_doc_id(identifier)

        # Get document first to show what will be deleted
        doc = get_document(doc_id)

        # Show what will be deleted
        console.print("\n[yellow]About to delete:[/yellow]")
        console.print(f"  ID: [cyan]{doc.id}[/cyan]")
        console.print(f"  Title: {doc.title or 'Untitled'}")
        console.print(f"  URL: {doc.source_url or 'N/A'}")

        if delete_content:
            console.print("  [red]Content file will also be deleted[/red]")

        # Handle --yes/-y and deprecated --force
        if force and not yes_flag:
            console.print("[yellow]⚠️  --force is deprecated, use --yes or -y instead[/yellow]")

        # Confirm deletion
        if not (yes_flag or force):
            confirm = console.input("\n[bold]Are you sure? (y/N):[/bold] ")
            if confirm.lower() != "y":
                console.print("[dim]Cancelled[/dim]")
                return

        # Delete document
        result = delete_document(doc_id, delete_content=delete_content)

        console.print(f"\n[green]✓[/green] Deleted document: [cyan]{result['deleted_id']}[/cyan]")
        console.print(f"  Title: {result['title']}")

        if delete_content:
            if result["content_deleted"]:
                console.print("  [green]✓[/green] Content file deleted")
            else:
                console.print("  [yellow]Content file not found or not deleted[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

"""Delete command - Delete content from project."""

import click
from rich.console import Console

console = Console()


@click.command("delete")
@click.argument("document_id")
@click.option(
    "--delete-content",
    is_flag=True,
    help="Also delete content file from filesystem",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete_document_cmd(document_id: str, delete_content: bool, force: bool):
    """
    Delete content from your project.

    Examples:
        kurt content delete 550e8400-e29b-41d4-a716-446655440000
        kurt content delete 550e8400 --delete-content
        kurt content delete 550e8400 --force
    """
    from kurt.content.document import delete_document, get_document

    try:
        # Get document first to show what will be deleted
        doc = get_document(document_id)

        # Show what will be deleted
        console.print("\n[yellow]About to delete:[/yellow]")
        console.print(f"  ID: [cyan]{doc.id}[/cyan]")
        console.print(f"  Title: {doc.title or 'Untitled'}")
        console.print(f"  URL: {doc.source_url or 'N/A'}")

        if delete_content:
            console.print("  [red]Content file will also be deleted[/red]")

        # Confirm deletion
        if not force:
            confirm = console.input("\n[bold]Are you sure? (y/N):[/bold] ")
            if confirm.lower() != "y":
                console.print("[dim]Cancelled[/dim]")
                return

        # Delete document
        result = delete_document(document_id, delete_content=delete_content)

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

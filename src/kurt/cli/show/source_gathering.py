"""Show source gathering strategy command."""

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command()
@track_command
def source_gathering_cmd():
    """
    Display iterative source gathering strategy.

    Shows the mandatory multi-method approach for discovering and gathering
    content sources. Extracted from agent instructions.

    Examples:
        kurt show source-gathering
    """
    console.print()
    console.print("[bold cyan]⚠️ Iterative Source Gathering Strategy[/bold cyan]")
    console.print()

    console.print("[yellow]When gathering sources, MUST follow multi-method approach:[/yellow]")
    console.print()

    # Section 1: Try Multiple Query Variants
    console.print("[bold]1. Try Multiple Query Variants (3-5 attempts minimum)[/bold]")
    console.print()
    console.print("   [dim]Different phrasings:[/dim]")
    console.print('   "authentication" → "auth" → "login" → "user verification"')
    console.print()
    console.print("   [dim]Related terms:[/dim]")
    console.print('   "API" → "REST API" → "GraphQL" → "webhooks"')
    console.print()
    console.print("   [dim]Broader/narrower:[/dim]")
    console.print('   "deployment" → "Docker deployment" → "Kubernetes deployment"')
    console.print()

    # Section 2: Combine Multiple Discovery Methods
    console.print("[bold]2. Combine Multiple Discovery Methods[/bold]")
    console.print()
    console.print("   [dim]Start with semantic search:[/dim]")
    console.print('   [cyan]kurt content search "query"[/cyan]')
    console.print()
    console.print("   [dim]Then try entity filtering:[/dim]")
    console.print('   [cyan]kurt content list --with-entity "Topic:query"[/cyan]')
    console.print()
    console.print("   [dim]Explore related entities:[/dim]")
    console.print("   [cyan]kurt content list-entities topic[/cyan] → find related topics")
    console.print()
    console.print("   [dim]Check clusters:[/dim]")
    console.print("   [cyan]kurt content list-clusters[/cyan] → browse related clusters")
    console.print()
    console.print("   [dim]Use link analysis:[/dim]")
    console.print("   [cyan]kurt content links <doc-id>[/cyan] → find prerequisites/related docs")
    console.print()

    # Section 3: Fan Out to Related Topics
    console.print("[bold]3. Fan Out to Related Topics/Technologies[/bold]")
    console.print()
    console.print('   [dim]If searching for "authentication", also check:[/dim]')
    console.print('   "OAuth", "JWT", "session management", "authorization"')
    console.print()
    console.print('   [dim]If searching for "Python", also check:[/dim]')
    console.print('   "FastAPI", "Django", "Flask", "Python libraries"')
    console.print()

    # Section 4: Document All Findings
    console.print("[bold]4. Document ALL Findings in plan.md[/bold]")
    console.print()
    console.print('   • Update "Sources of Ground Truth" section with all found sources')
    console.print("   • Include path and purpose for each source")
    console.print("   • Link sources to documents in document_level_details")
    console.print()

    # Anti-patterns
    console.print("[bold red]❌ Never:[/bold red]")
    console.print("   Single search attempt and give up")
    console.print()

    console.print("[bold green]✅ Always:[/bold green]")
    console.print("   Try variants, multiple methods, related topics")
    console.print()

    console.print("[dim]💡 Full details: See @kurt-main rule 'Content Discovery' section[/dim]")
    console.print()

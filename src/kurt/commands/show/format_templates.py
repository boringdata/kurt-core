"""Show format templates command."""

import re
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


def get_template_description(template_path: Path) -> str:
    """Extract description from template file."""
    try:
        with open(template_path, "r") as f:
            content = f.read(500)  # Read first 500 chars

            # Try to find first heading
            match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if match:
                # Remove " Template" suffix if present
                desc = match.group(1).replace(" Template", "")
                return desc

            # Try to find Purpose in Overview section
            match = re.search(r"- \*\*Purpose:\*\*\s+(.+)", content)
            if match:
                return match.group(1).strip()

            return "No description"
    except Exception:
        return "No description"


def categorize_template(name: str) -> str:
    """Categorize template as internal or public-facing."""
    internal_keywords = ["positioning", "icp", "persona", "campaign", "launch"]

    for keyword in internal_keywords:
        if keyword in name.lower():
            return "internal"

    return "public"


@click.command()
@track_command
def format_templates_cmd():
    """
    List available format templates.

    Shows both system templates (from app installation) and customized templates
    (in your workspace). Templates are automatically copied to your workspace on
    first use for customization.

    Examples:
        kurt show format-templates
    """
    # Find app-space templates (from kurt installation)
    app_space_templates = {}
    package_root = Path(__file__).parent.parent.parent

    # Check agents directory for system templates
    agents_templates_dir = package_root / "agents" / "templates" / "formats"
    if agents_templates_dir.exists():
        for template_file in agents_templates_dir.glob("*.md"):
            app_space_templates[template_file.stem] = {
                "path": template_file,
                "description": get_template_description(template_file),
                "category": categorize_template(template_file.stem),
            }

    # Find user-space templates
    user_space_templates = {}
    user_templates_dir = Path.cwd() / "kurt" / "templates" / "formats"
    if user_templates_dir.exists():
        for template_file in user_templates_dir.glob("*.md"):
            user_space_templates[template_file.stem] = {
                "path": template_file,
                "description": get_template_description(template_file),
                "category": categorize_template(template_file.stem),
            }

    # Display system templates
    console.print()
    console.print("[bold cyan]📄 Format Templates[/bold cyan]")
    console.print()

    if app_space_templates:
        console.print(f"[bold]System Templates ({len(app_space_templates)} available):[/bold]")
        console.print()

        # Categorize templates
        internal = {k: v for k, v in app_space_templates.items() if v["category"] == "internal"}
        public = {k: v for k, v in app_space_templates.items() if v["category"] == "public"}

        if internal:
            console.print("[dim]Internal Artifacts:[/dim]")
            for name in sorted(internal.keys()):
                desc = internal[name]["description"]
                customized = name in user_space_templates
                marker = "✓" if customized else "•"
                console.print(f"  {marker} [cyan]{name}[/cyan]  {desc}")
            console.print()

        if public:
            console.print("[dim]Public-Facing Assets:[/dim]")
            for name in sorted(public.keys()):
                desc = public[name]["description"]
                customized = name in user_space_templates
                marker = "✓" if customized else "•"
                console.print(f"  {marker} [cyan]{name}[/cyan]  {desc}")
            console.print()
    else:
        console.print("[yellow]No system templates found[/yellow]")
        console.print()

    # Display customized templates
    if user_space_templates:
        console.print(
            f"[bold]Customized Templates ({len(user_space_templates)} in your workspace):[/bold]"
        )
        console.print()
        for name in sorted(user_space_templates.keys()):
            desc = user_space_templates[name]["description"]
            console.print(f"  ✓ [green]{name}[/green]  (customized for your style)")
        console.print()

    # Display helpful message
    if not user_space_templates:
        console.print(
            "[dim]💡 First time using a template? It will be copied to kurt/templates/formats/ for customization.[/dim]"
        )
    else:
        console.print(
            "[dim]💡 Templates marked with ✓ are customized in your workspace (kurt/templates/formats/)[/dim]"
        )

    console.print()

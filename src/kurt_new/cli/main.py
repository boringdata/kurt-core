"""Kurt CLI - Main command-line interface."""

import sys

import click
from dotenv import load_dotenv

load_dotenv()


class LazyGroup(click.Group):
    """A Click group that lazily loads subcommands."""

    def __init__(self, *args, lazy_subcommands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_subcommands = lazy_subcommands or {}
        self._loaded_commands = {}

    def list_commands(self, ctx):
        lazy = list(self.lazy_subcommands.keys())
        regular = list(self.commands.keys())
        return sorted(set(lazy + regular))

    def get_command(self, ctx, name):
        if name in self.commands:
            return self.commands[name]

        if name in self.lazy_subcommands:
            if name not in self._loaded_commands:
                module_path, cmd_name = self.lazy_subcommands[name]
                module = __import__(module_path, fromlist=[cmd_name])
                self._loaded_commands[name] = getattr(module, cmd_name)
            return self._loaded_commands[name]
        return None


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "content": ("kurt_new.documents.cli", "content_group"),
        "integrations": ("kurt_new.integrations.cli", "integrations_group"),
        "workflows": ("kurt_new.cli.workflows", "workflows_group"),
        "research": ("kurt_new.workflows.research.cli", "research_group"),
        "signals": ("kurt_new.workflows.signals.cli", "signals_group"),
        "admin": ("kurt_new.cli.admin", "admin"),
        "show": ("kurt_new.cli.show", "show_group"),
    },
)
@click.version_option(prog_name="kurt")
@click.pass_context
def main(ctx):
    """
    Kurt - Document intelligence CLI tool.

    Transform documents into structured knowledge graphs.
    """
    from kurt_new.config import config_file_exists

    # Skip migration check for init and admin (which includes migrate)
    if ctx.invoked_subcommand in ["init", "admin"]:
        return

    # Skip migration check if running in hook mode
    if "--hook-cc" in sys.argv:
        return

    # Check if project is initialized
    if not config_file_exists():
        return

    _check_migrations()


def _check_migrations():
    """Check and optionally apply pending database migrations."""
    try:
        from kurt_new.db.migrations.utils import (
            apply_migrations,
            check_migrations_needed,
            get_pending_migrations,
        )

        if not check_migrations_needed():
            return

        from rich.console import Console

        console = Console()
        pending = get_pending_migrations()
        is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

        console.print()
        console.print("[yellow]⚠ Database migrations are pending[/yellow]")
        console.print(f"[dim]{len(pending)} migration(s) need to be applied[/dim]")
        console.print()
        console.print(
            "[dim]Run [cyan]kurt admin migrate apply[/cyan] to update your database[/dim]"
        )
        console.print("[dim]Or run [cyan]kurt admin migrate status[/cyan] to see details[/dim]")
        console.print()

        if is_interactive:
            from rich.prompt import Confirm

            if Confirm.ask("[bold]Apply migrations now?[/bold]", default=False):
                result = apply_migrations(auto_confirm=True)
                if not result["success"]:
                    raise click.Abort()
            else:
                console.print(
                    "[yellow]⚠ Proceeding without migration. Some features may not work.[/yellow]"
                )
                console.print()
        else:
            result = apply_migrations(auto_confirm=True, silent=True)
            if result["success"] and result["applied"]:
                console.print(f"[green]✓ Applied {result['count']} migration(s)[/green]")
                console.print()

    except ImportError:
        pass
    except Exception:
        pass


from kurt_new.cli.init import init  # noqa: E402
from kurt_new.cli.status import status  # noqa: E402
from kurt_new.cli.update import update  # noqa: E402

main.add_command(init)
main.add_command(status)
main.add_command(update)


if __name__ == "__main__":
    main()

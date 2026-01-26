"""Kurt CLI - Main command-line interface.

Simplified CLI structure with ~12 top-level commands:
- init, status, doctor, repair, serve: Core operations
- workflow: Unified workflow management (TOML + MD)
- tool: All tools (map, fetch, llm, embed, save, sql, research, signals)
- docs: Document management
- sync: Version control (pull, push, branch, merge)
- connect: CMS and analytics integrations
- cloud: Kurt Cloud operations
- admin: Administrative commands
- help: Documentation and guides
"""

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
        # Core command groups
        "workflow": ("kurt.workflows.toml.cli", "workflow_group"),
        "tool": ("kurt.tools.cli", "tools_group"),
        "docs": ("kurt.documents.cli", "docs_group"),
        "sync": ("kurt.isolation.cli", "sync_group"),
        "connect": ("kurt.integrations.cli", "integrations_group"),
        "cloud": ("kurt.cloud.cli", "cloud_group"),
        "admin": ("kurt.admin.cli", "admin"),
        "help": ("kurt.cli.show", "show_group"),
    },
)
@click.version_option(package_name="kurt-core", prog_name="kurt")
@click.pass_context
def main(ctx):
    """
    Kurt - Document intelligence CLI tool.

    Transform documents into structured knowledge graphs.
    """
    from kurt.config import config_file_exists

    # Skip migration check for init, admin, cloud (which handle DB themselves)
    if ctx.invoked_subcommand in ["init", "admin", "cloud"]:
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
        from kurt.db.migrations.utils import (
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


# Core top-level commands (not under any group)
from kurt.cli.doctor import doctor_cmd, repair_cmd  # noqa: E402
from kurt.cli.init import init  # noqa: E402
from kurt.web.cli import serve  # noqa: E402
from kurt.status import status  # noqa: E402

main.add_command(init)
main.add_command(status)
main.add_command(serve)
main.add_command(doctor_cmd, name="doctor")
main.add_command(repair_cmd, name="repair")


if __name__ == "__main__":
    main()

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


def _auto_migrate_schema():
    """Auto-migrate schema on startup (adds missing columns)."""
    try:
        from kurt.db.auto_migrate import auto_migrate

        changes = auto_migrate()
        if changes:
            from rich.console import Console

            console = Console()
            for table, cols in changes.items():
                if cols and cols[0].startswith("[created"):
                    console.print(f"[dim]Created table: {table}[/dim]")
                else:
                    console.print(f"[dim]Added columns to {table}: {', '.join(cols)}[/dim]")
    except Exception:
        pass  # Silent fail - don't block CLI


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

    # Skip auto-migrate for init command (no DB yet)
    if ctx.invoked_subcommand in ["init", "help"]:
        return

    # Skip if no project initialized
    if not config_file_exists():
        return

    # Auto-migrate schema (adds missing columns)
    _auto_migrate_schema()


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

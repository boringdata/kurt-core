"""Kurt CLI - Main command-line interface.

Simplified CLI structure with ~13 top-level commands:
- init, status, doctor, repair, serve: Core operations
- workflow: Unified workflow management (TOML + MD in workflows/)
- tool: All tools (map, fetch, llm, embed, save, sql, research, signals)
- docs: Document management
- sync: Version control (pull, push, branch, merge)
- connect: CMS and analytics integrations
- cloud: Kurt Cloud operations
- admin: Administrative commands
- guides: Interactive guides for agents (project, source, template, etc.)
- help: Documentation and tool references

Robot Mode (Agent-Friendly Output):
- Global --json flag for structured JSON output
- Auto-detects piped output and switches to JSON
- Command aliases for LLM typo tolerance (e.g., doc -> docs)
"""


import click
from dotenv import load_dotenv

load_dotenv()

# Import robot mode utilities for global --json flag
from kurt.cli.robot import OutputContext  # noqa: E402


def _auto_migrate_schema():
    """Auto-migrate schema on startup (adds missing columns and tables)."""
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

    # Also ensure Dolt observability tables exist if using Dolt
    try:
        from pathlib import Path

        dolt_path = Path.cwd() / ".dolt"
        if dolt_path.exists():
            from kurt.db.dolt import DoltDB, check_schema_exists, init_observability_schema

            db = DoltDB(Path.cwd())
            schema_status = check_schema_exists(db)

            # Only initialize if any table is missing
            if not all(schema_status.values()):
                missing = [t for t, exists in schema_status.items() if not exists]
                init_observability_schema(db)

                from rich.console import Console

                console = Console()
                for table in missing:
                    console.print(f"[dim]Created Dolt table: {table}[/dim]")

            # Cleanup stale "running" workflows (orphaned processes)
            from kurt.observability.lifecycle import cleanup_stale_workflows

            stale_count = cleanup_stale_workflows(db, stale_minutes=60)
            if stale_count > 0:
                from rich.console import Console

                console = Console()
                console.print(f"[dim]Cleaned up {stale_count} stale workflow(s)[/dim]")
    except Exception:
        pass  # Silent fail - don't block CLI


class AliasedLazyGroup(click.Group):
    """A Click group with lazy loading and command aliases for LLM typo tolerance.

    Command aliases allow agents to use variations like:
    - kurt doc list -> kurt docs list
    - kurt stat -> kurt status
    - kurt wf run -> kurt workflow run
    """

    # Command aliases for LLM typo tolerance
    # Maps alias -> canonical command name
    ALIASES: dict[str, str] = {
        # docs variations
        "doc": "docs",
        "document": "docs",
        "documents": "docs",
        # status variations
        "stat": "status",
        "st": "status",
        # workflow variations
        "wf": "workflow",
        "workflows": "workflow",
        # agents variations
        "agent": "agents",
        # init variations
        "initialize": "init",
        # tool variations
        "tools": "tool",
        # config variations
        "cfg": "config",
        # sync variations
        "pull": "sync",  # common git alias
        "push": "sync",
    }

    def __init__(self, *args, lazy_subcommands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_subcommands = lazy_subcommands or {}
        self._loaded_commands = {}

    def list_commands(self, ctx):
        lazy = list(self.lazy_subcommands.keys())
        regular = list(self.commands.keys())
        return sorted(set(lazy + regular))

    def get_command(self, ctx, name):
        # Resolve alias first (LLM typo tolerance)
        name = self.ALIASES.get(name, name)

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
    cls=AliasedLazyGroup,
    lazy_subcommands={
        # Core command groups
        "workflow": ("kurt.workflows.toml.cli", "workflow_group"),
        "tool": ("kurt.tools.cli", "tools_group"),
        "docs": ("kurt.documents.cli", "docs_group"),
        "sync": ("kurt.db.isolation.cli", "sync_group"),
        "connect": ("kurt.integrations.cli", "integrations_group"),
        "cloud": ("kurt.cloud.cli", "cloud_group"),
        "admin": ("kurt.admin.cli", "admin"),
        "guides": ("kurt.cli.guides", "guides_group"),
        "help": ("kurt.cli.show", "show_group"),
        # Agent workflows
        "agents": ("kurt.workflows.agents.cli", "agents_group"),
    },
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="JSON output for AI agents (beads-style structured responses)",
)
@click.option(
    "--robot",
    "json_output",
    is_flag=True,
    hidden=True,
    help="Alias for --json",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Minimal output (suppress non-essential messages)",
)
@click.version_option(package_name="kurt-core", prog_name="kurt")
@click.pass_context
def main(ctx, json_output: bool, quiet: bool):
    """
    Kurt - Document intelligence CLI tool.

    Transform documents into structured knowledge graphs.

    \b
    Robot Mode (for AI agents):
      --json    Structured JSON output with success/error envelopes
      Piped output automatically uses JSON (no flag needed)

    \b
    Command Aliases (typo tolerance):
      doc, docs, documents -> docs
      stat, st -> status
      wf, workflow, workflows -> workflow
    """
    from kurt.config import config_file_exists

    # Initialize Click context with robot mode settings
    ctx.ensure_object(dict)
    ctx.obj["output"] = OutputContext(json_output, quiet)
    ctx.obj["json_output"] = json_output  # Backwards compat for existing commands

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
from kurt.status import status  # noqa: E402
from kurt.web.cli import serve  # noqa: E402

main.add_command(init)
main.add_command(status)
main.add_command(serve)
main.add_command(doctor_cmd, name="doctor")
main.add_command(repair_cmd, name="repair")


if __name__ == "__main__":
    main()

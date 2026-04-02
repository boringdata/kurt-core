"""Kurt init command - Initialize a new project with Git+Dolt isolation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


def _check_git_repo() -> bool:
    """Check if current directory is a Git repository."""
    return (Path.cwd() / ".git").is_dir()


def _check_dolt_repo() -> bool:
    """Check if current directory has a Dolt database."""
    return (Path.cwd() / ".dolt").is_dir()


def _check_config_exists() -> bool:
    """Check if kurt.toml exists."""
    return (Path.cwd() / "kurt.toml").exists()


def _check_workflows_dir() -> bool:
    """Check if workflows directory exists."""
    return (Path.cwd() / "workflows").is_dir()


def _check_hooks_installed() -> bool:
    """Check if Git hooks are installed."""
    hooks_dir = Path.cwd() / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return False
    # Check for at least one Kurt hook
    for hook_name in ["post-checkout", "post-commit", "pre-push"]:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            try:
                content = hook_path.read_text()
                if "Kurt Git Hook" in content:
                    return True
            except OSError:
                pass
    return False


def _detect_partial_init() -> dict[str, bool]:
    """Detect which components are already initialized."""
    return {
        "git": _check_git_repo(),
        "dolt": _check_dolt_repo(),
        "config": _check_config_exists(),
        "workflows": _check_workflows_dir(),
        "hooks": _check_hooks_installed(),
    }


def _git_init() -> bool:
    """Initialize Git repository if not already initialized."""
    if _check_git_repo():
        return True
    try:
        subprocess.run(
            ["git", "init"],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to initialize Git: {e.stderr.decode()}[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]Git not found. Please install Git.[/red]")
        return False


def _check_dolt_installed() -> bool:
    """Check if Dolt is installed and available in PATH."""
    try:
        subprocess.run(
            ["dolt", "version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _install_dolt() -> bool:
    """Install Dolt using the official install script."""
    console.print("[dim]Installing Dolt...[/dim]")
    try:
        # Use the official Dolt install script
        result = subprocess.run(
            ["bash", "-c", "curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | sudo bash"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            console.print(f"[red]Failed to install Dolt: {result.stderr}[/red]")
            return False

        # Verify installation
        if _check_dolt_installed():
            console.print("[green]  ✓ Dolt installed successfully[/green]")
            return True
        else:
            console.print("[red]Dolt installation completed but dolt command not found in PATH[/red]")
            return False
    except subprocess.TimeoutExpired:
        console.print("[red]Dolt installation timed out[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Failed to install Dolt: {e}[/red]")
        return False


def _get_git_identity() -> tuple[str, str]:
    """Get git user.name and user.email, with fallbacks."""
    name = "Kurt User"
    email = "kurt@localhost"

    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            name = result.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            email = result.stdout.strip()
    except Exception:
        pass

    return name, email


def _configure_dolt_identity() -> bool:
    """Configure Dolt with git identity or defaults."""
    name, email = _get_git_identity()

    try:
        # Set Dolt user config (local to avoid requiring --global)
        subprocess.run(
            ["dolt", "config", "--global", "--add", "user.name", name],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["dolt", "config", "--global", "--add", "user.email", email],
            capture_output=True,
            check=True,
        )
        return True
    except Exception:
        return False


def _get_git_branch() -> str | None:
    """Get current Git branch name."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _sync_dolt_branch_to_git() -> bool:
    """Sync Dolt branch to match current Git branch."""
    git_branch = _get_git_branch()
    if not git_branch or git_branch == "main":
        return True  # Nothing to do

    try:
        # Rename main branch to match git branch
        subprocess.run(
            ["dolt", "branch", "-m", "main", git_branch],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        # Branch rename failed, try checkout -b instead
        try:
            subprocess.run(
                ["dolt", "checkout", "-b", git_branch],
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
    except Exception:
        return False


def _dolt_init() -> bool:
    """Initialize Dolt database if not already initialized."""
    if _check_dolt_repo():
        return True

    # Check if Dolt is installed, install if not
    if not _check_dolt_installed():
        if not _install_dolt():
            console.print("[red]Dolt installation failed. Install manually from https://docs.dolthub.com/introduction/installation[/red]")
            return False

    # Configure Dolt identity from git config or defaults
    _configure_dolt_identity()

    try:
        # Set env var to skip Dolt registration prompts for local-only use
        env = os.environ.copy()
        env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"

        subprocess.run(
            ["dolt", "init"],
            capture_output=True,
            check=True,
            env=env,
        )

        # Sync Dolt branch to match Git branch
        _sync_dolt_branch_to_git()

        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to initialize Dolt: {e.stderr.decode()}[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]Dolt not found after installation. Check your PATH.[/red]")
        return False


def _create_observability_tables() -> bool:
    """Create observability tables in Dolt database."""
    try:
        from kurt.db.dolt import DoltDB, init_observability_schema

        db = DoltDB(Path.cwd())
        init_observability_schema(db)
        return True
    except Exception as e:
        console.print(f"[red]Failed to create observability tables: {e}[/red]")
        return False


def _install_hooks() -> bool:
    """Install Git hooks for auto-sync."""
    try:
        from kurt.db.isolation.hooks import install_hooks

        result = install_hooks(Path.cwd(), force=True)
        if result.errors:
            for error in result.errors:
                console.print(f"[yellow]Warning: {error}[/yellow]")
        return len(result.installed) > 0 or len(result.skipped) > 0
    except Exception as e:
        console.print(f"[red]Failed to install Git hooks: {e}[/red]")
        return False


def _create_config() -> bool:
    """Create kurt.toml configuration file."""
    import uuid

    config_path = Path.cwd() / "kurt.toml"

    # Skip if exists
    if config_path.exists():
        return True

    try:
        workspace_id = str(uuid.uuid4())

        # Create kurt.toml (TOML format)
        config_content = f'''# Kurt Project Configuration
# Auto-generated by 'kurt init'

[workspace]
id = "{workspace_id}"

[paths]
db = ".dolt"
sources = "sources"
projects = "projects"
rules = "rules"
workflows = "workflows"

[agent]
model = "openai/gpt-4o"

[tool.batch-llm]
model = "openai/gpt-4o-mini"
concurrency = 50

[tool.batch-embedding]
model = "openai/text-embedding-3-small"

[tool.fetch]
fetch_engine = "trafilatura"

[telemetry]
enabled = true

[cloud]
auth = false
'''
        config_path.write_text(config_content)
        return True
    except Exception as e:
        console.print(f"[red]Failed to create config file: {e}[/red]")
        return False


def _create_workflows_dir() -> bool:
    """Create workflows directory."""
    workflows_path = Path.cwd() / "workflows"
    try:
        workflows_path.mkdir(exist_ok=True)

        # Create a sample workflow file
        sample_path = workflows_path / "example.md"
        if not sample_path.exists():
            sample_content = '''---
name: example
title: Example Workflow
description: |
  This is an example agent workflow.
  Delete this file or modify it for your needs.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 10
  allowed_tools:
    - Bash
    - Read
    - Write
    - Glob
    - Grep

guardrails:
  max_tokens: 100000
  max_time: 300

inputs:
  task: "Describe your task here"

tags: [example]
---

# Example Workflow

This is an example workflow. Customize it for your needs.

## Task

{{task}}

## Instructions

1. Analyze the request
2. Take appropriate action
3. Report results
'''
            sample_path.write_text(sample_content)
        return True
    except Exception as e:
        console.print(f"[red]Failed to create workflows directory: {e}[/red]")
        return False


def _create_sources_dir() -> bool:
    """Create sources directory (gitignored)."""
    sources_path = Path.cwd() / "sources"
    try:
        sources_path.mkdir(exist_ok=True)
        return True
    except Exception as e:
        console.print(f"[red]Failed to create sources directory: {e}[/red]")
        return False


def _create_agents_dir() -> bool:
    """Create .agents directory with AGENTS.md from package."""
    agents_dir = Path.cwd() / ".agents"
    agents_md = agents_dir / "AGENTS.md"

    try:
        agents_dir.mkdir(exist_ok=True)

        # Copy AGENTS.md from package if not exists
        if not agents_md.exists():
            package_agents = Path(__file__).parent.parent / "agents" / "AGENTS.md"
            if package_agents.exists():
                import shutil
                shutil.copy2(package_agents, agents_md)
            else:
                # Create minimal AGENTS.md if package file not found
                agents_md.write_text("""# Kurt Agent Instructions

See https://github.com/wikumeo/kurt-core for documentation.

Run `kurt update` to get the latest agent instructions.
""")
        return True
    except Exception as e:
        console.print(f"[red]Failed to create .agents directory: {e}[/red]")
        return False


def _create_claude_config() -> bool:
    """Create .claude directory with symlink to AGENTS.md and hooks."""
    import json
    import shutil

    claude_dir = Path.cwd() / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    agents_md = Path.cwd() / ".agents" / "AGENTS.md"

    try:
        claude_dir.mkdir(exist_ok=True)

        # Create symlink to .agents/AGENTS.md if not exists
        if not claude_md.exists() and agents_md.exists():
            # Use relative symlink for portability
            claude_md.symlink_to("../.agents/AGENTS.md")

        # Install Claude Code hooks from package
        settings_source = Path(__file__).parent.parent / "agents" / "claude-settings.json"
        if settings_source.exists():
            dest_settings = claude_dir / "settings.json"
            with open(settings_source) as f:
                kurt_settings = json.load(f)

            if dest_settings.exists():
                # Merge hooks into existing settings
                with open(dest_settings) as f:
                    existing_settings = json.load(f)
                if "hooks" not in existing_settings:
                    existing_settings["hooks"] = {}
                existing_settings["hooks"].update(kurt_settings.get("hooks", {}))
                with open(dest_settings, "w") as f:
                    json.dump(existing_settings, f, indent=2)
            else:
                # Copy settings file
                shutil.copy2(settings_source, dest_settings)

        return True
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to create .claude config: {e}[/yellow]")
        return True  # Non-fatal


def _update_gitignore() -> bool:
    """Update .gitignore with Kurt-specific entries."""
    gitignore_path = Path.cwd() / ".gitignore"

    kurt_entries = [
        "# Kurt",
        "sources/",
        ".dolt/noms/",
        ".env",
    ]

    try:
        existing_content = ""
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text()

        # Check which entries are missing
        entries_to_add = []
        for entry in kurt_entries:
            # Skip comments when checking, but include them when adding
            if entry.startswith("#"):
                if entry not in existing_content:
                    entries_to_add.append(entry)
            else:
                # For actual patterns, check if line exists
                if entry not in existing_content.split("\n"):
                    entries_to_add.append(entry)

        if entries_to_add:
            # Add newline if file doesn't end with one
            if existing_content and not existing_content.endswith("\n"):
                existing_content += "\n"
            if existing_content and not existing_content.endswith("\n\n"):
                existing_content += "\n"

            with open(gitignore_path, "w") as f:
                f.write(existing_content)
                f.write("\n".join(entries_to_add))
                f.write("\n")

        return True
    except Exception as e:
        console.print(f"[red]Failed to update .gitignore: {e}[/red]")
        return False


@click.command()
@click.argument("path", default=".", type=click.Path())
@click.option(
    "--no-dolt",
    is_flag=True,
    default=False,
    help="Git-only mode (skip Dolt initialization)",
)
@click.option(
    "--no-hooks",
    is_flag=True,
    default=False,
    help="Skip Git hooks installation",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force initialization even if partially initialized",
)
@track_command
def init(path: str, no_dolt: bool, no_hooks: bool, force: bool):
    """
    Initialize a new Kurt project.

    Creates:
    - Git repository (if not exists)
    - Dolt database with observability tables
    - Git hooks for auto-sync
    - kurt.toml configuration file
    - workflows/ directory
    - content/ directory (gitignored)

    Use --no-dolt for Git-only mode without Dolt database.
    Use --no-hooks to skip Git hooks installation.
    Use --force to complete initialization of a partial setup.
    """
    import os

    # Change to target directory if specified
    if path != ".":
        target_path = Path(path).resolve()
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)
        os.chdir(target_path)

    cwd = Path.cwd()

    # Check for existing initialization
    status = _detect_partial_init()

    # If Dolt exists and not forcing, error out
    if status["dolt"] and not force and not no_dolt:
        console.print(f"[yellow]Kurt project already initialized at {cwd}[/yellow]")

        # Check what's missing
        missing = []
        if not status["config"]:
            missing.append("Config file")
        if not status["hooks"]:
            missing.append("Git hooks")
        if not status["workflows"]:
            missing.append("Workflows directory")

        if missing:
            console.print("\n[yellow]Existing project detected. Missing components:[/yellow]")
            for component in missing:
                console.print(f"  - {component}")
            console.print("\n[dim]Run 'kurt init --force' to complete setup.[/dim]")
            sys.exit(1)
        else:
            console.print("[dim]All components already initialized.[/dim]")
            sys.exit(1)

    console.print(f"[bold green]Initializing Kurt project in {cwd}[/bold green]\n")

    results = {}

    # Step 1: Initialize Git
    console.print("[dim]Initializing Git repository...[/dim]")
    if _git_init():
        results["git"] = True
        console.print("[green]  ✓ Git repository[/green]")
    else:
        results["git"] = False
        console.print("[red]  ✗ Git repository[/red]")
        sys.exit(2)

    # Step 2: Initialize Dolt (unless --no-dolt)
    if not no_dolt:
        console.print("[dim]Initializing Dolt database...[/dim]")
        if _dolt_init():
            results["dolt"] = True
            console.print("[green]  ✓ Dolt database[/green]")

            # Create observability tables
            console.print("[dim]Creating observability tables...[/dim]")
            if _create_observability_tables():
                results["tables"] = True
                console.print("[green]  ✓ Observability tables[/green]")
            else:
                results["tables"] = False
                console.print("[yellow]  ⚠ Observability tables (failed)[/yellow]")
        else:
            results["dolt"] = False
            console.print("[red]  ✗ Dolt database[/red]")
            sys.exit(2)
    else:
        results["dolt"] = None
        console.print("[dim]  - Dolt database (skipped)[/dim]")

    # Step 3: Install Git hooks (unless --no-hooks)
    if not no_hooks and not no_dolt:
        console.print("[dim]Installing Git hooks...[/dim]")
        if _install_hooks():
            results["hooks"] = True
            console.print("[green]  ✓ Git hooks installed[/green]")
        else:
            results["hooks"] = False
            console.print("[yellow]  ⚠ Git hooks (failed)[/yellow]")
    else:
        results["hooks"] = None
        reason = "no-hooks" if no_hooks else "no-dolt"
        console.print(f"[dim]  - Git hooks (skipped: {reason})[/dim]")

    # Step 4: Create config file
    console.print("[dim]Creating configuration file...[/dim]")
    if _create_config():
        results["config"] = True
        console.print("[green]  ✓ Config file created: kurt.toml[/green]")
    else:
        results["config"] = False
        console.print("[yellow]  ⚠ Config file (failed)[/yellow]")

    # Step 5: Create workflows directory
    console.print("[dim]Creating workflows directory...[/dim]")
    if _create_workflows_dir():
        results["workflows"] = True
        console.print("[green]  ✓ Workflows directory: workflows/[/green]")
    else:
        results["workflows"] = False
        console.print("[yellow]  ⚠ Workflows directory (failed)[/yellow]")

    # Step 6: Create sources directory
    console.print("[dim]Creating sources directory...[/dim]")
    if _create_sources_dir():
        results["sources"] = True
        console.print("[green]  ✓ Sources directory: sources/[/green]")
    else:
        results["sources"] = False
        console.print("[yellow]  ⚠ Sources directory (failed)[/yellow]")

    # Step 7: Update .gitignore
    console.print("[dim]Updating .gitignore...[/dim]")
    if _update_gitignore():
        results["gitignore"] = True
        console.print("[green]  ✓ .gitignore updated[/green]")
    else:
        results["gitignore"] = False
        console.print("[yellow]  ⚠ .gitignore (failed)[/yellow]")

    # Step 8: Create .agents directory with AGENTS.md
    console.print("[dim]Setting up agent instructions...[/dim]")
    if _create_agents_dir():
        results["agents"] = True
        console.print("[green]  ✓ Agent instructions: .agents/AGENTS.md[/green]")
    else:
        results["agents"] = False
        console.print("[yellow]  ⚠ Agent instructions (failed)[/yellow]")

    # Step 9: Create .claude config directory
    console.print("[dim]Setting up Claude Code config...[/dim]")
    if _create_claude_config():
        results["claude"] = True
        console.print("[green]  ✓ Claude config: .claude/CLAUDE.md → .agents/AGENTS.md[/green]")
    else:
        results["claude"] = False
        console.print("[yellow]  ⚠ Claude config (failed)[/yellow]")

    # Summary
    console.print()
    console.print(f"[bold green]Initialized Kurt project in {cwd}[/bold green]")

    # Count failures
    failures = sum(1 for v in results.values() if v is False)

    if failures > 0:
        console.print(f"[yellow]⚠ {failures} component(s) had issues[/yellow]")

    console.print()
    console.print("[dim]Run 'kurt doctor' to verify setup.[/dim]")

    # Exit with appropriate code
    if failures > 0:
        sys.exit(2)
    sys.exit(0)

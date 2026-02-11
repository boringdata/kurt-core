"""CLI commands for Kurt skill management.

Provides commands to install/uninstall Kurt as a Claude Code (OpenClaw) skill.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import click


@click.group()
def skill():
    """Skill management for AI assistants."""


@skill.command("install-openclaw")
@click.option("--force", is_flag=True, help="Overwrite existing installation")
@click.option("--dry-run", is_flag=True, help="Show what would be installed")
def install_openclaw(force: bool, dry_run: bool):
    """Install Kurt as an OpenClaw skill for Claude Code."""
    from kurt.skills.installer import install_skill, is_installed

    skill_dir = Path.home() / ".claude" / "skills" / "kurt"

    if is_installed(skill_dir) and not force and not dry_run:
        if not click.confirm(f"Kurt skill already exists at {skill_dir}. Overwrite?"):
            raise click.Abort()
        force = True

    if dry_run:
        click.echo("Would create:")
        click.echo(f"  {skill_dir}/SKILL.md")
        click.echo(f"  {skill_dir}/skill.py")
        click.echo(f"  {skill_dir}/README.md")
        return

    click.echo("Installing Kurt skill for Claude Code...\n")

    try:
        result_dir = install_skill(skill_dir, force=force)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))

    click.echo(f"  Created {result_dir}/SKILL.md")
    click.echo(f"  Created {result_dir}/skill.py")
    click.echo(f"  Created {result_dir}/README.md")

    # Verify kurt is in PATH
    if shutil.which("kurt"):
        click.echo("  Verified kurt is in PATH")
    else:
        click.echo("  Warning: 'kurt' not found in PATH")
        click.echo("  Make sure Kurt is installed: pip install kurt")

    click.echo("\nKurt skill installed successfully!\n")
    click.echo("Claude Code will now recognize:")
    click.echo("  /kurt fetch <url>")
    click.echo("  /kurt map <source>")
    click.echo("  /kurt workflow run <file>")
    click.echo("  /kurt tool list")
    click.echo("\nRestart Claude Code to activate the skill.")


@skill.command("uninstall-openclaw")
def uninstall_openclaw():
    """Remove Kurt skill from Claude Code."""
    from kurt.skills.installer import uninstall_skill

    skill_dir = Path.home() / ".claude" / "skills" / "kurt"

    if not skill_dir.exists():
        click.echo("Kurt skill not installed.")
        return

    if click.confirm(f"Remove {skill_dir}?"):
        uninstall_skill(skill_dir)
        click.echo("Kurt skill removed.")


@skill.command("status")
def skill_status():
    """Check Kurt skill installation status."""
    from kurt.skills.installer import is_installed

    skill_dir = Path.home() / ".claude" / "skills" / "kurt"

    if is_installed(skill_dir):
        click.echo("Kurt skill: installed")
        click.echo(f"Location: {skill_dir}")

        # List installed files
        for f in sorted(skill_dir.iterdir()):
            if f.is_file():
                click.echo(f"  {f.name}")
    else:
        click.echo("Kurt skill: not installed")
        click.echo("Run: kurt skill install-openclaw")

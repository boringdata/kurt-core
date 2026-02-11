"""Install and uninstall Kurt skills for Claude Code (OpenClaw).

Copies skill templates to ~/.claude/skills/kurt/ for Claude Code discovery.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Directory containing the skill template files
_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Default install location for Claude Code skills
_DEFAULT_SKILLS_DIR = Path.home() / ".claude" / "skills" / "kurt"


def install_skill(
    target_dir: Path | None = None,
    *,
    force: bool = False,
) -> Path:
    """Install Kurt skill files to Claude Code skills directory.

    Copies SKILL.md, skill.py, and README.md to the target directory.

    Args:
        target_dir: Target directory (default: ~/.claude/skills/kurt/)
        force: Overwrite existing files if True

    Returns:
        Path to the installed skill directory

    Raises:
        FileExistsError: If target_dir exists and force is False
        FileNotFoundError: If template files are missing
    """
    target = target_dir or _DEFAULT_SKILLS_DIR

    if target.exists() and not force:
        raise FileExistsError(
            f"Skill already installed at {target}. Use --force to overwrite."
        )

    # Verify templates exist
    required_files = ["SKILL.md", "skill.py", "README.md"]
    for name in required_files:
        src = _TEMPLATES_DIR / name
        if not src.exists():
            raise FileNotFoundError(f"Template file not found: {src}")

    # Create target directory
    target.mkdir(parents=True, exist_ok=True)

    # Copy template files
    for name in required_files:
        src = _TEMPLATES_DIR / name
        dst = target / name
        shutil.copy2(src, dst)

    # Make skill.py executable
    skill_py = target / "skill.py"
    skill_py.chmod(skill_py.stat().st_mode | 0o111)

    return target


def uninstall_skill(target_dir: Path | None = None) -> bool:
    """Remove Kurt skill files from Claude Code skills directory.

    Args:
        target_dir: Target directory (default: ~/.claude/skills/kurt/)

    Returns:
        True if skill was removed, False if it wasn't installed
    """
    target = target_dir or _DEFAULT_SKILLS_DIR

    if not target.exists():
        return False

    shutil.rmtree(target)
    return True


def is_installed(target_dir: Path | None = None) -> bool:
    """Check if Kurt skill is installed.

    Args:
        target_dir: Target directory (default: ~/.claude/skills/kurt/)

    Returns:
        True if SKILL.md exists in the target directory
    """
    target = target_dir or _DEFAULT_SKILLS_DIR
    return (target / "SKILL.md").exists()

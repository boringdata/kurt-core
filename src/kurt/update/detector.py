"""Detect which files need updating."""

from dataclasses import dataclass
from pathlib import Path

from .hasher import compute_file_hash, was_file_modified


@dataclass
class FileUpdate:
    """Represents a file that can be updated."""

    rel_path: str  # Relative path from project root (e.g., ".claude/CLAUDE.md")
    local_path: Path  # Absolute path to local file
    package_path: Path  # Absolute path to file in package
    status: str  # needs_update, modified_locally, user_created, up_to_date
    category: str  # claude_main, claude_instructions, templates, etc.


@dataclass
class UpdateSummary:
    """Summary of files that can be updated."""

    needs_update: list[FileUpdate]  # Safe to update (unchanged locally)
    modified_locally: list[FileUpdate]  # Changed by user, needs prompt
    user_created: list[FileUpdate]  # Not in package, preserve
    up_to_date: list[FileUpdate]  # Already current


def get_package_plugin_path(ide: str) -> Path:
    """Get path to plugin directory in the installed package."""
    import kurt

    kurt_path = Path(kurt.__file__).parent
    plugin_dir = "claude_plugin" if ide == "claude" else "cursor_plugin"
    return kurt_path / plugin_dir


def detect_ide_installations() -> list[str]:
    """Detect which IDEs are installed in current directory."""
    ides = []
    if (Path.cwd() / ".claude").exists():
        ides.append("claude")
    if (Path.cwd() / ".cursor").exists():
        ides.append("cursor")
    return ides


def scan_directory_files(
    local_dir: Path, package_dir: Path, rel_prefix: str, category: str
) -> list[FileUpdate]:
    """
    Scan a directory for files to update.

    Args:
        local_dir: Local directory (e.g., .claude/instructions/)
        package_dir: Package directory with source files
        rel_prefix: Relative path prefix for tracking (e.g., ".claude/instructions")
        category: Category name for grouping (e.g., "claude_instructions")

    Returns:
        List of FileUpdate objects
    """
    updates = []

    # Get all files in package
    package_files = {}
    if package_dir.exists():
        for pkg_file in package_dir.rglob("*"):
            if pkg_file.is_file():
                rel_to_pkg = pkg_file.relative_to(package_dir)
                package_files[str(rel_to_pkg)] = pkg_file

    # Get all files in local directory
    local_files = set()
    if local_dir.exists():
        for local_file in local_dir.rglob("*"):
            if local_file.is_file():
                rel_to_local = local_file.relative_to(local_dir)
                local_files.add(str(rel_to_local))

                rel_path = f"{rel_prefix}/{rel_to_local}"
                pkg_file = package_files.get(str(rel_to_local))

                if pkg_file:
                    # File exists in both package and local
                    pkg_hash = compute_file_hash(pkg_file)
                    local_hash = compute_file_hash(local_file)

                    if pkg_hash == local_hash:
                        status = "up_to_date"
                    elif was_file_modified(rel_path, local_file):
                        status = "modified_locally"
                    else:
                        status = "needs_update"
                else:
                    # File exists locally but not in package (user-created)
                    status = "user_created"

                updates.append(
                    FileUpdate(
                        rel_path=rel_path,
                        local_path=local_file,
                        package_path=pkg_file if pkg_file else local_file,
                        status=status,
                        category=category,
                    )
                )

    # Check for new files in package that don't exist locally
    for rel_file, pkg_file in package_files.items():
        if rel_file not in local_files:
            rel_path = f"{rel_prefix}/{rel_file}"
            local_file = local_dir / rel_file

            updates.append(
                FileUpdate(
                    rel_path=rel_path,
                    local_path=local_file,
                    package_path=pkg_file,
                    status="needs_update",
                    category=category,
                )
            )

    return updates


def detect_updates() -> UpdateSummary:
    """
    Detect all files that can be updated.

    Returns:
        UpdateSummary with categorized file updates
    """
    all_updates: list[FileUpdate] = []

    # Check which IDEs are installed
    installed_ides = detect_ide_installations()

    for ide in installed_ides:
        package_plugin = get_package_plugin_path(ide)

        if ide == "claude":
            ide_dir = Path.cwd() / ".claude"

            # Check CLAUDE.md
            claude_md_local = ide_dir / "CLAUDE.md"
            claude_md_pkg = package_plugin / "CLAUDE.md"

            if claude_md_pkg.exists():
                if not claude_md_local.exists():
                    status = "needs_update"
                else:
                    pkg_hash = compute_file_hash(claude_md_pkg)
                    local_hash = compute_file_hash(claude_md_local)

                    if pkg_hash == local_hash:
                        status = "up_to_date"
                    elif was_file_modified(".claude/CLAUDE.md", claude_md_local):
                        status = "modified_locally"
                    else:
                        status = "needs_update"

                all_updates.append(
                    FileUpdate(
                        rel_path=".claude/CLAUDE.md",
                        local_path=claude_md_local,
                        package_path=claude_md_pkg,
                        status=status,
                        category="claude_main",
                    )
                )

            # Check instructions/ directory
            all_updates.extend(
                scan_directory_files(
                    ide_dir / "instructions",
                    package_plugin / "instructions",
                    ".claude/instructions",
                    "claude_instructions",
                )
            )

            # Check commands/ directory
            all_updates.extend(
                scan_directory_files(
                    ide_dir / "commands",
                    package_plugin / "commands",
                    ".claude/commands",
                    "claude_commands",
                )
            )

        elif ide == "cursor":
            ide_dir = Path.cwd() / ".cursor"

            # Check rules/ directory
            all_updates.extend(
                scan_directory_files(
                    ide_dir / "rules",
                    package_plugin / "rules",
                    ".cursor/rules",
                    "cursor_rules",
                )
            )

    # Check shared templates (kurt/ directory)
    # Templates are shared between both IDEs
    if installed_ides:
        package_plugin = get_package_plugin_path(installed_ides[0])
        all_updates.extend(
            scan_directory_files(
                Path.cwd() / "kurt",
                package_plugin / "kurt",
                "kurt",
                "templates",
            )
        )

    # Categorize updates
    needs_update = [u for u in all_updates if u.status == "needs_update"]
    modified_locally = [u for u in all_updates if u.status == "modified_locally"]
    user_created = [u for u in all_updates if u.status == "user_created"]
    up_to_date = [u for u in all_updates if u.status == "up_to_date"]

    return UpdateSummary(
        needs_update=needs_update,
        modified_locally=modified_locally,
        user_created=user_created,
        up_to_date=up_to_date,
    )

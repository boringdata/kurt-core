"""Utility package for Kurt."""

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from kurt.utils.project_utils import extract_section

logger = logging.getLogger(__name__)


def get_git_commit_hash(file_path: Path) -> Optional[str]:
    """
    Get the current git commit hash for a specific file.

    Uses `git log -1 --format=%H -- <file>` to get the most recent commit
    that modified the file.

    Args:
        file_path: Path to the file (absolute or relative to git repo)

    Returns:
        Git commit hash (40-char SHA-1) or None if not in git repo or error

    Example:
        hash = get_git_commit_hash(Path("sources/example.com/article.md"))
        # Returns: "a1b2c3d4e5f6..."
    """
    try:
        # Run git log to get last commit for this file
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(file_path)],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
            timeout=5,  # Timeout after 5 seconds
        )

        if result.returncode == 0 and result.stdout.strip():
            commit_hash = result.stdout.strip()
            logger.debug(f"Git commit hash for {file_path}: {commit_hash[:8]}")
            return commit_hash

        logger.debug(f"No git commit found for {file_path}")
        return None

    except FileNotFoundError:
        logger.debug("Git command not found - not in git repository")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"Git command timed out for {file_path}")
        return None
    except Exception as e:
        logger.warning(f"Error getting git commit hash for {file_path}: {e}")
        return None


def calculate_content_hash(content: str, algorithm: str = "sha256") -> str:
    """
    Calculate hash of content for deduplication and change detection.

    Args:
        content: Content to hash (string)
        algorithm: Hash algorithm ("md5", "sha256", "sha1")

    Returns:
        Hexadecimal hash string

    Raises:
        ValueError: If algorithm is not supported

    Example:
        hash = calculate_content_hash(content)
        # Returns: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        hash = calculate_content_hash(content, "md5")
        # Returns: "d41d8cd98f00b204e9800998ecf8427e"
    """
    if algorithm not in {"md5", "sha256", "sha1"}:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}. Use md5, sha256, or sha1")

    # Create hash object
    if algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha256":
        hasher = hashlib.sha256()
    else:  # sha1
        hasher = hashlib.sha1()

    # Hash content (encode to bytes)
    hasher.update(content.encode("utf-8"))

    # Return hex digest
    hash_value = hasher.hexdigest()
    logger.debug(f"Content hash ({algorithm}): {hash_value[:16]}...")
    return hash_value


def get_file_content_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of file content.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ("md5", "sha256", "sha1")

    Returns:
        Hexadecimal hash string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported

    Example:
        hash = get_file_content_hash(Path("sources/example.com/article.md"))
        # Returns: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    return calculate_content_hash(content, algorithm)


def should_force(force_flag: bool) -> bool:
    """
    Check if force mode should be enabled.

    Returns True if either the force_flag parameter is True OR
    the KURT_FORCE environment variable is set to "1".

    Args:
        force_flag: The --force flag value from CLI

    Returns:
        True if force mode should be enabled, False otherwise

    Example:
        # Via CLI flag
        should_force(force=True)  # Returns: True

        # Via environment variable
        os.environ["KURT_FORCE"] = "1"
        should_force(force=False)  # Returns: True
    """
    return force_flag or os.getenv("KURT_FORCE") == "1"


__all__ = [
    "calculate_content_hash",
    "get_git_commit_hash",
    "get_file_content_hash",
    "should_force",
    "extract_section",
]

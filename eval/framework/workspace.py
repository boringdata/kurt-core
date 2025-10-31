"""Workspace isolation for eval scenarios.

Creates temporary, isolated Kurt projects for each test scenario.
"""

import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class IsolatedWorkspace:
    """Manages an isolated temporary workspace for scenario execution.

    Each workspace gets its own temporary directory where Kurt can be initialized
    without affecting the actual project or other test scenarios.

    Example:
        >>> workspace = IsolatedWorkspace()
        >>> workspace.setup()
        >>> # Now in /tmp/kurt_eval_abc123/
        >>> # Agent can run: kurt init, kurt content add, etc.
        >>> workspace.teardown()
    """

    def __init__(
        self,
        preserve_on_error: bool = False,
        preserve_always: bool = False,
        init_kurt: bool = True,
        install_claude_plugin: bool = False,
        claude_plugin_source: Optional[Path] = None,
    ):
        """Initialize workspace.

        Args:
            preserve_on_error: If True, keep workspace on failures for debugging
            preserve_always: If True, always keep workspace (even on success)
            init_kurt: If True, run 'kurt init' after creating workspace
            install_claude_plugin: If True, copy .claude/ config from source
            claude_plugin_source: Path to source .claude/ directory (defaults to kurt-demo)
        """
        self.temp_dir: Optional[Path] = None
        self.original_cwd: Optional[Path] = None
        self.preserve_on_error = preserve_on_error
        self.preserve_always = preserve_always
        self.init_kurt = init_kurt
        self.install_claude_plugin = install_claude_plugin
        self.claude_plugin_source = claude_plugin_source
        self._setup_complete = False

    def setup(self) -> Path:
        """Create and enter the isolated workspace.

        Returns:
            Path to the workspace directory
        """
        # Create unique temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="kurt_eval_"))

        # Remember where we came from
        self.original_cwd = Path.cwd()

        # Change to temp directory
        os.chdir(self.temp_dir)

        print(f"📁 Workspace created: {self.temp_dir}")

        # Initialize Kurt project
        if self.init_kurt:
            self._run_kurt_init()

        # Install Claude Code plugin
        if self.install_claude_plugin:
            self._install_claude_plugin()

        self._setup_complete = True

        return self.temp_dir

    def _run_kurt_init(self):
        """Run 'kurt init' to initialize the project."""
        print("🔧 Running kurt init...")
        try:
            result = subprocess.run(
                ["uv", "run", "kurt", "init"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.temp_dir,
            )

            if result.returncode == 0:
                print("✅ Kurt initialized successfully")

                # Create standard directories (sources/, rules/, projects/)
                self._create_standard_directories()
            else:
                print(f"⚠️  kurt init exited with code {result.returncode}")
                if result.stderr:
                    print(f"   stderr: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("⚠️  kurt init timed out after 30s")
        except Exception as e:
            print(f"⚠️  kurt init failed: {e}")

    def _create_standard_directories(self):
        """Create standard Kurt directories: sources/, rules/, projects/."""
        if not self.temp_dir:
            return

        dirs = ["sources", "rules", "projects"]
        for dir_name in dirs:
            dir_path = self.temp_dir / dir_name
            dir_path.mkdir(exist_ok=True)

        print("✅ Created sources/, rules/, projects/ directories")

    def _install_claude_plugin(self):
        """Copy .claude/ directory from source to workspace."""
        # Determine source path
        if self.claude_plugin_source:
            source_claude = self.claude_plugin_source
        else:
            # Default: assume kurt-demo is sibling to kurt-core
            kurt_core = Path(__file__).parent.parent.parent
            source_claude = kurt_core.parent.parent / "kurt-demo" / ".claude"

        if not source_claude.exists():
            print(f"⚠️  Claude plugin source not found: {source_claude}")
            return

        dest_claude = self.temp_dir / ".claude"

        print(f"🔌 Installing Claude Code plugin from {source_claude}...")

        try:
            shutil.copytree(source_claude, dest_claude)
            print("✅ Claude Code plugin installed")

            # Also copy .env.example if it exists
            source_env = source_claude.parent / ".env.example"
            if source_env.exists():
                shutil.copy(source_env, self.temp_dir / ".env.example")
                print("✅ .env.example copied")

        except Exception as e:
            print(f"⚠️  Failed to install Claude plugin: {e}")

    def teardown(self, had_error: bool = False):
        """Clean up the workspace.

        Args:
            had_error: Whether the scenario had an error
        """
        if not self._setup_complete:
            return

        # Return to original directory
        if self.original_cwd:
            os.chdir(self.original_cwd)

        # Decide whether to preserve
        should_preserve = self.preserve_always or (had_error and self.preserve_on_error)

        if should_preserve:
            print(f"⚠️  Workspace preserved for inspection: {self.temp_dir}")
        else:
            # Clean up
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print("🧹 Workspace cleaned up")

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in the workspace.

        Args:
            path: Relative path from workspace root

        Returns:
            True if file exists
        """
        if not self.temp_dir:
            return False
        return (self.temp_dir / path).exists()

    def read_file(self, path: str) -> str:
        """Read a file from the workspace.

        Args:
            path: Relative path from workspace root

        Returns:
            File contents

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not self.temp_dir:
            raise RuntimeError("Workspace not setup")

        file_path = self.temp_dir / path
        return file_path.read_text()

    def count_files(self, pattern: str = "**/*") -> int:
        """Count files matching a pattern.

        Args:
            pattern: Glob pattern (default: all files)

        Returns:
            Number of matching files
        """
        if not self.temp_dir:
            return 0

        return len(list(self.temp_dir.glob(pattern)))

    def query_db(self, query: str) -> Any:
        """Execute a SQL query on the Kurt database.

        Args:
            query: SQL query to execute

        Returns:
            Query result (depends on query type)
        """
        if not self.temp_dir:
            return None

        db_path = self.temp_dir / ".kurt" / "kurt.sqlite"
        if not db_path.exists():
            return None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def get_context(self) -> Dict[str, Any]:
        """Get current workspace context for user agent decisions.

        Returns:
            Dictionary with workspace state information
        """
        if not self.temp_dir:
            return {}

        return {
            "workspace_path": str(self.temp_dir),
            "has_config": self.file_exists("kurt.config"),
            "has_database": self.file_exists(".kurt/kurt.sqlite"),
            "source_count": self.count_files("sources/**/*.md"),
            "project_count": self.count_files("projects/*/project.md"),
        }

    @property
    def path(self) -> Path:
        """Get the workspace path.

        Returns:
            Path to workspace directory

        Raises:
            RuntimeError: If workspace not setup
        """
        if not self.temp_dir:
            raise RuntimeError("Workspace not setup")
        return self.temp_dir

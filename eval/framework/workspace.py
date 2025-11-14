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
        setup_commands: Optional[list] = None,
        use_http_mocks: bool = True,
    ):
        """Initialize workspace.

        Args:
            preserve_on_error: If True, keep workspace on failures for debugging
            preserve_always: If True, always keep workspace (even on success)
            init_kurt: If True, run 'kurt init' after creating workspace
            install_claude_plugin: If True, copy .claude/ config from source
            claude_plugin_source: Path to source .claude/ directory (defaults to kurt-demo)
            setup_commands: Optional list of bash commands to run after initialization
            use_http_mocks: If True, patch HTTP clients to use mock data (default: True)
        """
        self.temp_dir: Optional[Path] = None
        self.original_cwd: Optional[Path] = None
        self.preserve_on_error = preserve_on_error
        self.preserve_always = preserve_always
        self.init_kurt = init_kurt
        self.install_claude_plugin = install_claude_plugin
        self.claude_plugin_source = claude_plugin_source
        self.setup_commands = setup_commands
        self.use_http_mocks = use_http_mocks
        self.mock_server = None
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

        # Disable telemetry for eval scenarios
        os.environ["KURT_TELEMETRY_DISABLED"] = "1"

        print(f"📁 Workspace created: {self.temp_dir}")

        # Initialize Kurt project
        if self.init_kurt:
            self._run_kurt_init()

        # Install Claude Code plugin
        if self.install_claude_plugin:
            self._install_claude_plugin()

        # Run setup commands (if specified)
        if self.setup_commands:
            self._run_setup_commands()

        # Setup HTTP mocking (if enabled)
        if self.use_http_mocks:
            self._setup_http_mocks()

        self._setup_complete = True

        return self.temp_dir

    def _setup_http_mocks(self):
        """Setup HTTP mocking using a local HTTP server as proxy."""
        try:
            from eval.framework.mock_server import create_mock_server

            # Start mock HTTP server
            self.mock_server = create_mock_server(port=8765)
            self.mock_server.start()

            # Set HTTP_PROXY environment variable for HTTP URLs only
            # httpx respects this automatically when making requests
            # Note: Only set HTTP_PROXY, not HTTPS_PROXY, since our mock URLs use http://
            os.environ["HTTP_PROXY"] = "http://127.0.0.1:8765"
            os.environ["http_proxy"] = "http://127.0.0.1:8765"

            print("✅ HTTP mocking enabled via proxy server")
            print("   Proxy: http://127.0.0.1:8765")
            print("   HTTP_PROXY environment variable set (HTTP only)")
        except Exception as e:
            print(f"⚠️  Failed to setup HTTP mocks: {e}")
            print("   Scenarios will make real HTTP requests")

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

                # Configure httpx fetch engine for eval scenarios (works with proxy mocking)
                if self.use_http_mocks:
                    self._configure_httpx_engine()
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

    def _configure_httpx_engine(self):
        """Configure Kurt to use httpx fetch engine (works with proxy mocking)."""
        if not self.temp_dir:
            return

        config_path = self.temp_dir / "kurt.config"
        if not config_path.exists():
            print("⚠️  kurt.config not found, cannot set fetch engine")
            return

        try:
            # Read existing config
            config_content = config_path.read_text()

            # Replace INGESTION_FETCH_ENGINE value
            if "INGESTION_FETCH_ENGINE" in config_content:
                # Update existing value
                import re

                config_content = re.sub(
                    r'INGESTION_FETCH_ENGINE\s*=\s*["\']?[^"\'\n]+["\']?',
                    'INGESTION_FETCH_ENGINE = "httpx"',
                    config_content,
                )
            else:
                # Add new value at the end
                config_content += '\nINGESTION_FETCH_ENGINE = "httpx"\n'

            # Write back
            config_path.write_text(config_content)
            print("✅ Configured Kurt to use httpx fetch engine")

        except Exception as e:
            print(f"⚠️  Failed to configure httpx engine: {e}")

    def _install_claude_plugin(self):
        """Copy .claude/ directory from source to workspace."""
        # Determine source path
        if self.claude_plugin_source:
            source_claude = self.claude_plugin_source
        else:
            # Default: use .claude from current project (kurt-core)
            kurt_core = Path(__file__).parent.parent.parent
            source_claude = kurt_core / ".claude"

        if not source_claude.exists():
            print(f"⚠️  Claude plugin source not found: {source_claude}")
            return

        dest_claude = self.temp_dir / ".claude"

        print(f"🔌 Installing Claude Code plugin from {source_claude}...")

        try:
            shutil.copytree(source_claude, dest_claude)
            print("✅ Claude Code plugin installed")

            # Copy .env file from eval directory if it exists (for API keys)
            # Filter out FIRECRAWL_API_KEY to force httpx engine usage in eval scenarios
            eval_env = Path(__file__).parent.parent / ".env"  # eval/.env
            if eval_env.exists():
                env_content = eval_env.read_text()
                # Remove FIRECRAWL_API_KEY lines (commented or not)
                filtered_lines = [
                    line
                    for line in env_content.splitlines()
                    if not line.strip().startswith("FIRECRAWL_API_KEY")
                    and not line.strip().startswith("# FIRECRAWL_API_KEY")
                ]
                (self.temp_dir / ".env").write_text("\n".join(filtered_lines) + "\n")
                print("✅ .env copied from eval/ (FIRECRAWL_API_KEY filtered out)")

            # Also copy .env.example if it exists
            source_env = source_claude.parent / ".env.example"
            if source_env.exists():
                shutil.copy(source_env, self.temp_dir / ".env.example")
                print("✅ .env.example copied")

        except Exception as e:
            print(f"⚠️  Failed to install Claude plugin: {e}")

    def _run_setup_commands(self):
        """Execute setup commands in the workspace."""
        if not self.setup_commands:
            return

        print(f"🔧 Running {len(self.setup_commands)} setup command(s)...")

        for i, cmd in enumerate(self.setup_commands, 1):
            print(f"   [{i}/{len(self.setup_commands)}] {cmd}")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout per command
                    cwd=self.temp_dir,
                )

                if result.returncode == 0:
                    print(f"   ✅ Command {i} succeeded")
                    if result.stdout:
                        # Print first few lines of output
                        lines = result.stdout.strip().split("\n")[:3]
                        for line in lines:
                            print(f"      {line}")
                else:
                    print(f"   ⚠️  Command {i} exited with code {result.returncode}")
                    if result.stderr:
                        print(f"      stderr: {result.stderr[:200]}")

            except subprocess.TimeoutExpired:
                print(f"   ⚠️  Command {i} timed out after 120s")
            except Exception as e:
                print(f"   ⚠️  Command {i} failed: {e}")

        print("✅ Setup commands completed")

    def teardown(self, had_error: bool = False):
        """Clean up the workspace.

        Args:
            had_error: Whether the scenario had an error
        """
        if not self._setup_complete:
            return

        # Stop HTTP mock server and clean up environment
        if self.mock_server:
            self.mock_server.stop()

            # Remove HTTP_PROXY environment variables
            for key in ["HTTP_PROXY", "http_proxy"]:
                if key in os.environ:
                    del os.environ[key]

        # Clean up telemetry env var
        if "KURT_TELEMETRY_DISABLED" in os.environ:
            del os.environ["KURT_TELEMETRY_DISABLED"]

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

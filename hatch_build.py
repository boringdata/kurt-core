"""Hatch build hook to compile frontend before packaging."""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Build the frontend client before creating the wheel."""

    PLUGIN_NAME = "frontend-build"

    def initialize(self, version, build_data):
        """Run npm build before packaging."""
        # Only build for wheel target
        if self.target_name != "wheel":
            return

        client_dir = Path(self.root) / "src" / "kurt" / "web" / "client"
        if not client_dir.exists():
            self.app.display_warning(f"Client directory not found: {client_dir}")
            return

        package_json = client_dir / "package.json"
        if not package_json.exists():
            self.app.display_warning(f"package.json not found: {package_json}")
            return

        # Check if npm is available
        if not shutil.which("npm"):
            self.app.display_warning("npm not found - skipping frontend build")
            return

        self.app.display_info("Building frontend client...")

        # Install dependencies
        self.app.display_info("Installing npm dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=client_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.app.display_error(f"npm install failed: {result.stderr}")
            raise RuntimeError(f"npm install failed: {result.stderr}")

        # Build the frontend
        self.app.display_info("Running npm build...")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=client_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.app.display_error(f"npm build failed: {result.stderr}")
            raise RuntimeError(f"npm build failed: {result.stderr}")

        # Verify build output exists
        dist_dir = client_dir / "dist"
        if not dist_dir.exists() or not (dist_dir / "index.html").exists():
            raise RuntimeError(f"Build output not found at {dist_dir}")

        self.app.display_success("Frontend build completed successfully")

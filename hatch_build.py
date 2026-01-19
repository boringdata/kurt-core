"""Hatch build hook to compile frontend before packaging."""

import os
import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Build the frontend client before creating the wheel."""

    PLUGIN_NAME = "frontend-build"

    def initialize(self, version, build_data):
        """Run npm build before packaging."""
        # Skip if SKIP_FRONTEND_BUILD env var is set (for CI/serverless environments)
        if os.environ.get("SKIP_FRONTEND_BUILD"):
            self.app.display_info("Skipping frontend build (SKIP_FRONTEND_BUILD set)")
            return

        # Only build for wheel target
        if self.target_name != "wheel":
            return

        client_dir = Path(self.root) / "src" / "kurt" / "web" / "client"

        # Skip if client directory doesn't exist (shallow clone, API-only install, etc.)
        if not client_dir.exists():
            self.app.display_info(
                f"Client directory not found: {client_dir} - skipping frontend build"
            )
            return

        package_json = client_dir / "package.json"
        if not package_json.exists():
            self.app.display_info(
                f"package.json not found: {package_json} - skipping frontend build"
            )
            return

        # Check if dist already exists (pre-built or cached)
        dist_dir = client_dir / "dist"
        if dist_dir.exists() and (dist_dir / "index.html").exists():
            self.app.display_info("Frontend already built - skipping build")
            return

        # Check if npm is available
        if not shutil.which("npm"):
            self.app.display_info("npm not found - skipping frontend build")
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

"""Kurt web UI serve command."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


def _start_process(label: str, cmd: list[str], cwd: Path, env: dict[str, str]):
    console.print(f"[dim]Starting {label}:[/dim] {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(cwd), env=env)


@click.command()
@click.option("--host", default="127.0.0.1", help="Host for the web UI")
@click.option("--port", default=8765, type=int, help="Port for the web server")
@click.option("--no-browser", is_flag=True, help="Do not open the browser automatically")
@click.option("--reload", is_flag=True, help="Enable auto-reload (for development)")
@click.option(
    "--claude-cmd",
    default="claude",
    help="Command to run Claude Code CLI (default: claude)",
)
@click.option(
    "--codex-cmd",
    default="codex",
    help="Command to run Codex CLI (default: codex)",
)
@track_command
def serve(
    host: str,
    port: int,
    no_browser: bool,
    reload: bool,
    claude_cmd: str,
    codex_cmd: str,
):
    """Serve the Kurt web UI (production mode).

    This starts the FastAPI server which serves both the API and the
    pre-built frontend static files. For development, run the API server
    and Vite dev server separately:

    \b
    # Terminal 1: API server with reload
    uvicorn kurt.web.api.server:app --reload --port 8765

    \b
    # Terminal 2: Vite dev server (from src/kurt/web/client/)
    npm run dev
    """
    # Check if built frontend exists
    client_dist = Path(__file__).parent.parent / "web" / "client" / "dist"
    if not client_dist.exists() or not (client_dist / "index.html").exists():
        console.print(
            "[yellow]Warning: Built frontend not found at src/kurt/web/client/dist/[/yellow]"
        )
        console.print(
            "[yellow]Run 'npm run build' in src/kurt/web/client/ first, or use dev mode.[/yellow]"
        )
        console.print()

    env = os.environ.copy()
    env["KURT_WEB_ORIGIN"] = f"http://{host}:{port}"
    env["KURT_WEB_API_URL"] = f"http://{host}:{port}"
    project_root = Path(os.environ.get("KURT_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
    env["KURT_PROJECT_ROOT"] = str(project_root)
    env["KURT_PTY_CWD"] = str(project_root)
    env["KURT_CLAUDE_CMD"] = claude_cmd
    env["KURT_CODEX_CMD"] = codex_cmd
    env["KURT_PTY_CMD"] = claude_cmd

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "kurt.web.api.server:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        api_cmd.append("--reload")

    console.print(f"[bold]Starting Kurt Web UI on http://{host}:{port}[/bold]")
    console.print()

    process = _start_process("API server", api_cmd, Path.cwd(), env)

    if not no_browser:
        # Give server a moment to start
        time.sleep(1)
        webbrowser.open(f"http://{host}:{port}")

    try:
        while True:
            if process.poll() is not None:
                console.print(f"[yellow]Server exited with code {process.returncode}.[/yellow]")
                raise SystemExit(process.returncode or 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopping server...[/dim]")
    finally:
        if process.poll() is None:
            process.terminate()
        time.sleep(0.5)
        if process.poll() is None:
            process.kill()

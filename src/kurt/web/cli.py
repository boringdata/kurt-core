"""Kurt web UI serve command."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command


def _is_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for offset in range(max_attempts):
        port = start_port + offset
        if _is_port_available(host, port):
            return port
    raise RuntimeError(
        f"No available port found in range {start_port}-{start_port + max_attempts - 1}"
    )


console = Console()


def _start_process(label: str, cmd: list[str], cwd: Path, env: dict[str, str]):
    console.print(f"[dim]Starting {label}:[/dim] {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(cwd), env=env)


@click.command()
@click.option("--host", default="127.0.0.1", help="Host for the web UI")
@click.option("--port", default=8765, type=int, help="Port for the web server")
@click.option("--no-browser", is_flag=True, help="Do not open the browser automatically")
@click.option("--reload", is_flag=True, help="Enable auto-reload (for development)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server logs")
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
    verbose: bool,
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
    # Check if uvicorn is installed (part of 'web' extra)
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        console.print("[red]Error: uvicorn not installed.[/red]")
        console.print()
        console.print("The web UI requires the 'web' extra. Install it with:")
        console.print("  [cyan]uv pip install 'kurt-core\\[web]'[/cyan]")
        console.print("  or")
        console.print("  [cyan]pip install 'kurt-core\\[web]'[/cyan]")
        raise SystemExit(1)

    # Find an available port
    original_port = port
    try:
        port = _find_available_port(host, port)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)

    if port != original_port:
        console.print(f"[yellow]Port {original_port} is in use, using {port} instead[/yellow]")

    # Check if built frontend exists
    client_dist = Path(__file__).parent / "client" / "dist"
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
        "--log-level",
        "info" if verbose else "warning",
    ]
    if reload:
        api_cmd.append("--reload")

    console.print(f"[bold]Starting Kurt Web UI on http://{host}:{port}[/bold]")
    if not verbose:
        console.print("[dim]Use --verbose for detailed server logs[/dim]")
    console.print()

    if verbose:
        process = _start_process("API server", api_cmd, Path.cwd(), env)
    else:
        # Suppress server output in non-verbose mode
        process = subprocess.Popen(
            api_cmd,
            cwd=str(Path.cwd()),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if not no_browser:
        # Wait for server to be ready before opening browser
        import urllib.error
        import urllib.request

        url = f"http://{host}:{port}/api/project"
        max_wait = 10  # seconds
        start = time.time()
        ready = False

        while time.time() - start < max_wait:
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(0.2)

        if ready:
            webbrowser.open(f"http://{host}:{port}")
        else:
            console.print("[yellow]Server not responding, opening browser anyway...[/yellow]")
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

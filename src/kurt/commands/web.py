"""Kurt web UI serve command."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


def _find_repo_root(start: Path) -> Path:
    for candidate in [start] + list(start.parents):
        if (candidate / "web" / "package.json").exists() and (candidate / "src" / "kurt").exists():
            return candidate
    return start


def _start_process(label: str, cmd: list[str], cwd: Path, env: dict[str, str]):
    console.print(f"[dim]Starting {label}:[/dim] {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(cwd), env=env)


@click.command()
@click.option("--host", default="127.0.0.1", help="Host for the web UI and API")
@click.option("--api-port", default=8765, type=int, help="Port for the FastAPI backend")
@click.option("--web-port", default=5173, type=int, help="Port for the Vite dev server")
@click.option("--pty-port", default=8767, type=int, help="Port for the Claude CLI bridge")
@click.option("--no-browser", is_flag=True, help="Do not open the browser automatically")
@click.option("--no-bridge", is_flag=True, help="Skip starting the Claude CLI bridge")
@click.option("--reload/--no-reload", default=True, help="Enable FastAPI auto-reload")
@click.option(
    "--claude-cmd",
    default="claude",
    help="Command to run Claude Code CLI (default: claude)",
)
@track_command
def serve(
    host: str,
    api_port: int,
    web_port: int,
    pty_port: int,
    no_browser: bool,
    no_bridge: bool,
    reload: bool,
    claude_cmd: str,
):
    """Serve the local web UI with API and Claude CLI bridge."""
    root = _find_repo_root(Path.cwd())
    web_dir = root / "web"
    bridge_entry = web_dir / "bridge" / "server.js"

    if not web_dir.exists():
        console.print("[red]Web UI directory not found (expected ./web).[/red]")
        raise click.Abort()

    if not shutil.which("npm"):
        console.print("[red]npm is required to run the web UI.[/red]")
        raise click.Abort()

    if not no_bridge and not shutil.which("node"):
        console.print("[red]node is required to run the Claude CLI bridge.[/red]")
        raise click.Abort()

    if not no_bridge and not bridge_entry.exists():
        console.print("[red]Claude CLI bridge entrypoint not found (web/bridge/server.js).[/red]")
        raise click.Abort()

    if not no_bridge and not shutil.which(claude_cmd):
        console.print(
            f"[yellow]Claude CLI not found on PATH: {claude_cmd}. The bridge may fail to start.[/yellow]"
        )

    env = os.environ.copy()
    env["KURT_WEB_ORIGIN"] = f"http://{host}:{web_port}"
    env["KURT_WEB_API_URL"] = f"http://{host}:{api_port}"
    env["VITE_API_URL"] = f"http://{host}:{api_port}"
    env["VITE_PTY_HOST"] = host
    env["VITE_PTY_PORT"] = str(pty_port)
    env["KURT_PTY_PORT"] = str(pty_port)
    env["KURT_PTY_CWD"] = str(Path.cwd())
    env["KURT_CLAUDE_CMD"] = claude_cmd

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "kurt.web_api.server:app",
        "--host",
        host,
        "--port",
        str(api_port),
    ]
    if reload:
        api_cmd.append("--reload")

    web_cmd = ["npm", "run", "dev", "--", "--host", host, "--port", str(web_port)]
    bridge_cmd = ["node", str(bridge_entry)]

    processes: list[tuple[str, subprocess.Popen | None]] = []
    processes.append(("api", _start_process("API", api_cmd, root, env)))
    if not no_bridge:
        processes.append(("bridge", _start_process("Claude bridge", bridge_cmd, web_dir, env)))
    processes.append(("web", _start_process("Web UI", web_cmd, web_dir, env)))

    if not no_browser:
        webbrowser.open(f"http://{host}:{web_port}")

    try:
        while True:
            for label, proc in processes:
                if proc and proc.poll() is not None:
                    console.print(f"[yellow]{label} exited with code {proc.returncode}.[/yellow]")
                    raise SystemExit(proc.returncode or 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopping servers...[/dim]")
    finally:
        for _, proc in processes:
            if proc and proc.poll() is None:
                proc.terminate()
        time.sleep(0.5)
        for _, proc in processes:
            if proc and proc.poll() is None:
                proc.kill()

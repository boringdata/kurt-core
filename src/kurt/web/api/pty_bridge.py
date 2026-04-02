"""
PTY Bridge for WebSocket connections.

Provides a WebSocket handler that spawns PTY processes (like Claude CLI)
and bridges input/output between the WebSocket and the PTY.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from collections import deque
from typing import Optional

import ptyprocess
from fastapi import WebSocket, WebSocketDisconnect

MAX_HISTORY_BYTES = int(os.environ.get("KURT_PTY_HISTORY_BYTES", "200000"))
IDLE_TTL_SECONDS = int(os.environ.get("KURT_PTY_IDLE_TTL", "30"))
MAX_SESSIONS = int(os.environ.get("KURT_PTY_MAX_SESSIONS", "20"))

_SESSION_REGISTRY: dict[str, "SharedSession"] = {}
_SESSION_REGISTRY_LOCK = asyncio.Lock()


class PTYSession:
    """Manages a single PTY session connected to a WebSocket."""

    def __init__(
        self,
        cmd: str,
        args: list[str],
        cwd: str,
        cols: int = 60,
        rows: int = 30,
        extra_env: Optional[dict[str, str]] = None,
        no_color: bool = False,
    ):
        self.cmd = cmd
        self.args = args
        self.cwd = cwd
        self.cols = cols
        self.rows = rows
        self.extra_env = extra_env or {}
        self.no_color = no_color
        self.pty: Optional[ptyprocess.PtyProcess] = None
        self._read_task: Optional[asyncio.Task] = None

    def spawn(self, no_color: bool = False) -> None:
        """Spawn the PTY process."""
        env = os.environ.copy()

        if no_color:
            # Disable colors for cleaner output parsing
            env.update(
                {
                    "TERM": "dumb",
                    "NO_COLOR": "1",
                    "FORCE_COLOR": "0",
                    # Signal to Claude Code hooks that this session is running from web UI
                    "CLAUDE_CODE_REMOTE": "true",
                    # Set terminal dimensions for tools that check env vars (like rich)
                    "COLUMNS": str(self.cols),
                    "LINES": str(self.rows),
                }
            )
        else:
            env.update(
                {
                    "TERM": env.get("TERM", "xterm-256color"),
                    "COLORTERM": env.get("COLORTERM", "truecolor"),
                    "FORCE_COLOR": env.get("FORCE_COLOR", "1"),
                    # Signal to Claude Code hooks that this session is running from web UI
                    "CLAUDE_CODE_REMOTE": "true",
                    # Set terminal dimensions for tools that check env vars (like rich)
                    "COLUMNS": str(self.cols),
                    "LINES": str(self.rows),
                }
            )
        # Add extra environment variables (e.g., session info for hooks)
        env.update(self.extra_env)

        cmd_path = shutil.which(self.cmd)
        if not cmd_path:
            cmd_path = self.cmd

        self.pty = ptyprocess.PtyProcess.spawn(
            [cmd_path] + self.args,
            cwd=self.cwd,
            env=env,
            dimensions=(self.rows, self.cols),
        )

    def is_alive(self) -> bool:
        return bool(self.pty and self.pty.isalive())

    def write(self, data: str) -> None:
        """Write data to the PTY."""
        if self.pty and self.pty.isalive():
            self.pty.write(data.encode("utf-8"))

    def resize(self, cols: int, rows: int) -> None:
        """Resize the PTY."""
        self.cols = cols
        self.rows = rows
        if self.pty and self.pty.isalive():
            self.pty.setwinsize(rows, cols)

    def kill(self, force: bool = False) -> None:
        """Kill the PTY process.

        Args:
            force: If True, kill immediately without graceful shutdown.
        """
        if self._read_task:
            self._read_task.cancel()
        if self.pty:
            try:
                if self.pty.isalive():
                    self.pty.terminate(force=force or True)
                # Close PTY file descriptor to free resources
                self.pty.close()
            except Exception:
                pass
            self.pty = None

    async def read_loop(self, on_data, on_exit) -> None:
        """Async loop to read from PTY and call callbacks."""
        loop = asyncio.get_event_loop()

        def read_sync():
            try:
                return self.pty.read(1024)
            except EOFError:
                return None
            except Exception:
                return None

        while self.pty and self.pty.isalive():
            try:
                data = await loop.run_in_executor(None, read_sync)
                if data is None:
                    break
                await on_data(data)
            except asyncio.CancelledError:
                break
            except Exception:
                break

        exit_code = self.pty.exitstatus if self.pty else None
        signal_code = self.pty.signalstatus if self.pty else None
        await on_exit(exit_code, signal_code)


class SharedSession:
    def __init__(self, session_id: str, session: PTYSession):
        self.session_id = session_id
        self.session = session
        self.clients: set[WebSocket] = set()
        self.history: deque[str] = deque()
        self.history_bytes = 0
        self.read_task: Optional[asyncio.Task] = None
        self.idle_task: Optional[asyncio.Task] = None
        self.idle_token = 0

    def is_alive(self) -> bool:
        return self.session.is_alive()

    def append_history(self, text: str) -> None:
        if not text:
            return
        self.history.append(text)
        self.history_bytes += len(text)
        while self.history_bytes > MAX_HISTORY_BYTES and self.history:
            removed = self.history.popleft()
            self.history_bytes -= len(removed)

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for client in self.clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    async def send_history(self, websocket: WebSocket) -> None:
        if not self.history:
            return
        text = "".join(self.history)
        chunk_size = 8000
        for idx in range(0, len(text), chunk_size):
            chunk = text[idx : idx + chunk_size]
            try:
                await websocket.send_json(
                    {
                        "type": "history",
                        "data": chunk,
                    }
                )
            except Exception:
                break

    async def add_client(self, websocket: WebSocket) -> None:
        self.clients.add(websocket)
        if self.idle_task:
            self.idle_task.cancel()
            self.idle_task = None

    async def remove_client(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)
        if self.clients:
            return
        await self.schedule_idle_cleanup()

    async def schedule_idle_cleanup(self) -> None:
        if IDLE_TTL_SECONDS <= 0:
            await self.terminate()
            return
        self.idle_token += 1
        token = self.idle_token

        async def _cleanup():
            try:
                await asyncio.sleep(IDLE_TTL_SECONDS)
            except asyncio.CancelledError:
                return
            if self.clients:
                return
            if token != self.idle_token:
                return
            await self.terminate()

        self.idle_task = asyncio.create_task(_cleanup())

    async def start(self) -> None:
        self.session.spawn(no_color=self.session.no_color)

        async def on_data(data: bytes) -> None:
            text = data.decode("utf-8", errors="replace")
            self.append_history(text)

            if "No conversation found with session ID" in text:
                await self.broadcast(
                    {
                        "type": "session_not_found",
                        "data": text,
                    }
                )

            await self.broadcast(
                {
                    "type": "output",
                    "data": text,
                }
            )

        async def on_exit(exit_code, signal_code) -> None:
            await self.broadcast(
                {
                    "type": "exit",
                    "code": exit_code,
                    "signal": signal_code,
                }
            )
            await self.terminate()

        self.read_task = asyncio.create_task(self.session.read_loop(on_data, on_exit))
        self.session._read_task = self.read_task

    async def terminate(self, force: bool = False) -> None:
        """Terminate the session and clean up.

        Args:
            force: If True, kill immediately without graceful shutdown.
        """
        if self.idle_task:
            self.idle_task.cancel()
            self.idle_task = None
        if self.read_task:
            self.read_task.cancel()
            self.read_task = None
        for client in list(self.clients):
            try:
                await client.close()
            except Exception:
                pass
        self.clients.clear()
        self.session.kill(force=force)
        async with _SESSION_REGISTRY_LOCK:
            existing = _SESSION_REGISTRY.get(self.session_id)
            if existing is self:
                _SESSION_REGISTRY.pop(self.session_id, None)


def build_claude_args(
    base_args: list[str],
    session_id: Optional[str],
    resume: bool,
    force_new: bool,
    fork_session: Optional[str],
    cwd: Optional[str] = None,
    json_mode: bool = False,
) -> list[str]:
    """Build Claude CLI arguments based on session parameters."""
    args = list(base_args)

    # Add JSON streaming mode for structured I/O
    if json_mode:
        if "--output-format" not in args:
            args.extend(["--output-format", "stream-json"])
        if "--input-format" not in args:
            args.extend(["--input-format", "stream-json"])

    # Add --settings flag if project has .claude/settings.json
    if cwd:
        from pathlib import Path

        settings_file = Path(cwd) / ".claude" / "settings.json"
        if settings_file.exists() and "--settings" not in args:
            args.extend(["--settings", str(settings_file)])

    if force_new:
        return args

    if not session_id and not fork_session:
        return args

    session_flag = os.environ.get("KURT_CLAUDE_SESSION_FLAG", "--session-id")
    resume_flag = os.environ.get("KURT_CLAUDE_RESUME_FLAG", "--resume")
    fork_flag = os.environ.get("KURT_CLAUDE_FORK_FLAG", "--fork-session")

    if fork_session:
        if fork_flag and fork_flag not in args:
            args.extend([fork_flag, fork_session])
        if session_id and session_flag and session_flag not in args:
            args.extend([session_flag, session_id])
        return args

    if not resume:
        if session_flag and session_flag not in args:
            args.extend([session_flag, session_id])
        return args

    has_resume = resume_flag in args or "-r" in args

    if not has_resume:
        args.extend([resume_flag, session_id])

    return args


def build_codex_args(
    base_args: list[str],
    session_id: Optional[str],
    resume: bool,
    force_new: bool,
) -> list[str]:
    """Build Codex CLI arguments based on session parameters.

    Codex uses subcommands for resume: `codex resume <session_id>`
    For new sessions, just `codex` with no session args.
    """
    args = list(base_args)

    # For new sessions or force_new, just return base args (no session handling)
    if force_new or not resume:
        return args

    # For resume, prepend the 'resume' subcommand and session_id
    if resume and session_id:
        return ["resume", session_id] + args

    return args


# Allowlist of permitted kurt subcommands for security
KURT_ALLOWED_COMMANDS: dict[str, list[str]] = {
    "workflows": ["follow", "list", "status", "cancel"],
}


def build_kurt_args(
    subcommand: str,
    subcommand_args: list[str],
) -> list[str]:
    """Build Kurt CLI arguments with security validation.

    Only allows specific subcommands to prevent arbitrary command execution.
    """
    # Validate subcommand is in allowlist
    if subcommand not in KURT_ALLOWED_COMMANDS:
        raise ValueError(f"Kurt subcommand '{subcommand}' not allowed")

    args = [subcommand]

    # For workflows, validate the action is allowed
    if subcommand == "workflows" and subcommand_args:
        action = subcommand_args[0] if subcommand_args else None
        if action and action not in KURT_ALLOWED_COMMANDS["workflows"]:
            raise ValueError(f"Kurt workflows action '{action}' not allowed")
        args.extend(subcommand_args)

    return args


async def handle_pty_websocket(
    websocket: WebSocket,
    cmd: str = "claude",
    base_args: Optional[list[str]] = None,
    cwd: Optional[str] = None,
) -> None:
    """
    Handle a WebSocket connection for PTY bridging.

    Query parameters:
    - session_id: Optional session ID for Claude CLI
    - resume: If "1", resume existing session
    - force_new: If "1", force new session
    - provider: Provider name (e.g., "claude", "codex", "kurt")
    - session_name: Web UI session name/title
    - fork_session: Optional session ID to fork
    - kurt_subcommand: For kurt provider, the subcommand (e.g., "workflows")
    - kurt_args: For kurt provider, JSON-encoded args array
    """
    await websocket.accept()

    params = websocket.query_params
    session_id = params.get("session_id") or str(uuid.uuid4())
    resume = params.get("resume", "0") in ("1", "true")
    force_new = params.get("force_new", "0") in ("1", "true")
    provider = params.get("provider", "claude")
    session_name = params.get("session_name", "")
    fork_session = params.get("fork_session")

    # Kurt provider specific params
    kurt_subcommand = params.get("kurt_subcommand", "")
    kurt_args_raw = params.get("kurt_args", "[]")

    # Color mode - no_color=1 disables ANSI codes for cleaner parsing
    no_color = params.get("no_color", "0") in ("1", "true")

    # JSON mode - json_mode=1 uses --output-format stream-json --input-format stream-json
    json_mode = params.get("json_mode", "0") in ("1", "true")

    # Select command and build args based on provider
    if provider == "shell":
        # Plain shell terminal - use user's default shell
        cmd = os.environ.get("SHELL", "/bin/zsh")
        args = []
    elif provider == "kurt":
        cmd = os.environ.get("KURT_CMD", "kurt")
        try:
            kurt_args = json.loads(kurt_args_raw) if kurt_args_raw else []
            args = build_kurt_args(kurt_subcommand, kurt_args)
        except (json.JSONDecodeError, ValueError) as e:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": f"Invalid kurt command: {e}",
                }
            )
            await websocket.close()
            return
    elif provider == "codex":
        cmd = os.environ.get("KURT_CODEX_CMD", "codex")
        args = build_codex_args(base_args or [], session_id, resume, force_new)
    else:
        cmd = os.environ.get("KURT_CLAUDE_CMD", "claude")
        args = build_claude_args(
            base_args or [],
            session_id,
            resume,
            force_new,
            fork_session,
            cwd=cwd,
            json_mode=json_mode,
        )

    extra_env = {
        "KURT_SESSION_PROVIDER": provider,
        "KURT_SESSION_NAME": session_name,
    }

    stale: list[SharedSession] = []
    created = False

    async with _SESSION_REGISTRY_LOCK:
        existing = _SESSION_REGISTRY.get(session_id)
        if force_new and existing:
            stale.append(existing)
            _SESSION_REGISTRY.pop(session_id, None)
            existing = None
        if existing and existing.is_alive():
            shared = existing
        else:
            if existing:
                stale.append(existing)
                _SESSION_REGISTRY.pop(session_id, None)

            # Enforce max sessions limit - evict idle sessions if at capacity
            while len(_SESSION_REGISTRY) >= MAX_SESSIONS:
                # Find sessions with no clients (idle)
                idle_sessions = [
                    (sid, sess) for sid, sess in _SESSION_REGISTRY.items()
                    if not sess.clients
                ]
                if idle_sessions:
                    # Evict first idle session
                    evict_id, evict_sess = idle_sessions[0]
                    print(f"[PTY] Evicting idle session {evict_id} (at max {MAX_SESSIONS})")
                    stale.append(evict_sess)
                    _SESSION_REGISTRY.pop(evict_id, None)
                else:
                    # No idle sessions - reject connection
                    print(f"[PTY] Max sessions ({MAX_SESSIONS}) reached, no idle to evict")
                    break

            session = PTYSession(
                cmd=cmd,
                args=args,
                cwd=cwd or os.getcwd(),
                extra_env=extra_env,
                no_color=no_color,
            )
            shared = SharedSession(session_id, session)
            _SESSION_REGISTRY[session_id] = shared
            created = True

    # Clean up stale sessions with force kill to free FDs immediately
    for stale_session in stale:
        await stale_session.terminate(force=True)

    if created:
        try:
            shared.session._read_task = None
            print(f"[PTY] Spawning: {' '.join([cmd] + args)}")
            await shared.start()
        except Exception as e:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": f"Failed to start session: {e}",
                }
            )
            await websocket.close()
            await shared.terminate()
            return

    await shared.add_client(websocket)
    await shared.send_history(websocket)

    try:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = {"type": "input", "data": message}

            if payload.get("type") == "input" and isinstance(payload.get("data"), str):
                shared.session.write(payload["data"])

            if payload.get("type") == "resize":
                cols = payload.get("cols", 80)
                rows = payload.get("rows", 24)
                shared.session.resize(cols, rows)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await shared.remove_client(websocket)

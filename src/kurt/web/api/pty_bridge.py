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

_SESSION_REGISTRY: dict[str, "SharedSession"] = {}
_SESSION_REGISTRY_LOCK = asyncio.Lock()


class PTYSession:
    """Manages a single PTY session connected to a WebSocket."""

    def __init__(
        self,
        cmd: str,
        args: list[str],
        cwd: str,
        cols: int = 80,
        rows: int = 24,
        extra_env: Optional[dict[str, str]] = None,
    ):
        self.cmd = cmd
        self.args = args
        self.cwd = cwd
        self.cols = cols
        self.rows = rows
        self.extra_env = extra_env or {}
        self.pty: Optional[ptyprocess.PtyProcess] = None
        self._read_task: Optional[asyncio.Task] = None

    def spawn(self) -> None:
        """Spawn the PTY process."""
        env = os.environ.copy()
        env.update(
            {
                "TERM": env.get("TERM", "xterm-256color"),
                "COLORTERM": env.get("COLORTERM", "truecolor"),
                "FORCE_COLOR": env.get("FORCE_COLOR", "1"),
                # Signal to Claude Code hooks that this session is running from web UI
                "CLAUDE_CODE_REMOTE": "true",
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

    def kill(self) -> None:
        """Kill the PTY process."""
        if self._read_task:
            self._read_task.cancel()
        if self.pty and self.pty.isalive():
            try:
                self.pty.terminate(force=True)
            except Exception:
                pass

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
        self.session.spawn()

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

    async def terminate(self) -> None:
        if self.idle_task:
            self.idle_task.cancel()
            self.idle_task = None
        for client in list(self.clients):
            try:
                await client.close()
            except Exception:
                pass
        self.clients.clear()
        self.session.kill()
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
) -> list[str]:
    """Build Claude CLI arguments based on session parameters."""
    args = list(base_args)

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
    - provider: Provider name (e.g., "claude", "codex")
    - session_name: Web UI session name/title
    - fork_session: Optional session ID to fork
    """
    await websocket.accept()

    params = websocket.query_params
    session_id = params.get("session_id") or str(uuid.uuid4())
    resume = params.get("resume", "0") in ("1", "true")
    force_new = params.get("force_new", "0") in ("1", "true")
    provider = params.get("provider", "claude")
    session_name = params.get("session_name", "")
    fork_session = params.get("fork_session")

    # Select command and build args based on provider
    if provider == "codex":
        cmd = os.environ.get("KURT_CODEX_CMD", "codex")
        args = build_codex_args(base_args or [], session_id, resume, force_new)
    else:
        cmd = os.environ.get("KURT_CLAUDE_CMD", "claude")
        args = build_claude_args(base_args or [], session_id, resume, force_new, fork_session)

    extra_env = {
        "KURT_SESSION_PROVIDER": provider,
        "KURT_SESSION_NAME": session_name,
    }

    stale: Optional[SharedSession] = None
    created = False

    async with _SESSION_REGISTRY_LOCK:
        existing = _SESSION_REGISTRY.get(session_id)
        if force_new and existing:
            stale = existing
            _SESSION_REGISTRY.pop(session_id, None)
            existing = None
        if existing and existing.is_alive():
            shared = existing
        else:
            if existing:
                stale = existing
                _SESSION_REGISTRY.pop(session_id, None)
            session = PTYSession(
                cmd=cmd,
                args=args,
                cwd=cwd or os.getcwd(),
                extra_env=extra_env,
            )
            shared = SharedSession(session_id, session)
            _SESSION_REGISTRY[session_id] = shared
            created = True

    if stale:
        await stale.terminate()

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

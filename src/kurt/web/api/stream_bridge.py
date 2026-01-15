"""
Stream Bridge for WebSocket connections using asyncio subprocess.

Provides a WebSocket handler that spawns Claude CLI with stream-json format
and bridges input/output through pipes (not PTY). This enables structured
JSON communication for chat interfaces.

Protocol:
- Input (client → server): {"type": "user", "message": "..."}
- Output (server → client): Forward Claude's JSON lines directly
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections import deque
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

MAX_HISTORY_LINES = int(os.environ.get("KURT_STREAM_HISTORY_LINES", "1000"))
IDLE_TTL_SECONDS = int(os.environ.get("KURT_STREAM_IDLE_TTL", "60"))

_SESSION_REGISTRY: dict[str, "StreamSession"] = {}
_SESSION_REGISTRY_LOCK = asyncio.Lock()


class StreamSession:
    """Manages a Claude subprocess with pipe-based I/O for JSON streaming.

    Based on reverse engineering of Claude Code VSCode extension:
    - Process stays alive with stdin kept open for multiple messages
    - Uses stream-json format for bidirectional communication
    - Mode changes require restart with --resume to preserve history
    """

    def __init__(
        self,
        cmd: str,
        args: list[str],
        cwd: str,
        extra_env: Optional[dict[str, str]] = None,
    ):
        self.cmd = cmd
        self.args = args
        self.cwd = cwd
        self.extra_env = extra_env or {}
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._read_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self.clients: set[WebSocket] = set()
        self.history: deque[dict[str, Any]] = deque(maxlen=MAX_HISTORY_LINES)
        self.idle_task: Optional[asyncio.Task] = None
        self.idle_token = 0
        self.session_id: str = ""
        self._started = False
        self._terminated = False
        self._mode: Optional[str] = None  # Track current permission mode

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def spawn(self) -> None:
        """Spawn the subprocess with pipe-based I/O."""
        if self._started:
            return

        env = os.environ.copy()
        env.update(
            {
                "NO_COLOR": "1",
                "FORCE_COLOR": "0",
                "CLAUDE_CODE_REMOTE": "true",
            }
        )
        env.update(self.extra_env)

        cmd_path = shutil.which(self.cmd)
        if not cmd_path:
            cmd_path = self.cmd

        print(f"[Stream] Spawning: {cmd_path} {' '.join(self.args)}")

        self.proc = await asyncio.create_subprocess_exec(
            cmd_path,
            *self.args,
            cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._started = True

    async def write_message(self, message: str) -> None:
        """Write a user message to Claude's stdin.

        With --input-format stream-json, Claude expects JSON lines:
        {"type": "user", "session_id": "", "message": {"role": "user", "content": [{"type": "text", "text": "..."}]}}
        """
        if not self.proc or not self.proc.stdin:
            return

        # Send JSON line per stream-json input format
        # Content must be an array of content blocks (like VSCode extension)
        payload = {
            "type": "user",
            "session_id": "",  # Required by Claude CLI stream-json protocol
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": message}],
            },
        }
        line = json.dumps(payload) + "\n"

        try:
            self.proc.stdin.write(line.encode("utf-8"))
            await self.proc.stdin.drain()
        except Exception as e:
            print(f"[Stream] Write error: {e}")

    async def write_message_content(self, content: list[dict[str, Any]]) -> None:
        """Write a user message with structured content blocks.

        Content should be an array of content blocks (per VSCode extension):
        - Text: {"type": "text", "text": "..."}
        - Image: {"type": "image", "data": "<base64>", "mimeType": "image/png"}

        The CLI handles @path syntax natively for file references.
        """
        if not self.proc or not self.proc.stdin:
            return

        payload = {
            "type": "user",
            "session_id": "",  # Required by Claude CLI stream-json protocol
            "message": {
                "role": "user",
                "content": content,
            },
        }
        await self.write_json(payload)

    async def write_image(self, base64_data: str, mime_type: str, text: str = "") -> None:
        """Write a message with an image attachment.

        Args:
            base64_data: Base64-encoded image data
            mime_type: MIME type (e.g., "image/png", "image/jpeg")
            text: Optional text to accompany the image
        """
        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        content.append(
            {
                "type": "image",
                "data": base64_data,
                "mimeType": mime_type,
            }
        )
        await self.write_message_content(content)

    async def interrupt(self) -> None:
        """Interrupt the current Claude operation.

        Sends SIGINT to the subprocess (like Ctrl+C).
        """
        if self.proc and self.proc.returncode is None:
            try:
                import signal

                self.proc.send_signal(signal.SIGINT)
                print("[Stream] Sent interrupt signal to Claude")
            except Exception as e:
                print(f"[Stream] Interrupt error: {e}")

    async def write_json(self, payload: dict[str, Any]) -> None:
        """Write a raw JSON payload to Claude's stdin."""
        if not self.proc or not self.proc.stdin:
            print(
                f"[Stream] Cannot write - proc={self.proc is not None} stdin={self.proc.stdin if self.proc else None}"
            )
            return

        line = json.dumps(payload) + "\n"
        print(f"[Stream] Sending JSON type={payload.get('type')} length={len(line)}")
        print(f"[Stream] Payload: {line[:200]}...")

        try:
            self.proc.stdin.write(line.encode("utf-8"))
            await self.proc.stdin.drain()
        except Exception as e:
            print(f"[Stream] Write error: {e}")

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        # No history storage - CLI handles conversation history via --resume
        dead: list[WebSocket] = []
        for client in self.clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    async def send_history(self, websocket: WebSocket) -> None:
        """Send accumulated history to a newly connected client."""
        for payload in self.history:
            try:
                await websocket.send_json(payload)
            except Exception:
                break

    async def add_client(self, websocket: WebSocket) -> None:
        """Add a client and cancel idle cleanup."""
        self.clients.add(websocket)
        if self.idle_task:
            self.idle_task.cancel()
            self.idle_task = None

    async def remove_client(self, websocket: WebSocket) -> None:
        """Remove a client and schedule cleanup if no clients remain."""
        self.clients.discard(websocket)
        if not self.clients:
            await self.schedule_idle_cleanup()

    async def schedule_idle_cleanup(self) -> None:
        """Schedule session termination after idle timeout."""
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

    async def start_read_loop(self) -> None:
        """Start reading stdout and stderr from the subprocess."""
        if not self.proc:
            return

        async def read_stdout():
            """Read JSON lines from stdout and broadcast."""
            if not self.proc or not self.proc.stdout:
                return

            try:
                async for line in self.proc.stdout:
                    if self._terminated:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    if not text:
                        continue

                    # Try to parse as JSON, forward raw if not valid JSON
                    try:
                        payload = json.loads(text)
                        # Debug: log ALL message types
                        msg_type = payload.get("type", "unknown")
                        subtype = payload.get("subtype", "")
                        # Log every message from CLI
                        print(f"[Stream] CLI>>> type={msg_type} subtype={subtype}")
                        keys = list(payload.keys())

                        # Handle control_request/control_cancel_request from CLI (permission prompts)
                        # These need to be forwarded to frontend and responses sent back
                        if msg_type in ("control_request", "control_cancel_request"):
                            print(f"[Stream] CONTROL: {json.dumps(payload, indent=2)}")
                            # Forward to frontend for UI handling
                            await self.broadcast(payload)
                            continue

                        # Log full payload for permission-related or error types
                        if msg_type in (
                            "permission",
                            "permission_request",
                            "input_request",
                            "user_input_request",
                        ):
                            print(f"[Stream] PERMISSION: {json.dumps(payload, indent=2)}")
                        elif subtype == "error_during_execution" or "error" in subtype.lower():
                            errors = payload.get("errors", [])
                            print(f"[Stream] ERROR: {errors}")
                        elif msg_type == "user":
                            # Log user messages (includes slash command outputs)
                            msg_content = payload.get("message", {}).get("content", "")
                            if isinstance(msg_content, str) and "local-command" in msg_content:
                                print(f"[Stream] CMD OUTPUT: {msg_content[:200]}...")
                            else:
                                print(f"[Stream] USER MSG from CLI: {type(msg_content).__name__}")
                        elif msg_type == "assistant":
                            # Log tool use details
                            content = payload.get("message", {}).get("content", [])
                            for item in content:
                                if item.get("type") == "tool_use":
                                    print(
                                        f"[Stream] TOOL: {item.get('name')} input_keys={list(item.get('input', {}).keys())}"
                                    )
                        else:
                            print(f"[Stream] OUT: type={msg_type} subtype={subtype} keys={keys}")

                        await self.broadcast(payload)
                    except json.JSONDecodeError:
                        # Forward raw text as a message
                        await self.broadcast(
                            {
                                "type": "raw",
                                "data": text,
                            }
                        )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[Stream] stdout read error: {e}")

            # Process exited
            if not self._terminated:
                exit_code = self.proc.returncode if self.proc else None
                await self.broadcast(
                    {
                        "type": "result",
                        "subtype": "exit",
                        "exit_code": exit_code,
                    }
                )
                await self.terminate()

        async def read_stderr():
            """Read stderr and log/broadcast errors."""
            if not self.proc or not self.proc.stderr:
                return

            try:
                async for line in self.proc.stderr:
                    if self._terminated:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        print(f"[Stream] stderr: {text}")
                        await self.broadcast(
                            {
                                "type": "system",
                                "subtype": "stderr",
                                "message": text,
                            }
                        )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[Stream] stderr read error: {e}")

        self._read_task = asyncio.create_task(read_stdout())
        self._stderr_task = asyncio.create_task(read_stderr())

    async def terminate(self) -> None:
        """Terminate the session and clean up."""
        if self._terminated:
            return
        self._terminated = True

        if self.idle_task:
            self.idle_task.cancel()
            self.idle_task = None

        if self._read_task:
            self._read_task.cancel()
            self._read_task = None

        if self._stderr_task:
            self._stderr_task.cancel()
            self._stderr_task = None

        if self.proc:
            if self.proc.returncode is None:
                try:
                    self.proc.terminate()
                    try:
                        await asyncio.wait_for(self.proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        # Close all client connections
        for client in list(self.clients):
            try:
                await client.close()
            except Exception:
                pass
        self.clients.clear()

        # Remove from registry
        async with _SESSION_REGISTRY_LOCK:
            existing = _SESSION_REGISTRY.get(self.session_id)
            if existing is self:
                _SESSION_REGISTRY.pop(self.session_id, None)


def build_stream_args(
    base_args: list[str],
    session_id: Optional[str],
    resume: bool,
    cwd: Optional[str] = None,
    mode: Optional[str] = None,
    allowed_tools: Optional[list[str]] = None,
    disallowed_tools: Optional[list[str]] = None,
    max_thinking_tokens: Optional[int] = None,
    include_partial: bool = True,
) -> list[str]:
    """Build Claude CLI arguments for stream-json mode.

    Based on reverse engineering of VSCode extension. Uses --print mode
    with stream-json input/output formats for bidirectional communication.

    Args:
        base_args: Base CLI arguments
        session_id: Session ID for conversation continuity
        resume: If True, use --resume instead of --session-id
        cwd: Working directory (used for settings file)
        mode: UI mode - "ask", "act", or "plan"
              Maps to --permission-mode: ask=default, act=acceptEdits, plan=plan
        allowed_tools: List of allowed tools (e.g., ["Bash", "Read", "Write"])
        disallowed_tools: List of disallowed tools (e.g., ["WebSearch"])
        max_thinking_tokens: Maximum thinking tokens budget
        include_partial: Include partial messages for streaming (default True)
    """
    args = list(base_args)

    # Enable JSON streaming I/O (no --print, VSCode extension doesn't use it)
    if "--output-format" not in args:
        args.extend(["--output-format", "stream-json"])
    if "--input-format" not in args:
        args.extend(["--input-format", "stream-json"])
    if "--verbose" not in args:
        args.append("--verbose")

    # Include partial messages for better streaming UX
    # NOTE: --include-partial-messages sends stream_event type messages
    # which the frontend doesn't handle. Disabled for now.
    # if include_partial and "--include-partial-messages" not in args:
    #     args.append("--include-partial-messages")

    # Set permission mode based on UI mode
    if mode and "--permission-mode" not in " ".join(args):
        mode_map = {
            "ask": "default",
            "act": "acceptEdits",
            "plan": "plan",
        }
        permission_mode = mode_map.get(mode)
        if permission_mode:
            args.extend(["--permission-mode", permission_mode])

    # Enable interactive permission prompts via stdin/stdout (like SDK does)
    # This flag makes CLI send control_request messages for permission decisions
    # instead of auto-denying or using terminal prompts
    if "--permission-prompt-tool" not in args:
        args.extend(["--permission-prompt-tool", "stdio"])

    # Tool restrictions (from VSCode extension reverse engineering)
    if allowed_tools and "--allowedTools" not in args:
        args.extend(["--allowedTools", ",".join(allowed_tools)])
    if disallowed_tools and "--disallowedTools" not in args:
        args.extend(["--disallowedTools", ",".join(disallowed_tools)])

    # Thinking tokens budget
    if max_thinking_tokens and "--max-thinking-tokens" not in args:
        args.extend(["--max-thinking-tokens", str(max_thinking_tokens)])

    # Match VSCode extension: load user/project/local settings sources
    if "--setting-sources" not in args:
        args.extend(["--setting-sources", "user,project,local"])

    # Session handling
    session_flag = os.environ.get("KURT_CLAUDE_SESSION_FLAG", "--session-id")
    resume_flag = os.environ.get("KURT_CLAUDE_RESUME_FLAG", "--resume")

    if session_id:
        if resume:
            if resume_flag and resume_flag not in args:
                args.extend([resume_flag, session_id])
        else:
            if session_flag and session_flag not in args:
                args.extend([session_flag, session_id])

    return args


async def handle_stream_websocket(
    websocket: WebSocket,
    cmd: str = "claude",
    base_args: Optional[list[str]] = None,
    cwd: Optional[str] = None,
) -> None:
    """
    Handle a WebSocket connection for Claude stream-json bridging.

    Query parameters:
    - session_id: Session ID for Claude CLI (auto-generated if not provided)
    - resume: If "1", resume existing session
    - force_new: If "1", force new session (terminate existing)
    - mode: UI mode - "ask", "act", or "plan" (maps to --permission-mode)

    Client messages:
    - {"type": "user", "message": "..."} - Send message to Claude
    - {"type": "ping"} - Keep-alive ping

    Server messages:
    - Forward Claude's JSON output directly
    - {"type": "system", "subtype": "...", ...} - System messages (errors, etc.)
    """
    await websocket.accept()

    import uuid

    params = websocket.query_params
    original_session_id = params.get("session_id")
    session_id = original_session_id or str(uuid.uuid4())
    resume = params.get("resume", "0") in ("1", "true")
    force_new = params.get("force_new", "0") in ("1", "true")
    mode = params.get("mode", "ask")  # Default to "ask" mode

    extra_env = {
        "KURT_SESSION_PROVIDER": "claude-stream",
        "KURT_SESSION_NAME": session_id,
    }

    stale: Optional[StreamSession] = None
    created = False

    # Check registry FIRST to determine if session already exists
    # Only use --resume if Claude CLI already knows about this session
    async with _SESSION_REGISTRY_LOCK:
        existing = _SESSION_REGISTRY.get(session_id)

        # Track if we need to resume (for mode change or reconnecting)
        should_resume = False

        # If session exists in registry, Claude CLI knows about it - use --resume
        # to preserve history across reconnections
        if existing:
            should_resume = True

        if force_new and existing:
            stale = existing
            _SESSION_REGISTRY.pop(session_id, None)
            existing = None
            # Use --resume to preserve conversation history
            should_resume = True
            print(f"[Stream] Force new session requested, will resume: {session_id}")

        # Check if mode changed - need to restart session with new mode
        if existing and existing.is_alive():
            existing_mode = getattr(existing, "_mode", None)
            if existing_mode != mode:
                print(
                    f"[Stream] Mode changed from {existing_mode} to {mode}, will resume with new mode"
                )
                stale = existing
                _SESSION_REGISTRY.pop(session_id, None)
                existing = None
                # Use --resume to preserve conversation history
                should_resume = True

        if existing and existing.is_alive():
            session = existing
        else:
            if existing:
                stale = existing
                _SESSION_REGISTRY.pop(session_id, None)
                # Existing but dead session - Claude CLI knows about it
                should_resume = True

            # Build args with the correct resume flag
            # - For brand new sessions: should_resume=False -> uses --session-id
            # - For reconnecting/mode change: should_resume=True -> uses --resume
            args = build_stream_args(
                base_args or [],
                session_id,
                resume=resume or should_resume,  # Use --resume only if CLI knows about session
                cwd=cwd,
                mode=mode,
            )
            print(f"[Stream] Building new session: resume={resume or should_resume}, mode={mode}")

            session = StreamSession(
                cmd=cmd,
                args=args,
                cwd=cwd or os.getcwd(),
                extra_env=extra_env,
            )
            session.session_id = session_id
            session._mode = mode  # Track mode for future comparisons
            _SESSION_REGISTRY[session_id] = session
            created = True

    # Clean up stale session
    if stale:
        await stale.terminate()

    # Start new session if created
    if created:
        try:
            await session.spawn()
            await session.start_read_loop()
        except Exception as e:
            await websocket.send_json(
                {
                    "type": "system",
                    "subtype": "error",
                    "message": f"Failed to start session: {e}",
                }
            )
            await websocket.close()
            await session.terminate()
            return

    await session.add_client(websocket)
    # Don't send history - CLI handles it via --resume

    # Send connection confirmation
    await websocket.send_json(
        {
            "type": "system",
            "subtype": "connected",
            "session_id": session_id,
            "resumed": not created and not force_new,
        }
    )

    try:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                # Treat raw text as a user message
                payload = {"type": "user", "message": message}

            msg_type = payload.get("type")

            if msg_type == "user":
                user_message = payload.get("message", "")
                context_files = payload.get("context_files", [])
                images = payload.get("images", [])  # List of {data: base64, mimeType: string}

                # Debug: log what frontend sent
                print(f"[Stream] USER MSG: message type={type(user_message).__name__}")
                if isinstance(user_message, dict):
                    msg_content = user_message.get("content", [])
                    content_types = (
                        [c.get("type") for c in msg_content]
                        if isinstance(msg_content, list)
                        else "not-list"
                    )
                    print(
                        f"[Stream] USER MSG: content types={content_types}, images param={len(images)}"
                    )

                content: Optional[list[dict[str, Any]]] = None

                if isinstance(user_message, dict):
                    content = user_message.get("content")
                elif isinstance(user_message, list):
                    content = user_message
                elif isinstance(user_message, str):
                    content = [{"type": "text", "text": user_message}]

                # Prepend context files as @ references (CLI handles @path natively)
                if context_files:
                    file_refs = " ".join(f"@{f}" for f in context_files)
                    prefix = {"type": "text", "text": file_refs}
                    if content:
                        content = [prefix, *content]
                    else:
                        content = [prefix]

                # Append images as content blocks (per VSCode extension format)
                # Format: {"type": "image", "data": "<base64>", "mimeType": "image/png"}
                if images:
                    if content is None:
                        content = []
                    for img in images:
                        if isinstance(img, dict) and "data" in img:
                            content.append(
                                {
                                    "type": "image",
                                    "data": img.get("data", ""),
                                    "mimeType": img.get("mimeType", "image/png"),
                                }
                            )

                # Mode is set via --permission-mode at session startup
                # To change mode, frontend should reconnect with new mode param

                # CLI actually expects Anthropic API format for images:
                # {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
                # No transformation needed - pass through as-is
                if content:
                    # Log image blocks for debugging
                    for block in content:
                        if block.get("type") == "image":
                            source = block.get("source", {})
                            print(
                                f"[Stream] Image block: source.type={source.get('type')}, media_type={source.get('media_type')}"
                            )
                    await session.write_message_content(content)

            elif msg_type == "command":
                # Handle slash commands - send directly to Claude CLI
                command = payload.get("command", "")
                print(f"[Stream] COMMAND received: {command}")
                if command:
                    # Claude Code CLI interprets slash commands from user messages
                    await session.write_message(command)
                    print(f"[Stream] COMMAND sent to CLI: {command}")

            elif msg_type == "control_response":
                # Handle control_response from UI (for permission prompts)
                # UI can send either full CLI format or a simplified payload.
                if isinstance(payload.get("response"), dict):
                    await session.write_json(payload)
                    continue

                request_id = payload.get("request_id")
                decision = payload.get("decision")
                behavior = payload.get("behavior")
                allow = payload.get("allow")
                tool_input = payload.get("tool_input", {})
                updated_input = payload.get("updatedInput") or payload.get("updated_input")
                permission_suggestions = payload.get("permission_suggestions") or payload.get(
                    "permissionSuggestions"
                )
                permission_suggestions = payload.get("permission_suggestions") or payload.get(
                    "permissionSuggestions"
                )
                deny_message = payload.get("message", "User denied permission")

                if decision is None:
                    decision = behavior
                if decision is None and allow is not None:
                    decision = "allow" if allow else "deny"
                if decision is None:
                    decision = "allow"

                behavior_value = decision
                behavior_text = (
                    str(behavior_value).lower() if isinstance(behavior_value, str) else ""
                )
                is_deny = behavior_text in ("deny", "reject", "block")
                updated_value = updated_input if updated_input is not None else tool_input

                print(
                    f"[Stream] Control response: request_id={request_id} behavior={behavior_value}"
                )

                if not is_deny:
                    response_payload = {
                        "type": "control_response",
                        "response": {
                            "subtype": "success",
                            "request_id": request_id,
                            "response": {
                                "behavior": behavior_value,
                                "updatedInput": updated_value,
                            },
                        },
                    }
                    if permission_suggestions:
                        response_payload["response"]["response"]["permission_suggestions"] = (
                            permission_suggestions
                        )
                    if permission_suggestions is not None:
                        response_payload["response"]["response"]["permission_suggestions"] = (
                            permission_suggestions
                        )
                else:
                    response_payload = {
                        "type": "control_response",
                        "response": {
                            "subtype": "success",
                            "request_id": request_id,
                            "response": {
                                "behavior": behavior_value,
                                "message": deny_message,
                            },
                        },
                    }
                await session.write_json(response_payload)

            elif msg_type == "approval_response":
                # Legacy approval response handler - convert to control_response format
                decision = payload.get("decision", "allow")
                request_id = payload.get("request_id") or payload.get("tool_id")
                tool_input = payload.get("tool_input", {})
                print(
                    f"[Stream] Approval response (legacy): decision={decision} request_id={request_id}"
                )

                if decision in ("allow", "always", "grant"):
                    response_payload = {
                        "type": "control_response",
                        "response": {
                            "subtype": "success",
                            "request_id": request_id,
                            "response": {
                                "behavior": "allow",
                                "updatedInput": tool_input,
                            },
                        },
                    }
                else:
                    response_payload = {
                        "type": "control_response",
                        "response": {
                            "subtype": "success",
                            "request_id": request_id,
                            "response": {
                                "behavior": "deny",
                                "message": "User denied permission",
                            },
                        },
                    }
                await session.write_json(response_payload)

            elif msg_type == "interrupt":
                # Interrupt current Claude operation (like Ctrl+C)
                await session.interrupt()
                await websocket.send_json(
                    {
                        "type": "system",
                        "subtype": "interrupted",
                        "session_id": session_id,
                    }
                )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "restart":
                # Restart the session
                await session.terminate()
                async with _SESSION_REGISTRY_LOCK:
                    session = StreamSession(
                        cmd=cmd,
                        args=args,
                        cwd=cwd or os.getcwd(),
                        extra_env=extra_env,
                    )
                    session.session_id = session_id
                    _SESSION_REGISTRY[session_id] = session
                await session.spawn()
                await session.start_read_loop()
                await session.add_client(websocket)
                await websocket.send_json(
                    {
                        "type": "system",
                        "subtype": "restarted",
                        "session_id": session_id,
                    }
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Stream] WebSocket error: {e}")
    finally:
        await session.remove_client(websocket)

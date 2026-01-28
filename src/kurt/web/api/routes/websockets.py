"""WebSocket routes: PTY terminal and Claude stream sessions."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, WebSocket

from kurt.web.api.pty_bridge import handle_pty_websocket
from kurt.web.api.stream_bridge import handle_stream_websocket

router = APIRouter()

# PTY WebSocket endpoint for terminal sessions
PTY_CMD = os.environ.get("KURT_PTY_CMD", "claude")
PTY_ARGS = os.environ.get("KURT_PTY_ARGS", "").split()

# Stream-JSON WebSocket endpoint for structured Claude communication
STREAM_CMD = os.environ.get("KURT_STREAM_CMD", os.environ.get("KURT_CLAUDE_CMD", "claude"))
STREAM_ARGS = os.environ.get("KURT_STREAM_ARGS", "").split()


@router.websocket("/ws/pty")
async def websocket_pty(websocket: WebSocket):
    """WebSocket endpoint for PTY terminal sessions."""
    await handle_pty_websocket(
        websocket,
        cmd=PTY_CMD,
        base_args=[a for a in PTY_ARGS if a],
        cwd=str(Path.cwd()),
    )


@router.websocket("/ws/claude-stream")
async def websocket_claude_stream(websocket: WebSocket):
    """WebSocket endpoint for Claude stream-json sessions.

    Uses pipe-based I/O (not PTY) for structured JSON communication.
    Client sends: {"type": "user", "message": "..."}
    Server forwards Claude's stream-json output directly.
    """
    await handle_stream_websocket(
        websocket,
        cmd=STREAM_CMD,
        base_args=[a for a in STREAM_ARGS if a],
        cwd=str(Path.cwd()),
    )

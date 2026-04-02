"""Claude stream route: POST /api/claude for streaming Claude CLI output."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from kurt.web.api.pty_bridge import build_claude_args

router = APIRouter()


# --- Pydantic models ---

class ClaudeStreamPayload(BaseModel):
    prompt: str
    session_id: str | None = None
    resume: bool = False
    fork_session: str | None = None
    output_format: str = "stream-json"


# --- Endpoints ---

@router.post("/api/claude")
async def api_claude_stream(payload: ClaudeStreamPayload, request: Request):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    cmd = os.environ.get("KURT_CLAUDE_CMD", "claude")
    base_args = os.environ.get("KURT_CLAUDE_ARGS", "").split()
    output_flag = os.environ.get("KURT_CLAUDE_OUTPUT_FLAG", "--output-format")
    prompt_flag = os.environ.get("KURT_CLAUDE_PROMPT_FLAG", "").strip()

    if output_flag and output_flag not in base_args:
        base_args += [output_flag, payload.output_format]

    args = build_claude_args(
        base_args,
        payload.session_id,
        payload.resume,
        False,
        payload.fork_session,
        cwd=str(Path.cwd()),
    )

    send_stdin = True
    if prompt_flag:
        args += [prompt_flag, prompt]
        send_stdin = False

    env = os.environ.copy()
    env.setdefault("CLAUDE_CODE_REMOTE", "true")
    env["KURT_SESSION_PROVIDER"] = "claude"
    if payload.session_id:
        env["KURT_SESSION_NAME"] = payload.session_id

    try:
        proc = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            cwd=str(Path.cwd()),
            stdin=asyncio.subprocess.PIPE if send_stdin else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Claude CLI not found: {exc}") from exc

    async def stream():
        if send_stdin and proc.stdin:
            proc.stdin.write((prompt + "\n").encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

        try:
            while True:
                if await request.is_disconnected():
                    proc.terminate()
                    break
                chunk = await proc.stdout.read(1024)
                if not chunk:
                    break
                yield chunk

            stderr = await proc.stderr.read()
            await proc.wait()
            if proc.returncode and stderr:
                detail = stderr.decode("utf-8", errors="replace").strip()
                if detail:
                    error_line = json.dumps(
                        {
                            "type": "result",
                            "subtype": "error",
                            "result": f"Claude exited with code {proc.returncode}: {detail}",
                        }
                    )
                    yield (error_line + "\n").encode("utf-8")
        finally:
            if proc.returncode is None:
                proc.terminate()

    return StreamingResponse(stream(), media_type="text/plain")

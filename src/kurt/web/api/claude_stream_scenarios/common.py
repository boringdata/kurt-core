#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from urllib.parse import urlencode

import websockets


class MessageBus:
    def __init__(self, verbose: bool = False) -> None:
        self.history: list[dict] = []
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
        self.verbose = verbose

    def feed(self, payload: dict) -> None:
        if self.verbose:
            msg_type = payload.get("type")
            subtype = payload.get("subtype", "")
            print(f"[stream] {msg_type} {subtype}".strip())
        self.history.append(payload)
        self.queue.put_nowait(payload)

    async def wait_for(self, predicate, timeout: float) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                payload = await asyncio.wait_for(self.queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            if predicate(payload):
                return payload
        return None


def resolve_session_id(value: str | None) -> str:
    return value or os.environ.get("KURT_SESSION_ID") or str(uuid.uuid4())


def build_ws_url(
    base_url: str,
    session_id: str,
    mode: str,
    resume: bool,
    extra_params: dict[str, str] | None = None,
) -> str:
    params = {"session_id": session_id, "mode": mode}
    if resume:
        params["resume"] = "1"
    if extra_params:
        params.update(extra_params)
    return f"{base_url}?{urlencode(params)}"


async def connect_session(
    base_url: str,
    session_id: str,
    mode: str,
    resume: bool,
    verbose: bool,
    extra_params: dict[str, str] | None = None,
):
    ws_url = build_ws_url(base_url.rstrip("?"), session_id, mode, resume, extra_params)
    bus = MessageBus(verbose=verbose)
    ws = await websockets.connect(ws_url)

    async def reader():
        async for raw in ws:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"type": "raw", "data": raw}
            bus.feed(payload)

    reader_task = asyncio.create_task(reader())
    return ws, bus, reader_task


async def send_user_text(ws, text: str, context_files: list[str] | None = None):
    payload: dict = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": text}],
        },
    }
    if context_files:
        payload["context_files"] = context_files
    await ws.send(json.dumps(payload))


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--ws-url",
        default=os.environ.get("KURT_WS_URL", "ws://127.0.0.1:8765/ws/claude-stream"),
    )
    parser.add_argument("--session-id", default=os.environ.get("KURT_SESSION_ID"))
    parser.add_argument("--mode", default="ask")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--test-events", action="store_true")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--verbose", action="store_true")
    return parser

#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os

from common import base_parser, connect_session, resolve_session_id, send_user_text


async def run():
    parser = base_parser("Trigger Edit and Bash (rm) tool usage and approve permissions.")
    parser.add_argument(
        "--edit-text",
        default="Use the Edit tool (not Write) to create or update perm-tool-test.txt "
        "by appending a line: 'permission check'. You must call the Edit tool before replying.",
    )
    parser.add_argument(
        "--rm-text",
        default="Use the Bash tool to run `rm -f perm-tool-test.txt`. "
        "You must call the Bash tool before replying.",
    )
    args = parser.parse_args()
    session_id = resolve_session_id(args.session_id)

    ws, bus, reader_task = await connect_session(
        args.ws_url, session_id, args.mode, args.resume, args.verbose
    )

    async def approve_next_permission(label: str, expected_tool: str) -> bool:
        request = await bus.wait_for(lambda p: p.get("type") == "control_request", args.timeout)
        if request:
            tool_name = request.get("request", {}).get("tool_name")
            tool_ok = tool_name == expected_tool
            await ws.send(
                json.dumps(
                    {
                        "type": "control_response",
                        "request_id": request.get("request_id"),
                        "decision": "allow",
                        "tool_input": request.get("request", {}).get("input", {}),
                    }
                )
            )
            print(f"{label}=allowed tool={tool_name or 'unknown'} match={tool_ok}")
            return True
        print(f"{label}=timeout")
        return False

    async def wait_for_tool_or_result(label: str) -> None:
        first = await bus.wait_for(
            lambda p: (
                p.get("type") == "assistant"
                and any(
                    (c or {}).get("type") == "tool_use"
                    for c in (p.get("message", {}).get("content") or [])
                )
            )
            or p.get("type") == "result",
            args.timeout,
        )
        if first and first.get("type") == "assistant":
            tool_result = await bus.wait_for(
                lambda p: p.get("type") == "user"
                and any(
                    (c or {}).get("type") == "tool_result"
                    for c in (p.get("message", {}).get("content") or [])
                ),
                args.timeout,
            )
            print(f"{label}_tool_use=ok")
            print(f"{label}_tool_result={'ok' if tool_result else 'timeout'}")
            return
        if first and first.get("type") == "result":
            print(f"{label}_tool_use=missing")
            print(f"{label}_result=ok")
            return
        print(f"{label}_tool_use=timeout")

    # Ensure we start in the repo root for relative paths.
    os.chdir(os.getcwd())

    await send_user_text(ws, args.edit_text)
    await approve_next_permission("permission_edit", "Edit")
    await wait_for_tool_or_result("edit")

    await send_user_text(ws, args.rm_text)
    await approve_next_permission("permission_rm", "Bash")
    await wait_for_tool_or_result("rm")
    print(f"session_id={session_id}")

    await ws.close()
    reader_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())

#!/usr/bin/env python3
from __future__ import annotations

import asyncio

from common import base_parser, connect_session, resolve_session_id, send_user_text


async def run():
    parser = base_parser("Send a slash command message and wait for result.")
    parser.add_argument("--command", default="/context")
    args = parser.parse_args()
    session_id = resolve_session_id(args.session_id)

    ws, bus, reader_task = await connect_session(
        args.ws_url, session_id, args.mode, args.resume, args.verbose
    )
    await send_user_text(ws, args.command)

    result = await bus.wait_for(lambda p: p.get("type") == "result", args.timeout)
    print(f"session_id={session_id}")
    print(f"result={'ok' if result else 'timeout'}")

    await ws.close()
    reader_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())

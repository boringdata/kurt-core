#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json

from common import base_parser, connect_session, resolve_session_id


async def run():
    parser = base_parser("Connect to Claude stream and print session info.")
    args = parser.parse_args()
    session_id = resolve_session_id(args.session_id)

    ws, bus, reader_task = await connect_session(
        args.ws_url, session_id, args.mode, args.resume, args.verbose
    )
    print(f"session_id={session_id}")

    connected = await bus.wait_for(
        lambda p: p.get("type") == "system" and p.get("subtype") == "connected",
        args.timeout,
    )
    if connected:
        print("connected=ok")
    else:
        print("connected=timeout")

    await ws.send(
        json.dumps(
            {
                "type": "control",
                "subtype": "initialize",
                "capabilities": {"permissions": True, "file_diffs": True, "user_questions": True},
            }
        )
    )

    await ws.close()
    reader_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())

#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json

from common import base_parser, connect_session, resolve_session_id


async def run():
    parser = base_parser("Send control updates for model and thinking tokens.")
    parser.add_argument("--model", default="claude-sonnet-4")
    parser.add_argument("--max-thinking", type=int, default=1024)
    args = parser.parse_args()
    session_id = resolve_session_id(args.session_id)

    ws, bus, reader_task = await connect_session(
        args.ws_url, session_id, args.mode, args.resume, args.verbose
    )
    await ws.send(json.dumps({"type": "control", "subtype": "set_model", "model": args.model}))
    await ws.send(
        json.dumps(
            {
                "type": "control",
                "subtype": "set_max_thinking_tokens",
                "max_thinking_tokens": args.max_thinking,
            }
        )
    )

    print(f"session_id={session_id}")
    print("sent=ok")

    await ws.close()
    reader_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())

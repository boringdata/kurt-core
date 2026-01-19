#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json

from common import base_parser, connect_session, resolve_session_id

ONE_BY_ONE_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB"
    "/p0pJv0AAAAASUVORK5CYII="
)


async def run():
    parser = base_parser("Send a base64 image content block.")
    parser.add_argument("--text", default="Describe the attached image.")
    args = parser.parse_args()
    session_id = resolve_session_id(args.session_id)

    ws, bus, reader_task = await connect_session(
        args.ws_url, session_id, args.mode, args.resume, args.verbose
    )
    payload = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "text", "text": args.text},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": ONE_BY_ONE_PNG,
                    },
                },
            ],
        },
    }
    await ws.send(json.dumps(payload))

    result = await bus.wait_for(lambda p: p.get("type") == "result", args.timeout)
    print(f"session_id={session_id}")
    print(f"result={'ok' if result else 'timeout'}")

    await ws.close()
    reader_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())

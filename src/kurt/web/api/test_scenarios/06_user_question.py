#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json

from common import base_parser, connect_session, resolve_session_id, send_user_text


async def run():
    parser = base_parser("Trigger AskUserQuestion and respond.")
    parser.set_defaults(test_events=True)
    parser.add_argument("--text", default="__emit_question__")
    args = parser.parse_args()
    session_id = resolve_session_id(args.session_id)
    extra_params = {"test_events": "1"} if args.test_events else None

    ws, bus, reader_task = await connect_session(
        args.ws_url, session_id, args.mode, args.resume, args.verbose, extra_params
    )
    await send_user_text(ws, args.text)

    question = await bus.wait_for(
        lambda p: (
            p.get("type") == "control_request"
            and p.get("request", {}).get("tool_name") == "AskUserQuestion"
        )
        or (p.get("type") == "control" and p.get("subtype") == "user_question_request"),
        args.timeout,
    )

    if question:
        await ws.send(
            json.dumps(
                {
                    "type": "control_response",
                    "request_id": question.get("request_id"),
                    "answers": {"0": "Red"},
                }
            )
        )
        print("question=answered")
    else:
        print("question=timeout")

    print(f"session_id={session_id}")

    await ws.close()
    reader_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())

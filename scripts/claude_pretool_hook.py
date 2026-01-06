#!/usr/bin/env python3
from __future__ import annotations

import difflib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://127.0.0.1:8765"
DEFAULT_TIMEOUT_SECONDS = 600


@dataclass
class ToolPayload:
    tool_name: str
    tool_input: dict[str, Any]
    session_id: str


def _read_stdin() -> ToolPayload:
    raw = sys.stdin.read()
    if not raw.strip():
        return ToolPayload(tool_name="", tool_input={}, session_id="")
    payload = json.loads(raw)
    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    session_id = payload.get("session_id") or payload.get("sessionId") or ""
    return ToolPayload(tool_name=tool_name, tool_input=tool_input, session_id=session_id)


def _post_json(url: str, data: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    return Path(path_value).expanduser().resolve()


def _load_file(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _build_diff_from_strings(path_value: str, old_string: str, new_string: str) -> str:
    rel_path = path_value.lstrip("/")
    diff_lines = list(
        difflib.unified_diff(
            old_string.splitlines(),
            new_string.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
            n=1,
        )
    )
    if not diff_lines:
        return ""
    diff_lines.insert(0, f"diff --git a/{rel_path} b/{rel_path}")
    return "\n".join(diff_lines)


def _build_diff(path_value: str, old_content: str, new_content: str) -> str:
    rel_path = path_value.lstrip("/")
    diff_lines = list(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
            n=1,
        )
    )
    if not diff_lines:
        return ""
    diff_lines.insert(0, f"diff --git a/{rel_path} b/{rel_path}")
    return "\n".join(diff_lines)


def _derive_new_content(old_content: str, tool_input: dict[str, Any]) -> str:
    new_content = (
        tool_input.get("content")
        or tool_input.get("new_content")
        or tool_input.get("new_text")
        or tool_input.get("replacement_text")
        or tool_input.get("newString")
        or tool_input.get("new_string")
    )
    if isinstance(new_content, str):
        return new_content

    old_string = (
        tool_input.get("old_string")
        or tool_input.get("oldString")
        or tool_input.get("old_text")
        or tool_input.get("oldText")
    )
    new_string = (
        tool_input.get("new_string")
        or tool_input.get("newString")
        or tool_input.get("new_text")
        or tool_input.get("newText")
    )
    if isinstance(old_string, str) and isinstance(new_string, str) and old_content:
        if old_string in old_content:
            return old_content.replace(old_string, new_string, 1)
        old_norm = old_content.replace("\r\n", "\n")
        old_string_norm = old_string.replace("\r\n", "\n")
        new_string_norm = new_string.replace("\r\n", "\n")
        if old_string_norm in old_norm:
            return old_norm.replace(old_string_norm, new_string_norm, 1)
    return old_content


def _print_decision(decision: str, reason: str):
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def _is_web_session() -> bool:
    """Check if this Claude Code session is running from the web UI."""
    return os.environ.get("CLAUDE_CODE_REMOTE") == "true"


def main():
    api_url = os.environ.get("KURT_WEB_API_URL", DEFAULT_API_URL).rstrip("/")
    timeout_seconds = int(os.environ.get("KURT_APPROVAL_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))

    # If not running from web UI, skip the web approval flow
    if not _is_web_session():
        _print_decision("ask", "Not a web session - using default approval flow.")
        return

    tool_payload = _read_stdin()
    if not tool_payload.tool_name:
        _print_decision("ask", "No tool payload received.")
        return

    tool_input = tool_payload.tool_input
    path_value = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("file")
        or tool_input.get("target_file")
    )
    resolved_path = _resolve_path(path_value)
    old_content = _load_file(resolved_path)
    new_content = _derive_new_content(old_content, tool_input)
    old_string = (
        tool_input.get("old_string")
        or tool_input.get("oldString")
        or tool_input.get("old_text")
        or tool_input.get("oldText")
    )
    new_string = (
        tool_input.get("new_string")
        or tool_input.get("newString")
        or tool_input.get("new_text")
        or tool_input.get("newText")
    )
    if isinstance(old_string, str) and isinstance(new_string, str):
        diff_text = _build_diff_from_strings(path_value or "unknown", old_string, new_string)
    else:
        diff_text = _build_diff(path_value or "unknown", old_content, new_content)

    request_payload = {
        "tool_name": tool_payload.tool_name,
        "file_path": path_value or "",
        "diff": diff_text,
        "tool_input": tool_input,
        "session_id": tool_payload.session_id,
        "session_provider": os.environ.get("KURT_SESSION_PROVIDER", ""),
        "session_name": os.environ.get("KURT_SESSION_NAME", ""),
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = _post_json(f"{api_url}/api/approval/request", request_payload)
    except urllib.error.URLError as exc:
        _print_decision("ask", f"Approval service unavailable: {exc}")
        return

    request_id = response.get("request_id")
    if not request_id:
        _print_decision("ask", "Approval service did not return request_id.")
        return

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            status = _get_json(f"{api_url}/api/approval/status?request_id={request_id}")
        except urllib.error.URLError:
            time.sleep(0.5)
            continue

        decision = status.get("status")
        if decision in ("allow", "deny"):
            request = status.get("request", {})
            reason = request.get("decision_reason") or "User responded via web UI."
            _print_decision(decision, reason)
            return
        time.sleep(0.5)

    _print_decision("ask", "Approval timed out.")


if __name__ == "__main__":
    main()

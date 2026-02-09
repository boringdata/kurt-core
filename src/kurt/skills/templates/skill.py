#!/usr/bin/env python3
"""Kurt skill wrapper for Claude Code (OpenClaw) integration.

This script translates OpenClaw skill invocations into Kurt CLI calls.
It is installed to ~/.claude/skills/kurt/ by `kurt skill install-openclaw`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


def run_kurt(args: list[str]) -> dict[str, Any]:
    """Run kurt CLI and return structured output.

    Args:
        args: Command-line arguments to pass to kurt

    Returns:
        dict with success, output, and error fields
    """
    try:
        # Add --json for machine-readable output where supported
        if args and args[0] in ("fetch", "map", "tool"):
            if "--json" not in args:
                args = list(args) + ["--json"]

        result = subprocess.run(
            ["kurt"] + args,
            capture_output=True,
            text=True,
            env={**os.environ},
            timeout=300,
        )

        # Try to parse JSON output
        output: Any = result.stdout
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "success": result.returncode == 0,
            "output": output,
            "error": result.stderr if result.returncode != 0 else None,
            "exit_code": result.returncode,
        }

    except FileNotFoundError:
        return {
            "success": False,
            "output": None,
            "error": "kurt not found. Install with: pip install kurt",
            "exit_code": 127,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "error": "Command timed out after 5 minutes",
            "exit_code": 124,
        }


ACTIONS = {"fetch", "map", "workflow", "tool", "status", "docs"}


def main() -> None:
    """Entry point for skill invocation."""
    if len(sys.argv) < 2:
        result = run_kurt(["--help"])
    else:
        action = sys.argv[1]
        args = sys.argv[2:]

        if action in ACTIONS:
            result = run_kurt([action] + args)
        elif action == "help":
            result = run_kurt(["--help"])
        elif action == "version":
            result = run_kurt(["--version"])
        else:
            result = {
                "success": False,
                "output": None,
                "error": f"Unknown action: {action}. Available: {', '.join(sorted(ACTIONS))}",
                "exit_code": 1,
            }

    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["success"] else result.get("exit_code", 1))


if __name__ == "__main__":
    main()

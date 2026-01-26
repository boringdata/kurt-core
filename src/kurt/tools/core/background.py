from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable


def workflow_path_for(workflow_func: Callable[..., Any]) -> str:
    return f"{workflow_func.__module__}:{workflow_func.__name__}"


def start_background_workflow(
    workflow_path: str,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    priority: int = 10,
    wait_for_id: bool = True,
    id_timeout_sec: float = 5.0,
) -> str | None:
    """
    Start a workflow in a detached worker process.
    """
    payload = {
        "args": list(args),
        "kwargs": kwargs or {},
    }
    workflow_args_json = json.dumps(payload, default=str)

    id_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".workflow_id")
    id_file_path = id_file.name
    id_file.close()

    cmd = [
        sys.executable,
        "-m",
        "kurt.core._worker",
        workflow_path,
        workflow_args_json,
        str(priority),
    ]

    env = os.environ.copy()
    env["KURT_NEW_WORKFLOW_ID_FILE"] = id_file_path

    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    if not wait_for_id:
        return None

    workflow_id = None
    start = time.time()
    id_path = Path(id_file_path)
    while time.time() - start < id_timeout_sec:
        if id_path.exists() and id_path.stat().st_size > 0:
            with id_path.open("r") as handle:
                workflow_id = handle.read().strip() or None
            if workflow_id:
                break
        time.sleep(0.1)

    try:
        os.unlink(id_file_path)
    except Exception:
        pass

    return workflow_id

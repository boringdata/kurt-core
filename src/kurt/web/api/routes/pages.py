"""Workflow page routes: page data, asset libraries, edit dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# --- Pydantic models ---


class PageDataUpdate(BaseModel):
    rows: list[dict[str, Any]] = []


class EditIntentAction(BaseModel):
    """A single editing intent from the UI."""

    action: str  # add_text, add_shape, move_element, resize_element, delete_element, trim, cut
    text: Optional[str] = None
    shape_id: Optional[str] = None
    element_id: Optional[str] = None
    position: Optional[dict[str, float]] = None  # {x, y}
    size: Optional[dict[str, float]] = None  # {width, height}
    style: Optional[dict[str, Any]] = None  # {font, size, color, ...}
    time_range: Optional[dict[str, float]] = None  # {start, end} for video overlays
    animated: bool = False


class EditIntentRequest(BaseModel):
    """Request body for dispatching editing intents to the agent."""

    intents: list[EditIntentAction] = []
    session_id: Optional[str] = None  # If provided, use existing Claude session


# --- Helper functions ---


def _get_file_mtime(file_path: Optional[Path]) -> Optional[float]:
    """Get file modification time as Unix timestamp, or None if file doesn't exist."""
    if file_path and file_path.exists():
        return file_path.stat().st_mtime
    return None


def _read_table_data(page: dict, offset: int, limit: int) -> dict:
    """Read data from a table page's data_path file."""
    data_path = page.get("data_path")
    if not data_path:
        return {"columns": page.get("columns", []), "rows": [], "total": 0}

    file_path = Path(data_path)
    if not file_path.exists():
        return {"columns": page.get("columns", []), "rows": [], "total": 0}

    suffix = file_path.suffix.lower()
    rows = []

    if suffix == ".json":
        with open(file_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict) and "rows" in data:
            rows = data["rows"]
    elif suffix == ".csv":
        import csv

        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    else:
        return {"columns": page.get("columns", []), "rows": [], "total": 0, "error": f"Unsupported format: {suffix}"}

    total = len(rows)
    paginated = rows[offset : offset + limit]

    # Auto-detect columns if not specified
    columns = page.get("columns", [])
    if not columns and paginated:
        columns = [{"name": k, "label": k, "type": "text", "editable": True} for k in paginated[0].keys()]

    return {
        "columns": columns,
        "rows": paginated,
        "total": total,
        "offset": offset,
        "limit": limit,
        "seed": page.get("seed", False),
    }


def _read_image_data(page: dict) -> dict:
    """Read metadata for an image page."""
    image_path = page.get("image_path", "")
    file_path = Path(image_path) if image_path else None
    exists = file_path.exists() if file_path else False

    return {
        "type": "image",
        "image_path": image_path,
        "exists": exists,
        "editable": page.get("editable", False),
        "title": page.get("title", "Image"),
        "mtime": _get_file_mtime(file_path),
    }


def _read_video_data(page: dict) -> dict:
    """Read metadata for a video page."""
    video_path = page.get("video_path", "")
    file_path = Path(video_path) if video_path else None
    exists = file_path.exists() if file_path else False

    return {
        "type": "video",
        "video_path": video_path,
        "exists": exists,
        "trim": page.get("trim", True),
        "max_duration": page.get("max_duration"),
        "title": page.get("title", "Video"),
        "mtime": _get_file_mtime(file_path),
    }


def _read_motion_canvas_data(page: dict) -> dict:
    """Read metadata for a motion canvas page."""
    scene_path = page.get("scene_path", "")
    output_path = page.get("output_path", "")
    file_path = Path(scene_path) if scene_path else None
    output_file = Path(output_path) if output_path else None
    exists = file_path.exists() if file_path else False
    output_exists = output_file.exists() if output_file else False

    return {
        "type": "motion-canvas",
        "scene_path": scene_path,
        "output_path": output_path,
        "exists": exists,
        "output_exists": output_exists,
        "preview_url": page.get("preview_url"),
        "duration": page.get("duration"),
        "fps": page.get("fps", 30),
        "editable": page.get("editable", False),
        "title": page.get("title", "Motion Canvas"),
        "mtime": _get_file_mtime(output_file or file_path),
    }


def _read_video_sequence_data(page: dict) -> dict:
    """Read metadata for a video sequence (MC composition) page."""
    output_path = page.get("output_path", "")
    output_file = Path(output_path) if output_path else None
    output_exists = output_file.exists() if output_file else False
    scenes = page.get("scenes", [])

    # Check which scenes have rendered output
    scene_status = []
    for scene in scenes:
        s = dict(scene)
        if scene.get("type") == "motion-canvas":
            rendered = Path(scene.get("rendered_path", "")) if scene.get("rendered_path") else None
            s["rendered_exists"] = rendered.exists() if rendered else False
        elif scene.get("type") == "clip":
            source = Path(scene.get("source_path", "")) if scene.get("source_path") else None
            s["source_exists"] = source.exists() if source else False
        scene_status.append(s)

    return {
        "type": "video-sequence",
        "output_path": output_path,
        "output_exists": output_exists,
        "scenes": scene_status,
        "transitions": page.get("transitions", []),
        "resolution": page.get("resolution", [1920, 1080]),
        "title": page.get("title", "Video Sequence"),
        "mtime": _get_file_mtime(output_file),
    }


# --- Page Endpoints ---


@router.get("/api/workflows/{workflow_id}/pages")
def api_get_workflow_pages(workflow_id: str):
    """Get page definitions for a workflow (from workflow definition file)."""
    try:
        from kurt.workflows.agents.registry import find_definition_by_workflow_id

        pages = find_definition_by_workflow_id(workflow_id)
        return {"pages": pages}
    except Exception:
        # Workflow may not have pages or registry may not be available
        return {"pages": []}


@router.get("/api/workflows/{workflow_id}/pages/{page_id}/data")
def api_get_page_data(
    workflow_id: str,
    page_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    """Get data for a specific workflow page.

    For data-table pages, reads from the data_path file (CSV/JSON).
    For image/video/motion-canvas pages, returns file metadata.
    """
    try:
        from kurt.workflows.agents.registry import get_page_config

        page = get_page_config(workflow_id, page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")

        if page["type"] == "data-table":
            return _read_table_data(page, offset, limit)
        elif page["type"] == "image":
            return _read_image_data(page)
        elif page["type"] == "video":
            return _read_video_data(page)
        elif page["type"] == "motion-canvas":
            return _read_motion_canvas_data(page)
        elif page["type"] == "video-sequence":
            return _read_video_sequence_data(page)
        else:
            return {"page": page, "data": None}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/workflows/{workflow_id}/pages/{page_id}/data")
def api_update_page_data(
    workflow_id: str,
    page_id: str,
    body: PageDataUpdate,
):
    """Update data for a data-table page. Writes back to the data_path file."""
    try:
        from kurt.workflows.agents.registry import get_page_config

        page = get_page_config(workflow_id, page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")

        if page["type"] != "data-table":
            raise HTTPException(status_code=400, detail="Only data-table pages support data updates")

        data_path = page.get("data_path")
        if not data_path:
            raise HTTPException(status_code=400, detail="Page has no data_path configured")

        file_path = Path(data_path)
        suffix = file_path.suffix.lower()

        if suffix == ".json":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(body.rows, f, indent=2)
        elif suffix == ".csv":
            import csv

            file_path.parent.mkdir(parents=True, exist_ok=True)
            if body.rows:
                fieldnames = list(body.rows[0].keys())
                with open(file_path, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(body.rows)
            else:
                file_path.write_text("")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported data format: {suffix}")

        return {"status": "ok", "rows_written": len(body.rows)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/workflows/{workflow_id}/pages/{page_id}/run")
def api_run_workflow_from_page(
    workflow_id: str,
    page_id: str,
):
    """Trigger a workflow re-run after seed data has been edited."""
    try:
        from kurt.workflows.agents.registry import get_definition_for_workflow, get_page_config

        page = get_page_config(workflow_id, page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")

        if not page.get("seed"):
            raise HTTPException(status_code=400, detail="Page is not a seed data page")

        definition = get_definition_for_workflow(workflow_id)
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        from kurt.workflows.agents import run_definition

        result = run_definition(definition["name"], background=True)
        return {"status": "started", "workflow_id": result.get("workflow_id")}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/workflows/{workflow_id}/pages/{page_id}/edit")
def api_dispatch_page_edit(
    workflow_id: str,
    page_id: str,
    body: EditIntentRequest,
):
    """Dispatch editing intents to the agent for a workflow page.

    Converts structured intents into a natural language prompt and either:
    - Injects into an existing Claude session (if session_id provided)
    - Starts a new background agent workflow
    """
    try:
        from kurt.workflows.agents.registry import get_page_config

        page = get_page_config(workflow_id, page_id)
        if not page:
            raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")

        from kurt.web.api.intent_dispatch import build_edit_prompt, dispatch_edit

        prompt = build_edit_prompt(page, [i.model_dump() for i in body.intents])
        result = dispatch_edit(
            workflow_id=workflow_id,
            page=page,
            prompt=prompt,
            session_id=body.session_id,
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Asset Library Endpoints ---


@router.get("/api/assets/shapes")
def api_get_shapes():
    """Get shape library manifest from assets/shapes/manifest.json."""
    manifest_path = Path.cwd() / "assets" / "shapes" / "manifest.json"
    if not manifest_path.exists():
        return {"shapes": []}
    try:
        with open(manifest_path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"shapes": data}
    except Exception:
        return {"shapes": []}


@router.get("/api/assets/fonts")
def api_get_fonts():
    """Get font library manifest from assets/fonts/manifest.json."""
    manifest_path = Path.cwd() / "assets" / "fonts" / "manifest.json"
    if not manifest_path.exists():
        return {"fonts": []}
    try:
        with open(manifest_path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"fonts": data}
    except Exception:
        return {"fonts": []}

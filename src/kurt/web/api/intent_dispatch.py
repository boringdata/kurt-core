"""Intent-to-prompt conversion and dispatch for workflow page editing.

Converts structured editing intents from the UI into natural language prompts
for the Claude Code agent. Supports two dispatch modes:
- Chat dispatch: inject into existing Claude WebSocket session
- Background dispatch: start a new agent workflow execution
"""

from __future__ import annotations

from typing import Any, Optional


def build_edit_prompt(page: dict, intents: list[dict]) -> str:
    """Convert structured editing intents into a natural language prompt.

    Args:
        page: Page config dict (type, scene_path, video_path, image_path, etc.)
        intents: List of intent dicts with action, position, text, etc.

    Returns:
        Natural language prompt string for the agent.
    """
    page_type = page.get("type", "")
    target_file = _get_target_file(page)

    lines = []
    lines.append(f"Edit the file at `{target_file}`:")
    lines.append("")

    for intent in intents:
        line = _format_intent(intent, page_type)
        if line:
            lines.append(f"- {line}")

    lines.append("")

    # Add type-specific context
    if page_type == "motion-canvas":
        lines.append("This is a Motion Canvas scene file (.tsx). Use Motion Canvas 2D API.")
        lines.append("Import shapes from '@motion-canvas/2d' and use generator functions for animations.")
        assets_dir = page.get("assets_dir")
        if assets_dir:
            lines.append(f"Custom assets (shapes, fonts) are in `{assets_dir}/`.")
    elif page_type == "video":
        lines.append("Use ffmpeg CLI commands to apply the edits to the video file.")
        lines.append("Preserve the original file as a backup before modifying.")
    elif page_type == "video-sequence":
        lines.append("This is a video sequence project using Motion Canvas as the composition layer.")
        lines.append("Each scene is a .tsx file. Video clips are wrapped as MC Video elements.")
    elif page_type == "image":
        lines.append("Use ImageMagick or Python Pillow to apply the edits to the image file.")
        lines.append("Preserve the original file as a backup before modifying.")
        assets_dir = page.get("assets_dir")
        if assets_dir:
            lines.append(f"Custom fonts are in `{assets_dir}/fonts/` and shapes in `{assets_dir}/shapes/`.")

    return "\n".join(lines)


def _get_target_file(page: dict) -> str:
    """Get the primary target file path for a page type."""
    page_type = page.get("type", "")
    if page_type == "motion-canvas":
        return page.get("scene_path", "scene.tsx")
    elif page_type == "video":
        return page.get("video_path", "video.mp4")
    elif page_type == "video-sequence":
        return page.get("output_path", "output/final.mp4")
    elif page_type == "image":
        return page.get("image_path", "image.png")
    return "unknown"


def _format_intent(intent: dict, page_type: str) -> str:
    """Format a single intent into a human-readable instruction."""
    action = intent.get("action", "")

    if action == "add_text":
        text = intent.get("text", "")
        pos = intent.get("position", {})
        style = intent.get("style", {})
        parts = [f"Add text '{text}'"]
        if pos:
            parts.append(f"at position ({pos.get('x', 0)}, {pos.get('y', 0)})")
        if style.get("font"):
            parts.append(f"using font '{style['font']}'")
        if style.get("size"):
            parts.append(f"size {style['size']}")
        if style.get("color"):
            parts.append(f"color {style['color']}")
        time_range = intent.get("time_range")
        if time_range and page_type in ("video", "motion-canvas", "video-sequence"):
            parts.append(f"visible from {time_range.get('start', 0)}s to {time_range.get('end', 0)}s")
        return " ".join(parts)

    elif action == "add_shape":
        shape_id = intent.get("shape_id", "shape")
        pos = intent.get("position", {})
        size = intent.get("size", {})
        animated = intent.get("animated", False)
        parts = [f"Add SVG shape '{shape_id}'"]
        if pos:
            parts.append(f"at ({pos.get('x', 0)}, {pos.get('y', 0)})")
        if size:
            parts.append(f"size {size.get('width', 100)}x{size.get('height', 100)}")
        if animated:
            parts.append("with entrance animation")
        return " ".join(parts)

    elif action == "move_element":
        element_id = intent.get("element_id", "element")
        pos = intent.get("position", {})
        return f"Move element '{element_id}' to ({pos.get('x', 0)}, {pos.get('y', 0)})"

    elif action == "resize_element":
        element_id = intent.get("element_id", "element")
        size = intent.get("size", {})
        return f"Resize element '{element_id}' to {size.get('width', 100)}x{size.get('height', 100)}"

    elif action == "delete_element":
        element_id = intent.get("element_id", "element")
        return f"Delete element '{element_id}'"

    elif action == "trim":
        time_range = intent.get("time_range", {})
        return f"Trim to {time_range.get('start', 0)}s - {time_range.get('end', 0)}s"

    elif action == "cut":
        time_range = intent.get("time_range", {})
        return f"Cut segment from {time_range.get('start', 0)}s to {time_range.get('end', 0)}s"

    return f"Unknown action: {action}"


def dispatch_edit(
    workflow_id: str,
    page: dict,
    prompt: str,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Dispatch an editing prompt to the agent.

    Args:
        workflow_id: DBOS workflow ID
        page: Page config dict
        prompt: Natural language editing prompt
        session_id: If provided, inject into existing Claude session

    Returns:
        dict with dispatch result (status, workflow_id or session info)
    """
    if session_id:
        # Mode A: Chat dispatch - inject into existing session
        # This would use the StreamSession to send a message
        return {
            "status": "dispatched",
            "mode": "chat",
            "session_id": session_id,
            "prompt": prompt,
        }
    else:
        # Mode B: Background dispatch - start new agent workflow
        try:
            from kurt.workflows.agents import run_definition
            from kurt.workflows.agents.registry import get_definition_for_workflow

            definition = get_definition_for_workflow(workflow_id)
            if not definition:
                return {"status": "error", "detail": "Workflow definition not found"}

            result = run_definition(
                definition["name"],
                inputs={"task": prompt},
                background=True,
            )
            return {
                "status": "started",
                "mode": "background",
                "workflow_id": result.get("workflow_id"),
            }
        except Exception as e:
            return {"status": "error", "detail": str(e)}

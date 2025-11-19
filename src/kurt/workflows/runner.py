"""DBOS workflow runner for background execution.

Wraps workflow execution in DBOS workflows for durability and resumability.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from kurt.workflows import DBOS, DBOS_AVAILABLE, get_dbos
from kurt.workflows.executor import WorkflowExecutor
from kurt.workflows.parser import load_workflow

logger = logging.getLogger(__name__)


if DBOS_AVAILABLE:

    @DBOS.workflow()
    def run_yaml_workflow(
        workflow_file: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        DBOS workflow that executes a YAML workflow definition.

        This workflow is durable and resumable - if it crashes, it will resume
        from the last completed step.

        Args:
            workflow_file: Path to YAML workflow file
            variables: Variables to pass to the workflow

        Returns:
            Workflow execution results
        """
        logger.info(f"Starting YAML workflow: {workflow_file}")

        # Publish workflow start event
        DBOS.send(topic="workflow_start", message={"file": workflow_file})

        try:
            # Load workflow definition
            workflow_def = load_workflow(workflow_file)

            # Create executor
            executor = WorkflowExecutor(workflow_def, variables)

            # Execute workflow
            result = executor.execute()

            # Publish completion event
            DBOS.send(
                topic="workflow_complete",
                message={
                    "file": workflow_file,
                    "status": result["status"],
                },
            )

            logger.info(f"Workflow completed: {workflow_file}")
            return result

        except Exception as e:
            logger.error(f"Workflow failed: {workflow_file}: {e}")

            # Publish error event
            DBOS.send(
                topic="workflow_error",
                message={
                    "file": workflow_file,
                    "error": str(e),
                },
            )

            return {
                "status": "error",
                "error": str(e),
            }


def run_workflow_sync(
    workflow_file: Path | str, variables: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run a workflow synchronously (blocking).

    Args:
        workflow_file: Path to YAML workflow file
        variables: Variables to pass to the workflow

    Returns:
        Workflow execution results
    """
    workflow_def = load_workflow(workflow_file)
    executor = WorkflowExecutor(workflow_def, variables)
    return executor.execute()


def run_workflow_background(
    workflow_file: Path | str, variables: Optional[Dict[str, Any]] = None
) -> str:
    """
    Run a workflow in the background using DBOS.

    Args:
        workflow_file: Path to YAML workflow file
        variables: Variables to pass to the workflow

    Returns:
        Workflow ID for tracking

    Raises:
        RuntimeError: If DBOS is not available
    """
    if not DBOS_AVAILABLE:
        raise RuntimeError(
            "DBOS is not available. Install it with: uv sync\n"
            "Background workflows require DBOS to be installed."
        )

    # Initialize DBOS if needed
    dbos = get_dbos()

    # Start workflow in background
    workflow_file_str = str(workflow_file)
    handle = dbos.start_workflow(run_yaml_workflow, workflow_file_str, variables)

    return handle.workflow_id


__all__ = [
    "run_workflow_sync",
    "run_workflow_background",
]

if DBOS_AVAILABLE:
    __all__.append("run_yaml_workflow")

"""
DBOS integration for streaming events to the CLI.

This module provides the integration between the indexing framework
and DBOS event streams for real-time progress updates.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import DBOS
try:
    from dbos import DBOS

    HAS_DBOS = True
except ImportError:
    HAS_DBOS = False
    logger.debug("DBOS not available - events will only be logged")


class DBOSStreamWriter:
    """
    Writes events to DBOS streams for CLI consumption.

    This integrates with the DBOS workflow system to provide
    real-time progress updates to the CLI.
    """

    def __init__(self, workflow_id: Optional[str] = None):
        """
        Initialize DBOS stream writer.

        Args:
            workflow_id: Current workflow ID
        """
        self.workflow_id = workflow_id
        self.stream_name = f"indexing_{workflow_id}" if workflow_id else "indexing_default"

    def write_event(self, event_type: str, data: Dict[str, Any]):
        """
        Write an event to the DBOS stream.

        Args:
            event_type: Type of event (started, progress, completed, failed)
            data: Event data
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "workflow_id": self.workflow_id,
            **data,
        }

        if HAS_DBOS:
            try:
                # Write to DBOS stream
                DBOS.write_stream(self.stream_name, json.dumps(event))
                logger.debug(f"Wrote event to DBOS stream {self.stream_name}: {event_type}")
            except Exception as e:
                logger.error(f"Failed to write to DBOS stream: {e}")
        else:
            # Fallback to logging
            logger.info(f"DBOS Event [{self.stream_name}]: {json.dumps(event)}")

    def write_model_started(self, model_name: str, description: str = ""):
        """Write model started event."""
        self.write_event(
            "model_started", {"model": model_name, "description": description, "status": "running"}
        )

    def write_model_progress(self, model_name: str, current: int, total: int, message: str = ""):
        """Write model progress event."""
        self.write_event(
            "model_progress",
            {
                "model": model_name,
                "current": current,
                "total": total,
                "percentage": (current / total * 100) if total > 0 else 0,
                "message": message,
            },
        )

    def write_model_completed(self, model_name: str, rows_written: int, execution_time: float):
        """Write model completed event."""
        self.write_event(
            "model_completed",
            {
                "model": model_name,
                "rows_written": rows_written,
                "execution_time": execution_time,
                "status": "success",
            },
        )

    def write_model_failed(self, model_name: str, error: str):
        """Write model failed event."""
        self.write_event("model_failed", {"model": model_name, "error": error, "status": "failed"})


# Global writer instance
_global_writer: Optional[DBOSStreamWriter] = None


def get_dbos_writer() -> DBOSStreamWriter:
    """Get the global DBOS writer instance."""
    global _global_writer
    if _global_writer is None:
        _global_writer = DBOSStreamWriter()
    return _global_writer


def configure_dbos_writer(workflow_id: Optional[str] = None):
    """Configure the global DBOS writer with workflow context."""
    global _global_writer
    _global_writer = DBOSStreamWriter(workflow_id=workflow_id)

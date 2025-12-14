"""
Display utilities for model execution progress.

Provides a simple API for displaying model execution progress,
with DBOS streaming integration for CLI consumption.
"""

import logging
from typing import Any, Dict, Optional

from .dbos_integration import get_dbos_writer

logger = logging.getLogger(__name__)


class Display:
    """
    Display manager for model execution progress with DBOS streaming.

    This provides both console output and DBOS event streaming for
    real-time progress updates in the CLI.
    """

    def __init__(self):
        """Initialize display manager."""
        self.current_step: Optional[str] = None
        self.step_context: Dict[str, Any] = {}
        self.dbos_writer = get_dbos_writer()

    def start_step(self, step_name: str, description: str = "") -> None:
        """
        Start a new step in the display.

        Args:
            step_name: Name of the step
            description: Optional description of what the step does
        """
        self.current_step = step_name
        self.step_context = {"description": description}

        # Print step header
        header = f"▶ {step_name}"
        if description:
            header += f": {description}"

        logger.info(header)
        print(header)

        # Stream to DBOS
        self.dbos_writer.write_model_started(step_name, description)

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update the current step's progress.

        Args:
            updates: Dictionary of progress updates
        """
        if not self.current_step:
            return

        # Update context
        self.step_context.update(updates)

        # Log updates
        logger.debug(
            f"Progress update for {self.current_step}",
            extra={"step": self.current_step, **updates},
        )

        # Stream progress to DBOS if we have current/total
        if "current" in updates and "total" in updates:
            message = updates.get("message", "")
            self.dbos_writer.write_model_progress(
                self.current_step, updates["current"], updates["total"], message
            )

    def end_step(self, step_name: str, summary: Dict[str, Any]) -> None:
        """
        End a step and display summary.

        Args:
            step_name: Name of the step to end
            summary: Summary information to display
        """
        if self.current_step != step_name:
            logger.warning(f"Ending step {step_name} but current step is {self.current_step}")

        # Determine status symbol
        status = summary.get("status", "completed")
        if status == "completed":
            symbol = "✓"
        elif status == "failed":
            symbol = "✗"
        else:
            symbol = "?"

        # Print summary
        summary_line = f"{symbol} {step_name}"

        # Add execution time if available
        if "execution_time" in summary:
            summary_line += f" ({summary['execution_time']})"

        # Add error if failed
        if status == "failed" and "error" in summary:
            summary_line += f" - Error: {summary['error']}"

        logger.info(summary_line)
        print(summary_line)

        # Stream to DBOS
        if status == "completed":
            rows_written = summary.get("rows_written", 0)
            exec_time_str = summary.get("execution_time", "0s")
            # Parse execution time (format: "2.5s")
            try:
                exec_time = float(exec_time_str.rstrip("s"))
            except (ValueError, AttributeError):
                exec_time = 0.0
            self.dbos_writer.write_model_completed(step_name, rows_written, exec_time)
        elif status == "failed":
            error = summary.get("error", "Unknown error")
            self.dbos_writer.write_model_failed(step_name, error)

        # Reset state
        self.current_step = None
        self.step_context = {}


# Global display instance
display = Display()

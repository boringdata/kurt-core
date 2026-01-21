"""
SaveStep - Observable transaction step for saving data to workflow tables.

Provides a durable DBOS transaction wrapper for batch-saving rows to SQLModel tables.
Uses the same StepHooks pattern as LLMStep for lifecycle observation.

Example:
    from sqlmodel import SQLModel, Field
    from kurt.core import SaveStep

    class MyEntity(SQLModel, table=True):
        __tablename__ = "my_entities"
        id: int | None = Field(default=None, primary_key=True)
        name: str
        value: float

    save_step = SaveStep(name="save_entities", model=MyEntity)

    # Must be called from within a @DBOS.workflow()
    result = save_step.run([
        {"name": "Entity A", "value": 1.0},
        {"name": "Entity B", "value": 2.0},
    ])
    # Returns: {"saved": 2, "errors": [], "table": "my_entities"}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dbos import DBOS
from pydantic import ValidationError

from .hooks import NoopStepHooks, StepHooks

if TYPE_CHECKING:
    from sqlmodel import SQLModel


def _format_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    """Format Pydantic validation errors into a structured list."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )
    return errors


class SaveStep:
    """
    Observable transaction step for saving data to workflow tables.

    Wraps a DBOS transaction for batch-saving rows to a SQLModel table.
    Validates each row against the model schema before persisting.

    Args:
        name: Step name for tracking and logging
        model: SQLModel class with __tablename__ defined
        hooks: Optional StepHooks for lifecycle callbacks

    Note:
        Must be called from within a @DBOS.workflow() context (DBOS constraint).
    """

    def __init__(
        self,
        *,
        name: str,
        model: type[SQLModel],
        hooks: StepHooks | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self._hooks = hooks or NoopStepHooks()
        self._table_name = getattr(model, "__tablename__", model.__name__)

        self._register_transaction()

    def _register_transaction(self) -> None:
        """Register the DBOS transaction for saving rows."""
        step_instance = self

        @DBOS.transaction()
        def save_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
            """
            Durable transaction to save rows to the database.

            Validates each row against the model schema and persists valid rows.
            Returns summary with saved count, errors, and table name.
            """
            from kurt.db import managed_session

            saved = 0
            errors: list[dict[str, Any]] = []

            with managed_session() as session:
                for idx, row in enumerate(rows):
                    try:
                        # Validate and create model instance
                        instance = step_instance.model(**row)
                        session.add(instance)
                        session.flush()  # Flush to catch DB-level errors early
                        saved += 1
                    except ValidationError as exc:
                        errors.append(
                            {
                                "idx": idx,
                                "type": "validation",
                                "errors": _format_validation_errors(exc),
                            }
                        )
                    except Exception as exc:
                        errors.append(
                            {
                                "idx": idx,
                                "type": "database",
                                "error": str(exc),
                            }
                        )

            return {
                "saved": saved,
                "errors": errors,
                "table": step_instance._table_name,
            }

        self._save_rows = save_rows

    def run(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Validate and save rows via DBOS transaction.

        Args:
            rows: List of dicts to save as model instances

        Returns:
            Dict with:
                - saved: Number of successfully saved rows
                - errors: List of error dicts with idx and error details
                - table: Name of the target table
        """
        from kurt.db import ensure_tables

        # Ensure table exists before saving
        ensure_tables([self.model])

        total = len(rows)

        # Call on_start hook (concurrency is 1 for transactions)
        self._hooks.on_start(
            step_name=self.name,
            total=total,
            concurrency=1,
        )

        # Execute the DBOS transaction
        result = self._save_rows(rows)

        # Call on_end hook with results
        self._hooks.on_end(
            step_name=self.name,
            successful=result["saved"],
            total=total,
            errors=[str(e) for e in result["errors"]],
        )

        return result

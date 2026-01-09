"""Initial schema - LLM traces table

Revision ID: 001_initial
Revises:
Create Date: 2026-01-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("step_name", sa.String(), nullable=False),
        # Model info
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="anthropic"),
        # Request/Response
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("structured_output", sa.Text(), nullable=True),
        # Token usage
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        # Cost tracking (in USD)
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        # Timing
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        # Error tracking
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        # Mixins
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_llm_traces_workflow_id", "llm_traces", ["workflow_id"])
    op.create_index("ix_llm_traces_step_name", "llm_traces", ["step_name"])
    op.create_index("ix_llm_traces_user_id", "llm_traces", ["user_id"])
    op.create_index("ix_llm_traces_workspace_id", "llm_traces", ["workspace_id"])
    op.create_index("ix_llm_traces_created_at", "llm_traces", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_traces_created_at", "llm_traces")
    op.drop_index("ix_llm_traces_workspace_id", "llm_traces")
    op.drop_index("ix_llm_traces_user_id", "llm_traces")
    op.drop_index("ix_llm_traces_step_name", "llm_traces")
    op.drop_index("ix_llm_traces_workflow_id", "llm_traces")
    op.drop_table("llm_traces")

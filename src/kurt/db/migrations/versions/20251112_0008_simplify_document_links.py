"""Simplify document_links table

Remove link_type and context fields. Keep only essential link data:
source, target, and anchor_text. Claude interprets anchor text to
understand relationship types.

Revision ID: 008_simplify_links
Revises: 007_document_links
Create Date: 2025-11-12

"""

from alembic import op

# revision identifiers, used by Alembic
revision: str = "008_simplify_links"
down_revision: str = "007_document_links"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Remove link_type and context columns from document_links."""
    # Drop link_type column (enum)
    op.drop_column("document_links", "link_type")

    # Drop context column
    op.drop_column("document_links", "context")


def downgrade() -> None:
    """Restore link_type and context columns."""
    import sqlalchemy as sa

    # Restore context column
    op.add_column(
        "document_links",
        sa.Column("context", sa.VARCHAR(length=1000), nullable=True),
    )

    # Restore link_type column with enum
    # Note: This is a simplified downgrade - original enum type may need recreation
    op.add_column(
        "document_links",
        sa.Column(
            "link_type",
            sa.VARCHAR(length=50),
            nullable=False,
            server_default="outbound",
        ),
    )

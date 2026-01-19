"""merge_migration_heads

Revision ID: 0b94d9578a11
Revises: 84688a81b9ab, 008_rls_workspace
Create Date: 2026-01-19 11:13:28.015585+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0b94d9578a11"
down_revision: Union[str, None] = ("84688a81b9ab", "008_rls_workspace")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""add identifying image status

Revision ID: 47b6ba380f48
Revises: 3fb644e16b27
Create Date: 2026-08-28 23:12:12.013205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47b6ba380f48'
down_revision: Union[str, Sequence[str], None] = '3fb644e16b27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE image_status ADD VALUE IF NOT EXISTS 'identifying'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enums; downgrading would require
    # recreating the type and rewriting the column, which isn't worth it for
    # an additive status value. Left as a no-op - the value simply becomes
    # unused again if the app code stops writing it.
    pass

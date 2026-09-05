"""cascade delete jobs when image deleted

Revision ID: 3fb644e16b27
Revises: 30bcd2235788
Create Date: 2026-08-28 23:04:15.817296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fb644e16b27'
down_revision: Union[str, Sequence[str], None] = '30bcd2235788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('jobs_image_id_fkey'), 'jobs', type_='foreignkey')
    op.create_foreign_key(
        'jobs_image_id_fkey', 'jobs', 'images', ['image_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('jobs_image_id_fkey', 'jobs', type_='foreignkey')
    op.create_foreign_key(op.f('jobs_image_id_fkey'), 'jobs', 'images', ['image_id'], ['id'])

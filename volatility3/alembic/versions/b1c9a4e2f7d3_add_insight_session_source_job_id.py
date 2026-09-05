"""add insight_sessions.source_job_id

Revision ID: b1c9a4e2f7d3
Revises: e996f9c0a648
Create Date: 2026-08-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b1c9a4e2f7d3'
down_revision: Union[str, Sequence[str], None] = 'e996f9c0a648'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable, no server_default needed: existing sessions are all
    # whole-image baseline sessions, correctly represented as NULL here
    # (distinct from a per-job Insights session, which sets this).
    op.add_column('insight_sessions', sa.Column('source_job_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_insight_sessions_source_job_id_jobs',
        'insight_sessions', 'jobs',
        ['source_job_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_insight_sessions_source_job_id_jobs', 'insight_sessions', type_='foreignkey')
    op.drop_column('insight_sessions', 'source_job_id')

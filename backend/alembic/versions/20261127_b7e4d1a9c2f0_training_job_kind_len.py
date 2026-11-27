"""training_jobs.kind: VARCHAR(8) -> VARCHAR(16) ("autolabel" sig'ishi uchun)

Revision ID: b7e4d1a9c2f0
Revises: 9a1c2e7d5b30
Create Date: 2026-11-27 12:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e4d1a9c2f0"
down_revision: Union[str, Sequence[str], None] = "9a1c2e7d5b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("training_jobs", "kind", type_=sa.String(16), existing_type=sa.String(8))


def downgrade() -> None:
    op.alter_column("training_jobs", "kind", type_=sa.String(8), existing_type=sa.String(16))

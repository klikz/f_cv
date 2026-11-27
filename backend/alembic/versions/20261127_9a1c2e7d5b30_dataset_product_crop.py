"""dataset_images: product_id va crop

Revision ID: 9a1c2e7d5b30
Revises: 63ae1c97f023
Create Date: 2026-11-27 10:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9a1c2e7d5b30"
down_revision: Union[str, Sequence[str], None] = "63ae1c97f023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dataset_images", sa.Column("product_id", sa.Integer(), nullable=True))
    op.add_column("dataset_images", sa.Column("crop", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index("ix_dataset_images_product_id", "dataset_images", ["product_id"], unique=False)
    op.create_foreign_key(
        "fk_dataset_images_product_id_products",
        "dataset_images",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_dataset_images_product_id_products", "dataset_images", type_="foreignkey")
    op.drop_index("ix_dataset_images_product_id", table_name="dataset_images")
    op.drop_column("dataset_images", "crop")
    op.drop_column("dataset_images", "product_id")

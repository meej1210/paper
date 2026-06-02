"""expand sast issue test_id

Revision ID: d2c8f6a4b913
Revises: b8a4d8c1e2f0
Create Date: 2026-05-11 15:02:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2c8f6a4b913"
down_revision = "b8a4d8c1e2f0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sast_issues", schema=None) as batch_op:
        batch_op.alter_column(
            "test_id",
            existing_type=sa.String(length=64),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table("sast_issues", schema=None) as batch_op:
        batch_op.alter_column(
            "test_id",
            existing_type=sa.String(length=255),
            type_=sa.String(length=64),
            existing_nullable=True,
        )

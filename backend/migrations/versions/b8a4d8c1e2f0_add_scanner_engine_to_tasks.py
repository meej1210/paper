"""add scanner_engine to tasks

Revision ID: b8a4d8c1e2f0
Revises: 56c463a0a97d
Create Date: 2026-05-07 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b8a4d8c1e2f0"
down_revision = "56c463a0a97d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("scanner_engine", sa.String(length=32), nullable=True))
        batch_op.create_index(batch_op.f("ix_tasks_scanner_engine"), ["scanner_engine"], unique=False)


def downgrade():
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tasks_scanner_engine"))
        batch_op.drop_column("scanner_engine")

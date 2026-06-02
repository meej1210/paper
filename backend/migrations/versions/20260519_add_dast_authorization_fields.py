"""add dast authorization fields

Revision ID: 20260519_dast_auth
Revises: 20260519_add_sca_tables
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260519_dast_auth"
down_revision = "20260519addsca"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("authorization_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("target_host", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("target_ip", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("target_policy", sa.String(length=64), nullable=True))
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("authorization_confirmed", server_default=None)


def downgrade():
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("target_policy")
        batch_op.drop_column("target_ip")
        batch_op.drop_column("target_host")
        batch_op.drop_column("authorization_confirmed")

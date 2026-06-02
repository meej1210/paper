"""add sca to task type enum

Revision ID: 20260528scatype
Revises: 20260519_dast_auth
Create Date: 2026-05-28 12:18:00.000000

"""
from alembic import op


revision = "20260528scatype"
down_revision = "20260519_dast_auth"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute("ALTER TABLE tasks MODIFY task_type ENUM('SAST','DAST','SCA') NOT NULL")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute("ALTER TABLE tasks MODIFY task_type ENUM('SAST','DAST') NOT NULL")

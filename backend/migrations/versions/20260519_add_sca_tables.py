"""add sca tables

Revision ID: 20260519addsca
Revises: e4b8c1a9f217
Create Date: 2026-05-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "20260519addsca"
down_revision = "e4b8c1a9f217"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sca_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("dependency_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vulnerability_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fixable_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_report_path", sa.Text(), nullable=True),
        sa.Column("package_distribution", sa.Text(), nullable=True),
        sa.Column("severity_distribution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_table(
        "sca_issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("installed_version", sa.String(length=128), nullable=True),
        sa.Column("vulnerability_id", sa.String(length=128), nullable=True),
        sa.Column("aliases", sa.Text(), nullable=True),
        sa.Column("fix_versions", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sca_issues_task_id"), "sca_issues", ["task_id"], unique=False)
    op.create_index(op.f("ix_sca_issues_package_name"), "sca_issues", ["package_name"], unique=False)
    op.create_index(op.f("ix_sca_issues_vulnerability_id"), "sca_issues", ["vulnerability_id"], unique=False)
    op.create_index(op.f("ix_sca_issues_severity"), "sca_issues", ["severity"], unique=False)

    with op.batch_alter_table("sca_results", schema=None) as batch_op:
        batch_op.alter_column("dependency_count", server_default=None)
        batch_op.alter_column("vulnerability_count", server_default=None)
        batch_op.alter_column("fixable_count", server_default=None)


def downgrade():
    op.drop_index(op.f("ix_sca_issues_severity"), table_name="sca_issues")
    op.drop_index(op.f("ix_sca_issues_vulnerability_id"), table_name="sca_issues")
    op.drop_index(op.f("ix_sca_issues_package_name"), table_name="sca_issues")
    op.drop_index(op.f("ix_sca_issues_task_id"), table_name="sca_issues")
    op.drop_table("sca_issues")
    op.drop_table("sca_results")

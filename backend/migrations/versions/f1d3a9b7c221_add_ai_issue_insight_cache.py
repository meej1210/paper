"""add ai issue insight cache

Revision ID: f1d3a9b7c221
Revises: c3f4a8f2b129
Create Date: 2026-03-22 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1d3a9b7c221'
down_revision = 'c3f4a8f2b129'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_issue_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=16), nullable=False),
        sa.Column('issue_id', sa.Integer(), nullable=False),
        sa.Column('issue_fingerprint', sa.String(length=128), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=True),
        sa.Column('meaning', sa.Text(), nullable=False),
        sa.Column('impact', sa.Text(), nullable=False),
        sa.Column('fix', sa.Text(), nullable=False),
        sa.Column('verify', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_issue_insights_task_id'), 'ai_issue_insights', ['task_id'], unique=False)
    op.create_index(op.f('ix_ai_issue_insights_task_type'), 'ai_issue_insights', ['task_type'], unique=False)
    op.create_index(op.f('ix_ai_issue_insights_issue_id'), 'ai_issue_insights', ['issue_id'], unique=False)
    op.create_index(op.f('ix_ai_issue_insights_issue_fingerprint'), 'ai_issue_insights', ['issue_fingerprint'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_ai_issue_insights_issue_fingerprint'), table_name='ai_issue_insights')
    op.drop_index(op.f('ix_ai_issue_insights_issue_id'), table_name='ai_issue_insights')
    op.drop_index(op.f('ix_ai_issue_insights_task_type'), table_name='ai_issue_insights')
    op.drop_index(op.f('ix_ai_issue_insights_task_id'), table_name='ai_issue_insights')
    op.drop_table('ai_issue_insights')

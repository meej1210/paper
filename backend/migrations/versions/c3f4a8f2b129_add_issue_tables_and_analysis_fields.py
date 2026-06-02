"""add issue tables and analysis fields

Revision ID: c3f4a8f2b129
Revises: 9a7e1c4d2b31
Create Date: 2026-03-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3f4a8f2b129'
down_revision = '9a7e1c4d2b31'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sast_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confidence_distribution', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('file_distribution', sa.Text(), nullable=True))

    with op.batch_alter_table('dast_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('anomaly_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('additional_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('crawled_pages', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('scan_scope', sa.String(length=64), nullable=True))

    with op.batch_alter_table('dast_results', schema=None) as batch_op:
        batch_op.alter_column('anomaly_count', server_default=None)
        batch_op.alter_column('additional_count', server_default=None)
        batch_op.alter_column('crawled_pages', server_default=None)

    op.create_table(
        'sast_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.String(length=64), nullable=True),
        sa.Column('test_name', sa.String(length=255), nullable=True),
        sa.Column('issue_severity', sa.String(length=32), nullable=True),
        sa.Column('issue_confidence', sa.String(length=32), nullable=True),
        sa.Column('issue_text', sa.Text(), nullable=True),
        sa.Column('filename', sa.String(length=512), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('line_range', sa.Text(), nullable=True),
        sa.Column('code', sa.Text(), nullable=True),
        sa.Column('more_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sast_issues_task_id'), 'sast_issues', ['task_id'], unique=False)
    op.create_index(op.f('ix_sast_issues_issue_severity'), 'sast_issues', ['issue_severity'], unique=False)
    op.create_index(op.f('ix_sast_issues_issue_confidence'), 'sast_issues', ['issue_confidence'], unique=False)
    op.create_index(op.f('ix_sast_issues_filename'), 'sast_issues', ['filename'], unique=False)

    op.create_table(
        'dast_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('level', sa.String(length=32), nullable=True),
        sa.Column('method', sa.String(length=16), nullable=True),
        sa.Column('path', sa.Text(), nullable=True),
        sa.Column('parameter', sa.String(length=255), nullable=True),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('module', sa.String(length=128), nullable=True),
        sa.Column('referer', sa.Text(), nullable=True),
        sa.Column('http_request', sa.Text(), nullable=True),
        sa.Column('curl_command', sa.Text(), nullable=True),
        sa.Column('wstg', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dast_issues_task_id'), 'dast_issues', ['task_id'], unique=False)
    op.create_index(op.f('ix_dast_issues_category'), 'dast_issues', ['category'], unique=False)
    op.create_index(op.f('ix_dast_issues_level'), 'dast_issues', ['level'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_dast_issues_level'), table_name='dast_issues')
    op.drop_index(op.f('ix_dast_issues_category'), table_name='dast_issues')
    op.drop_index(op.f('ix_dast_issues_task_id'), table_name='dast_issues')
    op.drop_table('dast_issues')

    op.drop_index(op.f('ix_sast_issues_filename'), table_name='sast_issues')
    op.drop_index(op.f('ix_sast_issues_issue_confidence'), table_name='sast_issues')
    op.drop_index(op.f('ix_sast_issues_issue_severity'), table_name='sast_issues')
    op.drop_index(op.f('ix_sast_issues_task_id'), table_name='sast_issues')
    op.drop_table('sast_issues')

    with op.batch_alter_table('dast_results', schema=None) as batch_op:
        batch_op.drop_column('scan_scope')
        batch_op.drop_column('crawled_pages')
        batch_op.drop_column('additional_count')
        batch_op.drop_column('anomaly_count')

    with op.batch_alter_table('sast_results', schema=None) as batch_op:
        batch_op.drop_column('file_distribution')
        batch_op.drop_column('confidence_distribution')
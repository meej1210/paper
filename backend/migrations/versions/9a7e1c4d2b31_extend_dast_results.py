"""extend dast results

Revision ID: 9a7e1c4d2b31
Revises: e0dfbe7cd429
Create Date: 2026-03-19 23:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a7e1c4d2b31'
down_revision = 'e0dfbe7cd429'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('dast_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('issue_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('severity_distribution', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('type_distribution', sa.Text(), nullable=True))

    with op.batch_alter_table('dast_results', schema=None) as batch_op:
        batch_op.alter_column('issue_count', server_default=None)


def downgrade():
    with op.batch_alter_table('dast_results', schema=None) as batch_op:
        batch_op.drop_column('type_distribution')
        batch_op.drop_column('severity_distribution')
        batch_op.drop_column('issue_count')
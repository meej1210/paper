"""add user_task_no to tasks

Revision ID: e4b8c1a9f217
Revises: d2c8f6a4b913
Create Date: 2026-05-11 15:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e4b8c1a9f217"
down_revision = "d2c8f6a4b913"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tasks", sa.Column("user_task_no", sa.Integer(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, user_id FROM tasks ORDER BY user_id ASC, created_at ASC, id ASC")
    ).fetchall()

    counters: dict[int, int] = {}
    for row in rows:
        user_id = int(row.user_id)
        counters[user_id] = counters.get(user_id, 0) + 1
        conn.execute(
            sa.text("UPDATE tasks SET user_task_no = :user_task_no WHERE id = :task_id"),
            {"user_task_no": counters[user_id], "task_id": int(row.id)},
        )

    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.alter_column("user_task_no", existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint("uq_tasks_user_id_user_task_no", ["user_id", "user_task_no"])


def downgrade():
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_constraint("uq_tasks_user_id_user_task_no", type_="unique")
        batch_op.drop_column("user_task_no")

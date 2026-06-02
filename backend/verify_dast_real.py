import os
import time

from app import create_app
from app.extensions import db
from app.models import TaskType, User
from app.services.dast_service import run_dast_scan
from app.services.task_service import create_task


TARGET_URL = os.getenv("VERIFY_DAST_TARGET", "http://127.0.0.1:5000/")

app = create_app()

with app.app_context():
    user = User.query.first()
    if not user:
        raise RuntimeError("No users found in database. Register a user first.")

    task = create_task(
        user_id=user.id,
        task_type=TaskType.DAST,
        task_name=f"manual-dast-{int(time.time())}",
        description="manual real dast verification",
        target_url=TARGET_URL,
        timeout_seconds=20,
    )
    run_dast_scan(task)
    db.session.refresh(task)
    print(task.to_dict())
    print(task.dast_result.to_dict() if task.dast_result else None)
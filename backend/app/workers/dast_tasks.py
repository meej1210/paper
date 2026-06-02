from flask import current_app

from .celery_app import celery_app


def _has_app_context():
    try:
        return bool(current_app._get_current_object())
    except RuntimeError:
        return False


@celery_app.task(name="app.workers.dast_tasks.execute_dast_task")
def execute_dast_task(task_id: int):
    from ..extensions import db
    from ..models import Task
    from ..services.dast_service import run_dast_scan

    if _has_app_context():
        task = db.session.get(Task, task_id)
        if task:
            run_dast_scan(task)
        return

    from .. import create_app

    app = create_app()
    with app.app_context():
        task = db.session.get(Task, task_id)
        if task:
            run_dast_scan(task)

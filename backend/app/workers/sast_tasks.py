from flask import current_app

from .celery_app import celery_app


def _has_app_context():
    try:
        return bool(current_app._get_current_object())
    except RuntimeError:
        return False


@celery_app.task(name="app.workers.sast_tasks.execute_sast_task")
def execute_sast_task(task_id: int):
    from ..extensions import db
    from ..models import Task, TaskStatus
    from ..services.task_service import update_task_status
    from ..services.sast_service import run_bandit_scan, run_semgrep_scan

    def _run(task: Task):
        if (task.scanner_engine or "bandit").lower() == "semgrep":
            run_semgrep_scan(task)
            return
        run_bandit_scan(task)

    if _has_app_context():
        task = db.session.get(Task, task_id)
        if task:
            try:
                _run(task)
            except Exception as exc:
                db.session.rollback()
                update_task_status(
                    task,
                    TaskStatus.FAILED,
                    progress=100,
                    summary="SAST 扫描异常失败",
                    error_message=str(exc)[:1000] or "未知异常",
                )
                raise
        return

    from .. import create_app

    app = create_app()
    with app.app_context():
        task = db.session.get(Task, task_id)
        if task:
            try:
                _run(task)
            except Exception as exc:
                db.session.rollback()
                update_task_status(
                    task,
                    TaskStatus.FAILED,
                    progress=100,
                    summary="SAST 扫描异常失败",
                    error_message=str(exc)[:1000] or "未知异常",
                )
                raise

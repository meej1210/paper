from flask import current_app

from .celery_app import celery_app


def _has_app_context():
    try:
        return bool(current_app._get_current_object())
    except RuntimeError:
        return False


@celery_app.task(name="app.workers.sca_tasks.execute_sca_task")
def execute_sca_task(task_id: int):
    from ..extensions import db
    from ..models import Task, TaskStatus
    from ..services.sca_service import run_pip_audit_scan
    from ..services.task_service import update_task_status

    def _run():
        task = db.session.get(Task, task_id)
        if task:
            try:
                run_pip_audit_scan(task)
            except Exception as exc:
                db.session.rollback()
                update_task_status(
                    task,
                    TaskStatus.FAILED,
                    progress=100,
                    summary="SCA 扫描异常失败",
                    error_message=str(exc)[:1000] or "未知异常",
                )
                raise

    if _has_app_context():
        _run()
        return

    from .. import create_app

    app = create_app()
    with app.app_context():
        _run()

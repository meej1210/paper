import time
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Task, TaskStatus, TaskType, User, UserRole
from ..utils.exceptions import ApiError


def create_task(
    *,
    user_id: int,
    task_type: TaskType,
    task_name=None,
    description=None,
    target_path=None,
    target_url=None,
    timeout_seconds=None,
    scanner_engine=None,
    authorization_confirmed=False,
    target_host=None,
    target_ip=None,
    target_policy=None,
) -> Task:
    max_attempts = 10
    for attempt in range(max_attempts):
        task = Task(
            user_id=user_id,
            task_type=task_type,
            task_name=task_name,
            description=description,
            target_path=target_path,
            target_url=target_url,
            timeout_seconds=timeout_seconds,
            scanner_engine=scanner_engine,
            authorization_confirmed=authorization_confirmed,
            target_host=target_host,
            target_ip=target_ip,
            target_policy=target_policy,
            result_summary="任务已创建",
        )
        db.session.add(task)
        try:
            db.session.commit()
            return task
        except IntegrityError:
            db.session.rollback()
            if attempt == max_attempts - 1:
                raise
            time.sleep(0.01 * (attempt + 1))
    raise RuntimeError("task creation retry loop exhausted")


def get_user_task(task_id: int, user_id: int) -> Task:
    user = db.session.get(User, user_id)
    if user and user.role == UserRole.ADMIN:
        task = db.session.get(Task, task_id)
    else:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        raise ApiError("task not found", code=40400, status_code=404)
    return task


def update_task_status(task: Task, status: TaskStatus, *, progress=None, summary=None, error_message=None, report_path=None):
    task.status = status
    if progress is not None:
        task.progress = progress
    if summary is not None:
        task.result_summary = summary
    if error_message is not None:
        task.error_message = error_message
    if report_path is not None:
        task.report_path = report_path
    if status == TaskStatus.RUNNING and not task.started_at:
        task.started_at = datetime.now(UTC)
    if status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.TIMEOUT, TaskStatus.CANCELLED}:
        now = datetime.now(UTC).replace(tzinfo=None)
        task.finished_at = now
        if task.started_at:
            start = task.started_at.replace(tzinfo=None) if task.started_at.tzinfo else task.started_at
            task.duration_ms = int((now - start).total_seconds() * 1000)
    db.session.commit()
    return task


def cancel_task(task: Task):
    if task.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
        raise ApiError("task status transition not allowed", code=40005, status_code=400)

    if task.queue_task_id and task.status == TaskStatus.RUNNING:
        try:
            from ..workers.celery_app import celery_app

            celery_app.control.revoke(task.queue_task_id, terminate=True, signal="SIGTERM")
        except Exception:
            pass

    return update_task_status(task, TaskStatus.CANCELLED, progress=100, summary="任务已取消")


def clone_task(task: Task) -> Task:
    return create_task(
        user_id=task.user_id,
        task_type=task.task_type,
        task_name=f"{task.task_name or task.task_type.value.lower()}-rerun",
        description=f"rerun from task {task.id}",
        target_path=task.target_path,
        target_url=task.target_url,
        timeout_seconds=task.timeout_seconds,
        scanner_engine=task.scanner_engine,
        authorization_confirmed=task.authorization_confirmed,
        target_host=task.target_host,
        target_ip=task.target_ip,
        target_policy=task.target_policy,
    )

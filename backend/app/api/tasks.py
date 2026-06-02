from datetime import datetime

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models import Task, TaskStatus, TaskType
from ..services.audit_service import log_action
from ..services.task_service import cancel_task, clone_task, get_user_task
from ..utils.exceptions import ApiError
from ..utils.response import success_response
from ..utils.security import current_user
from ..workers.dast_tasks import execute_dast_task
from ..workers.sca_tasks import execute_sca_task
from ..workers.sast_tasks import execute_sast_task


tasks_bp = Blueprint("tasks", __name__)


def _parse_datetime(value: str, field_name: str):
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={field_name: "must be ISO datetime"}) from exc


@tasks_bp.get("")
@jwt_required()
def list_tasks():
    user = current_user()
    query = Task.query.filter_by(user_id=user.id)

    task_type = request.args.get("task_type")
    status = request.args.get("status")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")
    if task_type:
        try:
            query = query.filter_by(task_type=TaskType(task_type))
        except ValueError as exc:
            raise ApiError("invalid parameters", code=40001, status_code=400, errors={"task_type": "invalid value"}) from exc
    if status:
        try:
            query = query.filter_by(status=TaskStatus(status))
        except ValueError as exc:
            raise ApiError("invalid parameters", code=40001, status_code=400, errors={"status": "invalid value"}) from exc
    if start_time:
        query = query.filter(Task.created_at >= _parse_datetime(start_time, "start_time"))
    if end_time:
        query = query.filter(Task.created_at <= _parse_datetime(end_time, "end_time"))

    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 10)), 1), 100)
    pagination = query.order_by(Task.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)

    return success_response(
        {
            "items": [item.to_dict() for item in pagination.items],
            "pagination": {"page": page, "page_size": page_size, "total": pagination.total},
        }
    )


@tasks_bp.post("/<int:task_id>/cancel")
@jwt_required()
def cancel_task_endpoint(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    cancel_task(task)
    log_action(
        "TASK_CANCEL",
        user_id=user.id,
        resource_type="task",
        resource_id=task.id,
        detail={"task_id": task.id, "task_type": task.task_type.value, "result": "success"},
        request=request,
    )
    return success_response({"task_id": task.id, "status": task.status.value}, message="task cancelled")


@tasks_bp.post("/<int:task_id>/rerun")
@jwt_required()
def rerun_task(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    new_task = clone_task(task)
    if new_task.task_type == TaskType.SAST:
        if current_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
            execute_sast_task(new_task.id)
            new_task.queue_task_id = f"eager-sast-{new_task.id}"
        else:
            async_result = execute_sast_task.delay(new_task.id)
            new_task.queue_task_id = async_result.id
    elif new_task.task_type == TaskType.DAST:
        if current_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
            execute_dast_task(new_task.id)
            new_task.queue_task_id = f"eager-dast-{new_task.id}"
        else:
            async_result = execute_dast_task.delay(new_task.id)
            new_task.queue_task_id = async_result.id
    else:
        if current_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
            execute_sca_task(new_task.id)
            new_task.queue_task_id = f"eager-sca-{new_task.id}"
        else:
            async_result = execute_sca_task.delay(new_task.id)
            new_task.queue_task_id = async_result.id
    db.session.commit()
    db.session.refresh(new_task)

    log_action(
        "TASK_RERUN",
        user_id=user.id,
        resource_type="task",
        resource_id=new_task.id,
        detail={"task_id": new_task.id, "source_task_id": task.id, "task_type": new_task.task_type.value, "result": "created"},
        request=request,
    )
    return success_response({"original_task_id": task.id, "new_task": new_task.to_dict()}, message="task rerun created", status_code=201)

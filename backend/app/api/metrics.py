from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from ..models import Task, TaskStatus, TaskType, UserRole
from ..utils.response import success_response
from ..utils.security import current_user


metrics_bp = Blueprint("metrics", __name__)


def build_task_summary(query, scope: str) -> dict:
    tasks = query.all()
    by_status = {status.value: 0 for status in TaskStatus}
    by_type = {task_type.value: 0 for task_type in TaskType}
    durations = []
    window_start = datetime.now(UTC) - timedelta(hours=current_app.config["QUEUE_STABILITY_WINDOW_HOURS"])
    recent_24h_count = 0

    for task in tasks:
        by_status[task.status.value] += 1
        by_type[task.task_type.value] += 1
        if task.duration_ms is not None:
            durations.append(task.duration_ms)
        created_at = task.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at >= window_start:
            recent_24h_count += 1

    return {
        "totals": len(tasks),
        "by_status": by_status,
        "by_type": by_type,
        "running_count": by_status[TaskStatus.RUNNING.value],
        "pending_count": by_status[TaskStatus.PENDING.value],
        "failed_count": by_status[TaskStatus.FAILED.value] + by_status[TaskStatus.TIMEOUT.value] + by_status[TaskStatus.CANCELLED.value],
        "success_count": by_status[TaskStatus.SUCCESS.value],
        "recent_24h_count": recent_24h_count,
        "average_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
        "scope": scope,
    }


@metrics_bp.get("/task-summary")
@jwt_required()
def task_summary():
    user = current_user()
    scope = "all" if request.args.get("scope") == "all" and user.role == UserRole.ADMIN else "user"
    query = Task.query if scope == "all" else Task.query.filter_by(user_id=user.id)
    return success_response(build_task_summary(query, scope))

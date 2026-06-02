import json
import shutil
from collections import Counter

from datetime import datetime

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from ..extensions import db, get_redis_client
from ..models import AuditLog, DastIssue, DastResult, SastIssue, ScaIssue, Task, TaskStatus, TaskType, User, UserRole
from ..utils.exceptions import ApiError
from ..utils.response import success_response
from ..utils.security import require_roles


admin_bp = Blueprint("admin", __name__)


def _status_map() -> dict:
    return {status.value: 0 for status in TaskStatus}


def _type_map() -> dict:
    return {task_type.value: 0 for task_type in TaskType}


def _task_totals() -> dict:
    tasks = Task.query.all()
    by_status = _status_map()
    by_type = _type_map()
    for task in tasks:
        by_status[task.status.value] += 1
        by_type[task.task_type.value] += 1
    return {
        "total": len(tasks),
        "by_type": by_type,
        "by_status": by_status,
        "success": by_status[TaskStatus.SUCCESS.value],
        "failed": by_status[TaskStatus.FAILED.value] + by_status[TaskStatus.TIMEOUT.value] + by_status[TaskStatus.CANCELLED.value],
        "running": by_status[TaskStatus.RUNNING.value],
        "pending": by_status[TaskStatus.PENDING.value],
    }


def _severity_counter(values) -> dict:
    counter = Counter((value or "UNKNOWN").upper() for value in values)
    return {key: counter.get(key, 0) for key in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]}


def _risk_summary() -> dict:
    sast = _severity_counter(issue.issue_severity for issue in SastIssue.query.all())
    dast_counter = Counter()
    for result in DastResult.query.all():
        try:
            distribution = json.loads(result.severity_distribution or "{}")
        except json.JSONDecodeError:
            distribution = {}
        for key, value in distribution.items():
            dast_counter[(key or "UNKNOWN").upper()] += int(value or 0)
    if not dast_counter:
        dast_counter.update((issue.level or "UNKNOWN").upper() for issue in DastIssue.query.all())
    dast = {key: dast_counter.get(key, 0) for key in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]}
    sca_issues = ScaIssue.query.all()
    fixable = 0
    for issue in sca_issues:
        try:
            versions = json.loads(issue.fix_versions or "[]")
        except json.JSONDecodeError:
            versions = []
        if versions:
            fixable += 1
    return {
        "sast": sast,
        "dast": dast,
        "sca": {"vulnerability_count": len(sca_issues), "fixable_count": fixable},
    }


def _recent_audit_logs() -> list[dict]:
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "detail": item.detail,
            "ip_address": item.ip_address,
            "created_at": item.created_at.isoformat(),
        }
        for item in logs
    ]


def _recent_failed_tasks() -> list[dict]:
    tasks = (
        Task.query.filter(Task.status.in_([TaskStatus.FAILED, TaskStatus.TIMEOUT, TaskStatus.CANCELLED]))
        .order_by(Task.created_at.desc())
        .limit(10)
        .all()
    )
    return [task.to_dict() for task in tasks]


def _dast_targets() -> list[dict]:
    tasks = Task.query.filter_by(task_type=TaskType.DAST).order_by(Task.created_at.desc()).limit(10).all()
    return [
        {
            "task_id": task.id,
            "target_url": task.target_url,
            "target_host": task.target_host,
            "target_ip": task.target_ip,
            "target_policy": task.target_policy,
            "authorization_confirmed": task.authorization_confirmed,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
        }
        for task in tasks
    ]


def _parse_datetime(value: str, field_name: str):
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={field_name: "must be ISO datetime"}) from exc


def _task_report_available(task: Task) -> bool:
    return task.status == TaskStatus.SUCCESS and bool(task.report_path)


def _admin_task_dict(task: Task) -> dict:
    item = task.to_dict()
    item["user"] = {
        "id": task.user.id,
        "username": task.user.username,
        "email": task.user.email,
        "role": task.user.role.value,
    }
    item["report_available"] = _task_report_available(task)
    item["report_route"] = f"/tasks/{task.id}?type={task.task_type.value}&from=admin"
    return item


def _runtime() -> dict:
    db_status = "up"
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    redis_status = "down"
    try:
        client = get_redis_client(current_app.config)
        if client.ping():
            redis_status = "up"
    except Exception:
        redis_status = "down"

    return {
        "service": "up",
        "database": db_status,
        "redis": redis_status,
        "dast_scanner": "up" if shutil.which(current_app.config["DAST_SCANNER_CMD"]) else "down",
        "celery_mode": "eager" if current_app.config.get("CELERY_TASK_ALWAYS_EAGER") else "async",
    }


@admin_bp.get("/dashboard")
@jwt_required()
@require_roles(UserRole.ADMIN)
def dashboard():
    return success_response(
        {
            "task_totals": _task_totals(),
            "risk_summary": _risk_summary(),
            "recent_audit_logs": _recent_audit_logs(),
            "recent_failed_tasks": _recent_failed_tasks(),
            "dast_targets": _dast_targets(),
            "runtime": _runtime(),
        }
    )


@admin_bp.get("/tasks")
@jwt_required()
@require_roles(UserRole.ADMIN)
def list_all_tasks():
    query = Task.query.join(User)

    keyword = (request.args.get("keyword") or "").strip()
    task_type = request.args.get("task_type")
    status = request.args.get("status")
    user_id = request.args.get("user_id")
    start_time = request.args.get("start_time")
    end_time = request.args.get("end_time")

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Task.task_name.ilike(like),
                Task.description.ilike(like),
                Task.target_url.ilike(like),
                Task.target_path.ilike(like),
                User.username.ilike(like),
                User.email.ilike(like),
            )
        )
    if task_type:
        try:
            query = query.filter(Task.task_type == TaskType(task_type))
        except ValueError as exc:
            raise ApiError("invalid parameters", code=40001, status_code=400, errors={"task_type": "invalid value"}) from exc
    if status:
        try:
            query = query.filter(Task.status == TaskStatus(status))
        except ValueError as exc:
            raise ApiError("invalid parameters", code=40001, status_code=400, errors={"status": "invalid value"}) from exc
    if user_id:
        try:
            query = query.filter(Task.user_id == int(user_id))
        except ValueError as exc:
            raise ApiError("invalid parameters", code=40001, status_code=400, errors={"user_id": "must be integer"}) from exc
    if start_time:
        query = query.filter(Task.created_at >= _parse_datetime(start_time, "start_time"))
    if end_time:
        query = query.filter(Task.created_at <= _parse_datetime(end_time, "end_time"))

    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 12)), 1), 100)
    pagination = query.order_by(Task.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)

    return success_response(
        {
            "items": [_admin_task_dict(item) for item in pagination.items],
            "pagination": {"page": page, "page_size": page_size, "total": pagination.total},
        }
    )

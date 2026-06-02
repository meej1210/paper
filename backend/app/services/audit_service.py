import json
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import Request
from sqlalchemy import or_

from ..extensions import db
from ..models import AuditLog, User, UserRole


ACTION_LABELS = {
    "AUTH_LOGIN_SUCCESS": "登录成功",
    "AUTH_LOGIN_FAILED": "登录失败",
    "AUTH_LOGOUT": "退出登录",
    "REGISTER": "注册账号",
    "LOGIN": "登录成功",
    "TASK_CREATE": "创建扫描任务",
    "TASK_CANCEL": "取消任务",
    "TASK_RERUN": "重新执行任务",
    "TASK_STATUS_CHANGE": "任务状态变更",
    "REPORT_VIEW": "查看报告",
    "REPORT_DOWNLOAD_JSON": "下载 JSON 报告",
    "REPORT_EXPORT_HTML": "导出 HTML 报告",
    "REPORT_EXPORT_PDF": "导出 PDF 报告",
    "TASK_DOWNLOAD_REPORT": "下载 JSON 报告",
    "TASK_EXPORT_REPORT": "导出报告",
    "DAST_AUTH_CONFIRMED": "DAST 授权确认",
    "DAST_AUTH_REJECTED": "DAST 授权拒绝",
    "ADMIN_DASHBOARD_VIEW": "访问管理看板",
    "ADMIN_TASK_VIEW": "管理员查看用户任务",
}


def _json_detail(detail: Any):
    if detail is None or isinstance(detail, str):
        return detail
    return json.dumps(detail, ensure_ascii=False)


def log_action(action: str, user_id=None, resource_type=None, resource_id=None, detail=None, request: Request | None = None):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=_json_detail(detail),
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def parse_detail(detail: str | None):
    if not detail:
        return None
    try:
        return json.loads(detail)
    except (TypeError, ValueError):
        return detail


def normalize_action(action: str, detail=None) -> str:
    if action == "LOGIN":
        return "AUTH_LOGIN_SUCCESS"
    if action == "TASK_DOWNLOAD_REPORT":
        return "REPORT_DOWNLOAD_JSON"
    if action == "TASK_EXPORT_REPORT":
        parsed = detail if isinstance(detail, dict) else parse_detail(detail)
        text = json.dumps(parsed, ensure_ascii=False).lower() if isinstance(parsed, dict) else str(parsed or "").lower()
        if "pdf" in text:
            return "REPORT_EXPORT_PDF"
        if "html" in text:
            return "REPORT_EXPORT_HTML"
    return action


def action_label(action: str) -> str:
    return ACTION_LABELS.get(action, action)


def detail_result(action: str, detail) -> str:
    if isinstance(detail, dict) and detail.get("result"):
        return str(detail["result"])
    normalized = normalize_action(action, detail)
    if normalized == "AUTH_LOGIN_FAILED":
        return "failed"
    if normalized == "DAST_AUTH_REJECTED":
        return "rejected"
    if normalized == "TASK_CREATE":
        return "created"
    return "success"


def report_route_for(item: AuditLog, detail, viewer: User) -> str | None:
    if not isinstance(detail, dict):
        return None
    task_id = detail.get("task_id") or (item.resource_id if item.resource_type == "task" else None)
    task_type = detail.get("task_type")
    if not task_id or not task_type:
        return None
    route = f"/tasks/{task_id}?type={task_type}"
    if viewer.role == UserRole.ADMIN:
        route += "&from=admin"
    return route


def serialize_audit_log(item: AuditLog, viewer: User) -> dict:
    detail = parse_detail(item.detail)
    normalized_action = normalize_action(item.action, detail)
    result = detail_result(normalized_action, detail)
    return {
        "id": item.id,
        "created_at": item.created_at.isoformat(),
        "user_id": item.user_id,
        "user": item.user.to_dict() if item.user else None,
        "action": normalized_action,
        "raw_action": item.action,
        "action_label": action_label(normalized_action),
        "resource_type": item.resource_type,
        "resource_id": item.resource_id,
        "result": result,
        "ip_address": item.ip_address,
        "user_agent": item.user_agent,
        "detail": detail,
        "report_route": report_route_for(item, detail, viewer),
    }


def scoped_audit_query(viewer: User):
    query = AuditLog.query.outerjoin(User)
    if viewer.role != UserRole.ADMIN:
        query = query.filter(AuditLog.user_id == viewer.id)
    return query


def apply_audit_filters(query, *, keyword=None, action=None, resource_id=None, start_time=None, end_time=None):
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(User.username.ilike(like), User.email.ilike(like), AuditLog.action.ilike(like), AuditLog.detail.ilike(like)))
    if action:
        if action == "AUTH_LOGIN_SUCCESS":
            query = query.filter(AuditLog.action.in_(["AUTH_LOGIN_SUCCESS", "LOGIN"]))
        elif action == "REPORT_DOWNLOAD_JSON":
            query = query.filter(AuditLog.action.in_(["REPORT_DOWNLOAD_JSON", "TASK_DOWNLOAD_REPORT"]))
        elif action in {"REPORT_EXPORT_HTML", "REPORT_EXPORT_PDF"}:
            query = query.filter(AuditLog.action.in_([action, "TASK_EXPORT_REPORT"]))
        else:
            query = query.filter(AuditLog.action == action)
    if resource_id:
        query = query.filter(AuditLog.resource_id == str(resource_id))
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
    return query


def filter_items_by_result(items: list[AuditLog], result: str | None) -> list[AuditLog]:
    if not result:
        return items
    expected = result.lower()
    return [item for item in items if detail_result(normalize_action(item.action, item.detail), parse_detail(item.detail)).lower() == expected]


def summary_for(query) -> dict:
    today = datetime.now(UTC).date()
    rows = query.filter(AuditLog.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=UTC)).all()
    actions = [normalize_action(row.action, row.detail) for row in rows]
    return {
        "today_count": len(rows),
        "login_failed_count": actions.count("AUTH_LOGIN_FAILED"),
        "task_create_count": actions.count("TASK_CREATE"),
        "report_view_count": actions.count("REPORT_VIEW"),
        "report_export_count": sum(1 for action in actions if action in {"REPORT_DOWNLOAD_JSON", "REPORT_EXPORT_HTML", "REPORT_EXPORT_PDF"}),
        "dast_authorized_count": actions.count("DAST_AUTH_CONFIRMED"),
    }


def charts_for(query) -> dict:
    since = datetime.now(UTC) - timedelta(hours=24)
    rows = query.filter(AuditLog.created_at >= since).all()
    by_action: dict[str, int] = {}
    for row in rows:
        action = normalize_action(row.action, row.detail)
        by_action[action] = by_action.get(action, 0) + 1

    current_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    hours = [current_hour - timedelta(hours=offset) for offset in range(23, -1, -1)]
    buckets = {hour.strftime("%H:00"): 0 for hour in hours}
    for row in rows:
        bucket = row.created_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0).strftime("%H:00")
        if bucket in buckets:
            buckets[bucket] += 1
    return {
        "by_action": by_action,
        "by_hour_24h": [{"hour": hour, "count": count} for hour, count in buckets.items()],
    }

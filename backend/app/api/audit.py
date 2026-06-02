from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..models import AuditLog
from ..services.audit_service import (
    apply_audit_filters,
    charts_for,
    filter_items_by_result,
    scoped_audit_query,
    serialize_audit_log,
    summary_for,
)
from ..utils.exceptions import ApiError
from ..utils.response import success_response
from ..utils.security import current_user


audit_bp = Blueprint("audit", __name__)


@audit_bp.get("")
@jwt_required()
def list_audit_logs():
    viewer = current_user()
    base_query = scoped_audit_query(viewer)

    keyword = request.args.get("keyword")
    action = request.args.get("action")
    result = request.args.get("result")
    resource_id = request.args.get("resource_id")
    start_time = _parse_datetime_arg("start_time")
    end_time = _parse_datetime_arg("end_time")

    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    filtered_query = apply_audit_filters(
        base_query,
        keyword=keyword,
        action=action,
        resource_id=resource_id,
        start_time=start_time,
        end_time=end_time,
    ).order_by(AuditLog.created_at.desc())
    filtered_items = filter_items_by_result(filtered_query.all(), result)
    total = len(filtered_items)
    page_items = filtered_items[(page - 1) * page_size : page * page_size]

    return success_response(
        {
            "items": [serialize_audit_log(item, viewer) for item in page_items],
            "pagination": {"page": page, "page_size": page_size, "total": total},
            "summary": summary_for(base_query),
            "charts": charts_for(base_query),
            "viewer": viewer.to_dict(),
        }
    )


def _parse_datetime_arg(name: str):
    value = request.args.get(name)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={name: "must be ISO datetime"}) from exc

import json
from pathlib import Path

from flask import Blueprint, current_app, request, send_file, Response
from flask_jwt_extended import jwt_required

from ..extensions import db, limiter
from ..models import TaskType, UserRole
from ..services.audit_service import log_action
from ..services.dast_service import build_dast_analysis, list_dast_issues
from ..services.report_export_service import export_report
from ..services.task_service import create_task, get_user_task
from ..utils.response import success_response
from ..utils.security import current_user
from ..utils.validators import validate_dast_payload
from ..workers.dast_tasks import execute_dast_task
from ..utils.exceptions import ApiError


dast_bp = Blueprint("dast", __name__)


@dast_bp.post("/tasks")
@jwt_required()
@limiter.limit(lambda: current_app.config["TASK_CREATE_RATE_LIMIT"])
def create_dast_task():
    payload = request.get_json(silent=True) or {}
    user = current_user()
    try:
        target_url, timeout, target_context = validate_dast_payload(
            payload,
            current_app.config["DEFAULT_DAST_TIMEOUT"],
            current_app.config["MAX_DAST_TIMEOUT"],
            allowed_hosts=current_app.config["DAST_ALLOWED_HOSTS"],
            allow_private_networks=current_app.config["DAST_ALLOW_PRIVATE_NETWORKS"],
            allow_public_targets=current_app.config["DAST_ALLOW_PUBLIC_TARGETS"],
            public_max_timeout=current_app.config["DAST_PUBLIC_MAX_TIMEOUT"],
        )
    except ApiError as exc:
        log_action(
            "DAST_AUTH_REJECTED",
            user_id=user.id,
            resource_type="dast_target",
            detail={
                "target_url": payload.get("target_url"),
                "authorization_confirmed": payload.get("authorization_confirmed") is True,
                "result": "rejected",
                "reject_reason": (exc.errors or {}).get("target_url") or exc.message,
            },
            request=request,
        )
        raise
    task = create_task(
        user_id=user.id,
        task_type=TaskType.DAST,
        task_name=payload.get("task_name"),
        description=payload.get("description"),
        target_url=target_url,
        timeout_seconds=timeout,
        authorization_confirmed=target_context["authorization_confirmed"],
        target_host=target_context["hostname"],
        target_ip=target_context["resolved_ip"],
        target_policy=target_context["policy"],
    )

    if current_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
        execute_dast_task(task.id)
        task.queue_task_id = f"eager-dast-{task.id}"
    else:
        async_result = execute_dast_task.delay(task.id)
        task.queue_task_id = async_result.id
    db.session.commit()
    db.session.refresh(task)

    auth_detail = {
        "task_id": task.id,
        "target_url": target_url,
        "target_host": target_context["hostname"],
        "target_ip": target_context["resolved_ip"],
        "target_policy": target_context["policy"],
        "policy": target_context["policy"],
        "authorization_confirmed": target_context["authorization_confirmed"],
        "allowed_reason": target_context["allowed_reason"],
        "public_low_intensity": target_context["public_low_intensity"],
        "effective_timeout": timeout,
        "result": "success",
    }
    log_action("DAST_AUTH_CONFIRMED", user_id=user.id, resource_type="task", resource_id=task.id, detail=auth_detail, request=request)
    log_action(
        "TASK_CREATE",
        user_id=user.id,
        resource_type="task",
        resource_id=task.id,
        detail={**auth_detail, "task_type": "DAST", "task_name": task.task_name, "result": "created"},
        request=request,
    )
    return success_response({"task": task.to_dict()}, message="dast task created", status_code=201)


@dast_bp.get("/tasks/<int:task_id>")
@jwt_required()
def get_dast_task(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    detail = {
        "task_id": task.id,
        "task_type": "DAST",
        "owner_user_id": task.user_id,
        "viewer_user_id": user.id,
        "viewer_role": user.role.value,
        "report_action": "view",
        "result": "success",
    }
    log_action("REPORT_VIEW", user_id=user.id, resource_type="task", resource_id=task.id, detail=detail, request=request)
    if user.role == UserRole.ADMIN and task.user_id != user.id:
        log_action("ADMIN_TASK_VIEW", user_id=user.id, resource_type="task", resource_id=task.id, detail=detail, request=request)
    return success_response(
        {
            "task": task.to_dict(),
            "result": task.dast_result.to_dict() if task.dast_result else None,
            "issues": list_dast_issues(task),
            "analysis": build_dast_analysis(task),
        }
    )


@dast_bp.get("/tasks/<int:task_id>/report")
@jwt_required()
def download_dast_report(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    if not task.report_path:
        raise ApiError("report not ready", code=42200, status_code=422)

    report_path = Path(task.report_path)
    if not report_path.exists():
        raise ApiError("resource not found", code=40400, status_code=404)

    log_action("REPORT_DOWNLOAD_JSON", user_id=user.id, resource_type="task", resource_id=task.id, detail={"task_id": task.id, "task_type": "DAST", "format": "json", "result": "success"}, request=request)
    return send_file(report_path, mimetype="application/json", as_attachment=True, download_name=f"dast_report_{task.id}.json")


@dast_bp.get("/tasks/<int:task_id>/export")
@jwt_required()
def export_dast_report(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    export_format = request.args.get("format", "html")
    payload, mimetype, filename = export_report(task, export_format)
    action = "REPORT_EXPORT_PDF" if export_format == "pdf" else "REPORT_EXPORT_HTML"
    log_action(action, user_id=user.id, resource_type="task", resource_id=task.id, detail={"task_id": task.id, "task_type": "DAST", "format": export_format, "result": "success"}, request=request)
    return Response(payload, mimetype=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})

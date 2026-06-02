from pathlib import Path

from flask import Blueprint, current_app, request, send_file, Response
from flask_jwt_extended import jwt_required

from ..extensions import db, limiter
from ..models import TaskType, UserRole
from ..services.audit_service import log_action
from ..services.report_export_service import export_report
from ..services.sast_service import build_sast_analysis, list_sast_issues
from ..services.task_service import create_task, get_user_task
from ..utils.exceptions import ApiError
from ..utils.file_handler import save_upload
from ..utils.response import success_response
from ..utils.security import current_user
from ..utils.validators import validate_upload
from ..workers.sast_tasks import execute_sast_task


sast_bp = Blueprint("sast", __name__)


@sast_bp.post("/tasks")
@jwt_required()
@limiter.limit(lambda: current_app.config["TASK_CREATE_RATE_LIMIT"])
def create_sast_task():
    user = current_user()
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"file": "required"})

    scanner_engine = (request.form.get("scanner_engine") or current_app.config["SAST_DEFAULT_ENGINE"]).strip().lower()
    if scanner_engine not in current_app.config["SAST_ALLOWED_ENGINES"]:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"scanner_engine": "invalid value"})

    uploaded_file.stream.seek(0, 2)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    validate_upload(
        uploaded_file.filename,
        file_size,
        current_app.config["ALLOWED_UPLOAD_EXTENSIONS"],
        current_app.config["MAX_UPLOAD_SIZE_MB"],
    )

    saved_path = save_upload(uploaded_file)
    task = create_task(
        user_id=user.id,
        task_type=TaskType.SAST,
        task_name=request.form.get("task_name"),
        description=request.form.get("description"),
        target_path=saved_path,
        scanner_engine=scanner_engine,
    )

    if current_app.config.get("CELERY_TASK_ALWAYS_EAGER"):
        execute_sast_task(task.id)
        task.queue_task_id = f"eager-sast-{task.id}"
    else:
        async_result = execute_sast_task.delay(task.id)
        task.queue_task_id = async_result.id
    db.session.commit()
    db.session.refresh(task)

    log_action(
        "TASK_CREATE",
        user_id=user.id,
        resource_type="task",
        resource_id=task.id,
        detail={
            "task_id": task.id,
            "task_type": "SAST",
            "task_name": task.task_name,
            "scanner_engine": scanner_engine,
            "target_name": task.to_dict().get("target_name"),
            "result": "created",
        },
        request=request,
    )
    return success_response({"task": task.to_dict()}, message="sast task created", status_code=201)


@sast_bp.get("/tasks/<int:task_id>")
@jwt_required()
def get_sast_task(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    detail = {
        "task_id": task.id,
        "task_type": "SAST",
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
            "result": task.sast_result.to_dict() if task.sast_result else None,
            "issues": list_sast_issues(task),
            "analysis": build_sast_analysis(task),
        }
    )


@sast_bp.get("/tasks/<int:task_id>/report")
@jwt_required()
def download_report(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    if not task.report_path:
        raise ApiError("report not ready", code=42200, status_code=422)

    report_path = Path(task.report_path)
    if not report_path.exists():
        raise ApiError("resource not found", code=40400, status_code=404)

    log_action("REPORT_DOWNLOAD_JSON", user_id=user.id, resource_type="task", resource_id=task.id, detail={"task_id": task.id, "task_type": "SAST", "format": "json", "result": "success"}, request=request)
    return send_file(report_path, mimetype="application/json", as_attachment=True, download_name=f"sast_report_{task.id}.json")


@sast_bp.get("/tasks/<int:task_id>/export")
@jwt_required()
def export_sast_report(task_id: int):
    user = current_user()
    task = get_user_task(task_id, user.id)
    export_format = request.args.get("format", "html")
    payload, mimetype, filename = export_report(task, export_format)
    action = "REPORT_EXPORT_PDF" if export_format == "pdf" else "REPORT_EXPORT_HTML"
    log_action(action, user_id=user.id, resource_type="task", resource_id=task.id, detail={"task_id": task.id, "task_type": "SAST", "format": export_format, "result": "success"}, request=request)
    return Response(payload, mimetype=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..services.ai_service import get_issue_insight
from ..services.audit_service import log_action
from ..services.task_service import get_user_task
from ..utils.exceptions import ApiError
from ..utils.response import success_response
from ..utils.security import current_user


ai_bp = Blueprint("ai", __name__)


@ai_bp.post("/issue-insight")
@jwt_required()
def generate_issue_insight():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("task_id")
    issue_id = payload.get("issue_id")
    if not task_id or not issue_id:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"task_id": "required", "issue_id": "required"})

    user = current_user()
    task = get_user_task(int(task_id), user.id)
    result = get_issue_insight(task, int(issue_id))
    log_action(
        "AI_ISSUE_INSIGHT",
        user_id=user.id,
        resource_type="task",
        resource_id=task.id,
        detail=f"generated ai insight for issue {issue_id}",
        request=request,
    )
    return success_response(result)

import hashlib
import json
from urllib import error, request

from flask import current_app

from ..extensions import db
from ..models import AiIssueInsight, DastIssue, SastIssue, ScaIssue, Task, TaskType
from ..utils.exceptions import ApiError


def _issue_fingerprint(task_type: str, issue: SastIssue | DastIssue | ScaIssue) -> str:
    if task_type == TaskType.SAST.value:
        payload = "|".join(
            [
                str(issue.test_id or ""),
                str(issue.test_name or ""),
                str(issue.filename or ""),
                str(issue.line_number or ""),
                str(issue.issue_text or ""),
            ]
        )
    elif task_type == TaskType.DAST.value:
        payload = "|".join(
            [
                str(issue.category or ""),
                str(issue.level or ""),
                str(issue.method or ""),
                str(issue.path or ""),
                str(issue.parameter or ""),
                str(issue.info or ""),
            ]
        )
    else:
        payload = "|".join(
            [
                str(issue.package_name or ""),
                str(issue.installed_version or ""),
                str(issue.vulnerability_id or ""),
                str(issue.aliases or ""),
                str(issue.fix_versions or ""),
                str(issue.description or ""),
            ]
        )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_issue_payload(task_type: str, task: Task, issue: SastIssue | DastIssue | ScaIssue) -> dict:
    if task_type == TaskType.SAST.value:
        return {
            "task_type": task_type,
            "task_id": task.id,
            "task_name": task.task_name,
            "target": task.target_path,
            "issue_id": issue.id,
            "severity": issue.issue_severity,
            "confidence": issue.issue_confidence,
            "rule_id": issue.test_id,
            "rule_name": issue.test_name,
            "issue_text": issue.issue_text,
            "file": issue.filename,
            "line_number": issue.line_number,
            "code": issue.code,
            "evidence": issue.more_info,
        }
    if task_type == TaskType.SCA.value:
        return {
            "task_type": task_type,
            "task_id": task.id,
            "task_name": task.task_name,
            "target": task.target_path,
            "issue_id": issue.id,
            "severity": issue.severity,
            "package_name": issue.package_name,
            "installed_version": issue.installed_version,
            "vulnerability_id": issue.vulnerability_id,
            "aliases": json.loads(issue.aliases or "[]"),
            "fix_versions": json.loads(issue.fix_versions or "[]"),
            "description": issue.description,
        }
    return {
        "task_type": task_type,
        "task_id": task.id,
        "task_name": task.task_name,
        "target": task.target_url,
        "issue_id": issue.id,
        "level": issue.level,
        "category": issue.category,
        "method": issue.method,
        "path": issue.path,
        "parameter": issue.parameter,
        "info": issue.info,
        "http_request": issue.http_request,
        "curl_command": issue.curl_command,
        "referer": issue.referer,
        "wstg": issue.wstg,
    }


def _build_prompt(task_type: str, payload: dict) -> str:
    shared_rules = (
        "输出必须是 JSON，对象仅包含 meaning、impact、fix、verify 四个字段。"
        "每个字段只写 1 句，每句不超过 45 个汉字，直指用户痛点。"
        "先说当前证据暴露的直接问题，再说真实影响和下一步动作。"
        "不要输出背景科普、概念定义、客套话、免责声明或字段外不存在的背景设定。"
        "不要使用“可能需要进一步了解业务”这类空话。"
    )
    if task_type == TaskType.SAST.value:
        return (
            "你是代码安全审计助手，请严格根据下面给出的 SAST 问题数据生成中文解读，不要脱离字段内容猜测系统架构。"
            f"{shared_rules}"
            "meaning 先说当前证据暴露的直接问题，必须点名文件、行号、规则或代码片段中的关键信号；"
            "impact 说明该问题会让开发者、系统或用户承受的具体损失；"
            "fix 给出针对当前代码形态的最小修复动作；"
            "verify 说明修复后的验证命令、复扫方式或检查点。\n\n"
            f"问题数据：{json.dumps(payload, ensure_ascii=False)}"
        )
    if task_type == TaskType.SCA.value:
        return (
            "你是软件成分分析助手，请严格根据下面给出的 SCA 依赖漏洞数据生成中文解读，不要脱离字段内容猜测业务架构。"
            f"{shared_rules}"
            "meaning 先点名依赖包、当前版本和漏洞编号暴露的直接问题；"
            "impact 说明继续使用该依赖版本会带来的具体安全后果；"
            "fix 优先给出可修复版本升级动作；"
            "verify 说明升级后如何通过 SCA 复扫或依赖清单检查确认。\n\n"
            f"问题数据：{json.dumps(payload, ensure_ascii=False)}"
        )
    return (
        "你是动态扫描结果分析助手，请严格根据下面给出的 DAST 问题数据生成中文解读，不要脱离字段内容猜测目标站点业务。"
        f"{shared_rules}"
        "meaning 先说当前路径/方法/参数暴露的直接问题；"
        "impact 说明攻击者能造成的具体影响和用户痛点；"
        "fix 给出服务端、路由、参数或响应层的下一步动作；"
        "verify 说明修复后如何用请求样例、复扫或日志确认。\n\n"
        f"问题数据：{json.dumps(payload, ensure_ascii=False)}"
    )


def _call_deepseek(prompt: str) -> dict:
    api_key = current_app.config.get("AI_API_KEY")
    if not api_key:
        raise ApiError("AI service not configured", code=50310, status_code=503)

    endpoint = current_app.config.get("AI_API_BASE", "https://api.deepseek.com").rstrip("/") + "/chat/completions"
    model_name = current_app.config.get("AI_MODEL", "deepseek-chat")
    request_payload = {
        "model": model_name,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是安全报告增强助手，只能基于提供的问题字段输出精确、克制、结构化的中文 JSON。"
                    "答案必须短、准、直击用户痛点，避免科普和泛泛建议。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }

    body = json.dumps(request_payload).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=current_app.config.get("AI_TIMEOUT", 25)) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ApiError("AI service request failed", code=50311, status_code=503, errors={"detail": detail[:500]}) from exc
    except Exception as exc:
        raise ApiError("AI service unavailable", code=50312, status_code=503, errors={"detail": str(exc)}) from exc

    payload = json.loads(raw)
    content = payload.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise ApiError("AI service returned empty response", code=50313, status_code=503)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ApiError("AI response format invalid", code=50314, status_code=503, errors={"detail": content[:500]}) from exc

    return {
        "meaning": str(parsed.get("meaning") or "").strip(),
        "impact": str(parsed.get("impact") or "").strip(),
        "fix": str(parsed.get("fix") or "").strip(),
        "verify": str(parsed.get("verify") or "").strip(),
        "model_name": model_name,
    }


def get_issue_insight(task: Task, issue_id: int) -> dict:
    task_type = task.task_type.value
    if task_type == TaskType.SAST.value:
        issue = SastIssue.query.filter_by(task_id=task.id, id=issue_id).first()
    elif task_type == TaskType.DAST.value:
        issue = DastIssue.query.filter_by(task_id=task.id, id=issue_id).first()
    else:
        issue = ScaIssue.query.filter_by(task_id=task.id, id=issue_id).first()

    if not issue:
        raise ApiError("resource not found", code=40400, status_code=404, errors={"issue_id": "not found"})

    fingerprint = _issue_fingerprint(task_type, issue)
    cached = AiIssueInsight.query.filter_by(task_id=task.id, task_type=task_type, issue_id=issue.id, issue_fingerprint=fingerprint).first()
    if cached:
        return {"issue_id": issue.id, "cached": True, "insight": cached.to_dict()}

    prompt = _build_prompt(task_type, _build_issue_payload(task_type, task, issue))
    insight_payload = _call_deepseek(prompt)
    if not all(insight_payload.get(key) for key in ("meaning", "impact", "fix", "verify")):
        raise ApiError("AI response incomplete", code=50315, status_code=503)

    insight = AiIssueInsight(
        task_id=task.id,
        task_type=task_type,
        issue_id=issue.id,
        issue_fingerprint=fingerprint,
        model_name=insight_payload["model_name"],
        meaning=insight_payload["meaning"],
        impact=insight_payload["impact"],
        fix=insight_payload["fix"],
        verify=insight_payload["verify"],
    )
    db.session.add(insight)
    db.session.commit()
    return {"issue_id": issue.id, "cached": False, "insight": insight.to_dict()}

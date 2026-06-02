import json
import re
import subprocess
from pathlib import Path

from flask import current_app

from ..extensions import db
from ..models import SastIssue, SastResult, Task, TaskStatus
from ..services.task_service import update_task_status
from ..utils.cwe_mapping import build_owasp_distribution, lookup_bandit
from ..utils.file_handler import prepare_sast_target


SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
CONFIDENCE_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _load_json(value: str | None) -> dict:
    return json.loads(value) if value else {}


def _sorted_distribution_entries(payload: dict, limit: int = 5) -> list[dict]:
    return [
        {"name": key, "count": value}
        for key, value in sorted(payload.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def list_sast_issues(task: Task) -> list[dict]:
    issues = SastIssue.query.filter_by(task_id=task.id).all()
    issues.sort(
        key=lambda item: (
            -SEVERITY_ORDER.get(item.issue_severity or "", 0),
            -CONFIDENCE_ORDER.get(item.issue_confidence or "", 0),
            item.filename or "",
            item.line_number or 0,
        )
    )
    return [issue.to_dict() for issue in issues]


def build_sast_analysis(task: Task) -> dict | None:
    result = task.sast_result
    if not result:
        return None

    severity_distribution = _load_json(result.severity_distribution)
    confidence_distribution = _load_json(result.confidence_distribution)
    type_distribution = _load_json(result.type_distribution)
    file_distribution = _load_json(result.file_distribution)

    issue_count = result.issue_count
    high_count = severity_distribution.get("HIGH", 0)
    medium_count = severity_distribution.get("MEDIUM", 0)
    affected_files = len(file_distribution)
    top_rule = _sorted_distribution_entries(type_distribution, limit=1)
    top_file = _sorted_distribution_entries(file_distribution, limit=1)

    headline = f"本次静态审计共识别 {issue_count} 个问题，覆盖 {affected_files} 个文件。"
    if high_count:
        headline = f"本次静态审计识别 {issue_count} 个问题，其中高危 {high_count} 个，需优先修复。"

    highlights = [
        f"高危问题 {high_count} 个，中危问题 {medium_count} 个。",
        f"最高频规则为 {top_rule[0]['name']}（{top_rule[0]['count']} 次）。" if top_rule else "当前未形成明显规则聚集。",
        f"问题最集中的文件为 {top_file[0]['name']}（{top_file[0]['count']} 次）。" if top_file else "当前未形成明显文件聚集。",
    ]

    recommendations = []
    if high_count:
        recommendations.append("优先处理高危问题，并结合对应文件和代码位置进行复核。")
    if confidence_distribution.get("HIGH", 0):
        recommendations.append("优先关注高置信度问题，这类问题通常更适合作为论文中的重点案例。")
    if top_rule:
        recommendations.append("可围绕高频规则整理修复建议，说明系统如何辅助开发者定位重复风险。")
    if not recommendations:
        recommendations.append("当前结果以低危或零散问题为主，可作为安全基线扫描结果展示。")

    return {
        "headline": headline,
        "highlights": highlights,
        "recommendations": recommendations,
        "top_rules": _sorted_distribution_entries(type_distribution),
        "top_files": _sorted_distribution_entries(file_distribution),
        "owasp_distribution": build_owasp_distribution([i.to_dict() for i in task.sast_issues]),
    }


def _prepare_target_path(task: Task) -> str:
    target_path = prepare_sast_target(task.target_path)
    if target_path != task.target_path:
        task.target_path = target_path
        db.session.commit()
    return target_path


def _mark_scan_failed(task: Task, summary: str, error_message: str | None = None):
    update_task_status(
        task,
        TaskStatus.FAILED,
        progress=100,
        summary=summary,
        error_message=(error_message or "")[:1000] or None,
    )


def _read_report_payload(report_path: Path) -> dict:
    if not report_path.exists():
        return {}
    return json.loads(report_path.read_text(encoding="utf-8"))


def _persist_sast_results(task: Task, issues: list[dict], report_path: Path, engine_name: str):
    severity_distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    confidence_distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    type_distribution: dict[str, int] = {}
    file_distribution: dict[str, int] = {}

    SastIssue.query.filter_by(task_id=task.id).delete(synchronize_session=False)

    for item in issues:
        severity = (item.get("issue_severity") or "LOW").upper()
        confidence = (item.get("issue_confidence") or "LOW").upper()
        filename = item.get("filename") or "unknown"
        test_id = item.get("test_id")
        test_name = item.get("test_name") or "unknown"

        severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        confidence_distribution[confidence] = confidence_distribution.get(confidence, 0) + 1

        rule_key = f"{test_id or 'UNKNOWN'}:{test_name}"
        type_distribution[rule_key] = type_distribution.get(rule_key, 0) + 1
        file_distribution[filename] = file_distribution.get(filename, 0) + 1

        db.session.add(
            SastIssue(
                task_id=task.id,
                test_id=test_id,
                test_name=item.get("test_name"),
                issue_severity=severity,
                issue_confidence=confidence,
                issue_text=item.get("issue_text"),
                filename=filename,
                line_number=item.get("line_number"),
                line_range=json.dumps(item.get("line_range", [])),
                code=item.get("code"),
                more_info=item.get("more_info"),
                cwe=item.get("cwe"),
                owasp=item.get("owasp"),
            )
        )

    sast_result = task.sast_result or SastResult(task_id=task.id)
    sast_result.issue_count = len(issues)
    sast_result.high_count = severity_distribution.get("HIGH", 0)
    sast_result.medium_count = severity_distribution.get("MEDIUM", 0)
    sast_result.low_count = severity_distribution.get("LOW", 0)
    sast_result.severity_distribution = json.dumps(severity_distribution, ensure_ascii=False)
    sast_result.confidence_distribution = json.dumps(confidence_distribution, ensure_ascii=False)
    sast_result.type_distribution = json.dumps(type_distribution, ensure_ascii=False)
    sast_result.file_distribution = json.dumps(file_distribution, ensure_ascii=False)
    sast_result.raw_report_path = str(report_path)
    db.session.add(sast_result)

    summary = f"{engine_name} 扫描完成：发现 {len(issues)} 个问题，涉及 {len(file_distribution)} 个文件"
    update_task_status(task, TaskStatus.SUCCESS, progress=100, summary=summary, report_path=str(report_path))
    db.session.commit()


def _normalize_semgrep_severity(value: str | None) -> str:
    mapping = {
        "ERROR": "HIGH",
        "WARNING": "MEDIUM",
        "INFO": "LOW",
    }
    return mapping.get((value or "").upper(), "LOW")


def _normalize_semgrep_confidence(value: str | None) -> str:
    normalized = (value or "").upper()
    if normalized in {"HIGH", "MEDIUM", "LOW"}:
        return normalized
    return "MEDIUM"


def _to_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _pick_cwe(value) -> str | None:
    for item in _to_list(value):
        match = re.search(r"CWE-\d+", item, flags=re.IGNORECASE)
        if match:
            return match.group(0).upper()
    return None


def _pick_owasp(value) -> str | None:
    candidates = _to_list(value)
    if not candidates:
        return None
    preferred = next((item for item in candidates if "2021" in item), candidates[0])
    return preferred.replace(" - ", "-")


def _build_semgrep_more_info(metadata: dict) -> str | None:
    values: list[str] = []
    for key in ("source", "source-rule-url", "shortlink"):
        text = metadata.get(key)
        if text:
            values.append(str(text).strip())
    values.extend(_to_list(metadata.get("references")))
    unique_values: list[str] = []
    for item in values:
        if item and item not in unique_values:
            unique_values.append(item)
    return "\n".join(unique_values) if unique_values else None


def _resolve_semgrep_path(raw_path: str | None, target_path: str) -> str | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return str(candidate)
    base = Path(target_path)
    root = base if base.is_dir() else base.parent
    resolved = (root / candidate).resolve()
    return str(resolved)


def _extract_code_snippet(filename: str | None, line_range: list[int]) -> str | None:
    if not filename or not line_range:
        return None
    source = Path(filename)
    if not source.exists():
        return None
    start_line = max(line_range[0], 1)
    end_line = max(line_range[-1], start_line)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = source.read_text(encoding="utf-8-sig").splitlines()
    snippet = lines[start_line - 1 : end_line]
    return "\n".join(snippet).strip() or None


def _normalize_semgrep_issue(item: dict, *, target_path: str) -> dict:
    extra = item.get("extra") or {}
    metadata = extra.get("metadata") or {}
    check_id = item.get("check_id")
    start_line = int((item.get("start") or {}).get("line") or 0)
    end_line = int((item.get("end") or {}).get("line") or start_line or 0)
    line_range = [line for line in (start_line, end_line) if line]
    filename = _resolve_semgrep_path(item.get("path"), target_path)
    code = extra.get("lines")
    if code == "requires login":
        code = None
    code = code or _extract_code_snippet(filename, line_range)

    return {
        "test_id": check_id,
        "test_name": metadata.get("shortlink") or check_id,
        "issue_severity": _normalize_semgrep_severity(extra.get("severity")),
        "issue_confidence": _normalize_semgrep_confidence(metadata.get("confidence")),
        "issue_text": extra.get("message"),
        "filename": filename or item.get("path"),
        "line_number": start_line or None,
        "line_range": line_range,
        "code": code,
        "more_info": _build_semgrep_more_info(metadata),
        "cwe": _pick_cwe(metadata.get("cwe")),
        "owasp": _pick_owasp(metadata.get("owasp")),
    }


def run_bandit_scan(task: Task):
    report_path = Path(current_app.config["REPORT_DIR"]) / f"sast_{task.id}.json"
    update_task_status(task, TaskStatus.RUNNING, progress=10, summary="Bandit 扫描已开始")

    _prepare_target_path(task)

    command = ["bandit", "-r", task.target_path, "-f", "json", "-o", str(report_path)]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        _mark_scan_failed(task, "Bandit 扫描失败", str(exc))
        return

    if completed.returncode not in {0, 1}:
        _mark_scan_failed(task, "Bandit 扫描失败", completed.stderr or completed.stdout)
        return

    try:
        payload = _read_report_payload(report_path)
    except (OSError, json.JSONDecodeError) as exc:
        _mark_scan_failed(task, "Bandit 报告解析失败", str(exc))
        return

    normalized_issues = []
    for item in payload.get("results", []):
        test_id = item.get("test_id")
        cwe_info = lookup_bandit(test_id)
        normalized_issues.append(
            {
                "test_id": test_id,
                "test_name": item.get("test_name"),
                "issue_severity": item.get("issue_severity", "LOW"),
                "issue_confidence": item.get("issue_confidence", "LOW"),
                "issue_text": item.get("issue_text"),
                "filename": item.get("filename", "unknown"),
                "line_number": item.get("line_number"),
                "line_range": item.get("line_range", []),
                "code": item.get("code"),
                "more_info": item.get("more_info"),
                "cwe": cwe_info.get("cwe"),
                "owasp": cwe_info.get("owasp"),
            }
        )

    _persist_sast_results(task, normalized_issues, report_path, "Bandit")


def run_semgrep_scan(task: Task):
    report_path = Path(current_app.config["REPORT_DIR"]) / f"sast_{task.id}.json"
    update_task_status(task, TaskStatus.RUNNING, progress=10, summary="Semgrep 扫描已开始")

    target_path = _prepare_target_path(task)
    command = [
        current_app.config["SEMGREP_CMD"],
        "scan",
        "--config",
        current_app.config["SEMGREP_RULESET"],
        "--json",
        "--output",
        str(report_path),
        target_path,
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        _mark_scan_failed(task, "Semgrep 扫描失败", str(exc))
        return

    if completed.returncode != 0:
        _mark_scan_failed(task, "Semgrep 扫描失败", completed.stderr or completed.stdout)
        return

    try:
        payload = _read_report_payload(report_path)
    except (OSError, json.JSONDecodeError) as exc:
        _mark_scan_failed(task, "Semgrep 报告解析失败", str(exc))
        return

    normalized_issues = [
        _normalize_semgrep_issue(item, target_path=target_path)
        for item in payload.get("results", [])
    ]
    _persist_sast_results(task, normalized_issues, report_path, "Semgrep")

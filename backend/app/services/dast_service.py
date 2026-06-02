import json
import ipaddress
import subprocess
from pathlib import Path

from flask import current_app

from ..extensions import db
from ..models import DastIssue, DastResult, Task, TaskStatus
from ..services.task_service import update_task_status
from ..utils.cwe_mapping import build_owasp_distribution, lookup_wapiti


LEVEL_NAMES = {
    0: "INFO",
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
    4: "CRITICAL",
    "0": "INFO",
    "1": "LOW",
    "2": "MEDIUM",
    "3": "HIGH",
    "4": "CRITICAL",
    "info": "INFO",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}

LEVEL_ORDER = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1, "UNKNOWN": 0}


def _load_json(value: str | None) -> dict:
    return json.loads(value) if value else {}


def _sorted_distribution_entries(payload: dict, limit: int = 5) -> list[dict]:
    return [
        {"name": key, "count": value}
        for key, value in sorted(payload.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _normalize_level(level) -> str:
    if level is None:
        return "UNKNOWN"
    return LEVEL_NAMES.get(level, LEVEL_NAMES.get(str(level).lower(), "UNKNOWN"))


def _build_report_path(task: Task) -> Path:
    report_dir = Path(current_app.config["REPORT_DIR"])
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir / f"dast_{task.id}.json"


def _is_public_target(task: Task) -> bool:
    if task.target_policy == "public_allowed":
        return True
    if task.target_policy == "allowed_host" and task.target_host not in {"localhost", "127.0.0.1", "::1"}:
        return True
    for candidate in (task.target_host, task.target_ip):
        if not candidate:
            continue
        try:
            ip_address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        return not (ip_address.is_loopback or ip_address.is_private)
    return False


def _build_wapiti_command(task: Task, report_path: Path) -> list[str]:
    timeout = task.timeout_seconds or current_app.config["DEFAULT_DAST_TIMEOUT"]
    public_target = _is_public_target(task)
    scan_limit_key = "DAST_PUBLIC_MAX_SCAN_TIME" if public_target else "DAST_MAX_SCAN_TIME"
    attack_limit_key = "DAST_PUBLIC_MAX_ATTACK_TIME" if public_target else "DAST_MAX_ATTACK_TIME"
    request_timeout_key = "DAST_PUBLIC_REQUEST_TIMEOUT" if public_target else "DAST_REQUEST_TIMEOUT"
    max_scan_time = min(timeout, current_app.config[scan_limit_key])
    max_attack_time = min(timeout, current_app.config[attack_limit_key])
    modules = current_app.config.get("DAST_MODULES", "common")
    scope = current_app.config["DAST_PUBLIC_SCOPE"] if public_target else current_app.config["DAST_DEFAULT_SCOPE"]

    return [
        current_app.config["DAST_SCANNER_CMD"],
        "-u",
        task.target_url,
        "-f",
        "json",
        "-o",
        str(report_path),
        "--scope",
        scope,
        "--max-scan-time",
        str(max_scan_time),
        "--max-attack-time",
        str(max_attack_time),
        "-t",
        str(current_app.config[request_timeout_key]),
        "--tasks",
        "2",
        "-m",
        modules,
        "-v",
        "0",
    ]


def list_dast_issues(task: Task) -> list[dict]:
    issues = DastIssue.query.filter_by(task_id=task.id).all()
    issues.sort(key=lambda item: (-LEVEL_ORDER.get(item.level or "UNKNOWN", 0), item.category or "", item.path or ""))
    return [issue.to_dict() for issue in issues]


def build_dast_analysis(task: Task) -> dict | None:
    result = task.dast_result
    if not result:
        return None

    severity_distribution = _load_json(result.severity_distribution)
    type_distribution = _load_json(result.type_distribution)
    issues = list_dast_issues(task)
    path_distribution = {}
    for issue in issues:
        path = issue.get("path") or "unknown"
        path_distribution[path] = path_distribution.get(path, 0) + 1

    high_count = severity_distribution.get("HIGH", 0) + severity_distribution.get("CRITICAL", 0)
    top_type = _sorted_distribution_entries(type_distribution, limit=1)
    top_path = _sorted_distribution_entries(path_distribution, limit=1)

    headline = f"本次动态扫描共识别 {result.issue_count} 个漏洞项，爬取页面 {result.crawled_pages} 个。"
    if high_count:
        headline = f"本次动态扫描识别 {result.issue_count} 个漏洞项，其中高风险 {high_count} 个。"

    highlights = [
        f"异常项 {result.anomaly_count} 个，附加发现 {result.additional_count} 个。",
        f"最高频漏洞类型为 {top_type[0]['name']}（{top_type[0]['count']} 次）。" if top_type else "当前未形成明显漏洞类型聚集。",
        f"问题最集中的路径为 {top_path[0]['name']}（{top_path[0]['count']} 次）。" if top_path else "当前未形成明显路径聚集。",
    ]

    recommendations = []
    if high_count:
        recommendations.append("优先复核高风险动态问题，并结合请求样例确认其可利用性。")
    if result.issue_count:
        recommendations.append("可在论文中展示代表性漏洞请求与风险描述，说明平台如何组织动态扫描结果。")
    if not recommendations:
        recommendations.append("当前未发现明显高风险动态问题，可作为本地靶场安全基线展示。")

    return {
        "headline": headline,
        "highlights": highlights,
        "recommendations": recommendations,
        "top_types": _sorted_distribution_entries(type_distribution),
        "top_paths": _sorted_distribution_entries(path_distribution),
        "owasp_distribution": build_owasp_distribution([i.to_dict() for i in task.dast_issues]),
    }


def _parse_wapiti_report(report_path: Path) -> dict:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    vulnerabilities = payload.get("vulnerabilities", {}) or {}
    anomalies = payload.get("anomalies", {}) or {}
    additionals = payload.get("additionals", {}) or {}
    infos = payload.get("infos", {}) or {}

    issue_count = 0
    severity_distribution = {"INFO": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
    type_distribution = {}
    issue_rows = []

    for category, items in vulnerabilities.items():
        count = len(items)
        if count:
            type_distribution[category] = count
        issue_count += count
        for item in items:
            level_name = _normalize_level(item.get("level"))
            severity_distribution[level_name] += 1
            cwe_info = lookup_wapiti(category)
            issue_rows.append(
                {
                    "category": category,
                    "level": level_name,
                    "method": item.get("method"),
                    "path": item.get("path"),
                    "parameter": item.get("parameter"),
                    "info": item.get("info"),
                    "module": item.get("module"),
                    "referer": item.get("referer"),
                    "http_request": item.get("http_request"),
                    "curl_command": item.get("curl_command"),
                    "wstg": json.dumps(item.get("wstg"), ensure_ascii=False) if isinstance(item.get("wstg"), list) else item.get("wstg"),
                    "cwe": cwe_info.get("cwe"),
                    "owasp": cwe_info.get("owasp"),
                }
            )

    anomaly_count = sum(len(items) for items in anomalies.values())
    additional_count = sum(len(items) for items in additionals.values())
    crawled_pages = infos.get("crawled_pages_nbr", 0)
    scan_scope = infos.get("scope")

    non_zero_severity = {key: value for key, value in severity_distribution.items() if value}
    summary = (
        f"Wapiti 扫描完成：{infos.get('target') or 'target'}，发现 {issue_count} 个漏洞、"
        f"{anomaly_count} 个异常、{additional_count} 个附加发现，爬取 {crawled_pages} 个页面"
    )

    return {
        "issue_count": issue_count,
        "severity_distribution": non_zero_severity,
        "type_distribution": type_distribution,
        "summary": summary,
        "anomaly_count": anomaly_count,
        "additional_count": additional_count,
        "crawled_pages": crawled_pages,
        "scan_scope": scan_scope,
        "issues": issue_rows,
    }


def run_dast_scan(task: Task):
    report_path = _build_report_path(task)
    update_task_status(task, TaskStatus.RUNNING, progress=10, summary="Wapiti 扫描已开始")

    command = _build_wapiti_command(task, report_path)
    process_timeout = task.timeout_seconds or current_app.config["DEFAULT_DAST_TIMEOUT"]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=process_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        dast_result = task.dast_result or DastResult(task_id=task.id, target_url=task.target_url)
        dast_result.is_timeout = True
        dast_result.issue_count = 0
        dast_result.anomaly_count = 0
        dast_result.additional_count = 0
        dast_result.crawled_pages = 0
        dast_result.scan_scope = current_app.config["DAST_DEFAULT_SCOPE"]
        dast_result.severity_distribution = json.dumps({}, ensure_ascii=False)
        dast_result.type_distribution = json.dumps({}, ensure_ascii=False)
        dast_result.summary = f"Wapiti 扫描超时：超过 {process_timeout} 秒"
        dast_result.raw_report_path = str(report_path) if report_path.exists() else None
        db.session.add(dast_result)
        update_task_status(
            task,
            TaskStatus.TIMEOUT,
            progress=100,
            summary=dast_result.summary,
            error_message="扫描超时",
            report_path=dast_result.raw_report_path,
        )
        return

    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        dast_result = task.dast_result or DastResult(task_id=task.id, target_url=task.target_url)
        dast_result.is_timeout = False
        dast_result.issue_count = 0
        dast_result.anomaly_count = 0
        dast_result.additional_count = 0
        dast_result.crawled_pages = 0
        dast_result.scan_scope = current_app.config["DAST_DEFAULT_SCOPE"]
        dast_result.severity_distribution = json.dumps({}, ensure_ascii=False)
        dast_result.type_distribution = json.dumps({}, ensure_ascii=False)
        dast_result.summary = "Wapiti 扫描失败"
        dast_result.raw_report_path = str(report_path) if report_path.exists() else None
        db.session.add(dast_result)
        update_task_status(
            task,
            TaskStatus.FAILED,
            progress=100,
            summary="Wapiti 扫描失败",
            error_message=stderr[:1000] if stderr else "扫描进程失败",
            report_path=dast_result.raw_report_path,
        )
        return

    if not report_path.exists():
        dast_result = task.dast_result or DastResult(task_id=task.id, target_url=task.target_url)
        dast_result.is_timeout = False
        dast_result.issue_count = 0
        dast_result.anomaly_count = 0
        dast_result.additional_count = 0
        dast_result.crawled_pages = 0
        dast_result.scan_scope = current_app.config["DAST_DEFAULT_SCOPE"]
        dast_result.severity_distribution = json.dumps({}, ensure_ascii=False)
        dast_result.type_distribution = json.dumps({}, ensure_ascii=False)
        dast_result.summary = "Wapiti 已结束但未生成报告"
        dast_result.raw_report_path = None
        db.session.add(dast_result)
        update_task_status(
            task,
            TaskStatus.FAILED,
            progress=100,
            summary=dast_result.summary,
            error_message="扫描报告未找到",
        )
        return

    parsed = _parse_wapiti_report(report_path)
    DastIssue.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    for issue_item in parsed["issues"]:
        db.session.add(DastIssue(task_id=task.id, **issue_item))

    dast_result = task.dast_result or DastResult(task_id=task.id, target_url=task.target_url)
    dast_result.is_timeout = False
    dast_result.issue_count = parsed["issue_count"]
    dast_result.anomaly_count = parsed["anomaly_count"]
    dast_result.additional_count = parsed["additional_count"]
    dast_result.crawled_pages = parsed["crawled_pages"]
    dast_result.scan_scope = parsed["scan_scope"]
    dast_result.severity_distribution = json.dumps(parsed["severity_distribution"], ensure_ascii=False)
    dast_result.type_distribution = json.dumps(parsed["type_distribution"], ensure_ascii=False)
    dast_result.summary = parsed["summary"]
    dast_result.raw_report_path = str(report_path)
    db.session.add(dast_result)

    update_task_status(
        task,
        TaskStatus.SUCCESS,
        progress=100,
        summary=parsed["summary"],
        report_path=str(report_path),
    )

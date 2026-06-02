import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

from flask import current_app

from ..extensions import db
from ..models import ScaIssue, ScaResult, Task, TaskStatus
from ..services.task_service import update_task_status
from ..utils.exceptions import ApiError


SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}


def _safe_zip_member(member_name: str) -> bool:
    member_path = Path(member_name)
    return not member_path.is_absolute() and ".." not in member_path.parts


def locate_requirements_file(target_path: str) -> str:
    source = Path(target_path)
    if source.suffix.lower() == ".txt":
        return str(source)
    if source.suffix.lower() != ".zip":
        raise ApiError("unsupported file type", code=40002, status_code=400)

    extract_dir = source.parent / f"sca_{source.stem}_{uuid4().hex}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                if not _safe_zip_member(member.filename):
                    raise ApiError("invalid archive content", code=40002, status_code=400)
            archive.extractall(extract_dir)
    except zipfile.BadZipFile as exc:
        raise ApiError("invalid archive content", code=40002, status_code=400, errors={"file": "invalid zip"}) from exc

    matches = sorted(path for path in extract_dir.rglob("*") if path.is_file() and path.name.lower() == "requirements.txt")
    if not matches:
        raise ApiError("requirements.txt not found", code=40002, status_code=400, errors={"file": "requirements.txt required"})
    return str(matches[0])


def _to_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_vulns(dependency: dict) -> list[dict]:
    return dependency.get("vulns") or dependency.get("vulnerabilities") or []


def _infer_severity(vulnerability: dict) -> str:
    severity = vulnerability.get("severity") or vulnerability.get("cvss_severity")
    if severity:
        normalized = str(severity).upper()
        if normalized in {"CRITICAL", "HIGH"}:
            return "HIGH"
        if normalized == "MEDIUM":
            return "MEDIUM"
        if normalized == "LOW":
            return "LOW"
    if _to_list(vulnerability.get("fix_versions") or vulnerability.get("fixes")):
        return "HIGH"
    return "MEDIUM"


def parse_pip_audit_report(payload: dict) -> dict:
    dependencies = payload.get("dependencies") or []
    issues: list[dict] = []
    fixable_count = 0

    for dependency in dependencies:
        package_name = dependency.get("name") or dependency.get("package")
        installed_version = dependency.get("version") or dependency.get("installed_version")
        for vulnerability in _normalize_vulns(dependency):
            fix_versions = _to_list(vulnerability.get("fix_versions") or vulnerability.get("fixes"))
            if fix_versions:
                fixable_count += 1
            issues.append(
                {
                    "package_name": package_name or "unknown",
                    "installed_version": installed_version,
                    "vulnerability_id": vulnerability.get("id") or vulnerability.get("vulnerability_id"),
                    "aliases": _to_list(vulnerability.get("aliases")),
                    "fix_versions": fix_versions,
                    "description": vulnerability.get("description") or vulnerability.get("details"),
                    "severity": _infer_severity(vulnerability),
                }
            )

    return {
        "dependency_count": len(dependencies),
        "vulnerability_count": len(issues),
        "fixable_count": fixable_count,
        "issues": issues,
    }


def list_sca_issues(task: Task) -> list[dict]:
    issues = ScaIssue.query.filter_by(task_id=task.id).all()
    issues.sort(key=lambda item: (-SEVERITY_ORDER.get(item.severity or "UNKNOWN", 0), item.package_name, item.vulnerability_id or ""))
    return [issue.to_dict() for issue in issues]


def build_sca_analysis(task: Task) -> dict | None:
    result = task.sca_result
    if not result:
        return None

    issues = list_sca_issues(task)
    vulnerable_packages = len({issue["package_name"] for issue in issues})
    high_count = sum(1 for issue in issues if issue.get("severity") == "HIGH")
    headline = f"本次依赖审计发现 {result.vulnerability_count} 个漏洞，涉及 {vulnerable_packages} 个依赖包。"
    highlights = [
        f"已扫描依赖 {result.dependency_count} 个。",
        f"可修复漏洞 {result.fixable_count} 个。",
        f"高优先级漏洞 {high_count} 个。",
    ]
    recommendations = [
        "优先升级已有修复版本的依赖包，并在升级后重新执行 SCA 扫描。",
        "将 requirements.txt 纳入版本管理，便于追踪依赖风险变化。",
    ]
    if not issues:
        recommendations = ["当前未发现存在漏洞的 Python 依赖包，建议在发布流程中保留周期性 SCA 扫描。"]

    return {
        "headline": headline,
        "highlights": highlights,
        "recommendations": recommendations,
        "top_packages": sorted(result.to_dict().get("package_distribution", {}).items(), key=lambda item: (-item[1], item[0]))[:5],
    }


def _persist_sca_results(task: Task, parsed: dict, report_path: Path):
    ScaIssue.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    package_distribution: dict[str, int] = {}
    severity_distribution: dict[str, int] = {}

    for item in parsed["issues"]:
        package_name = item["package_name"]
        severity = item.get("severity") or "UNKNOWN"
        package_distribution[package_name] = package_distribution.get(package_name, 0) + 1
        severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        db.session.add(
            ScaIssue(
                task_id=task.id,
                package_name=package_name,
                installed_version=item.get("installed_version"),
                vulnerability_id=item.get("vulnerability_id"),
                aliases=json.dumps(item.get("aliases") or [], ensure_ascii=False),
                fix_versions=json.dumps(item.get("fix_versions") or [], ensure_ascii=False),
                description=item.get("description"),
                severity=severity,
            )
        )

    sca_result = task.sca_result or ScaResult(task_id=task.id)
    sca_result.dependency_count = parsed["dependency_count"]
    sca_result.vulnerability_count = parsed["vulnerability_count"]
    sca_result.fixable_count = parsed["fixable_count"]
    sca_result.summary = (
        f"pip-audit 扫描完成：发现 {parsed['vulnerability_count']} 个漏洞，"
        f"覆盖 {parsed['dependency_count']} 个依赖"
    )
    sca_result.raw_report_path = str(report_path)
    sca_result.package_distribution = json.dumps(package_distribution, ensure_ascii=False)
    sca_result.severity_distribution = json.dumps(severity_distribution, ensure_ascii=False)
    db.session.add(sca_result)
    update_task_status(task, TaskStatus.SUCCESS, progress=100, summary=sca_result.summary, report_path=str(report_path))
    db.session.commit()


def _mark_scan_failed(task: Task, summary: str, error_message: str | None = None):
    update_task_status(
        task,
        TaskStatus.FAILED,
        progress=100,
        summary=summary,
        error_message=(error_message or "")[:1000] or None,
    )


def build_pip_audit_command(scanner_cmd: str | None, requirements_path: str, report_path: Path) -> list[str]:
    base_command = scanner_cmd.strip() if scanner_cmd else ""
    command = [base_command] if base_command else [sys.executable, "-m", "pip_audit"]
    return [
        *command,
        "-r",
        requirements_path,
        "--format",
        "json",
        "--output",
        str(report_path),
        "--disable-pip",
        "--no-deps",
    ]


def run_pip_audit_scan(task: Task):
    report_path = Path(current_app.config["REPORT_DIR"]) / f"sca_{task.id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    update_task_status(task, TaskStatus.RUNNING, progress=10, summary="pip-audit 扫描已开始")

    try:
        requirements_path = locate_requirements_file(task.target_path or "")
    except ApiError as exc:
        _mark_scan_failed(task, "SCA 目标准备失败", exc.message)
        return

    command = build_pip_audit_command(current_app.config.get("SCA_SCANNER_CMD"), requirements_path, report_path)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=current_app.config["SCA_SCAN_TIMEOUT"],
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _mark_scan_failed(task, "pip-audit 扫描失败", str(exc))
        return

    if completed.returncode not in {0, 1}:
        _mark_scan_failed(task, "pip-audit 扫描失败", completed.stderr or completed.stdout)
        return

    if not report_path.exists():
        _mark_scan_failed(task, "pip-audit report parse failed", "report file was not generated")
        return

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _mark_scan_failed(task, "pip-audit 报告解析失败", str(exc))
        return

    _persist_sca_results(task, parse_pip_audit_report(payload), report_path)

    source = Path(task.target_path or "")
    if source.suffix.lower() == ".zip":
        # Keep the original upload but remove temporary extracted requirements.
        temp_root = Path(requirements_path).parents
        for parent in temp_root:
            if parent.name.startswith("sca_") and parent.parent == source.parent:
                shutil.rmtree(parent, ignore_errors=True)
                break

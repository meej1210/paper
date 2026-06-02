"""把 Task 装配成模板需要的完整 payload。

模板里能直接拿到的字段：
    - task / result / analysis：与原服务保持兼容
    - issues_by_severity：按 CRITICAL → INFO 分组，已 truncate
    - ai_insights：dict[issue_id, AiIssueInsight.to_dict()]，一次性批量拉取
    - severity_rollup / severity_total
    - risk_score / risk_band
    - owasp_distribution / owasp_for_radar：前者用于表格，后者按 ``A0X:2021`` 键值
    - kb_versions / engine_meta：方法学章节使用
    - meta：cover/footer 用到的杂项（生成时间、报告版本、保密标识等）
"""
from __future__ import annotations

import importlib.metadata
import re
from datetime import datetime, timezone, timedelta
from typing import Iterable

from ...models import (
    AiIssueInsight,
    DastIssue,
    SastIssue,
    ScaIssue,
    Task,
    TaskType,
)
from ...utils.cwe_mapping import build_owasp_distribution, lookup_bandit, lookup_wapiti
from ..dast_service import build_dast_analysis, list_dast_issues
from ..sast_service import build_sast_analysis, list_sast_issues
from ..sca_service import build_sca_analysis, list_sca_issues
from . import labels_zh
from .risk_scoring import compute_risk_score, risk_band

BEIJING_TZ = timezone(timedelta(hours=8))

SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN")
MAX_ISSUES_PER_SEVERITY = 200
MAX_CODE_LINES = 60
MAX_DESCRIPTION_CHARS = 1200
REPORT_VERSION = "v2.0"

PRIORITY_BY_SEVERITY = {
    "CRITICAL": "P0",
    "HIGH": "P1",
    "MEDIUM": "P2",
    "LOW": "P3",
    "INFO": "P3",
    "UNKNOWN": "P3",
}

PRIORITY_DESCRIPTION = {
    "P0": "立即响应（24 小时内）",
    "P1": "本周内修复",
    "P2": "纳入下个迭代修复",
    "P3": "记录并跟踪",
}


def build_payload(task: Task) -> dict:
    task_type = task.task_type
    task_dict = task.to_dict()

    if task_type == TaskType.SAST:
        result = task.sast_result.to_dict() if task.sast_result else {}
        issues = list_sast_issues(task)
        analysis = build_sast_analysis(task) or {}
        ai_insights = _load_ai_insights(task.id, TaskType.SAST.value)
        enriched_issues = [_enrich_sast_issue(issue) for issue in issues]
        type_distribution = result.get("type_distribution", {}) or {}
        confidence_distribution = result.get("confidence_distribution", {}) or {}
        file_distribution = result.get("file_distribution", {}) or {}
        top_distributions = {
            "files": _top_items(file_distribution, transformer=labels_zh.display_filename),
            "rules": _top_items(type_distribution, transformer=lambda v: labels_zh.sast_rule_label(*v.split(":", 1)) if ":" in v else labels_zh.sast_rule_label(v)),
            "confidence": _confidence_items(confidence_distribution),
        }
    elif task_type == TaskType.DAST:
        result = task.dast_result.to_dict() if task.dast_result else {}
        issues = list_dast_issues(task)
        analysis = build_dast_analysis(task) or {}
        ai_insights = _load_ai_insights(task.id, TaskType.DAST.value)
        enriched_issues = [_enrich_dast_issue(issue) for issue in issues]
        type_distribution = result.get("type_distribution", {}) or {}
        confidence_distribution = {}
        top_distributions = {
            "types": _top_items(type_distribution, transformer=labels_zh.dast_category_label),
            "paths": _top_items_from_issues(enriched_issues, key="path"),
            "methods": _top_items_from_issues(enriched_issues, key="method"),
        }
    elif task_type == TaskType.SCA:
        result = task.sca_result.to_dict() if task.sca_result else {}
        issues = list_sca_issues(task)
        analysis = build_sca_analysis(task) or {}
        ai_insights = {}
        enriched_issues = [_enrich_sca_issue(issue) for issue in issues]
        package_distribution = result.get("package_distribution", {}) or {}
        confidence_distribution = {}
        top_distributions = {
            "packages": _top_items(package_distribution),
            "vulnerabilities": _top_items_from_issues(enriched_issues, key="vulnerability_id"),
        }
    else:
        result, issues, analysis, ai_insights, enriched_issues = {}, [], {}, {}, []
        confidence_distribution = {}
        top_distributions = {}

    severity_rollup = _build_severity_rollup(enriched_issues)
    severity_total = sum(severity_rollup.values())
    issues_by_severity = _group_by_severity(enriched_issues)
    truncated_by_severity = _truncate_groups(issues_by_severity, MAX_ISSUES_PER_SEVERITY)
    severity_breakdown = _severity_breakdown(severity_rollup)

    owasp_rows = analysis.get("owasp_distribution") or build_owasp_distribution(enriched_issues)
    owasp_for_radar = _radar_data(owasp_rows)

    risk_score = compute_risk_score(severity_rollup, confidence_distribution if confidence_distribution else None)
    band = risk_band(risk_score)
    kb_versions = _kb_versions()
    engine_meta = _engine_meta(task)
    kb_other = _format_kb_other(kb_versions, engine_meta["engine_key"])

    return {
        "task": task_dict,
        "task_type": task_type.value,
        "task_type_label": labels_zh.task_type_label(task_type.value),
        "task_type_label_full": labels_zh.task_type_label(task_type.value, full=True),
        "result": result,
        "analysis": analysis,
        "issues": enriched_issues,
        "issues_by_severity": truncated_by_severity,
        "ai_insights": ai_insights,
        "severity_rollup": severity_rollup,
        "severity_total": severity_total,
        "severity_order": SEVERITY_ORDER,
        "severity_breakdown": severity_breakdown,
        "risk_score": risk_score,
        "risk_band": band,
        "risk_band_label": labels_zh.risk_band_label(band),
        "risk_band_description": labels_zh.risk_band_description(band),
        "owasp_rows": owasp_rows,
        "owasp_for_radar": owasp_for_radar,
        "top_distributions": top_distributions,
        "confidence_distribution": confidence_distribution,
        "kb_versions": kb_versions,
        "kb_other_summary": kb_other,
        "engine_meta": engine_meta,
        "executed_by": _executed_by(task),
        "remediation_priorities": _build_remediation_plan(severity_rollup),
        "meta": {
            "generated_at": _now_str(),
            "generated_date": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d"),
            "report_version": REPORT_VERSION,
            "report_no": f"SECREP-{task_type.value}-{task.id:06d}",
            "confidentiality": "保密 · 内部使用",
            "platform_name": "DevSecOps 安全审计平台",
        },
        "status_label": labels_zh.status_label(task_dict.get("status")),
    }


# ---------- helpers ----------


def _load_ai_insights(task_id: int, task_type_value: str) -> dict[int, dict]:
    rows = (
        AiIssueInsight.query.filter_by(task_id=task_id, task_type=task_type_value).all()
        if AiIssueInsight is not None
        else []
    )
    return {row.issue_id: row.to_dict() for row in rows}


def _build_severity_rollup(issues: list[dict]) -> dict[str, int]:
    rollup: dict[str, int] = {sev: 0 for sev in SEVERITY_ORDER}
    for issue in issues:
        sev = (issue.get("severity") or issue.get("issue_severity") or issue.get("level") or "UNKNOWN").upper()
        rollup[sev] = rollup.get(sev, 0) + 1
    # 去掉空键，保留有序
    return {sev: count for sev, count in rollup.items() if count > 0} or {"UNKNOWN": 0}


def _severity_breakdown(severity_rollup: dict[str, int]) -> dict:
    """供模板使用的预组装数据，避免在 Jinja 里写 list comprehension。

    返回 ``{"items": [...], "palette": {中文名: 颜色}}``。
    """
    from .charts_svg import SEVERITY_PALETTE

    items: list[dict] = []
    palette: dict[str, str] = {}
    for sev in SEVERITY_ORDER:
        count = int(severity_rollup.get(sev, 0) or 0)
        if not count:
            continue
        name = labels_zh.severity_label(sev)
        color = SEVERITY_PALETTE.get(sev, "#94a3b8")
        items.append({
            "name": name,
            "raw": sev,
            "count": count,
            "color": color,
        })
        palette[name] = color
    return {"items": items, "palette": palette}


def _group_by_severity(issues: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {sev: [] for sev in SEVERITY_ORDER}
    for issue in issues:
        sev = (issue.get("severity") or issue.get("issue_severity") or issue.get("level") or "UNKNOWN").upper()
        groups.setdefault(sev, []).append(issue)
    return {sev: items for sev, items in groups.items() if items}


def _truncate_groups(groups: dict[str, list[dict]], cap: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sev, items in groups.items():
        truncated = items[:cap]
        out[sev] = {
            "items": truncated,
            "total": len(items),
            "truncated_count": max(0, len(items) - len(truncated)),
        }
    return out


def _top_items(distribution: dict[str, int], *, limit: int = 8, transformer=None) -> list[dict]:
    if not distribution:
        return []
    entries = sorted(
        ((str(k), int(v or 0)) for k, v in distribution.items() if int(v or 0) > 0),
        key=lambda item: (-item[1], item[0]),
    )[:limit]
    out = []
    for key, value in entries:
        label = transformer(key) if transformer else key
        out.append({"name": label, "raw": key, "count": value})
    return out


def _top_items_from_issues(issues: list[dict], *, key: str, limit: int = 8) -> list[dict]:
    bucket: dict[str, int] = {}
    for issue in issues:
        value = issue.get(key) or "未知"
        bucket[str(value)] = bucket.get(str(value), 0) + 1
    return _top_items(bucket, limit=limit)


def _confidence_items(distribution: dict[str, int]) -> list[dict]:
    if not distribution:
        return []
    order = ("HIGH", "MEDIUM", "LOW")
    out = []
    for key in order:
        value = int(distribution.get(key, 0) or 0)
        if value:
            out.append({"name": labels_zh.confidence_label(key), "raw": key, "count": value})
    # 未知类
    extras = {k: v for k, v in distribution.items() if k not in order and int(v or 0) > 0}
    for k, v in extras.items():
        out.append({"name": labels_zh.confidence_label(k), "raw": k, "count": int(v)})
    return out


def _radar_data(owasp_rows: list[dict]) -> dict[str, int]:
    """把 build_owasp_distribution 的输出折成 ``{ 'A03:2021': N }`` 的形式。"""
    radar: dict[str, int] = {}
    for row in owasp_rows or []:
        label = row.get("label") or ""
        match = re.match(r"^(A\d{1,2}:\d{4})", label)
        if not match:
            continue
        key = match.group(1)
        radar[key] = radar.get(key, 0) + int(row.get("count") or 0)
    return radar


def _kb_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in ("bandit", "semgrep", "wapiti3", "pip-audit"):
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "-"
        except Exception:
            versions[pkg] = "-"
    return versions


def _format_kb_other(kb_versions: dict[str, str], current_engine_key: str) -> str:
    parts = [
        f"{name} {ver}"
        for name, ver in kb_versions.items()
        if ver and ver != "-" and name != current_engine_key
    ]
    return "; ".join(parts) or "-"


def _engine_meta(task: Task) -> dict:
    engine_key = (task.scanner_engine or task.task_type.value).lower()
    return {
        "engine_key": engine_key,
        "engine_name": labels_zh.engine_label(engine_key),
        "engine_description": labels_zh.engine_description(engine_key),
    }


def _executed_by(task: Task) -> dict:
    user = getattr(task, "user", None)
    if not user:
        return {"id": task.user_id, "username": "-", "display_name": "-"}
    return {
        "id": user.id,
        "username": getattr(user, "username", "-"),
        "display_name": getattr(user, "display_name", None) or getattr(user, "username", "-"),
    }


def _build_remediation_plan(severity_rollup: dict[str, int]) -> list[dict]:
    """根据严重程度分布给出 P0/P1/P2/P3 计划。"""
    plan = []
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        count = severity_rollup.get(sev, 0)
        if not count:
            continue
        priority = PRIORITY_BY_SEVERITY.get(sev, "P3")
        plan.append(
            {
                "priority": priority,
                "severity": sev,
                "severity_label": labels_zh.severity_label(sev),
                "count": count,
                "timeline": PRIORITY_DESCRIPTION.get(priority, ""),
                "action": _suggest_action(sev),
            }
        )
    return plan


def _suggest_action(severity: str) -> str:
    return {
        "CRITICAL": "立即组织安全工程师与开发负责人联合排查，确认受影响范围与是否已被利用。",
        "HIGH": "纳入本周修复清单，配合代码审查与回归测试一并验证。",
        "MEDIUM": "在下个迭代窗口完成修复，可结合现有重构计划一并处理。",
        "LOW": "建立长期跟踪条目，纳入定期安全清理。",
        "INFO": "记录在案，便于趋势追踪与基线对比。",
    }.get(severity, "记录并跟踪。")


def _now_str() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")


# ---------- per-type enrichment ----------


def _truncate_text(text: str | None, limit: int = MAX_DESCRIPTION_CHARS) -> str | None:
    if text is None:
        return None
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…（已截断）"


def _truncate_code(code: str | None, max_lines: int = MAX_CODE_LINES) -> tuple[str | None, int]:
    if not code:
        return None, 0
    lines = str(code).splitlines()
    if len(lines) <= max_lines:
        return code, 0
    truncated = "\n".join(lines[:max_lines])
    return truncated, len(lines) - max_lines


def _enrich_sast_issue(issue: dict) -> dict:
    test_id = issue.get("test_id")
    test_name = issue.get("test_name")

    # 复算 CWE/OWASP（若上游缺失）
    cwe = issue.get("cwe")
    owasp = issue.get("owasp")
    if not cwe or not owasp:
        info = lookup_bandit(test_id)
        cwe = cwe or info.get("cwe")
        owasp = owasp or info.get("owasp")

    code, omitted = _truncate_code(issue.get("code"))
    sev = (issue.get("issue_severity") or "LOW").upper()

    return {
        **issue,
        "id": issue.get("id"),
        "severity": sev,
        "severity_label": labels_zh.severity_label(sev),
        "confidence_label": labels_zh.confidence_label(issue.get("issue_confidence")),
        "rule_label": labels_zh.sast_rule_label(test_id, test_name),
        "filename_label": labels_zh.display_filename(issue.get("filename")),
        "cwe": cwe,
        "owasp": owasp,
        "owasp_label": labels_zh.owasp_label(owasp),
        "issue_text": _truncate_text(issue.get("issue_text")),
        "more_info": _truncate_text(issue.get("more_info"), limit=500),
        "code": code,
        "code_omitted_lines": omitted,
        "priority": PRIORITY_BY_SEVERITY.get(sev, "P3"),
    }


def _enrich_dast_issue(issue: dict) -> dict:
    category = issue.get("category")
    cwe = issue.get("cwe")
    owasp = issue.get("owasp")
    if not cwe or not owasp:
        info = lookup_wapiti(category)
        cwe = cwe or info.get("cwe")
        owasp = owasp or info.get("owasp")

    level = (issue.get("level") or "UNKNOWN").upper()
    info_text = _truncate_text(issue.get("info"))
    return {
        **issue,
        "id": issue.get("id"),
        "severity": level,
        "severity_label": labels_zh.severity_label(level),
        "category_label": labels_zh.dast_category_label(category),
        "cwe": cwe,
        "owasp": owasp,
        "owasp_label": labels_zh.owasp_label(owasp),
        "info": info_text,
        "http_request": _truncate_text(issue.get("http_request"), limit=1500),
        "curl_command": _truncate_text(issue.get("curl_command"), limit=1500),
        "priority": PRIORITY_BY_SEVERITY.get(level, "P3"),
    }


def _enrich_sca_issue(issue: dict) -> dict:
    sev = (issue.get("severity") or "UNKNOWN").upper()
    fix_versions = issue.get("fix_versions") or []
    aliases = issue.get("aliases") or []
    return {
        **issue,
        "id": issue.get("id"),
        "severity": sev,
        "severity_label": labels_zh.severity_label(sev),
        "description": _truncate_text(issue.get("description")),
        "fix_versions_label": ", ".join(fix_versions) if fix_versions else "暂无官方修复版本",
        "aliases_label": ", ".join(aliases) if aliases else "",
        "priority": PRIORITY_BY_SEVERITY.get(sev, "P3"),
    }

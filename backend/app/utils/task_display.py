import re
from datetime import UTC, datetime, timedelta, timezone


BEIJING_TZ = timezone(timedelta(hours=8))


def format_beijing_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    source = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return source.astimezone(BEIJING_TZ).isoformat(timespec="seconds")


def localize_task_summary(summary: str | None) -> str | None:
    if not summary:
        return summary

    completed_match = re.fullmatch(
        r"Wapiti scan completed for (?P<target>.+): "
        r"(?P<vulnerabilities>\d+) vulnerabilities, (?P<anomalies>\d+) anomalies, "
        r"(?P<additional>\d+) additional findings, (?P<pages>\d+) crawled pages",
        summary,
    )
    if completed_match:
        data = completed_match.groupdict()
        return (
            f"Wapiti 扫描完成：{data['target']}，发现 {data['vulnerabilities']} 个漏洞、"
            f"{data['anomalies']} 个异常、{data['additional']} 个附加发现，"
            f"爬取 {data['pages']} 个页面"
        )

    sast_completed_match = re.fullmatch(
        r"(?P<engine>Bandit|Semgrep) scan completed with (?P<issues>\d+) issues across (?P<files>\d+) files",
        summary,
    )
    if sast_completed_match:
        data = sast_completed_match.groupdict()
        return f"{data['engine']} 扫描完成：发现 {data['issues']} 个问题，涉及 {data['files']} 个文件"

    sca_completed_match = re.fullmatch(
        r"pip-audit scan completed with (?P<vulnerabilities>\d+) vulnerabilities across (?P<dependencies>\d+) dependencies",
        summary,
    )
    if sca_completed_match:
        data = sca_completed_match.groupdict()
        return f"pip-audit 扫描完成：发现 {data['vulnerabilities']} 个漏洞，覆盖 {data['dependencies']} 个依赖"

    timeout_match = re.fullmatch(r"Wapiti scan timed out after (?P<seconds>\d+) seconds", summary)
    if timeout_match:
        return f"Wapiti 扫描超时：超过 {timeout_match.group('seconds')} 秒"

    labels = {
        "task created": "任务已创建",
        "task cancelled": "任务已取消",
        "Wapiti scan started": "Wapiti 扫描已开始",
        "Wapiti scan failed": "Wapiti 扫描失败",
        "Wapiti finished without producing report": "Wapiti 已结束但未生成报告",
        "Bandit scan started": "Bandit 扫描已开始",
        "Bandit scan failed": "Bandit 扫描失败",
        "Bandit report parse failed": "Bandit 报告解析失败",
        "Semgrep scan started": "Semgrep 扫描已开始",
        "Semgrep scan failed": "Semgrep 扫描失败",
        "Semgrep report parse failed": "Semgrep 报告解析失败",
        "pip-audit scan started": "pip-audit 扫描已开始",
        "pip-audit scan failed": "pip-audit 扫描失败",
        "pip-audit report parse failed": "pip-audit 报告解析失败",
        "SCA target preparation failed": "SCA 目标准备失败",
        "SAST scan failed unexpectedly": "SAST 扫描异常失败",
        "SCA scan failed unexpectedly": "SCA 扫描异常失败",
    }
    return labels.get(summary, summary)

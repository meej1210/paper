"""Jinja2 渲染编排。

为了不依赖 Flask 的 ``render_template``（便于测试 + 复用），这里维护一个独立的
``jinja2.Environment``，懒加载并缓存。所有翻译/SVG 工具函数都在这里集中注册成
过滤器或全局，模板里直接用即可。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import charts_svg, fonts, labels_zh
from .data_assembly import build_payload

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "report"

_env: Optional[Environment] = None


def get_env() -> Environment:
    global _env
    if _env is not None:
        return _env

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Filters
    env.filters["severity_label"] = labels_zh.severity_label
    env.filters["confidence_label"] = labels_zh.confidence_label
    env.filters["owasp_label"] = labels_zh.owasp_label
    env.filters["sast_rule_label"] = labels_zh.sast_rule_label
    env.filters["dast_category_label"] = labels_zh.dast_category_label
    env.filters["display_filename"] = labels_zh.display_filename
    env.filters["engine_label"] = labels_zh.engine_label
    env.filters["status_label"] = labels_zh.status_label
    env.filters["target_policy_label"] = labels_zh.target_policy_label
    env.filters["risk_band_label"] = labels_zh.risk_band_label
    env.filters["dash"] = _dash_filter
    env.filters["fmt_duration"] = _fmt_duration
    env.filters["fmt_num"] = _fmt_num

    # Globals (charts + helpers)
    env.globals["donut_svg"] = charts_svg.donut_svg
    env.globals["hbar_svg"] = charts_svg.hbar_svg
    env.globals["radar_svg"] = charts_svg.radar_svg
    env.globals["severity_bar_svg"] = charts_svg.severity_bar_svg
    env.globals["severity_palette"] = charts_svg.SEVERITY_PALETTE
    env.globals["owasp_axes"] = charts_svg.OWASP_AXES
    env.globals["font_face_css"] = fonts.font_face_css
    # Helper callables exposed as globals so templates can pass them to chart helpers
    env.globals["severity_label_fn"] = labels_zh.severity_label
    env.globals["owasp_label_fn"] = labels_zh.owasp_label

    _env = env
    return env


def render_html(task) -> str:
    payload = build_payload(task)
    template_name = _template_for_task(payload["task_type"])
    template = get_env().get_template(template_name)
    fonts.warn_if_missing()
    return template.render(**payload)


def _template_for_task(task_type: str) -> str:
    key = (task_type or "").upper()
    if key == "DAST":
        return "dast.html"
    if key == "SCA":
        return "sca.html"
    return "sast.html"


# ---------- filters ----------


def _dash_filter(value):
    if value is None or value == "":
        return "-"
    return value


def _fmt_duration(ms) -> str:
    if not ms:
        return "-"
    try:
        total = int(ms)
    except (TypeError, ValueError):
        return str(ms)
    if total < 1000:
        return f"{total} 毫秒"
    seconds = total / 1000.0
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes} 分 {secs} 秒"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} 小时 {minutes} 分"


def _fmt_num(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)

"""导出入口。

保留与原 ``report_export_service.py`` 完全一致的对外签名：
    - build_report_html(task) -> str
    - build_report_pdf(task)  -> bytes
    - export_report(task, format) -> (bytes, mimetype, filename)
"""
from __future__ import annotations

from ...models import Task
from ...utils.exceptions import ApiError
from . import fonts, rendering

try:
    from weasyprint import HTML as WeasyHTML  # type: ignore

    _WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):  # pragma: no cover - 环境相关
    _WEASYPRINT_AVAILABLE = False


def build_report_html(task: Task) -> str:
    return rendering.render_html(task)


def build_report_pdf(task: Task) -> bytes:
    if not _WEASYPRINT_AVAILABLE:
        raise ApiError(
            "PDF export requires weasyprint: pip install weasyprint",
            code=50100,
            status_code=501,
        )
    html_content = build_report_html(task)
    font_config = fonts.build_font_config()
    document = WeasyHTML(string=html_content)
    if font_config is not None:
        return document.write_pdf(font_config=font_config)
    return document.write_pdf()


def export_report(task: Task, export_format: str) -> tuple[bytes, str, str]:
    export_format = (export_format or "html").lower()
    if export_format == "html":
        payload = build_report_html(task).encode("utf-8")
        return (
            payload,
            "text/html; charset=utf-8",
            f"{task.task_type.value.lower()}_report_{task.id}.html",
        )
    if export_format == "pdf":
        payload = build_report_pdf(task)
        return (
            payload,
            "application/pdf",
            f"{task.task_type.value.lower()}_report_{task.id}.pdf",
        )
    raise ApiError(
        "invalid parameters",
        code=40001,
        status_code=400,
        errors={"format": "must be html or pdf"},
    )

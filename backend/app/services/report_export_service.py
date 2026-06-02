"""Backwards-compatible shim — real implementation lives in :mod:`app.services.report`.

历史调用方（``app/api/{sast,dast,sca}.py``）通过 ``from ..services.report_export_service
import export_report`` 引用本模块；为了避免改动 API 路由，这里转发到新的包。
"""
from .report import build_report_html, build_report_pdf, export_report

__all__ = ["build_report_html", "build_report_pdf", "export_report"]

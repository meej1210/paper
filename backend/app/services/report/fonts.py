"""字体注册。

WeasyPrint 在 Linux 下依赖 fontconfig 自动找到字体；在 Windows 下需要显式指定
``file:///`` 路径才能稳定加载中文字体，因此本模块按平台分两条路径：

- Windows: 探测 ``C:/Windows/Fonts/`` 下的思源黑体 / 微软雅黑，emit ``@font-face`` 规则
- Linux:   依赖系统的 ``Noto Sans CJK SC`` 或 ``WenQuanYi Zen Hei``，不生成 ``@font-face``

无论平台，body 字体栈写成 ``'Report Sans', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif``，
让浏览器/WeasyPrint 按优先级 fallback。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from flask import current_app, has_app_context
except ImportError:  # pragma: no cover - flask 必装
    current_app = None
    has_app_context = lambda: False  # noqa: E731


@dataclass(frozen=True)
class FontEntry:
    family: str
    path: Path
    weight: int = 400
    style: str = "normal"


WINDOWS_CANDIDATES: tuple[tuple[str, int, str], ...] = (
    # (file_name, weight, style)
    ("NotoSansSC-VF.ttf", 400, "normal"),
    ("NotoSansSC-VF.ttf", 700, "normal"),  # 同字体走 variation
    ("msyh.ttc", 400, "normal"),
    ("msyhbd.ttc", 700, "normal"),
    ("msyhl.ttc", 300, "normal"),
)

WINDOWS_MONO_CANDIDATES: tuple[tuple[str, int, str], ...] = (
    ("consola.ttf", 400, "normal"),
    ("consolab.ttf", 700, "normal"),
)


def _windows_font_dir() -> Path:
    return Path("C:/Windows/Fonts")


def _detect_windows_fonts() -> tuple[list[FontEntry], list[FontEntry]]:
    base = _windows_font_dir()
    if not base.is_dir():
        return [], []

    body: list[FontEntry] = []
    seen: set[Path] = set()
    for name, weight, style in WINDOWS_CANDIDATES:
        path = base / name
        if path in seen or not path.exists():
            continue
        seen.add(path)
        body.append(FontEntry(family="Report Sans", path=path, weight=weight, style=style))

    mono: list[FontEntry] = []
    seen_mono: set[Path] = set()
    for name, weight, style in WINDOWS_MONO_CANDIDATES:
        path = base / name
        if path in seen_mono or not path.exists():
            continue
        seen_mono.add(path)
        mono.append(FontEntry(family="Report Mono", path=path, weight=weight, style=style))
    return body, mono


def _file_url(path: Path) -> str:
    return path.as_uri()


def font_face_css() -> str:
    """返回要注入到 ``<head><style>`` 里的 @font-face 规则。

    - 没找到任何字体则返回空串，body CSS 仍会通过 fallback 列表退化到系统默认。
    - 只在 Windows 主动 emit ``@font-face``。
    """
    body_fonts, mono_fonts = _detect_windows_fonts() if sys.platform == "win32" else ([], [])

    if not body_fonts and not mono_fonts:
        return ""

    parts: list[str] = []
    for entry in body_fonts + mono_fonts:
        parts.append(
            "@font-face {\n"
            f"  font-family: '{entry.family}';\n"
            f"  src: url('{_file_url(entry.path)}') format('truetype');\n"
            f"  font-weight: {entry.weight};\n"
            f"  font-style: {entry.style};\n"
            "  font-display: swap;\n"
            "}"
        )
    return "\n".join(parts)


def build_font_config() -> Optional[object]:
    """返回 ``weasyprint.text.fonts.FontConfiguration`` 实例（若可用）。

    供 ``HTML(...).write_pdf(font_config=...)`` 使用，确保 @font-face 在 PDF
    生成期间被解析。
    """
    try:
        from weasyprint.text.fonts import FontConfiguration  # type: ignore

        return FontConfiguration()
    except Exception:  # pragma: no cover
        return None


def warn_if_missing() -> None:
    """如果没有探测到任何中文字体，给 Flask logger 一个提示。"""
    if sys.platform != "win32":
        return
    body, _ = _detect_windows_fonts()
    if body:
        return
    if has_app_context() and current_app is not None:
        current_app.logger.warning(
            "[report] 未在 C:/Windows/Fonts/ 找到 NotoSansSC-VF.ttf / msyh.ttc，"
            "PDF 可能出现中文渲染异常，请安装思源黑体或微软雅黑。"
        )

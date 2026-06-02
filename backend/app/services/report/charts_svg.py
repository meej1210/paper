"""纯 Python 生成 SVG 图表。

输出字符串可直接以 ``{{ chart | safe }}`` 嵌入 Jinja 模板，被 WeasyPrint 渲染为
矢量图，缩放不失真。每个函数只依赖标准库（math），不引入 matplotlib / Pillow。

设计约束：
- 颜色全部由 palette 参数传入，调用方可按场景换色。
- 所有文本走 SVG ``<text>`` 元素，font-family 在外层 CSS 已经声明为 'Report Sans'。
- 零计数切片直接跳过，避免出现退化弧/退化柱。
"""
from __future__ import annotations

import html
import math
from typing import Iterable

# 配色：与严重程度徽章保持一致（templates/report/_styles.css.jinja）
SEVERITY_PALETTE: dict[str, str] = {
    "CRITICAL": "#7f1d1d",
    "HIGH": "#dc2626",
    "MEDIUM": "#ea580c",
    "LOW": "#facc15",
    "INFO": "#0ea5e9",
    "UNKNOWN": "#94a3b8",
}

DEFAULT_PALETTE = (
    "#1d4ed8", "#0ea5e9", "#14b8a6", "#facc15", "#f97316",
    "#dc2626", "#7c3aed", "#db2777", "#10b981", "#475569",
)

OWASP_AXES: tuple[str, ...] = (
    "A01:2021", "A02:2021", "A03:2021", "A04:2021", "A05:2021",
    "A06:2021", "A07:2021", "A08:2021", "A09:2021", "A10:2021",
)


def _esc(text: str | None) -> str:
    return html.escape("" if text is None else str(text), quote=True)


def _truncate(label: str, max_chars: int) -> str:
    if max_chars <= 0 or len(label) <= max_chars:
        return label
    return label[: max(1, max_chars - 1)] + "…"


def donut_svg(
    distribution: dict[str, int] | Iterable[tuple[str, int]],
    *,
    palette: dict[str, str] | None = None,
    label_resolver=None,
    size: int = 200,
    thickness: int = 30,
    center_title: str = "",
    center_value: str = "",
    legend: bool = True,
) -> str:
    """环形图。distribution 形如 ``{"HIGH": 3, "MEDIUM": 5}``，零值会被剔除。

    palette 缺省取 SEVERITY_PALETTE；其他键按 DEFAULT_PALETTE 轮询。
    label_resolver(key) -> str 用于把键翻译成展示文本（如严重程度→"高危"）。
    """
    items = list(distribution.items() if isinstance(distribution, dict) else distribution)
    items = [(k, int(v or 0)) for k, v in items if int(v or 0) > 0]
    palette = dict(palette or SEVERITY_PALETTE)

    width = size + (200 if legend else 0)
    height = size
    cx = size // 2
    cy = size // 2
    r = (size - thickness) // 2
    circumference = 2.0 * math.pi * r

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="severity distribution">'
    )

    # 背景圆环
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e2e8f0" stroke-width="{thickness}" />'
    )

    total = sum(v for _, v in items)
    if total <= 0:
        parts.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" '
            f'font-size="14" fill="#94a3b8">暂无数据</text>'
        )
        parts.append("</svg>")
        return "".join(parts)

    # 切片：从 12 点钟方向起、顺时针递增
    rotation = -90
    cumulative = 0.0
    fallback_idx = 0
    for key, value in items:
        seg_len = circumference * value / total
        color = palette.get(key)
        if not color:
            color = DEFAULT_PALETTE[fallback_idx % len(DEFAULT_PALETTE)]
            fallback_idx += 1
        offset = -cumulative
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{thickness}" stroke-dasharray="{seg_len:.3f} {circumference - seg_len:.3f}" '
            f'stroke-dashoffset="{offset:.3f}" transform="rotate({rotation} {cx} {cy})" />'
        )
        cumulative += seg_len

    # 中心文本
    if center_value:
        parts.append(
            f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" dominant-baseline="central" '
            f'font-size="28" font-weight="700" fill="#0f172a">{_esc(center_value)}</text>'
        )
    if center_title:
        parts.append(
            f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" dominant-baseline="central" '
            f'font-size="11" fill="#64748b">{_esc(center_title)}</text>'
        )

    # 图例
    if legend:
        legend_x = size + 16
        legend_y = 16
        for idx, (key, value) in enumerate(items):
            color = palette.get(key) or DEFAULT_PALETTE[idx % len(DEFAULT_PALETTE)]
            label = label_resolver(key) if label_resolver else str(key)
            pct = value / total * 100
            top = legend_y + idx * 22
            parts.append(
                f'<rect x="{legend_x}" y="{top}" width="14" height="14" rx="3" fill="{color}" />'
            )
            parts.append(
                f'<text x="{legend_x + 22}" y="{top + 11}" font-size="12" fill="#1e293b">'
                f'{_esc(label)}</text>'
            )
            parts.append(
                f'<text x="{width - 8}" y="{top + 11}" font-size="12" fill="#475569" text-anchor="end">'
                f'{value} · {pct:.1f}%</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def hbar_svg(
    items: Iterable,
    *,
    label_key: str = "name",
    value_key: str = "count",
    label_resolver=None,
    palette: dict[str, str] | None = None,
    color: str = "#2563eb",
    width: int = 560,
    row_height: int = 28,
    max_label_chars: int = 24,
    label_width: int = 200,
    value_width: int = 64,
    show_grid: bool = True,
) -> str:
    """横向条形图。

    items 接受 dict-list（含 label_key/value_key）或 (label, value) 元组列表。
    palette 命中 label 时优先使用，否则统一用 color。
    """
    rows: list[tuple[str, int]] = []
    for item in items:
        if isinstance(item, dict):
            label = item.get(label_key, "")
            value = int(item.get(value_key) or 0)
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            label, value = item[0], int(item[1] or 0)
        else:
            continue
        rows.append((str(label), value))

    rows = [(label, val) for label, val in rows if val > 0]
    if not rows:
        height = row_height + 12
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">'
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="13" fill="#94a3b8">暂无数据</text>'
            f"</svg>"
        )

    max_value = max(v for _, v in rows)
    bar_area = max(40, width - label_width - value_width - 16)
    height = row_height * len(rows) + 16
    palette = palette or {}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="horizontal bar chart">'
    ]

    bar_origin = label_width + 8
    # 网格线（25/50/75/100%）
    if show_grid:
        for ratio in (0.25, 0.5, 0.75, 1.0):
            x = bar_origin + bar_area * ratio
            parts.append(
                f'<line x1="{x:.1f}" y1="8" x2="{x:.1f}" y2="{height - 8}" '
                f'stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2 4" />'
            )

    for idx, (label, value) in enumerate(rows):
        y = 8 + idx * row_height
        bar_len = bar_area * value / max_value
        bar_color = palette.get(label, color)
        display_label = label_resolver(label) if label_resolver else label
        display_label = _truncate(str(display_label), max_label_chars)

        parts.append(
            f'<text x="{label_width}" y="{y + row_height // 2}" text-anchor="end" '
            f'dominant-baseline="central" font-size="12" fill="#1e293b">{_esc(display_label)}</text>'
        )
        parts.append(
            f'<rect x="{bar_origin}" y="{y + 5}" width="{bar_len:.1f}" height="{row_height - 10}" '
            f'rx="3" fill="{bar_color}" fill-opacity="0.85" />'
        )
        parts.append(
            f'<text x="{bar_origin + bar_len + 6:.1f}" y="{y + row_height // 2}" '
            f'dominant-baseline="central" font-size="12" fill="#475569">{value}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def radar_svg(
    distribution: dict[str, int],
    *,
    axes: Iterable[str] = OWASP_AXES,
    axis_resolver=None,
    size: int = 320,
    fill: str = "#2563eb",
    fill_opacity: float = 0.32,
    stroke: str = "#1d4ed8",
) -> str:
    """OWASP 雷达图。axes 是要展示的轴顺序；resolver 把轴键翻译成展示文本。"""
    axis_list = list(axes)
    n = len(axis_list)
    if n < 3:
        return ""

    cx = size // 2
    cy = size // 2
    max_radius = size // 2 - 56
    label_radius = max_radius + 24

    values = [int((distribution or {}).get(axis, 0) or 0) for axis in axis_list]
    max_value = max(values) if max(values) > 0 else 1

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" role="img" aria-label="OWASP top 10 distribution">'
    ]

    # 同心多边形网格
    for ratio in (0.25, 0.5, 0.75, 1.0):
        points: list[str] = []
        for i in range(n):
            angle = -math.pi / 2 + 2 * math.pi * i / n
            x = cx + max_radius * ratio * math.cos(angle)
            y = cy + max_radius * ratio * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polygon points="{" ".join(points)}" fill="none" stroke="#e2e8f0" stroke-width="1" />'
        )

    # 轴线
    for i in range(n):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        x = cx + max_radius * math.cos(angle)
        y = cy + max_radius * math.sin(angle)
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="#e2e8f0" stroke-width="1" />'
        )

    # 数据多边形
    data_points: list[str] = []
    for i, value in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        r = max_radius * value / max_value
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        data_points.append(f"{x:.1f},{y:.1f}")
    parts.append(
        f'<polygon points="{" ".join(data_points)}" fill="{fill}" '
        f'fill-opacity="{fill_opacity}" stroke="{stroke}" stroke-width="1.5" />'
    )

    # 顶点圆点 + 数值
    for i, value in enumerate(values):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        r = max_radius * value / max_value
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{stroke}" />'
        )

    # 轴标签
    for i, axis in enumerate(axis_list):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        x = cx + label_radius * math.cos(angle)
        y = cy + label_radius * math.sin(angle)
        anchor = "middle"
        # 左右两侧用对齐方式贴边
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        label_text = axis_resolver(axis) if axis_resolver else axis
        value = values[i]
        display = f"{label_text} · {value}" if value else label_text
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="central" font-size="11" fill="#334155">{_esc(display)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def severity_bar_svg(
    severity_rollup: dict[str, int],
    *,
    order: tuple[str, ...] = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"),
    label_resolver=None,
    height: int = 18,
    width: int = 560,
) -> str:
    """一行堆叠条，展示严重程度占比。"""
    if label_resolver is None:
        from .labels_zh import severity_label as _default_resolver
        label_resolver = _default_resolver

    items = [(sev, int((severity_rollup or {}).get(sev, 0) or 0)) for sev in order]
    items = [(sev, val) for sev, val in items if val > 0]
    total = sum(val for _, val in items)

    svg_height = height + 28
    if total <= 0:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {svg_height}" '
            f'width="{width}" height="{svg_height}">'
            f'<rect x="0" y="6" width="{width}" height="{height}" rx="6" fill="#e2e8f0" />'
            f'<text x="{width // 2}" y="{height + 22}" text-anchor="middle" '
            f'font-size="12" fill="#94a3b8">未发现风险项</text>'
            f"</svg>"
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {svg_height}" '
        f'width="{width}" height="{svg_height}">'
    ]
    parts.append(
        f'<rect x="0" y="6" width="{width}" height="{height}" rx="6" fill="#e2e8f0" />'
    )

    cursor = 0.0
    for sev, val in items:
        seg = width * val / total
        color = SEVERITY_PALETTE.get(sev, "#94a3b8")
        parts.append(
            f'<rect x="{cursor:.1f}" y="6" width="{seg:.1f}" height="{height}" fill="{color}" />'
        )
        cursor += seg

    # 底部图例
    legend_y = svg_height - 4
    cursor = 0.0
    for sev, val in items:
        seg = width * val / total
        center = cursor + seg / 2
        label = label_resolver(sev) if label_resolver else sev
        parts.append(
            f'<text x="{center:.1f}" y="{legend_y}" text-anchor="middle" '
            f'font-size="11" fill="#334155">{_esc(label)} {val}</text>'
        )
        cursor += seg

    parts.append("</svg>")
    return "".join(parts)

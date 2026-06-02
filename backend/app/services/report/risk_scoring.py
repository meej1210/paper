"""风险评分。把每种严重程度的命中数压缩成一个 0-100 的可比较分值。

公式（确定性、可解释、可调）：
    raw   = sum(count[sev] * weight[sev])
    raw  *= confidence_multiplier (仅 SAST 有置信度分布时启用)
    score = round(100 * (1 - exp(-raw / SCALE)))   # 饱和曲线，避免超大项目刷爆 100

band:
    score >= 80 -> CRITICAL
    score >= 60 -> HIGH
    score >= 35 -> MEDIUM
    score >= 10 -> LOW
    其余        -> SAFE

参考点：
    1 CRITICAL                       -> ≈ 25  (band=LOW，刚好越过 SAFE 阈值)
    1 HIGH                           -> ≈ 16  (band=LOW)
    5 HIGH                           -> ≈ 58  (band=MEDIUM)
    10 HIGH                          -> ≈ 82  (band=CRITICAL)
    3 CRITICAL + 5 HIGH              -> ≈ 84  (band=CRITICAL)
"""
from __future__ import annotations

import math

SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 10.0,
    "HIGH": 6.0,
    "MEDIUM": 2.5,
    "LOW": 0.8,
    "INFO": 0.1,
}

CONFIDENCE_MULTIPLIER: dict[str, float] = {
    "HIGH": 1.0,
    "MEDIUM": 0.85,
    "LOW": 0.7,
    "UNDEFINED": 0.85,
    "UNKNOWN": 0.85,
}

SCALE = 35.0  # 越大越保守


def compute_risk_score(
    severity_rollup: dict | None,
    confidence_distribution: dict | None = None,
) -> int:
    if not severity_rollup:
        return 0

    raw = 0.0
    for sev, weight in SEVERITY_WEIGHTS.items():
        try:
            raw += float(severity_rollup.get(sev, 0)) * weight
        except (TypeError, ValueError):
            continue

    if confidence_distribution:
        total = sum(int(v or 0) for v in confidence_distribution.values())
        if total > 0:
            weighted = 0.0
            for key, value in confidence_distribution.items():
                mult = CONFIDENCE_MULTIPLIER.get(str(key).upper(), 0.85)
                weighted += int(value or 0) * mult
            raw *= weighted / total

    if raw <= 0:
        return 0

    score = 100.0 * (1.0 - math.exp(-raw / SCALE))
    return int(round(min(100.0, max(0.0, score))))


def risk_band(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    if score >= 10:
        return "LOW"
    return "SAFE"


def band_color(band: str) -> str:
    return {
        "CRITICAL": "#7f1d1d",
        "HIGH": "#b91c1c",
        "MEDIUM": "#c2410c",
        "LOW": "#15803d",
        "SAFE": "#0f766e",
    }.get(band, "#475569")

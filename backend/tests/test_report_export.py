"""Tests for the refactored report export pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import (
    DastIssue,
    DastResult,
    SastIssue,
    SastResult,
    ScaIssue,
    ScaResult,
    Task,
    TaskStatus,
    TaskType,
)
from app.services.report import build_report_html
from app.services.report.charts_svg import (
    donut_svg,
    hbar_svg,
    radar_svg,
    severity_bar_svg,
)
from app.services.report.labels_zh import (
    dast_category_label,
    display_filename,
    owasp_label,
    sast_rule_label,
    severity_label,
)
from app.services.report.risk_scoring import compute_risk_score, risk_band


# ---------- pure-function tests ----------


def _css_rule_block(css: str, selector: str) -> str:
    start = css.index(selector)
    open_brace = css.index("{", start)
    close_brace = css.index("}", open_brace)
    return css[open_brace + 1:close_brace]


def test_pdf_cover_css_keeps_cover_layout_in_document_flow():
    css_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "report" / "_styles.css.jinja"
    css = css_path.read_text(encoding="utf-8")

    assert ".cover .cover-main" in css
    assert "grid-template-columns: minmax(0, 1fr) 64mm" in _css_rule_block(css, ".cover .cover-main")

    for selector in (".cover .cover-score", ".cover .cover-meta"):
        block = _css_rule_block(css, selector)
        assert "position: absolute" not in block


def test_pdf_body_css_avoids_sparse_forced_section_pages():
    css_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "report" / "_styles.css.jinja"
    css = css_path.read_text(encoding="utf-8")

    toc_block = _css_rule_block(css, ".toc")
    assert "page-break-before: always" not in toc_block
    assert "page-break-after: always" not in toc_block

    major_block = _css_rule_block(css, "section.major")
    assert "page-break-before: always" not in major_block

    issue_card_block = _css_rule_block(css, ".issue-card")
    assert "page-break-inside: avoid" not in issue_card_block


def test_dast_overview_uses_compact_chart_set():
    template_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "report" / "dast.html"
    template = template_path.read_text(encoding="utf-8")

    overview = template.split("{% block overview_charts %}", 1)[1].split("{% endblock %}", 1)[0]
    assert overview.count("m.chart_card(") <= 4
    assert "size=150" in overview
    assert "row_height=22" in overview


def test_sca_overview_avoids_wide_grid_charts_that_clip_in_pdf():
    template_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "report" / "sca.html"
    template = template_path.read_text(encoding="utf-8")

    overview = template.split("{% block overview_charts %}", 1)[1].split("{% endblock %}", 1)[0]
    assert "wide=true" not in overview
    assert "size=150" in overview
    assert "row_height=22" in overview
    assert "width=360" in overview


def test_sca_overview_starts_on_new_page_to_keep_charts_complete():
    base_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "report" / "base.html"
    css_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "report" / "_styles.css.jinja"

    assert 'class="report report-{{ task_type | lower }}"' in base_path.read_text(encoding="utf-8")

    css = css_path.read_text(encoding="utf-8")
    assert ".report-sca #sec-overview" in css
    sca_overview_block = _css_rule_block(css, ".report-sca #sec-overview")
    assert "break-before: page" in sca_overview_block


def test_risk_score_empty():
    assert compute_risk_score({}) == 0
    assert risk_band(0) == "SAFE"


def test_risk_score_single_critical_crosses_low_threshold():
    score = compute_risk_score({"CRITICAL": 1})
    assert 20 <= score <= 35
    assert risk_band(score) == "LOW"


def test_risk_score_ten_highs_band_critical():
    score = compute_risk_score({"HIGH": 10})
    assert score >= 80
    assert risk_band(score) == "CRITICAL"


def test_risk_score_low_confidence_reduces_score():
    base = compute_risk_score({"HIGH": 5})
    reduced = compute_risk_score({"HIGH": 5}, confidence_distribution={"LOW": 5})
    assert reduced < base


def test_severity_label_chinese():
    assert severity_label("HIGH") == "高危"
    assert severity_label("medium") == "中危"
    assert severity_label("") == "未知"
    assert severity_label(None) == "未知"


def test_owasp_label_with_prefix():
    assert owasp_label("A03:2021") == "注入"
    assert owasp_label("A03:2021-Injection") == "A03:2021 注入"
    assert owasp_label("Uncategorized") == "未分类"
    assert owasp_label("Some-Other") == "Some-Other"


def test_sast_rule_label_resolves_bandit_id():
    assert sast_rule_label("B602") == "B602 shell=True 命令注入风险"
    assert sast_rule_label("b602", "subprocess_popen_with_shell_equals_true").startswith("B602")
    assert sast_rule_label(None, "yaml_load") == "不安全的 YAML 加载"


def test_dast_category_label_translates():
    assert dast_category_label("SQL Injection") == "SQL 注入"
    assert dast_category_label("Unknown thing") == "Unknown thing"


def test_display_filename_strips_hash_prefix():
    assert display_filename("/uploads/abc1234567890abcdef-app.py") == "app.py"
    assert display_filename(None) == "-"


# ---------- SVG generation tests ----------


def test_donut_svg_skips_zero_slices():
    svg = donut_svg({"HIGH": 0, "MEDIUM": 5}, center_value="5")
    assert svg.startswith("<svg")
    # 只应有 1 段切片 + 1 段背景 = 2 个 <circle>
    assert svg.count("<circle") == 2
    assert "5" in svg


def test_donut_svg_empty_renders_placeholder():
    svg = donut_svg({})
    assert "暂无数据" in svg


def test_hbar_svg_clips_to_top_items():
    svg = hbar_svg([{"name": "a", "count": 3}, {"name": "b", "count": 0}])
    # 0 计数会被跳过
    assert svg.count("<rect") == 1
    assert ">a<" in svg


def test_radar_svg_emits_polygon():
    svg = radar_svg({"A01:2021": 1, "A03:2021": 5})
    assert svg.count("<polygon") >= 5  # 4 网格 + 1 数据
    assert "A03:2021" in svg


def test_severity_bar_svg_outputs_legend():
    svg = severity_bar_svg({"HIGH": 3, "MEDIUM": 5})
    assert "高危" in svg
    assert "中危" in svg


# ---------- smoke render tests (Jinja) ----------


def _save_sast_fixture(db, sample_user) -> Task:
    task = Task(
        user_id=sample_user.id,
        task_type=TaskType.SAST,
        task_name="单测任务 · SAST",
        status=TaskStatus.SUCCESS,
        target_path="/tmp/demo/app.py",
        scanner_engine="bandit",
    )
    db.session.add(task)
    db.session.flush()

    sast_result = SastResult(
        task_id=task.id,
        issue_count=3,
        high_count=1,
        medium_count=1,
        low_count=1,
        severity_distribution=json.dumps({"HIGH": 1, "MEDIUM": 1, "LOW": 1}),
        confidence_distribution=json.dumps({"HIGH": 2, "MEDIUM": 1}),
        type_distribution=json.dumps({
            "B602:subprocess_popen_with_shell_equals_true": 2,
            "B105:hardcoded_password_string": 1,
        }),
        file_distribution=json.dumps({"/tmp/demo/app.py": 2, "/tmp/demo/util.py": 1}),
    )
    db.session.add(sast_result)

    for severity, conf, test_id, line in [
        ("HIGH", "HIGH", "B602", 12),
        ("MEDIUM", "MEDIUM", "B602", 24),
        ("LOW", "HIGH", "B105", 9),
    ]:
        db.session.add(
            SastIssue(
                task_id=task.id,
                test_id=test_id,
                test_name="subprocess_popen_with_shell_equals_true" if test_id == "B602" else "hardcoded_password_string",
                issue_severity=severity,
                issue_confidence=conf,
                issue_text=f"测试用例：{test_id} 触发的安全问题描述。",
                filename="/tmp/demo/app.py",
                line_number=line,
                line_range=json.dumps([line, line]),
                code=f"# line {line}\nsubprocess.Popen(cmd, shell=True)",
                more_info="https://bandit.readthedocs.io",
            )
        )
    db.session.commit()
    return task


def _save_dast_fixture(db, sample_user) -> Task:
    task = Task(
        user_id=sample_user.id,
        task_type=TaskType.DAST,
        task_name="单测任务 · DAST",
        status=TaskStatus.SUCCESS,
        target_url="http://lab.local/login",
        target_host="lab.local",
        target_ip="127.0.0.1",
        target_policy="loopback",
        authorization_confirmed=True,
        scanner_engine="wapiti",
    )
    db.session.add(task)
    db.session.flush()

    dast_result = DastResult(
        task_id=task.id,
        target_url="http://lab.local/login",
        issue_count=2,
        anomaly_count=1,
        additional_count=0,
        crawled_pages=14,
        scan_scope="folder",
        severity_distribution=json.dumps({"HIGH": 1, "MEDIUM": 1}),
        type_distribution=json.dumps({"SQL Injection": 1, "Cross Site Scripting": 1}),
        summary="DAST 演示扫描",
    )
    db.session.add(dast_result)

    for category, level in [("SQL Injection", "HIGH"), ("Cross Site Scripting", "MEDIUM")]:
        db.session.add(
            DastIssue(
                task_id=task.id,
                category=category,
                level=level,
                method="POST",
                path="/login",
                parameter="username",
                info=f"{category} 详情说明：参数被注入。",
                module="sql" if category.startswith("SQL") else "xss",
                curl_command="curl -X POST http://lab.local/login -d 'username=admin"+chr(39)+" OR 1=1--&password=x'",
            )
        )
    db.session.commit()
    return task


def _save_sca_fixture(db, sample_user) -> Task:
    task = Task(
        user_id=sample_user.id,
        task_type=TaskType.SCA,
        task_name="单测任务 · SCA",
        status=TaskStatus.SUCCESS,
        target_path="/tmp/demo/requirements.txt",
        scanner_engine="pip-audit",
    )
    db.session.add(task)
    db.session.flush()

    sca_result = ScaResult(
        task_id=task.id,
        dependency_count=23,
        vulnerability_count=2,
        fixable_count=2,
        package_distribution=json.dumps({"flask": 1, "requests": 1}),
        severity_distribution=json.dumps({"HIGH": 1, "MEDIUM": 1}),
        summary="演示 SCA",
    )
    db.session.add(sca_result)

    db.session.add(
        ScaIssue(
            task_id=task.id,
            package_name="flask",
            installed_version="0.12.0",
            vulnerability_id="GHSA-xxxx",
            aliases=json.dumps(["CVE-2018-1000656"]),
            fix_versions=json.dumps(["0.12.3"]),
            description="Flask 拒绝服务漏洞，建议升级到修复版本。",
            severity="HIGH",
        )
    )
    db.session.add(
        ScaIssue(
            task_id=task.id,
            package_name="requests",
            installed_version="2.5.0",
            vulnerability_id="GHSA-yyyy",
            aliases=json.dumps([]),
            fix_versions=json.dumps(["2.20.0"]),
            description="requests 旧版本存在凭据泄露风险。",
            severity="MEDIUM",
        )
    )
    db.session.commit()
    return task


def test_render_sast_report_smoke(app, db, sample_user):
    task = _save_sast_fixture(db, sample_user)
    html = build_report_html(task)
    assert "<!doctype html>" in html
    assert "SAST · 静态代码安全审计报告" in html
    assert "高危" in html and "中危" in html
    assert "<svg" in html
    assert "B602 shell=True 命令注入风险" in html
    assert "整改优先级与路线图" in html


def test_render_dast_report_smoke(app, db, sample_user):
    task = _save_dast_fixture(db, sample_user)
    html = build_report_html(task)
    assert "DAST · 动态应用安全扫描报告" in html
    assert "SQL 注入" in html
    assert "授权确认" in html or "授权边界" in html
    assert "lab.local" in html


def test_render_sca_report_smoke(app, db, sample_user):
    task = _save_sca_fixture(db, sample_user)
    html = build_report_html(task)
    assert "SCA · 软件依赖成分审计报告" in html
    assert "flask" in html
    assert "GHSA-xxxx" in html
    assert "可修复项" in html

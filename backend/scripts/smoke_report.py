"""手动 smoke 脚本：用内存数据库 + 一组示例任务渲染三份 HTML 和 PDF。

运行方式：
    cd backend
    python scripts/smoke_report.py
输出在 backend/tmp/ 下。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    AiIssueInsight,
    DastIssue,
    DastResult,
    SastIssue,
    SastResult,
    ScaIssue,
    ScaResult,
    Task,
    TaskStatus,
    TaskType,
    User,
)
from app.services.report import build_report_html, build_report_pdf  # noqa: E402
from app.utils.security import hash_password  # noqa: E402


def seed(app):
    db.create_all()
    user = User(
        username="demo",
        email="demo@example.com",
        password_hash=hash_password("demo-pass-1234"),
    )
    db.session.add(user)
    db.session.flush()

    sast = Task(
        user_id=user.id,
        task_type=TaskType.SAST,
        task_name="演示项目 · 后台服务静态扫描",
        status=TaskStatus.SUCCESS,
        target_path="/srv/demo/backend",
        scanner_engine="bandit",
        duration_ms=42_300,
        result_summary="Bandit 扫描完成：发现 14 个问题，涉及 6 个文件",
    )
    db.session.add(sast)
    db.session.flush()
    db.session.add(SastResult(
        task_id=sast.id,
        issue_count=14, high_count=3, medium_count=6, low_count=5,
        severity_distribution=json.dumps({"HIGH": 3, "MEDIUM": 6, "LOW": 5}),
        confidence_distribution=json.dumps({"HIGH": 6, "MEDIUM": 5, "LOW": 3}),
        type_distribution=json.dumps({
            "B602:subprocess_popen_with_shell_equals_true": 4,
            "B105:hardcoded_password_string": 3,
            "B324:hashlib": 2,
            "B201:flask_debug_true": 2,
            "B506:yaml_load": 2,
            "B110:try_except_pass": 1,
        }),
        file_distribution=json.dumps({
            "/srv/demo/backend/app/api/auth.py": 4,
            "/srv/demo/backend/app/utils/crypto.py": 3,
            "/srv/demo/backend/app/services/runner.py": 3,
            "/srv/demo/backend/app/main.py": 2,
            "/srv/demo/backend/app/tasks.py": 2,
        }),
    ))
    sast_samples = [
        ("HIGH", "HIGH", "B602", "subprocess_popen_with_shell_equals_true",
         "auth.py", 42, "subprocess.Popen(['ls', user_input], shell=True)",
         "使用 shell=True 调用 subprocess.Popen，可能被用户输入操纵命令。",
         "CWE-78", "A03:2021-Injection"),
        ("HIGH", "HIGH", "B105", "hardcoded_password_string",
         "crypto.py", 14, 'JWT_SECRET = "super-secret-key"',
         "硬编码的字符串看起来像密码：'super-secret-key'。",
         "CWE-259", "A07:2021-Identification and Authentication Failures"),
        ("HIGH", "MEDIUM", "B324", "hashlib",
         "crypto.py", 88, "hashlib.md5(payload).hexdigest()",
         "MD5 已被证明不具备抗碰撞性，请使用 SHA-256 或更强算法。",
         "CWE-327", "A02:2021-Cryptographic Failures"),
        ("MEDIUM", "HIGH", "B201", "flask_debug_true",
         "main.py", 9, "app.run(debug=True)",
         "Flask 调试模式开启会泄露敏感信息并允许任意代码执行。",
         "CWE-94", "A05:2021-Security Misconfiguration"),
        ("MEDIUM", "MEDIUM", "B506", "yaml_load",
         "runner.py", 33, "yaml.load(open(path))",
         "yaml.load 默认使用 Loader 可执行任意构造器，请改用 safe_load。",
         "CWE-502", "A08:2021-Software and Data Integrity Failures"),
        ("LOW", "LOW", "B110", "try_except_pass",
         "tasks.py", 102, "try:\n    do()\nexcept Exception:\n    pass",
         "try-except 中静默吞掉异常会掩盖问题。",
         "CWE-390", "A04:2021-Insecure Design"),
    ]
    for sev, conf, test_id, name, fname, line, code, text, cwe, owasp in sast_samples:
        issue = SastIssue(
            task_id=sast.id,
            test_id=test_id,
            test_name=name,
            issue_severity=sev,
            issue_confidence=conf,
            issue_text=text,
            filename=f"/srv/demo/backend/app/{'utils/' if fname == 'crypto.py' else 'api/' if fname == 'auth.py' else ''}{fname}",
            line_number=line,
            line_range=json.dumps([line, line]),
            code=code,
            more_info="https://bandit.readthedocs.io/en/latest/plugins/index.html",
            cwe=cwe,
            owasp=owasp,
        )
        db.session.add(issue)
        db.session.flush()
        if test_id in {"B602", "B105"}:
            db.session.add(AiIssueInsight(
                task_id=sast.id,
                task_type=TaskType.SAST.value,
                issue_id=issue.id,
                issue_fingerprint=f"fp-{issue.id}",
                model_name="demo-model",
                meaning=f"{name} 触发：当前调用允许把用户输入直接拼接到命令/凭据。",
                impact="一旦被攻击者可控，会造成命令注入或凭据被盗取。",
                fix="改用参数化调用或从安全配置中心读取凭据。",
                verify="本地构造 payload 重放并观察是否仍可触发命令执行。",
            ))

    # ---- DAST ----
    dast = Task(
        user_id=user.id,
        task_type=TaskType.DAST,
        task_name="演示项目 · Web 入口动态扫描",
        status=TaskStatus.SUCCESS,
        target_url="https://demo.lab.local/",
        target_host="demo.lab.local",
        target_ip="10.0.0.7",
        target_policy="allowed_host",
        authorization_confirmed=True,
        scanner_engine="wapiti",
        duration_ms=185_000,
        result_summary="Wapiti 扫描完成：demo.lab.local，发现 9 个漏洞、2 个异常、4 个附加发现，爬取 28 个页面",
    )
    db.session.add(dast)
    db.session.flush()
    db.session.add(DastResult(
        task_id=dast.id,
        target_url="https://demo.lab.local/",
        issue_count=9, anomaly_count=2, additional_count=4, crawled_pages=28,
        scan_scope="domain",
        severity_distribution=json.dumps({"HIGH": 2, "MEDIUM": 4, "LOW": 3}),
        type_distribution=json.dumps({
            "SQL Injection": 2, "Cross Site Scripting": 3,
            "HTTP Secure Headers": 1, "Backup file": 1,
            "Open Redirect": 1, "Clickjacking Protection": 1,
        }),
        summary="演示 DAST 扫描",
    ))
    dast_samples = [
        ("SQL Injection", "HIGH", "POST", "/api/login", "username",
         "通过在 username 参数注入 OR 1=1 -- 可绕过登录验证。", "sql",
         "curl -X POST https://demo.lab.local/api/login -d \"username=admin' OR 1=1--&password=x\""),
        ("Cross Site Scripting", "MEDIUM", "GET", "/search", "q",
         "搜索参数被原样反射到 HTML 上下文。", "xss",
         "curl 'https://demo.lab.local/search?q=<script>alert(1)</script>'"),
        ("Open Redirect", "MEDIUM", "GET", "/redirect", "next",
         "next 参数允许跳转到任意外部地址，可能被用于钓鱼。", "redirect",
         "curl 'https://demo.lab.local/redirect?next=https://evil.example/'"),
        ("HTTP Secure Headers", "LOW", "GET", "/", "",
         "缺少 Strict-Transport-Security 响应头。", "http_headers",
         "curl -I https://demo.lab.local/"),
    ]
    for cat, lvl, method, path, param, info, module, curl in dast_samples:
        issue = DastIssue(
            task_id=dast.id,
            category=cat, level=lvl, method=method, path=path,
            parameter=param or None, info=info, module=module,
            curl_command=curl,
        )
        db.session.add(issue)
        db.session.flush()
        if cat in {"SQL Injection", "Cross Site Scripting"}:
            db.session.add(AiIssueInsight(
                task_id=dast.id,
                task_type=TaskType.DAST.value,
                issue_id=issue.id,
                issue_fingerprint=f"fp-{issue.id}",
                model_name="demo-model",
                meaning=f"{cat}：参数未充分校验即返回到响应中。",
                impact="可造成数据泄露或会话劫持。",
                fix="启用参数化查询/上下文敏感输出编码，并增加 WAF 规则。",
                verify="使用相同 payload 重放验证响应不再回显或注入失败。",
            ))

    # ---- SCA ----
    sca = Task(
        user_id=user.id,
        task_type=TaskType.SCA,
        task_name="演示项目 · 依赖审计",
        status=TaskStatus.SUCCESS,
        target_path="/srv/demo/backend/requirements.txt",
        scanner_engine="pip-audit",
        duration_ms=8_400,
        result_summary="pip-audit 扫描完成：发现 6 个漏洞，覆盖 28 个依赖",
    )
    db.session.add(sca)
    db.session.flush()
    db.session.add(ScaResult(
        task_id=sca.id,
        dependency_count=28, vulnerability_count=6, fixable_count=5,
        package_distribution=json.dumps({
            "flask": 2, "requests": 1, "jinja2": 1, "urllib3": 1, "pyyaml": 1,
        }),
        severity_distribution=json.dumps({"HIGH": 3, "MEDIUM": 2, "LOW": 1}),
        summary="pip-audit 演示",
    ))
    sca_samples = [
        ("flask", "0.12.0", "GHSA-562c-5r94-xh97", ["CVE-2018-1000656"], ["0.12.3"],
         "Flask 旧版本在调试模式下会泄露未授权页面信息，可被远程触发。", "HIGH"),
        ("flask", "0.12.0", "GHSA-m2qf-hxjv-5gpq", [], ["1.0"],
         "Flask 受影响版本存在 cookie 序列化漏洞。", "MEDIUM"),
        ("requests", "2.18.0", "GHSA-x84v-xcm2-53pg", ["CVE-2018-18074"], ["2.20.0"],
         "请求库在重定向时会暴露认证头，建议升级。", "HIGH"),
        ("jinja2", "2.8", "GHSA-462w-v97r-4m45", ["CVE-2019-10906"], ["2.10.1"],
         "Jinja2 沙箱逃逸漏洞，可被构造模板触发。", "HIGH"),
        ("urllib3", "1.24", "GHSA-mh33-7rrq-662w", [], ["1.24.2"],
         "urllib3 CRLF 注入漏洞。", "MEDIUM"),
        ("pyyaml", "5.1", "GHSA-3pqx-4fqf-j49f", ["CVE-2020-1747"], ["5.3.1"],
         "PyYAML FullLoader 反序列化漏洞，可被恶意 YAML 触发任意代码执行。", "LOW"),
    ]
    for pkg, ver, vid, aliases, fixes, desc, sev in sca_samples:
        db.session.add(ScaIssue(
            task_id=sca.id,
            package_name=pkg, installed_version=ver,
            vulnerability_id=vid,
            aliases=json.dumps(aliases),
            fix_versions=json.dumps(fixes),
            description=desc, severity=sev,
        ))

    db.session.commit()
    return sast, dast, sca


def main():
    app = create_app("testing")
    out_dir = ROOT / "tmp"
    out_dir.mkdir(exist_ok=True)
    with app.app_context():
        sast, dast, sca = seed(app)
        for task, key in ((sast, "sast"), (dast, "dast"), (sca, "sca")):
            html = build_report_html(task)
            (out_dir / f"{key}_demo.html").write_text(html, encoding="utf-8")
            print(f"[OK] HTML => tmp/{key}_demo.html ({len(html)} chars)")
            try:
                pdf = build_report_pdf(task)
                (out_dir / f"{key}_demo.pdf").write_bytes(pdf)
                print(f"[OK] PDF  => tmp/{key}_demo.pdf ({len(pdf)} bytes)")
            except Exception as exc:  # noqa: BLE001
                print(f"[SKIP PDF] {key}: {exc}")


if __name__ == "__main__":
    main()

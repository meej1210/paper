"""中文术语映射。镜像 frontend/src/utils/report-labels.ts。

只把人类可读的标签翻成中文，CVE/CWE/Bandit/Semgrep 规则 ID 保留英文标识符。
"""
from __future__ import annotations

import re
from typing import Optional

SEVERITY_ZH: dict[str, str] = {
    "CRITICAL": "严重",
    "HIGH": "高危",
    "MEDIUM": "中危",
    "LOW": "低危",
    "INFO": "提示",
    "UNKNOWN": "未知",
}

CONFIDENCE_ZH: dict[str, str] = {
    "HIGH": "高",
    "MEDIUM": "中",
    "LOW": "低",
    "UNDEFINED": "未定",
    "UNKNOWN": "未知",
}

OWASP_ZH: dict[str, str] = {
    "A01:2021": "权限控制失效",
    "A02:2021": "加密机制失效",
    "A03:2021": "注入",
    "A04:2021": "不安全设计",
    "A05:2021": "安全配置错误",
    "A06:2021": "易受攻击和过时的组件",
    "A07:2021": "身份认证失败",
    "A08:2021": "软件和数据完整性失败",
    "A09:2021": "安全日志与监控失效",
    "A10:2021": "服务端请求伪造",
    "Uncategorized": "未分类",
    "UNCATEGORIZED": "未分类",
    "Other": "其他",
}

SAST_RULE_ZH: dict[str, str] = {
    "B101": "不安全的 assert 使用",
    "B102": "exec 调用",
    "B103": "不安全的文件权限",
    "B104": "绑定全部网络接口",
    "B105": "硬编码密码字符串",
    "B106": "函数参数中的硬编码密码",
    "B107": "默认参数中的硬编码密码",
    "B108": "硬编码临时目录",
    "B110": "try-except 忽略异常",
    "B112": "try-except 中 continue",
    "B201": "Flask 调试模式开启",
    "B202": "tarfile 解包不安全",
    "B301": "pickle 反序列化",
    "B302": "marshal 反序列化",
    "B303": "MD5 弱哈希",
    "B304": "不安全的加密算法",
    "B305": "不安全的加密模式",
    "B306": "mktemp 不安全",
    "B307": "eval 调用",
    "B308": "mark_safe 调用",
    "B310": "urlopen 调用风险",
    "B311": "不安全的随机数",
    "B312": "telnetlib 风险",
    "B313": "xml.etree.cElementTree 风险",
    "B314": "xml.etree.ElementTree 风险",
    "B315": "xml.sax expatreader 风险",
    "B316": "xml.sax 风险",
    "B317": "xml.dom.minidom 风险",
    "B318": "xml.dom.pulldom 风险",
    "B319": "xmlrpc 风险",
    "B320": "xslt 风险",
    "B321": "不安全的 ftplib",
    "B322": "Python2 input 风险",
    "B323": "未校验的 SSL 上下文",
    "B324": "弱哈希算法（hashlib）",
    "B325": "tempnam 不安全",
    "B401": "导入 telnetlib",
    "B402": "导入 ftplib",
    "B403": "导入 pickle",
    "B404": "导入 subprocess",
    "B405": "导入 xml.etree",
    "B406": "导入 xml.sax",
    "B407": "导入 xml.expat",
    "B408": "导入 xml.minidom",
    "B409": "导入 xml.pulldom",
    "B411": "导入 xmlrpclib",
    "B412": "导入 httpoxy",
    "B501": "关闭证书校验",
    "B502": "不安全的 SSL 版本",
    "B503": "不安全的 SSL 默认值",
    "B504": "未指定 SSL 版本",
    "B505": "弱加密密钥",
    "B506": "不安全的 YAML 加载",
    "B507": "未校验 SSH 主机密钥",
    "B508": "SNMP 不安全版本",
    "B509": "SNMP 弱凭据",
    "B601": "paramiko 不安全调用",
    "B602": "shell=True 命令注入风险",
    "B603": "subprocess 调用",
    "B604": "其他函数 shell=True 风险",
    "B605": "通过 shell 启动进程",
    "B606": "不通过 shell 启动进程",
    "B607": "不完整路径启动进程",
    "B608": "硬编码 SQL 拼接",
    "B609": "Linux 命令通配符注入",
    "B610": "django extra 调用风险",
    "B611": "django rawsql 调用风险",
    "B612": "logging.config.listen 不安全",
    "B613": "Trojan Source 字符",
    "B701": "Jinja2 autoescape 关闭",
    "B702": "Mako 模板使用风险",
    "B703": "Django mark_safe 调用",
}

SAST_RULE_NAME_ZH: dict[str, str] = {
    "hardcoded_password_string": "硬编码密码字符串",
    "hardcoded_password_funcarg": "函数参数中的硬编码密码",
    "hardcoded_password_default": "默认参数中的硬编码密码",
    "hardcoded_tmp_directory": "硬编码临时目录",
    "hardcoded_bind_all_interfaces": "绑定全部网络接口",
    "hashlib": "弱哈希算法（hashlib）",
    "blacklist": "不安全 import",
    "pickle": "pickle 反序列化",
    "yaml_load": "不安全的 YAML 加载",
    "exec_used": "exec 调用",
    "eval": "eval 调用",
    "flask_debug_true": "Flask 调试模式开启",
    "subprocess_popen_with_shell_equals_true": "shell=True 命令注入风险",
    "subprocess_without_shell_equals_true": "subprocess 调用",
    "any_other_function_with_shell_equals_true": "其他函数 shell=True 风险",
    "start_process_with_a_shell": "通过 shell 启动进程",
    "start_process_with_partial_path": "不完整路径启动进程",
    "hardcoded_sql_expressions": "硬编码 SQL 拼接",
    "request_with_no_cert_validation": "关闭证书校验",
    "assert_used": "不安全的 assert 使用",
    "try_except_pass": "try-except 忽略异常",
    "weak_cryptographic_key": "弱加密密钥",
}

DAST_CATEGORY_ZH: dict[str, str] = {
    "Unencrypted Channels": "未加密传输通道",
    "Clickjacking Protection": "点击劫持防护",
    "MIME Type Confusion": "MIME 类型混淆",
    "Backup file": "备份文件泄露",
    "Blind SQL Injection": "盲注 SQL",
    "Buffer Overflow": "缓冲区溢出",
    "Command execution": "命令执行",
    "Cross Site Scripting": "跨站脚本（XSS）",
    "CRLF Injection": "CRLF 注入",
    "Content Security Policy Configuration": "CSP 配置缺陷",
    "Cookie value not protected": "Cookie 值未保护",
    "Cookie not secure": "Cookie Secure 标志缺失",
    "Cookie HttpOnly Flag": "Cookie HttpOnly 标志缺失",
    "HttpOnly Flag cookie": "Cookie HttpOnly 标志缺失",
    "Secure Flag cookie": "Cookie Secure 标志缺失",
    "CSP_Config": "CSP 配置缺陷",
    "Cross Site Request Forgery": "跨站请求伪造（CSRF）",
    "Fingerprint web technology": "Web 技术指纹泄露",
    "HTTP Secure Headers": "HTTP 安全响应头",
    "HTTP Strict Transport Security": "HSTS 配置缺陷",
    "Internal Server Error": "内部服务器错误",
    "Open Redirect": "开放重定向",
    "Path Traversal": "路径穿越",
    "Permanent XSS": "存储型 XSS",
    "Reflected Cross Site Scripting": "反射型 XSS",
    "Resource Consumption": "资源消耗",
    "Server Side Request Forgery": "服务端请求伪造（SSRF）",
    "SQL Injection": "SQL 注入",
    "Weak credentials": "弱凭据",
    "XML External Entity": "XXE 漏洞",
    "Subresource Integrity": "子资源完整性缺失",
    "Cleartext Submission of Password": "密码明文传输",
}

# 章节里需要的工具引擎说明
ENGINE_ZH: dict[str, str] = {
    "bandit": "Bandit",
    "semgrep": "Semgrep",
    "wapiti": "Wapiti3",
    "wapiti3": "Wapiti3",
    "pip-audit": "pip-audit",
    "pip_audit": "pip-audit",
}

ENGINE_DESCRIPTION_ZH: dict[str, str] = {
    "bandit": "OpenStack 推出的 Python AST 静态审计工具，基于规则库识别常见安全反模式。",
    "semgrep": "基于模式匹配的多语言静态分析引擎，规则可读、覆盖广。",
    "wapiti": "开源黑盒动态扫描工具，通过爬取目标后注入 payload 探测漏洞。",
    "wapiti3": "开源黑盒动态扫描工具，通过爬取目标后注入 payload 探测漏洞。",
    "pip-audit": "PyPA 维护的 Python 依赖审计器，比对 OSV / PyPI Advisory 数据库。",
    "pip_audit": "PyPA 维护的 Python 依赖审计器，比对 OSV / PyPI Advisory 数据库。",
}

TASK_TYPE_ZH: dict[str, str] = {
    "SAST": "静态代码审计",
    "DAST": "动态应用扫描",
    "SCA": "依赖组件审计",
}

TASK_TYPE_FULL_ZH: dict[str, str] = {
    "SAST": "SAST · 静态代码安全审计报告",
    "DAST": "DAST · 动态应用安全扫描报告",
    "SCA": "SCA · 软件依赖成分审计报告",
}

STATUS_ZH: dict[str, str] = {
    "PENDING": "排队中",
    "RUNNING": "执行中",
    "SUCCESS": "执行成功",
    "FAILED": "执行失败",
    "TIMEOUT": "执行超时",
    "CANCELLED": "已取消",
}

TARGET_POLICY_ZH: dict[str, str] = {
    "loopback": "本地回环",
    "allowed_host": "允许的内网主机",
    "public_allowed": "已授权外网目标",
}

RISK_BAND_ZH: dict[str, str] = {
    "CRITICAL": "严重",
    "HIGH": "高",
    "MEDIUM": "中",
    "LOW": "低",
    "SAFE": "安全",
}

RISK_BAND_DESC_ZH: dict[str, str] = {
    "CRITICAL": "存在多个严重或高危问题，需立即响应。",
    "HIGH": "存在显著高危问题，建议优先排查。",
    "MEDIUM": "存在中等风险，建议纳入近期修复计划。",
    "LOW": "仅存在少量低危项，建议在下个迭代清理。",
    "SAFE": "未发现明显风险，维持基线监控即可。",
}

HASH_PREFIX_PATTERN = re.compile(r"^[0-9a-fA-F]{16,}-")


def severity_label(value: Optional[str]) -> str:
    if not value:
        return "未知"
    return SEVERITY_ZH.get(str(value).upper(), str(value))


def confidence_label(value: Optional[str]) -> str:
    if not value:
        return "-"
    return CONFIDENCE_ZH.get(str(value).upper(), str(value))


def owasp_label(value: Optional[str]) -> str:
    if not value:
        return "未分类"
    raw = str(value)
    if raw in OWASP_ZH:
        return OWASP_ZH[raw]
    match = re.match(r"^(A\d{1,2}:\d{4})", raw)
    if match:
        key = match.group(1)
        zh = OWASP_ZH.get(key)
        return f"{key} {zh}" if zh else raw
    return raw


def sast_rule_label(test_id: Optional[str], test_name: Optional[str] = None) -> str:
    if not test_id and not test_name:
        return "未命名规则"

    # 1) 先按 test_id 命中
    if test_id:
        key = str(test_id).upper()
        if key in SAST_RULE_ZH:
            return f"{key} {SAST_RULE_ZH[key]}"

    # 2) 按 test_name 命中
    if test_name:
        name_key = str(test_name).lower()
        if name_key in SAST_RULE_NAME_ZH:
            return f"{test_id} {SAST_RULE_NAME_ZH[name_key]}" if test_id else SAST_RULE_NAME_ZH[name_key]

    # 3) 兼容 "B602:subprocess_popen_with_shell_equals_true" 之类的复合值
    raw = str(test_id or test_name or "")
    if ":" in raw:
        prefix, suffix = raw.split(":", 1)
        zh_id = SAST_RULE_ZH.get(prefix.upper())
        if zh_id:
            return f"{prefix.upper()} {zh_id}"
        zh_name = SAST_RULE_NAME_ZH.get(suffix.strip().lower())
        if zh_name:
            return f"{prefix.upper()} {zh_name}"

    return raw or "未命名规则"


def dast_category_label(value: Optional[str]) -> str:
    if not value:
        return "未命名漏洞项"
    raw = str(value)
    return DAST_CATEGORY_ZH.get(raw, raw)


def display_filename(value: Optional[str]) -> str:
    if not value:
        return "-"
    raw = str(value).replace("\\", "/")
    basename = raw.rsplit("/", 1)[-1] or raw
    return HASH_PREFIX_PATTERN.sub("", basename)


def engine_label(value: Optional[str]) -> str:
    if not value:
        return "-"
    key = str(value).lower()
    return ENGINE_ZH.get(key, str(value))


def engine_description(value: Optional[str]) -> str:
    if not value:
        return "-"
    return ENGINE_DESCRIPTION_ZH.get(str(value).lower(), "-")


def task_type_label(value: Optional[str], *, full: bool = False) -> str:
    if not value:
        return "安全扫描报告"
    key = str(value).upper()
    source = TASK_TYPE_FULL_ZH if full else TASK_TYPE_ZH
    return source.get(key, key)


def status_label(value: Optional[str]) -> str:
    if not value:
        return "-"
    return STATUS_ZH.get(str(value).upper(), str(value))


def target_policy_label(value: Optional[str]) -> str:
    if not value:
        return "-"
    return TARGET_POLICY_ZH.get(str(value).lower(), str(value))


def risk_band_label(value: Optional[str]) -> str:
    if not value:
        return "未知"
    return RISK_BAND_ZH.get(str(value).upper(), str(value))


def risk_band_description(value: Optional[str]) -> str:
    if not value:
        return ""
    return RISK_BAND_DESC_ZH.get(str(value).upper(), "")

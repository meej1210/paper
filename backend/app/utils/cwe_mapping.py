# Bandit test_id → (CWE, OWASP Top 10 2021 category)
# Source: https://bandit.readthedocs.io/ + https://owasp.org/Top10/
BANDIT_CWE_MAP: dict[str, dict] = {
    "B101": {"cwe": "CWE-259", "owasp": "A07:2021-Identification and Authentication Failures", "category": "assert"},
    "B102": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "exec"},
    "B103": {"cwe": "CWE-676", "owasp": "A04:2021-Insecure Design", "category": "setattr"},
    "B104": {"cwe": "CWE-200", "owasp": "A01:2021-Broken Access Control", "category": "hardcoded_bind_all_interfaces"},
    "B105": {"cwe": "CWE-259", "owasp": "A07:2021-Identification and Authentication Failures", "category": "hardcoded_password_string"},
    "B106": {"cwe": "CWE-259", "owasp": "A07:2021-Identification and Authentication Failures", "category": "hardcoded_password_funcarg"},
    "B107": {"cwe": "CWE-259", "owasp": "A07:2021-Identification and Authentication Failures", "category": "hardcoded_password_default"},
    "B108": {"cwe": "CWE-377", "owasp": "A02:2021-Cryptographic Failures", "category": "hardcoded_tmp"},
    "B110": {"cwe": "CWE-390", "owasp": "A04:2021-Insecure Design", "category": "try_except_pass"},
    "B112": {"cwe": "CWE-390", "owasp": "A04:2021-Insecure Design", "category": "try_except_continue"},
    "B201": {"cwe": "CWE-94",  "owasp": "A05:2021-Security Misconfiguration", "category": "flask_debug_true"},
    "B202": {"cwe": "CWE-285", "owasp": "A01:2021-Broken Access Control", "category": "tarfile_unsafe_members"},
    "B301": {"cwe": "CWE-502", "owasp": "A08:2021-Software and Data Integrity Failures", "category": "pickle"},
    "B302": {"cwe": "CWE-502", "owasp": "A08:2021-Software and Data Integrity Failures", "category": "marshal"},
    "B303": {"cwe": "CWE-328", "owasp": "A02:2021-Cryptographic Failures", "category": "md5"},
    "B304": {"cwe": "CWE-328", "owasp": "A02:2021-Cryptographic Failures", "category": "ciphers"},
    "B305": {"cwe": "CWE-328", "owasp": "A02:2021-Cryptographic Failures", "category": "cipher_modes"},
    "B306": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "mktemp_q"},
    "B307": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "eval"},
    "B308": {"cwe": "CWE-79",  "owasp": "A03:2021-Injection", "category": "mark_safe"},
    "B310": {"cwe": "CWE-22",  "owasp": "A01:2021-Broken Access Control", "category": "urlopen"},
    "B311": {"cwe": "CWE-330", "owasp": "A02:2021-Cryptographic Failures", "category": "random"},
    "B312": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "telnetlib"},
    "B313": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_cElementTree"},
    "B314": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_ElementTree"},
    "B315": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_expatreader"},
    "B316": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_sax"},
    "B317": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_minidom"},
    "B318": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_pulldom"},
    "B319": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "xml_bad_xmlrpc"},
    "B320": {"cwe": "CWE-614", "owasp": "A02:2021-Cryptographic Failures", "category": "xsl_t"},
    "B321": {"cwe": "CWE-319", "owasp": "A02:2021-Cryptographic Failures", "category": "ftplib"},
    "B322": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "input"},
    "B323": {"cwe": "CWE-295", "owasp": "A02:2021-Cryptographic Failures", "category": "ssl_bad_version"},
    "B324": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "hashlib"},
    "B501": {"cwe": "CWE-295", "owasp": "A02:2021-Cryptographic Failures", "category": "request_with_no_cert_validation"},
    "B502": {"cwe": "CWE-322", "owasp": "A02:2021-Cryptographic Failures", "category": "ssl_with_bad_version"},
    "B503": {"cwe": "CWE-295", "owasp": "A02:2021-Cryptographic Failures", "category": "ssl_with_bad_defaults"},
    "B504": {"cwe": "CWE-295", "owasp": "A02:2021-Cryptographic Failures", "category": "ssl_with_no_version"},
    "B505": {"cwe": "CWE-327", "owasp": "A02:2021-Cryptographic Failures", "category": "weak_cryptographic_key"},
    "B506": {"cwe": "CWE-502", "owasp": "A08:2021-Software and Data Integrity Failures", "category": "yaml_load"},
    "B507": {"cwe": "CWE-798", "owasp": "A07:2021-Identification and Authentication Failures", "category": "ssh_no_host_key_verification"},
    "B508": {"cwe": "CWE-676", "owasp": "A04:2021-Insecure Design", "category": "snmp_insecure_version"},
    "B509": {"cwe": "CWE-676", "owasp": "A04:2021-Insecure Design", "category": "snmp_weak_credentials"},
    "B601": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "paramiko_calls"},
    "B602": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "subprocess_popen_with_shell_equals_true"},
    "B603": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "subprocess_without_shell_equals_true"},
    "B604": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "any_other_function_with_shell_equals_true"},
    "B605": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "start_process_with_a_shell"},
    "B606": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "start_process_with_no_shell"},
    "B607": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "start_process_with_partial_path"},
    "B608": {"cwe": "CWE-89",  "owasp": "A03:2021-Injection", "category": "hardcoded_sql_expressions"},
    "B609": {"cwe": "CWE-78",  "owasp": "A03:2021-Injection", "category": "linux_commands_wildcard_injection"},
    "B610": {"cwe": "CWE-79",  "owasp": "A03:2021-Injection", "category": "django_extra_used"},
    "B611": {"cwe": "CWE-89",  "owasp": "A03:2021-Injection", "category": "django_rawsql_used"},
    "B612": {"cwe": "CWE-798", "owasp": "A07:2021-Identification and Authentication Failures", "category": "logging_config_insecure_listen"},
    "B613": {"cwe": "CWE-676", "owasp": "A04:2021-Insecure Design", "category": "trojansource"},
}

# Wapiti category → (CWE, OWASP Top 10 2021)
WAPITI_CWE_MAP: dict[str, dict] = {
    "SQL Injection":                {"cwe": "CWE-89",  "owasp": "A03:2021-Injection"},
    "Blind SQL Injection":          {"cwe": "CWE-89",  "owasp": "A03:2021-Injection"},
    "XSS":                          {"cwe": "CWE-79",  "owasp": "A03:2021-Injection"},
    "Stored XSS":                   {"cwe": "CWE-79",  "owasp": "A03:2021-Injection"},
    "Reflected XSS":                {"cwe": "CWE-79",  "owasp": "A03:2021-Injection"},
    "DOM XSS":                      {"cwe": "CWE-79",  "owasp": "A03:2021-Injection"},
    "Path Traversal":               {"cwe": "CWE-22",  "owasp": "A01:2021-Broken Access Control"},
    "Command Execution":            {"cwe": "CWE-78",  "owasp": "A03:2021-Injection"},
    "Code Execution":               {"cwe": "CWE-94",  "owasp": "A03:2021-Injection"},
    "File Upload":                  {"cwe": "CWE-434", "owasp": "A04:2021-Insecure Design"},
    "CRLF Injection":               {"cwe": "CWE-113", "owasp": "A03:2021-Injection"},
    "Open Redirect":                {"cwe": "CWE-601", "owasp": "A01:2021-Broken Access Control"},
    "Unencrypted Channels":         {"cwe": "CWE-319", "owasp": "A02:2021-Cryptographic Failures"},
    "Clickjacking Protection":      {"cwe": "CWE-1021","owasp": "A05:2021-Security Misconfiguration"},
    "MIME Type Confusion":          {"cwe": "CWE-693", "owasp": "A05:2021-Security Misconfiguration"},
    "Cookies Without Secure Flag":  {"cwe": "CWE-614", "owasp": "A05:2021-Security Misconfiguration"},
    "Cookies Without HttpOnly Flag": {"cwe": "CWE-1004","owasp": "A05:2021-Security Misconfiguration"},
    "Insecure CORS":                {"cwe": "CWE-942", "owasp": "A05:2021-Security Misconfiguration"},
    "CSRF":                         {"cwe": "CWE-352", "owasp": "A01:2021-Broken Access Control"},
    "Broken Auth":                  {"cwe": "CWE-287", "owasp": "A07:2021-Identification and Authentication Failures"},
    "Weak Password":                {"cwe": "CWE-521", "owasp": "A07:2021-Identification and Authentication Failures"},
    "Server Side Request Forgery":  {"cwe": "CWE-918", "owasp": "A10:2021-Server-Side Request Forgery"},
    "XXE":                          {"cwe": "CWE-611", "owasp": "A05:2021-Security Misconfiguration"},
    "Information Disclosure":       {"cwe": "CWE-200", "owasp": "A01:2021-Broken Access Control"},
    "Internal Server Error":        {"cwe": "CWE-209", "owasp": "A04:2021-Insecure Design"},
    "Potential SSRF":               {"cwe": "CWE-918", "owasp": "A10:2021-Server-Side Request Forgery"},
}

OWASP_TOP_10 = [
    "A01:2021-Broken Access Control",
    "A02:2021-Cryptographic Failures",
    "A03:2021-Injection",
    "A04:2021-Insecure Design",
    "A05:2021-Security Misconfiguration",
    "A06:2021-Vulnerable and Outdated Components",
    "A07:2021-Identification and Authentication Failures",
    "A08:2021-Software and Data Integrity Failures",
    "A09:2021-Security Logging and Monitoring Failures",
    "A10:2021-Server-Side Request Forgery",
]


def lookup_bandit(test_id: str | None) -> dict:
    if not test_id:
        return {"cwe": None, "owasp": None, "category": None}
    entry = BANDIT_CWE_MAP.get(test_id)
    if entry:
        return entry
    return {"cwe": None, "owasp": None, "category": None}


def lookup_wapiti(category: str | None) -> dict:
    if not category:
        return {"cwe": None, "owasp": None, "category": None}
    entry = WAPITI_CWE_MAP.get(category)
    if entry:
        return {**entry, "category": category}
    # Fallback: try partial match
    for key, val in WAPITI_CWE_MAP.items():
        if key.lower() in category.lower() or category.lower() in key.lower():
            return {**val, "category": category}
    return {"cwe": None, "owasp": None, "category": category}


def build_owasp_distribution(issues: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for issue in issues:
        owasp = issue.get("owasp") or "Uncategorized"
        counts[owasp] = counts.get(owasp, 0) + 1
    total = sum(counts.values()) or 1
    return sorted(
        [{"label": k, "count": v, "percent": round(v / total * 100)} for k, v in counts.items()],
        key=lambda x: -x["count"],
    )

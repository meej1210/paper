// Centralised Chinese localisation helpers for the security report UI.
// Imported by report components and TaskDetailView to keep all labels consistent.

const SEVERITY_ZH: Record<string, string> = {
  CRITICAL: "严重",
  HIGH: "高危",
  MEDIUM: "中危",
  LOW: "低危",
  INFO: "提示",
  UNKNOWN: "未知",
};

export function severityLabel(value?: string | null): string {
  if (!value) return "未知";
  const key = String(value).toUpperCase();
  return SEVERITY_ZH[key] || String(value);
}

const CONFIDENCE_ZH: Record<string, string> = {
  HIGH: "高",
  MEDIUM: "中",
  LOW: "低",
  UNDEFINED: "未定",
  UNKNOWN: "未知",
};

export function confidenceLabel(value?: string | null): string {
  if (!value) return "-";
  const key = String(value).toUpperCase();
  return CONFIDENCE_ZH[key] || String(value);
}

const OWASP_ZH: Record<string, string> = {
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
  Uncategorized: "未分类",
  UNCATEGORIZED: "未分类",
  Other: "其他",
};

export function owaspLabel(value?: string | null): string {
  if (!value) return "未分类";
  const raw = String(value);
  if (OWASP_ZH[raw]) return OWASP_ZH[raw];
  const match = raw.match(/^(A\d{1,2}:\d{4})/);
  if (match) {
    const key = match[1];
    const zh = OWASP_ZH[key];
    return zh ? `${key} ${zh}` : raw;
  }
  return raw;
}

const SAST_RULE_ZH: Record<string, string> = {
  B101: "不安全的 assert 使用",
  B102: "exec 调用",
  B103: "不安全的文件权限",
  B104: "绑定全部网络接口",
  B105: "硬编码密码字符串",
  B106: "函数参数中的硬编码密码",
  B107: "默认参数中的硬编码密码",
  B108: "硬编码临时目录",
  B110: "try-except 忽略异常",
  B112: "try-except 中 continue",
  B201: "Flask 调试模式开启",
  B301: "pickle 反序列化",
  B302: "marshal 反序列化",
  B303: "MD5 弱哈希",
  B304: "不安全的加密算法",
  B305: "不安全的加密模式",
  B306: "mktemp 不安全",
  B307: "eval 调用",
  B308: "mark_safe 调用",
  B311: "不安全的随机数",
  B321: "不安全的 ftplib",
  B322: "Python2 input 风险",
  B323: "未校验的 SSL 上下文",
  B324: "弱哈希算法（hashlib）",
  B325: "tempnam 不安全",
  B401: "导入 telnetlib",
  B402: "导入 ftplib",
  B403: "导入 pickle",
  B404: "导入 subprocess",
  B405: "导入 xml.etree",
  B406: "导入 xml.sax",
  B407: "导入 xml.expat",
  B408: "导入 xml.minidom",
  B409: "导入 xml.pulldom",
  B411: "导入 xmlrpclib",
  B412: "导入 httpoxy",
  B501: "关闭证书校验",
  B502: "不安全的 SSL 版本",
  B503: "不安全的 SSL 默认值",
  B504: "未指定 SSL 版本",
  B505: "弱加密密钥",
  B506: "不安全的 YAML 加载",
  B507: "未校验 SSH 主机密钥",
  B601: "paramiko 不安全调用",
  B602: "shell=True 命令注入风险",
  B603: "subprocess 调用",
  B604: "其他函数 shell=True 风险",
  B605: "通过 shell 启动进程",
  B606: "不通过 shell 启动进程",
  B607: "不完整路径启动进程",
  B608: "硬编码 SQL 拼接",
  B609: "Linux 命令通配符注入",
  B701: "Jinja2 autoescape 关闭",
  B702: "Mako 模板使用风险",
  B703: "Django mark_safe 调用",
};

const SAST_RULE_NAME_ZH: Record<string, string> = {
  hardcoded_password_string: "硬编码密码字符串",
  hardcoded_password_funcarg: "函数参数中的硬编码密码",
  hardcoded_password_default: "默认参数中的硬编码密码",
  hardcoded_tmp_directory: "硬编码临时目录",
  hardcoded_bind_all_interfaces: "绑定全部网络接口",
  hashlib: "弱哈希算法（hashlib）",
  blacklist: "不安全 import",
  pickle: "pickle 反序列化",
  yaml_load: "不安全的 YAML 加载",
  exec_used: "exec 调用",
  eval: "eval 调用",
  flask_debug_true: "Flask 调试模式开启",
  subprocess_popen_with_shell_equals_true: "shell=True 命令注入风险",
  subprocess_without_shell_equals_true: "subprocess 调用",
  any_other_function_with_shell_equals_true: "其他函数 shell=True 风险",
  start_process_with_a_shell: "通过 shell 启动进程",
  start_process_with_partial_path: "不完整路径启动进程",
  hardcoded_sql_expressions: "硬编码 SQL 拼接",
  request_with_no_cert_validation: "关闭证书校验",
  assert_used: "不安全的 assert 使用",
  try_except_pass: "try-except 忽略异常",
  weak_cryptographic_key: "弱加密密钥",
};

export function sastRuleLabel(value?: string | null): string {
  if (!value) return "未命名规则";
  const raw = String(value);
  const colonIdx = raw.indexOf(":");
  if (colonIdx === -1) {
    const key = raw.toUpperCase();
    if (SAST_RULE_ZH[key]) return `${key} ${SAST_RULE_ZH[key]}`;
    const lower = raw.toLowerCase();
    if (SAST_RULE_NAME_ZH[lower]) return SAST_RULE_NAME_ZH[lower];
    return raw;
  }
  const id = raw.slice(0, colonIdx).toUpperCase();
  const name = raw.slice(colonIdx + 1).trim();
  const zhById = SAST_RULE_ZH[id];
  if (zhById) return `${id} ${zhById}`;
  const zhByName = SAST_RULE_NAME_ZH[name.toLowerCase()];
  if (zhByName) return `${id} ${zhByName}`;
  return raw;
}

const HASH_PREFIX_PATTERN = /^[0-9a-f]{16,}-/i;

export function displayFileName(value?: string | null): string {
  if (!value) return "-";
  const raw = String(value);
  const basename = raw.split(/[\\/]/).pop() || raw;
  return basename.replace(HASH_PREFIX_PATTERN, "");
}

const DAST_CATEGORY_ZH: Record<string, string> = {
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
  CSP_Config: "CSP 配置缺陷",
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
};

export function dastCategoryLabel(value?: string | null): string {
  if (!value) return "未命名漏洞项";
  const raw = String(value);
  return DAST_CATEGORY_ZH[raw] || raw;
}

# SCA 测试用例与演示说明

## 1. 文档目标

本文档用于演示 DevSecOps 平台的 SCA 软件成分分析能力，重点展示平台如何发现 Python 依赖中的已知漏洞，并给出漏洞 ID、影响组件、当前版本和可修复版本。

适用场景：

- 论文功能验证
- 答辩现场演示
- 项目联调验收
- CI/CD 安全门禁展示

## 2. 测试用例概览

| 用例编号 | 用例名称 | 测试目标 | 测试数据 | 预期结果 |
|---|---|---|---|---|
| SCA-001 | 含漏洞依赖清单扫描 | 验证平台能识别旧版本 Python 依赖中的已知漏洞 | `tests/sca_demo/requirements-vulnerable.txt` | 任务执行成功，详情页展示漏洞 ID、依赖包、当前版本和修复版本 |
| SCA-002 | SCA 报告导出 | 验证 SCA 结果可导出报告 | SCA-001 产生的任务 | 可下载 JSON/HTML/PDF 报告，报告内容与详情页一致 |
| SCA-003 | CI/CD 依赖漏洞门禁 | 验证存在可修复漏洞时门禁失败 | `tests/sca_demo/requirements-vulnerable.txt` | 脚本返回退出码 `3`，并生成摘要和报告文件 |

## 3. 前置条件

1. 平台服务已启动：

```powershell
cd D:\ziliao\dev
powershell -ExecutionPolicy Bypass -File .\start_demo_env.ps1
```

2. 可以访问前端和后端：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:5000/api/health
```

3. 已有可登录账号。演示账号可使用：

```text
管理员：admin@qq.com / admin
```

4. 后端环境中已安装 `pip-audit`。如未安装，SCA 任务可能失败，答辩时可解释为扫描器运行环境依赖未就绪。

## 4. 测试数据

测试文件：

```text
tests/sca_demo/requirements-vulnerable.txt
```

文件内容包含多个旧版本 Python 依赖：

```text
Django==2.2.0
Flask==0.12.2
requests==2.19.1
PyYAML==5.1
Jinja2==2.10
```

这些依赖版本仅用于 SCA 演示，不应安装到真实业务环境。

## 5. Web 页面演示步骤

### 5.1 创建 SCA 扫描任务

1. 打开前端登录页：

```text
http://127.0.0.1:5173/login
```

2. 使用管理员账号登录。
3. 进入“新建扫描”页面。
4. 扫描类型选择 `SCA`。
5. 上传文件：

```text
tests/sca_demo/requirements-vulnerable.txt
```

6. 任务名称建议填写：

```text
SCA演示-旧版本依赖漏洞扫描
```

7. 点击创建任务，进入任务详情或任务列表等待执行完成。

### 5.2 查看扫描结果

任务完成后，重点展示以下字段：

- 任务类型：`SCA`
- 任务状态：`SUCCESS`
- 依赖数量
- 漏洞数量
- 可修复漏洞数量
- 包名
- 当前版本
- 漏洞 ID
- 修复版本

展示重点：

- SCA 不是扫描源代码逻辑，而是扫描第三方依赖组件。
- 同一个依赖可能对应多个漏洞 ID。
- “可修复版本”可以直接支撑后续依赖升级整改。

### 5.3 导出报告

在任务详情页点击报告导出，建议按以下顺序展示：

1. JSON 报告：体现平台保留原始结构化结果，便于系统集成。
2. HTML 报告：适合浏览器查看和论文截图。
3. PDF 报告：适合归档和答辩材料展示。

如果 PDF 导出失败，优先说明这是本机 WeasyPrint/GTK/Pango 等原生依赖问题，不影响 SCA 扫描链路本身。可改为展示 HTML 或 JSON 报告。

## 6. CI/CD 命令行演示

先设置账号环境变量：

```powershell
cd D:\ziliao\dev
$env:DEVSECOPS_USER="admin@qq.com"
$env:DEVSECOPS_PASSWORD="admin"
```

执行 SCA 质量门禁：

```powershell
.\scripts\ci_security_scan.ps1 `
  -BaseUrl http://127.0.0.1:5000/api `
  -Type sca `
  -TargetFile tests\sca_demo\requirements-vulnerable.txt `
  -FailOn fixable `
  -OutDir tmp\ci-artifacts

$LASTEXITCODE
```

预期现象：

- 平台自动创建 SCA 任务。
- 脚本轮询任务直到完成。
- 脚本下载 JSON 报告。
- `tmp\ci-artifacts` 下生成摘要和报告文件。
- 因为样例中包含可修复依赖漏洞，退出码应为 `3`。

退出码说明：

| 退出码 | 含义 |
|---|---|
| `0` | 扫描成功，门禁通过 |
| `1` | 脚本调用或接口调用失败 |
| `2` | 任务失败、取消、超时 |
| `3` | 扫描成功，但命中质量门禁 |

## 7. 预期结果

### SCA-001 预期结果

- 任务创建成功。
- 任务最终状态为 `SUCCESS`。
- 详情页展示依赖漏洞列表。
- 每条漏洞至少包含包名、当前版本、漏洞 ID 和修复版本。

### SCA-002 预期结果

- JSON 报告可以下载。
- HTML/PDF 导出内容与页面详情保持一致。
- 报告可作为论文或答辩截图材料。

### SCA-003 预期结果

- 命令行输出报告保存路径。
- 摘要文件包含任务类型、任务状态、问题数量和门禁结果。
- `$LASTEXITCODE` 为 `3`，表示存在可修复依赖漏洞，CI/CD 门禁阻断通过。

## 8. 答辩展示话术

可以按下面顺序讲：

> 这里展示的是平台的 SCA 软件成分分析能力。与 SAST 检查源码缺陷、DAST 检查运行态 Web 漏洞不同，SCA 关注项目依赖组件本身是否存在公开漏洞。

> 我上传的是一个用于演示的 `requirements.txt`，里面包含 Django、Flask、requests、urllib3、PyYAML、Jinja2 等旧版本依赖。平台后端调用 `pip-audit` 进行扫描，并将扫描结果解析入库。

> 扫描完成后，详情页会展示漏洞 ID、影响依赖、当前版本和可修复版本。这里的修复版本可以直接作为研发整改依据，例如升级到不受影响的版本后重新执行扫描。

> 最后我用 CI/CD 脚本演示安全门禁。如果依赖漏洞存在可修复版本，脚本会返回非零退出码，从而阻断流水线继续发布。这说明平台不仅能在页面展示风险，也能接入自动化交付流程。

## 9. 截图建议

建议保留以下截图：

1. 新建扫描页面，扫描类型选择 `SCA`。
2. 上传 `requirements-vulnerable.txt` 的任务创建页面。
3. SCA 任务详情页，突出漏洞数量和可修复数量。
4. 漏洞列表，突出包名、当前版本、漏洞 ID、修复版本。
5. 报告导出页面或导出的 HTML/PDF 报告。
6. 命令行执行 `ci_security_scan.ps1` 后返回退出码 `3`。

## 10. 异常情况说明

### 10.1 任务失败：找不到 pip-audit

可能原因：

- 后端 Python 环境未安装 `pip-audit`。
- `SCA_SCANNER_CMD` 环境变量配置错误。

处理方式：

- 安装或修复 `pip-audit` 后重试。
- 答辩时说明平台链路已具备，失败点属于扫描器运行环境依赖问题。

### 10.2 任务失败：网络无法查询漏洞库

可能原因：

- 当前网络无法访问漏洞数据库。
- 代理或 DNS 配置异常。

处理方式：

- 切换网络后重新扫描。
- 使用历史扫描结果或预置报告作为降级展示。

### 10.3 PDF 导出失败

可能原因：

- Windows 环境缺少 WeasyPrint 依赖的 GTK/Pango 原生库。

处理方式：

- 改为展示 HTML 或 JSON 报告。
- 在论文中说明 PDF 导出依赖本地原生运行库，扫描与报告数据本身不受影响。

## 11. 论文表述参考

可在论文实验章节中表述为：

> 在 SCA 依赖漏洞扫描实验中，本文选取包含旧版本 Python 依赖的 `requirements.txt` 作为测试对象。系统接收依赖清单后调用 `pip-audit` 进行软件成分分析，并将漏洞 ID、影响组件、当前版本及修复版本写入数据库。实验结果表明，系统能够识别第三方依赖中的已知漏洞，并通过报告导出和 CI/CD 门禁机制支持后续整改与发布控制。

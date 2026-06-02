# CI/CD 集成说明

## 目标

本项目不搭建 Jenkins 或 GitLab Runner，而是提供可被流水线调用的脚本接口，用于证明平台具备安全质量门禁接入能力。

## 本地运行

```powershell
cd D:\ziliao\dev
$env:DEVSECOPS_USER="admin"
$env:DEVSECOPS_PASSWORD="your-password"
D:\anaconda\python.exe scripts\ci_security_scan.py --base-url http://127.0.0.1:5000/api --username $env:DEVSECOPS_USER --password $env:DEVSECOPS_PASSWORD --type sca --target-file requirements.txt --fail-on fixable --out-dir tmp\ci-artifacts
```

也可以使用 PowerShell 包装脚本：

```powershell
.\scripts\ci_security_scan.ps1 -Type sca -TargetFile requirements.txt -FailOn fixable
```

## 质量门禁

- 退出码 `0`：扫描完成且未命中门禁。
- 退出码 `1`：参数、登录、网络或接口调用失败。
- 退出码 `2`：平台任务失败、超时或取消。
- 退出码 `3`：扫描完成但命中门禁，例如存在高危问题或可修复依赖漏洞。

## 示例流水线

示例文件位于 `.github/workflows/security-scan.example.yml`。该文件只作为论文和答辩材料，不要求远程仓库真实运行。

## 截图建议

- PowerShell 执行脚本并显示退出码。
- 平台任务详情页展示 CI 创建的任务。
- `tmp\ci-artifacts` 中生成 JSON 报告和 summary 文件。

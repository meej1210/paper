# DevSecOps 管理员与 CI/CD 操作手册

> 适用项目：`D:\ziliao\dev`  
> 适用场景：本地演示、答辩前验收、管理员看板演示、CI/CD 安全门禁演示。

## 0. 最短命令清单

如果只是本地演示，按下面顺序执行即可。

### 0.1 初始化或确认管理员

```powershell
cd D:\ziliao\dev\backend
$env:ADMIN_USERNAME="admin@qq.com"
$env:ADMIN_EMAIL="admin@qq.com"
$env:ADMIN_PASSWORD="admin"
D:\anaconda\python.exe init_db.py
```

### 0.2 启动项目

```powershell
cd D:\ziliao\dev
powershell -ExecutionPolicy Bypass -File .\start_demo_env.ps1
```

### 0.3 登录地址

```text
http://127.0.0.1:5173/login
```

演示管理员：

```text
admin@qq.com / admin
```

管理员看板：

```text
http://127.0.0.1:5173/admin
```

### 0.4 设置 CI/CD 脚本账号

```powershell
cd D:\ziliao\dev
$env:DEVSECOPS_USER="admin@qq.com"
$env:DEVSECOPS_PASSWORD="admin"
```

### 0.5 跑 SCA 依赖漏洞门禁

```powershell
.\scripts\ci_security_scan.ps1 `
  -BaseUrl http://127.0.0.1:5000/api `
  -Type sca `
  -TargetFile backend\requirements.txt `
  -FailOn fixable `
  -OutDir tmp\ci-artifacts

$LASTEXITCODE
```

### 0.6 跑 SAST 代码安全门禁

```powershell
.\scripts\ci_security_scan.ps1 `
  -BaseUrl http://127.0.0.1:5000/api `
  -Type sast `
  -TargetFile tests\demo_sast.zip `
  -FailOn high `
  -OutDir tmp\ci-artifacts

$LASTEXITCODE
```

如果没有 `tests\demo_sast.zip`，把 `-TargetFile` 换成自己的 `.py`、`.zip` 或 `.tar.gz` 代码文件。

### 0.7 跑并发实验

```powershell
D:\anaconda\python.exe scripts\concurrency_probe.py `
  --base-url http://127.0.0.1:5000/api `
  --username $env:DEVSECOPS_USER `
  --password $env:DEVSECOPS_PASSWORD `
  --type sca `
  --target-file backend\requirements.txt `
  --count 10 `
  --parallel 5 `
  --out-dir tmp\concurrency-artifacts
```

### 0.8 最终验收

```powershell
cd D:\ziliao\dev
D:\anaconda\python.exe -m pytest backend\tests -q

cd D:\ziliao\dev\frontend
D:\nodejs\npm.cmd run build
```
## 1. 启动项目

### 1.1 一键启动

```powershell
cd D:\ziliao\dev
powershell -ExecutionPolicy Bypass -File .\start_demo_env.ps1
```

启动后重点访问：

| 服务 | 地址 | 用途 |
|---|---|---|
| 前端 | `http://127.0.0.1:5173` | 登录、创建扫描任务、查看报告、进入管理员看板 |
| 后端 API | `http://127.0.0.1:5000/api/health` | 健康检查 |
| Juice Shop 靶场 | `http://127.0.0.1:3000` | DAST 本地授权扫描目标 |

### 1.2 停止项目

```powershell
cd D:\ziliao\dev
powershell -ExecutionPolicy Bypass -File .\stop_demo_env.ps1
```

### 1.3 健康检查

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:5000/api/health -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:3000 -UseBasicParsing
```

如果前端或靶场端口不通，先查看：

```powershell
Get-Content D:\ziliao\dev\tmp\run-control\logs\api.err.log -Tail 80
Get-Content D:\ziliao\dev\tmp\run-control\logs\frontend.err.log -Tail 80
Get-Content D:\ziliao\dev\tmp\run-control\logs\worker.err.log -Tail 80
```

## 2. 管理员账号怎么登录

### 2.1 管理员生成规则

系统规则：**注册入口永远只创建普通用户，管理员由初始化脚本创建或修复**。

这样权限来源更清晰：

- 普通用户通过前端注册页创建，角色固定为 `user`。
- 管理员账号通过 `backend\init_db.py` 初始化，角色为 `admin`。
- 初始化脚本会按环境变量确保指定管理员存在；如果同名或同邮箱用户已存在，会刷新为管理员并更新密码。
- 当前演示管理员账号统一使用 `admin@qq.com / admin`，可用于前端登录、管理看板和 CI/CD 脚本。

### 2.2 创建或确认管理员

推荐在首次启动前执行一次初始化脚本：

```powershell
cd D:\ziliao\dev\backend

$env:ADMIN_USERNAME="admin@qq.com"
$env:ADMIN_EMAIL="admin@qq.com"
$env:ADMIN_PASSWORD="admin"

D:\anaconda\python.exe init_db.py
```

本手册约定的演示管理员为：

| 字段 | 默认值 |
|---|---|
| 用户名 | `admin@qq.com` |
| 邮箱 | `admin@qq.com` |
| 密码 | `admin` |

初始化完成后启动项目并登录：

```powershell
cd D:\ziliao\dev
powershell -ExecutionPolicy Bypass -File .\start_demo_env.ps1
```

登录地址：

```text
http://127.0.0.1:5173/login
```

管理员看板地址：

```text
http://127.0.0.1:5173/admin
```
### 2.3 确认当前账号是不是管理员

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"admin@qq.com","password":"admin"}'

$token = $login.data.access_token

Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/auth/me `
  -Headers @{ Authorization = "Bearer $token" }
```

如果返回内容里有：

```json
"role": "admin"
```

说明当前账号是管理员。

### 2.4 管理员看板能看什么

管理员访问：

```text
http://127.0.0.1:5173/admin
```

主要展示：

- 任务总数、成功数、失败数、运行/排队数。
- SAST / DAST / SCA 类型分布。
- SAST / DAST 风险等级摘要。
- SCA 漏洞数量和可修复数量。
- 最近审计日志。
- 最近 DAST 授权扫描目标、目标主机、解析 IP、命中策略。
- 运行状态：数据库、Redis、Celery 模式、DAST 扫描器状态。

## 3. 普通扫描怎么操作

### 3.1 创建 SAST 静态代码扫描

1. 登录前端。
2. 进入“扫描”页面。
3. 选择 `SAST`。
4. 上传 `.py`、`.zip` 或 `.tar.gz` 代码文件。
5. 选择扫描引擎：
   - `Bandit`：适合 Python 代码审计。
   - `Semgrep`：适合规则驱动扫描演示。
6. 创建任务后进入详情页查看结果。

### 3.2 创建 SCA 依赖漏洞扫描

1. 登录前端。
2. 进入“扫描”页面。
3. 选择 `SCA`。
4. 上传：
   - `requirements.txt`，或
   - 包含 `requirements.txt` 的 `.zip`。
5. 创建任务后查看依赖漏洞、漏洞 ID、可修复版本。

### 3.3 创建 DAST 动态扫描

1. 登录前端。
2. 进入“扫描”页面。
3. 选择 `DAST`。
4. 目标 URL 推荐填写：

```text
http://127.0.0.1:3000
```

5. 勾选：

```text
我确认该目标属于本地靶场或已获得授权的测试范围
```

6. 创建任务。
7. 在详情页查看：
   - 授权确认状态。
   - 目标主机。
   - 解析 IP。
   - 命中策略，例如 `localhost`、`private_network`、`allowed_host`。

注意：不勾选授权确认时，后端会拒绝创建 DAST 任务。

## 4. CI/CD 脚本怎么用

### 4.1 脚本位置

```text
D:\ziliao\dev\scripts\ci_security_scan.py
D:\ziliao\dev\scripts\ci_security_scan.ps1
```

脚本作用：模拟 CI/CD 流水线调用平台安全扫描能力。

脚本会自动完成：

1. 登录平台。
2. 创建 SAST 或 SCA 扫描任务。
3. 轮询任务状态。
4. 下载 JSON 报告。
5. 根据质量门禁返回退出码。

### 4.2 设置账号密码

先在 PowerShell 里设置环境变量：

```powershell
cd D:\ziliao\dev
$env:DEVSECOPS_USER="admin@qq.com"
$env:DEVSECOPS_PASSWORD="admin"
```

如果你的账号不是这个用户名和密码，替换成自己的。

### 4.3 运行 SCA 依赖漏洞门禁

推荐先用这个命令演示，因为项目自带 `backend\requirements.txt`：

```powershell
.\scripts\ci_security_scan.ps1 `
  -BaseUrl http://127.0.0.1:5000/api `
  -Type sca `
  -TargetFile backend\requirements.txt `
  -FailOn fixable `
  -OutDir tmp\ci-artifacts
```

含义：

- `-Type sca`：创建 SCA 任务。
- `-TargetFile backend\requirements.txt`：扫描 Python 依赖清单。
- `-FailOn fixable`：如果发现可修复依赖漏洞，则门禁失败。
- `-OutDir tmp\ci-artifacts`：输出报告和摘要。

### 4.4 运行 SAST 代码安全门禁

如果你有测试代码包，例如 `tests\demo_sast.zip`：

```powershell
.\scripts\ci_security_scan.ps1 `
  -BaseUrl http://127.0.0.1:5000/api `
  -Type sast `
  -TargetFile tests\demo_sast.zip `
  -FailOn high `
  -OutDir tmp\ci-artifacts
```

如果没有 `tests\demo_sast.zip`，可以换成自己的 `.py`、`.zip` 或 `.tar.gz` 文件。

### 4.5 直接运行 Python 版本

SCA：

```powershell
D:\anaconda\python.exe scripts\ci_security_scan.py `
  --base-url http://127.0.0.1:5000/api `
  --username $env:DEVSECOPS_USER `
  --password $env:DEVSECOPS_PASSWORD `
  --type sca `
  --target-file backend\requirements.txt `
  --fail-on fixable `
  --out-dir tmp\ci-artifacts
```

SAST：

```powershell
D:\anaconda\python.exe scripts\ci_security_scan.py `
  --base-url http://127.0.0.1:5000/api `
  --username $env:DEVSECOPS_USER `
  --password $env:DEVSECOPS_PASSWORD `
  --type sast `
  --target-file tests\demo_sast.zip `
  --fail-on high `
  --out-dir tmp\ci-artifacts
```

### 4.6 查看 CI/CD 退出码

脚本执行后查看：

```powershell
$LASTEXITCODE
```

退出码含义：

| 退出码 | 含义 | 说明 |
|---:|---|---|
| `0` | 通过 | 扫描成功，未命中门禁 |
| `1` | 脚本或接口错误 | 登录失败、参数错误、网络错误、接口异常 |
| `2` | 平台任务失败 | 扫描任务失败、超时或取消 |
| `3` | 质量门禁失败 | 扫描成功，但发现高危或可修复漏洞 |

注意：`3` 不代表脚本坏了，而是说明“安全门禁拦住了”。

### 4.7 输出文件

默认输出目录：

```text
D:\ziliao\dev\tmp\ci-artifacts
```

常见文件：

```text
sca_report_任务ID.json
sca_summary_任务ID.md
sast_report_任务ID.json
sast_summary_任务ID.md
```

这些文件可以作为论文或答辩截图材料。

## 5. 并发实验怎么用

脚本位置：

```text
D:\ziliao\dev\scripts\concurrency_probe.py
```

SCA 并发实验示例：

```powershell
D:\anaconda\python.exe scripts\concurrency_probe.py `
  --base-url http://127.0.0.1:5000/api `
  --username $env:DEVSECOPS_USER `
  --password $env:DEVSECOPS_PASSWORD `
  --type sca `
  --target-file backend\requirements.txt `
  --count 10 `
  --parallel 5 `
  --out-dir tmp\concurrency-artifacts
```

DAST 并发实验示例：

```powershell
D:\anaconda\python.exe scripts\concurrency_probe.py `
  --base-url http://127.0.0.1:5000/api `
  --username $env:DEVSECOPS_USER `
  --password $env:DEVSECOPS_PASSWORD `
  --type dast `
  --target-url http://127.0.0.1:3000 `
  --count 5 `
  --parallel 2 `
  --out-dir tmp\concurrency-artifacts
```

输出目录：

```text
D:\ziliao\dev\tmp\concurrency-artifacts
```

会生成：

```text
concurrency_sca_10.csv
concurrency_sca_10.md
```

或：

```text
concurrency_dast_5.csv
concurrency_dast_5.md
```

## 6. 答辩演示推荐流程

1. 启动项目：`start_demo_env.ps1`。
2. 登录管理员账号。
3. 创建 SAST 任务，展示代码安全问题。
4. 创建 SCA 任务，展示依赖漏洞和可修复版本。
5. 创建 DAST 任务，勾选授权确认，展示目标主机、解析 IP 和策略。
6. 打开管理员看板 `/admin`，展示全局任务、风险、审计和 DAST 授权目标。
7. 运行 CI/CD 脚本，展示质量门禁退出码。
8. 展示 `tmp\ci-artifacts` 和 `tmp\concurrency-artifacts` 中生成的报告。

## 7. 常见问题

### 7.1 看不到管理员入口

原因通常是当前账号不是管理员。

处理：

- 确认当前账号 `role` 是否为 `admin`。
- 管理员必须通过 `backend\init_db.py` 初始化或提升。
- 需要的话可以用数据库工具或脚本查看 `users` 表中的 `role` 字段。

### 7.2 CI/CD 登录失败

检查：

```powershell
$env:DEVSECOPS_USER
$env:DEVSECOPS_PASSWORD
```

再确认后端健康：

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:5000/api/health -UseBasicParsing
```

### 7.3 SCA 任务失败

可能原因：

- `pip-audit` 没安装。
- 网络无法查询漏洞库。
- 上传文件不是 `requirements.txt` 或包含它的 ZIP。

答辩时可以说明：SCA 结构、接口、报告链路已具备，演示环境可用预置依赖文件或预置报告降级展示。

### 7.4 DAST 创建失败

常见原因：

- 没勾选授权确认。
- URL 不是 `http` 或 `https`。
- 目标不是 localhost、私有网络或配置白名单。
- Juice Shop 没启动。

推荐演示目标：

```text
http://127.0.0.1:3000
```

## 8. 最终验收命令

```powershell
cd D:\ziliao\dev
D:\anaconda\python.exe -m pytest backend\tests -q

cd D:\ziliao\dev\frontend
D:\nodejs\npm.cmd run build
```

当前已验证过的结果：

- 后端测试：`66 passed`
- 前端构建：通过
- CI/CD 脚本语法检查：通过






# DAST 样本扩展落地方案

> 更新时间：2026-05-20
>
> 目标：解决当前 DAST 样本数量少、目标类型单一、实验数据覆盖不足的问题，同时保留“仅扫描本地靶场或明确授权目标”的安全边界，并为后续支持公网授权 URL 留出可控入口。

## 一、当前项目现状

### 1. 已具备的能力

- 后端已经接入真实 DAST 扫描器 Wapiti，任务创建入口为 `POST /api/dast/tasks`。
- DAST 任务已经有授权确认字段：`authorization_confirmed`。
- 后端会记录目标主机、解析 IP、命中策略和授权状态，包括 `target_host`、`target_ip`、`target_policy`。
- 默认配置只允许 `localhost`、`127.0.0.1`、私网地址或显式配置白名单目标。
- 管理员看板已经可以展示最近 DAST 授权目标。
- `docker-compose.yml` 当前只包含 Redis 和 Juice Shop。
- `start_demo_env.ps1` 当前只自动启动 Juice Shop，默认端口 `3000`，端口冲突时回退到 `3100`。

### 2. 当前样本不足

当前 `backend/reports` 中已有多个 DAST 报告，例如 `dast_40.json`、`dast_42.json`、`dast_43.json`、`dast_46.json`、`dast_48.json`、`dast_50.json`，但目标基本都是：

- `http://127.0.0.1:3000`
- `http://127.0.0.1:3100`

这些报告主要来自 Juice Shop，漏洞类型集中在：

- `Clickjacking Protection`
- `MIME Type Confusion`
- `Unencrypted Channels`
- `Content Security Policy Configuration`

这说明当前样本可以证明系统不是空壳，但还不足以支撑“多类型 Web 动态扫描实验”。

### 3. 当前前端阻塞点

统一新建扫描页中，DAST 提交逻辑会检查：

```ts
if (!dastForm.authorization_confirmed) {
  throw new Error("Please confirm the DAST target is local or explicitly authorized before submitting");
}
```

但当前 `dastForm` 没有定义 `authorization_confirmed` 字段，页面也没有勾选框。因此如果只通过统一扫描页创建 DAST，用户体验上会被前端阻塞。

涉及文件：

- `frontend/src/views/ScanCreateView.vue`
- `frontend/src/api/task.ts`
- `backend/app/api/dast.py`
- `backend/app/utils/validators.py`

## 二、总体方案

DAST 样本扩展分三层推进：

| 层级 | 目标 | 用途 | 风险控制 |
|---|---|---|---|
| 第一层 | 本地 Docker 靶场矩阵 | 增加可复现样本，支撑论文和答辩 | 仅监听 `127.0.0.1` 或本机端口 |
| 第二层 | 扫描预设与批量采样脚本 | 自动生成多轮 DAST 任务和统计数据 | 统一走后端授权校验 |
| 第三层 | 公网授权 URL 支持 | 后续扫描自有测试站点或已授权站点 | 默认关闭公网，显式白名单开启 |

原则：

- 不把随机公网网站加入默认可扫描列表。
- 不把 `DAST_ALLOW_PUBLIC_TARGETS` 默认改成 `true`。
- 公网 URL 只能作为“已授权目标”通过白名单显式配置。
- 本地靶场优先 Docker 化，保证实验可重复。
- 采样结果要能落到论文统计表和演示脚本中。

## 三、本地靶场矩阵

### 1. 第一批推荐靶场

| 靶场 | 建议端口 | 类型 | 推荐理由 | 入口 URL |
|---|---:|---|---|---|
| OWASP Juice Shop | 3000 / 3100 | 现代 Web / SPA | 当前已有，保留作为基线 | `http://127.0.0.1:3000` |
| DVWA | 3001 | 传统 Web 漏洞 | SQLi、XSS、命令执行、文件上传样本直观 | `http://127.0.0.1:3001` |
| OWASP WebGoat | 3002 | 训练型漏洞 | 覆盖认证、访问控制、注入等训练场景 | `http://127.0.0.1:3002/WebGoat` |
| Mutillidae II | 3003 | 传统 Web 综合靶场 | 漏洞类型丰富，适合补充 Wapiti 发现类型 | `http://127.0.0.1:3003` |
| OWASP crAPI | 3004 起 | API 安全靶场 | 后续补 API 场景，适合扩展 DAST 边界 | 视 crAPI compose 配置确定 |

参考项目：

- OWASP Juice Shop: <https://github.com/juice-shop/juice-shop>
- DVWA: <https://github.com/digininja/DVWA>
- OWASP WebGoat: <https://owasp.org/www-project-webgoat/>
- OWASP Mutillidae II: <https://github.com/webpwnized/mutillidae>
- OWASP crAPI: <https://owasp.org/www-project-crapi/>

### 2. 推荐实施顺序

第一阶段只加三个目标，控制复杂度：

1. 保留 Juice Shop。
2. 增加 DVWA。
3. 增加 Mutillidae II。

第二阶段再加：

1. WebGoat。
2. crAPI。

原因：

- DVWA 和 Mutillidae 更适合快速增加 Wapiti 可发现结果。
- WebGoat 有上下文课程和登录流程，可能需要额外处理认证。
- crAPI 更偏 API 安全，当前 Wapiti 配置不一定能充分覆盖，需要后续单独做 API 扫描策略。

## 四、Docker Compose 扩展

### 1. 当前配置

当前 `docker-compose.yml` 只有：

- `redis`
- `juice-shop`

### 2. 建议新增服务

建议扩展为：

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: devsecops-redis
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]

  juice-shop:
    image: bkimminich/juice-shop:latest
    container_name: devsecops-juice-shop
    ports:
      - "3000:3000"

  dvwa:
    image: vulnerables/web-dvwa:latest
    container_name: devsecops-dvwa
    ports:
      - "3001:80"

  mutillidae:
    image: citizenstig/nowasp:latest
    container_name: devsecops-mutillidae
    ports:
      - "3003:80"
```

说明：

- DVWA 和 Mutillidae 镜像可根据本机 Docker 拉取情况调整。
- 如果镜像拉取失败，优先使用官方仓库提供的 compose 方式独立启动，再把 URL 加入 DAST 预设。
- 端口只用于本地实验，不建议直接暴露到公网网卡。

### 3. WebGoat 和 crAPI 处理

WebGoat 推荐单独 profile：

```yaml
  webgoat:
    image: webgoat/webgoat:latest
    container_name: devsecops-webgoat
    ports:
      - "3002:8080"
```

crAPI 依赖组件更多，建议不要直接塞进主 `docker-compose.yml`，而是：

- 新增 `docker-compose.dast-labs.yml`。
- 或在文档中记录 crAPI 官方 compose 启动方式。
- 后端和前端只保存入口 URL 预设，不负责管理 crAPI 全部容器。

## 五、启动脚本改造

### 1. 当前问题

`start_demo_env.ps1` 只管理 Juice Shop，一个 DAST target 被写入 state：

```powershell
dast_target = $dastTarget
```

这不适合多靶场。

### 2. 建议改造目标

启动脚本输出多个目标：

```json
{
  "urls": {
    "frontend": "http://127.0.0.1:5173",
    "backend_health": "http://127.0.0.1:5000/api/health",
    "dast_targets": [
      {
        "name": "Juice Shop",
        "url": "http://127.0.0.1:3000",
        "type": "modern-web"
      },
      {
        "name": "DVWA",
        "url": "http://127.0.0.1:3001",
        "type": "classic-web"
      },
      {
        "name": "Mutillidae II",
        "url": "http://127.0.0.1:3003",
        "type": "classic-web"
      }
    ]
  }
}
```

### 3. 启动脚本验收标准

- 运行 `.\start_demo_env.ps1` 后至少输出 2 个可用 DAST 目标。
- 端口冲突时能说明哪个靶场未启动，而不是整个环境失败。
- `tmp/run-control/demo-runtime.json` 中记录所有可用目标。
- `.\stop_demo_env.ps1` 能停止由脚本启动的容器或进程。

## 六、前端改造

### 1. 修复授权确认字段

在 `frontend/src/views/ScanCreateView.vue` 中，`dastForm` 增加：

```ts
authorization_confirmed: false
```

DAST 表单增加勾选框：

```html
<label class="authorization-check">
  <input v-model="dastForm.authorization_confirmed" type="checkbox" />
  <span>我确认该目标属于本地靶场或已获得授权的测试范围</span>
</label>
```

提交按钮可以在 DAST 未勾选时禁用，或保持提交后提示错误。建议禁用按钮并保留错误提示。

### 2. 增加靶场预设

在 DAST 目标配置中新增预设列表：

```ts
const dastTargetPresets = [
  {
    name: "Juice Shop",
    task_name: "juice-shop-dast",
    target_url: "http://127.0.0.1:3000",
    timeout: 90,
    description: "本地 Juice Shop 动态扫描"
  },
  {
    name: "DVWA",
    task_name: "dvwa-dast",
    target_url: "http://127.0.0.1:3001",
    timeout: 120,
    description: "本地 DVWA 传统 Web 漏洞扫描"
  },
  {
    name: "Mutillidae II",
    task_name: "mutillidae-dast",
    target_url: "http://127.0.0.1:3003",
    timeout: 120,
    description: "本地 Mutillidae II 综合靶场扫描"
  },
  {
    name: "自定义授权 URL",
    task_name: "authorized-url-dast",
    target_url: "",
    timeout: 120,
    description: "已获得授权的自定义目标"
  }
];
```

页面交互：

- 选择预设后自动填入任务名、URL、超时时间和描述。
- 自定义授权 URL 允许用户手工输入。
- DAST 区域固定显示授权提醒。
- 目标摘要中显示当前目标 URL 和授权状态。

### 3. 前端验收标准

- 用户能选择 Juice Shop、DVWA、Mutillidae 预设。
- 未勾选授权确认时不能提交 DAST。
- 勾选后能正常向后端提交 `authorization_confirmed: true`。
- 提交成功后进入任务详情页。
- 任务详情页能展示目标 URL、目标主机、解析 IP、命中策略和授权状态。

## 七、后端配置与策略

### 1. 继续保留默认安全边界

当前配置应保持：

```python
DAST_ALLOWED_HOSTS = "127.0.0.1,localhost"
DAST_ALLOW_PRIVATE_NETWORKS = "true"
DAST_ALLOW_PUBLIC_TARGETS = "false"
```

这代表：

- 本地靶场允许扫描。
- 私网测试环境允许扫描。
- 公网默认不允许扫描。

### 2. 本地靶场不需要放开公网

DVWA、Mutillidae、WebGoat、crAPI 都通过 `127.0.0.1` 或私网地址访问，因此不会破坏当前授权模型。

### 3. 公网 URL 后续支持方案

后续如果要支持公网 URL，不建议直接设置：

```powershell
$env:DAST_ALLOW_PUBLIC_TARGETS="true"
```

推荐方案是显式白名单：

```powershell
$env:DAST_ALLOWED_HOSTS="127.0.0.1,localhost,security-test.example.com"
$env:DAST_ALLOW_PUBLIC_TARGETS="false"
```

这样只有 `security-test.example.com` 被允许，其他公网域名仍然拒绝。

### 4. 公网 URL 创建流程

公网目标必须满足：

- 目标属于本人、本团队或已获得书面授权。
- 域名或 IP 被加入 `DAST_ALLOWED_HOSTS`。
- 用户创建任务时勾选授权确认。
- 审计日志记录 `target_url`、`target_host`、`target_ip`、`target_policy`、`authorization_confirmed`。
- 管理员看板可查看该目标。

建议新增文档字段：

| 字段 | 说明 |
|---|---|
| `target_owner` | 目标归属方，例如个人测试站、课程靶场、企业授权环境 |
| `authorization_note` | 授权说明，例如“本人自有域名”或“课程实验环境” |
| `allowed_until` | 授权有效期，后续可选 |

第一版可以只记录在任务描述中，后续再考虑加数据库字段。

### 5. 公网 URL 风险控制

必须避免：

- 默认允许任意公网目标。
- 前端放一个“公网扫描”按钮绕过白名单。
- 在论文或演示中扫描无授权第三方网站。
- 把 `example.com`、搜索出来的随机网站当作成功样本。

可以保留的公网相关测试：

- `https://example.com` 默认被拒绝，用作失败场景。
- 显式白名单域名成功创建任务，用作授权公网目标样例。
- 未勾选授权确认时拒绝创建任务。

## 八、Wapiti 扫描参数分档

### 1. 当前配置

当前 Wapiti 命令由 `backend/app/services/dast_service.py` 构造，主要参数来自：

- `DAST_DEFAULT_SCOPE`
- `DAST_MODULES`
- `DAST_MAX_SCAN_TIME`
- `DAST_MAX_ATTACK_TIME`
- `DAST_REQUEST_TIMEOUT`

默认偏保守：

```text
scope = folder
modules = common
max scan time = 60
max attack time = 15
```

### 2. 建议增加扫描模式

| 模式 | 用途 | 超时 | 模块 | 说明 |
|---|---|---:|---|---|
| `quick` | 页面演示 | 60-90 秒 | `common` | 结果稳定，适合答辩演示 |
| `lab` | 论文采样 | 180-300 秒 | 根据 Wapiti 支持扩展 | 用于生成更丰富的实验数据 |
| `baseline` | 对照实验 | 固定 120 秒 | `common` | 多靶场同参数横向比较 |

第一版不一定要立刻改后端数据模型，可以先通过环境变量控制：

```powershell
$env:DAST_MAX_SCAN_TIME="180"
$env:DAST_MAX_ATTACK_TIME="45"
$env:DAST_MODULES="common"
```

后续再把扫描模式做成前端选项。

### 3. 注意事项

- 扫描时间越长，演示等待越久，不适合现场临时跑。
- 靶场越复杂，越容易出现登录态、爬虫深度和超时问题。
- 论文采样应该固定参数，避免不同样本不可比。

## 九、批量采样脚本

### 1. 目标

新增脚本自动对多个授权目标创建 DAST 任务，等待结果完成，并输出实验统计表。

建议文件：

- `scripts/run_dast_lab_samples.py`
- 或 `scripts/run_dast_lab_samples.ps1`

### 2. 输入参数

```text
--base-url http://127.0.0.1:5000/api
--username admin
--password your-password
--targets-file 主文档层/dast_targets.local.json
--rounds 3
--timeout 180
--out-dir tmp/dast-lab-samples
```

### 3. targets 文件示例

```json
[
  {
    "name": "juice-shop",
    "url": "http://127.0.0.1:3000",
    "description": "本地 Juice Shop 基线扫描"
  },
  {
    "name": "dvwa",
    "url": "http://127.0.0.1:3001",
    "description": "本地 DVWA 传统 Web 漏洞扫描"
  },
  {
    "name": "mutillidae",
    "url": "http://127.0.0.1:3003",
    "description": "本地 Mutillidae II 综合靶场扫描"
  }
]
```

### 4. 脚本行为

1. 登录平台获取 token。
2. 读取 targets 文件。
3. 对每个目标按 `rounds` 创建 DAST 任务。
4. 创建请求必须带 `authorization_confirmed: true`。
5. 轮询任务详情直到 `SUCCESS`、`FAILED`、`TIMEOUT` 或 `CANCELLED`。
6. 下载 JSON 报告。
7. 汇总耗时、问题数、严重度分布、漏洞类型分布、爬取页面数。
8. 输出 Markdown 和 JSON 两份统计结果。

### 5. 输出表格示例

| 靶场 | 轮次 | 状态 | 耗时 ms | 爬取页面 | 问题数 | 高危 | 中危 | 低危 | 主要类型 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| Juice Shop | 1 | SUCCESS | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 |
| DVWA | 1 | SUCCESS | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 |
| Mutillidae II | 1 | SUCCESS | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 | 记录实测 |

## 十、论文与答辩样本设计

### 1. 推荐样本规模

最小可用：

- 3 个靶场
- 每个靶场 3 轮
- 共 9 个 DAST 任务

较完整：

- 5 个靶场
- 每个靶场 3 轮
- 共 15 个 DAST 任务

### 2. 推荐统计维度

- 靶场名称
- 目标 URL
- 扫描模式
- 扫描耗时
- 任务状态
- 爬取页面数量
- 漏洞总数
- 严重度分布
- 漏洞类型分布
- 是否本地目标
- 是否公网授权目标
- 命中策略：`localhost`、`private_network`、`allowed_host`、`public_allowed`

### 3. 推荐论文表述

可以写：

> 为避免动态扫描误用于未授权目标，系统默认仅允许本地、私网或白名单目标创建 DAST 任务。实验阶段通过 Docker 部署多个本地漏洞靶场，构建可复现的动态扫描样本池；对于公网目标，系统采用显式白名单和授权确认机制，默认不开放任意公网扫描。

不要写：

> 系统可以扫描任意公网网站。

## 十一、公网 URL 后续落地路线

### 1. 第一版：环境变量白名单

适合当前项目，改动最小。

配置方式：

```powershell
$env:DAST_ALLOWED_HOSTS="127.0.0.1,localhost,security-test.example.com"
$env:DAST_ALLOW_PUBLIC_TARGETS="false"
```

优点：

- 不需要改数据库。
- 不需要新增管理员配置页面。
- 后端已有逻辑可以直接复用。

缺点：

- 修改白名单需要重启服务。
- 授权说明只能写在任务描述或文档中。

### 2. 第二版：管理员维护授权目标

新增数据库表：

```text
dast_authorized_targets
```

字段建议：

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `host` | 授权域名或 IP |
| `owner` | 目标归属 |
| `authorization_note` | 授权说明 |
| `allowed_until` | 授权有效期 |
| `enabled` | 是否启用 |
| `created_by` | 创建管理员 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

后端校验顺序：

1. localhost。
2. 显式环境变量白名单。
3. 数据库授权目标表。
4. 私网策略。
5. 是否允许全部公网。

### 3. 第三版：公网目标授权审计

管理员页面增加：

- 授权目标列表。
- 新增授权目标。
- 禁用授权目标。
- 查看最近扫描记录。
- 查看授权过期目标。

任务详情增加：

- 授权来源：环境变量白名单 / 管理员授权表 / 私网 / 本地。
- 授权说明。
- 授权有效期。

## 十二、开发任务拆分

### 任务 1：修复 DAST 前端授权确认

涉及文件：

- `frontend/src/views/ScanCreateView.vue`
- `frontend/src/api/task.ts`

验收：

- DAST 表单有授权确认勾选框。
- 未勾选不能提交。
- 勾选后 payload 包含 `authorization_confirmed: true`。

### 任务 2：新增 DAST 靶场预设

涉及文件：

- `frontend/src/views/ScanCreateView.vue`

验收：

- 能一键填入 Juice Shop、DVWA、Mutillidae。
- 支持自定义授权 URL。
- 目标摘要显示清晰。

### 任务 3：扩展 Docker 靶场

涉及文件：

- `docker-compose.yml`
- `start_demo_env.ps1`
- `stop_demo_env.ps1`

验收：

- 至少 Juice Shop、DVWA、Mutillidae 可启动。
- 启动脚本输出多个 DAST URL。
- 停止脚本能清理启动脚本管理的服务。

### 任务 4：批量 DAST 实验脚本

涉及文件：

- `scripts/run_dast_lab_samples.py`
- `主文档层/dast_targets.local.json`

验收：

- 能批量创建 DAST 任务。
- 自动下载报告。
- 输出 Markdown 统计表。

### 任务 5：公网授权 URL 支持

第一阶段只做文档和环境变量示例，不改数据库。

涉及文件：

- `主文档层/a05-项目操作手册.md`
- `主文档层/a09-验证边界与环境说明.md`
- `主文档层/a10-失败场景说明.md`
- `主文档层/a12-实验统计与案例.md`

验收：

- 文档说明如何配置 `DAST_ALLOWED_HOSTS`。
- 文档说明默认不允许任意公网。
- 文档包含失败样例和授权成功样例。

## 十三、验收清单

### 1. 功能验收

- DAST 页面可以选择多个靶场预设。
- DAST 页面必须勾选授权确认才能提交。
- 后端拒绝未授权公网 URL。
- 后端允许本地靶场 URL。
- 后端允许显式加入白名单的公网 URL。
- 管理员看板能看到 DAST 授权目标。

### 2. 实验验收

- 至少 3 个本地靶场成功扫描。
- 每个靶场至少保留 3 轮扫描任务。
- `backend/reports` 中有对应 DAST JSON 报告。
- `主文档层/a12-实验统计与案例.md` 更新多靶场统计。
- 答辩演示脚本中能展示多靶场 DAST 样本。

### 3. 安全验收

- `https://example.com` 在默认配置下仍然被拒绝。
- 未勾选 `authorization_confirmed` 时被拒绝。
- 不允许通过前端绕过后端白名单。
- 公网 URL 必须通过 `DAST_ALLOWED_HOSTS` 或后续授权目标表显式允许。

## 十四、推荐执行顺序

1. 修复前端授权确认字段。
2. 增加 DAST 靶场预设。
3. 扩展 Docker 本地靶场。
4. 改造启动脚本输出多目标。
5. 增加批量采样脚本。
6. 跑 3 个靶场各 3 轮，更新实验统计。
7. 补充公网授权 URL 文档。
8. 后续再做管理员维护授权目标表。

## 十五、最终结论

当前项目应优先把 DAST 样本池从单一 Juice Shop 扩展为本地多靶场矩阵，用 Docker 保证可复现，用批量脚本生成论文统计数据。公网 URL 支持可以保留，但必须走显式授权白名单，不能默认开放任意公网扫描。

推荐短期目标：

- Juice Shop + DVWA + Mutillidae。
- 每个靶场 3 轮。
- 形成 9 个 DAST 成功样本。
- 更新实验统计和答辩演示脚本。

推荐中期目标：

- 增加 WebGoat 和 crAPI。
- 增加扫描模式。
- 增加公网授权 URL 白名单示例。

推荐长期目标：

- 增加管理员授权目标表。
- 管理员页面维护公网授权目标。
- 任务报告中展示授权来源和授权说明。

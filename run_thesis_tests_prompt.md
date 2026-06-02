# 任务：跑测试 + 出图，给毕业论文第 6 章补量化数据

你是一名工程师，需要为一份本科毕业设计论文的「第 6 章 系统测试与结果分析」补齐量化数据。论文的代码仓库就在 `/workspace/dev`。论文目前的痛点是：表 6-2/6-3/6-4 只有"测试覆盖"、"未出现阻断"这类描述性结论，**没有任何真实数字**。你的任务是**真实运行系统、采集真实数据、生成图表与表格**，**严禁编造数据**。

---

## 1. 项目已知信息（直接照搬，避免你重新探索）

- 后端：`/workspace/dev/backend`，Flask 入口 `run.py`（默认 `http://localhost:5000`），用 Celery + Redis；启动脚本见 `start_demo_env.ps1`（Windows）或 `docker-compose.yml`（Redis 已经声明为 service）。
- 已存在的测试脚本（**先看再决定要不要造轮子**）：
  - `/workspace/dev/scripts/concurrency_probe.py`——已经实现并发任务提交 + 响应时间统计，输出 CSV，**这是性能测试的主力**。
  - `/workspace/dev/scripts/ci_security_scan.py`——封装了登录、建任务、上传文件、轮询、下载报告，**所有 HTTP 调用都可以复用**。
  - `/workspace/dev/backend/smoke_test*.py`——一组冒烟脚本，覆盖了 auth、tasks、dast、sast、async、cancel、audit 等接口，**功能测试用例的天然清单**，直接统计跑通了几个、失败了几个即可。
  - `/workspace/dev/backend/verify_*.py`、`real_integration_check.py`——更完整的集成验证。
- 测试样本：`/workspace/dev/tests/` 下有 `sql_and_injection_demo.py`、`weak_crypto.py`、`unsafe_deserialization.py`、`dangerous_ops.py`、`web_misconfig.py`、`sca_demo/`，**SAST 和 SCA 直接拿这些当扫描目标**。
- DAST 目标：docker-compose 里已经声明了 juice-shop（3000）、dvwa（3001）、webgoat（3002）、mutillidae（3003），**任选一个起来就能扫**（juice-shop 启动最快）。
- 输出位置：图片放 `/workspace/dev/figures/`，CSV 和 markdown 摘要也放同目录。

## 2. 准备工作

1. 启动依赖：`docker compose up -d redis juice-shop`（其它三个 DAST 靶场可选）。
2. 后端环境：`cd /workspace/dev/backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`（如果还没装）。
3. 初始化 DB：`python init_db.py`。
4. 启动 API：`python run.py`（后台跑）。
5. 启动 Celery worker：`celery -A celery_worker.celery worker -l info`（后台跑）。
6. 注册一个测试用户（`smoke_test.py` 里有现成代码可参考），拿到 token 备用。

**所有进程都用 `run_in_background=true` 后台启动**，不要阻塞主流程。启动后用 `curl http://localhost:5000/api/health` 验证。

## 3. 要采集的数据（对应论文表 6-2/6-3/6-4）

### 3.1 功能测试（表 6-2）
跑遍 `backend/` 下的 `smoke_test*.py` 和 `verify_*.py`，按模块分桶统计：

| 模块 | 用例数 | 通过 | 失败 | 失败原因摘要 |
|---|---|---|---|---|
| 用户认证 | … | … | … | … |
| 扫描任务管理 | … | … | … | … |
| SAST | … | … | … | … |
| DAST | … | … | … | … |
| SCA | … | … | … | … |
| 报告导出 | … | … | … | … |
| 审计日志 | … | … | … | … |
| 管理看板 | … | … | … | … |
| AI 辅助分析 | … | … | … | … |

输出 CSV：`figures/test_functional.csv`；柱状图：`figures/fig_6_2_functional.png`（横轴模块、纵轴用例数，叠加通过/失败两色）。

### 3.2 安全性测试（表 6-3）
按下面四类各跑 3-5 个 case，**用 Python `requests` 直接发请求**，记录 HTTP 状态码和响应里的错误信息：
- **越权**：用户 A 的 token 去访问用户 B 的任务详情/报告（应返回 403）；普通用户调 `/api/admin/*`（应 403）。
- **注入**：登录 / 搜索 / 任务查询接口塞 `' OR '1'='1`、`<script>alert(1)</script>` 等 payload，看是否被参数化处理或被过滤。
- **文件上传**：上传超大文件、上传 `.exe`、上传 zip slip 路径（`../../etc/passwd`）、上传空文件。
- **Token 失效**：过期 token、伪造签名 token、空 Authorization 头、错误 Bearer 格式。

输出 CSV：`figures/test_security.csv`，字段 `category, case_name, payload_summary, http_status, expected, actual, passed`。配一张堆叠柱状图：`figures/fig_6_3_security.png`（横轴四类、纵轴用例数，绿色=拦截成功、红色=未拦截）。

### 3.3 性能测试（表 6-4，最关键）
直接调用 `/workspace/dev/scripts/concurrency_probe.py`，跑下面几组：

**(a) 接口响应时间（单请求 P50/P95）**
对下面接口各连续打 50 次，记录 `time.perf_counter()` 差值（毫秒）：
- `POST /api/auth/login`
- `GET /api/tasks?page=1&page_size=20`（任务列表分页）
- `GET /api/tasks/{id}`（任务详情）
- `GET /api/metrics/dashboard`（管理看板）
- `GET /api/audit/logs?page=1`（审计日志）
- `GET /api/tasks/{id}/report?format=pdf`（PDF 报告导出）

输出表：`figures/test_perf_api.csv`（列：endpoint, n, min, p50, p95, max, mean），图：`figures/fig_6_4a_api_latency.png`（横轴接口、纵轴毫秒、画 P50 和 P95 两根柱）。

**(b) 扫描耗时**
分别对 `tests/sql_and_injection_demo.py`、`tests/sca_demo/` 跑 SAST 和 SCA 各 5 次；对 juice-shop（http://localhost:3000）跑 DAST 3 次（timeout 30s 即可，不必扫完）。
输出表：`figures/test_perf_scan.csv`（task_type, target, run_idx, duration_ms），图：`figures/fig_6_4b_scan_duration.png`（三个分组的箱线图或柱状图）。

**(c) 并发能力**
用 `concurrency_probe.py` 跑 1 / 5 / 10 / 20 个并发任务，记录任务创建成功率和平均创建响应时间。
输出表：`figures/test_perf_concurrency.csv`，图：`figures/fig_6_4c_concurrency.png`（双 Y 轴：左 = 成功率%、右 = 平均响应 ms）。

### 3.4 兼容性测试（表 6-4 续）
**老实声明：浏览器版本与 GUI 加载时间需要在用户本机的真实浏览器里测，命令行环境无法替代。** 你可以做的部分：
- 用 `requests` 测前端构建产物的 HTTP 加载时间（如果 `frontend/dist/` 已经 build），记 HTML、首屏 JS、首屏 CSS 的字节大小和下载耗时。
- 在 markdown 摘要里**留一张占位表**：`Chrome / Edge / Firefox` 三列，写明"待用户在本机浏览器中测试并填入版本号与 DOMContentLoaded 时间，建议用 Lighthouse 或 F12 Performance Tab 截图"。

不要瞎填浏览器版本号。

## 4. 输出物清单（最终交付）

全部放在 `/workspace/dev/figures/` 下：

1. **CSV 原始数据**（6 个）：
   - `test_functional.csv`
   - `test_security.csv`
   - `test_perf_api.csv`
   - `test_perf_scan.csv`
   - `test_perf_concurrency.csv`
   - `test_compat_assets.csv`

2. **PNG 图片**（6-7 张，宽 1200px、DPI 150、风格简洁，不要花哨配色）：
   - `fig_6_2_functional.png`
   - `fig_6_3_security.png`
   - `fig_6_4a_api_latency.png`
   - `fig_6_4b_scan_duration.png`
   - `fig_6_4c_concurrency.png`
   - `fig_6_4d_compat_assets.png`（可选）

3. **一份总结 markdown：`figures/THESIS_TEST_SUMMARY.md`**
   按论文章节顺序组织，每节包含：
   - 一张表格（直接可粘贴进 Word）
   - 1-3 句结论性文字（"P95 < XXXms"、"在 20 并发下成功率 X%"、"X 个用例中 Y 个被拦截"这种**带数字**的结论）
   - 引用对应的图片文件名
   末尾附**"测试环境"小节**（CPU、内存、OS、Python 版本、Docker 版本、各服务进程数），方便论文写"6.1 测试环境"。

## 5. 严格约束

- ❗**禁止编造任何数字**。某项测不到就在 markdown 里写明"未实测，原因：XXX，建议人工补测"。
- 📊 图片用 `matplotlib`，不要用 seaborn 或 plotly，避免依赖问题；中文字体设置 `plt.rcParams['font.sans-serif'] = ['DejaVu Sans']`（论文图例可以全英文，反而更专业）。
- 🔁 每个数据点至少跑 3 次取均值/中位数，单次结果不可信。
- 🪵 跑测过程中产生的 raw log 保留到 `figures/raw_logs/` 下，方便答辩时回溯。
- 🚦 如果某个进程起不来（比如 docker 拉不到 juice-shop），先尝试 fallback（用 `http://example.com` 当 DAST 目标），然后在 summary 里说明。
- 🔇 不要修改后端业务代码；如果发现 bug，记到 summary 末尾的"测试中发现的问题"小节，不要顺手 fix。
- ⏱ 整体预算 60-90 分钟。超时就先交付已完成部分，未完成项在 summary 里列出。

## 6. 开始前请先汇报

读完本提示词后，先用 2-3 句话告诉我：
1. 你打算先跑哪一组测试（建议顺序：环境就绪验证 → 功能 → 安全 → 性能 → 兼容性）；
2. 哪些子任务你判断不可行、原因是什么；
3. 预计总耗时。

得到我确认后再开始执行，避免方向跑偏。
